import os
import json
import base64
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, render_template, g
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

# ─── OpenAI ───────────────────────────────────────────────────────────────────
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

SYSTEM_PROMPT = """
You are an expert flea-market pricing assistant for Japanese platforms.
Given an image of an item, respond ONLY with a minified JSON object (no markdown, no prose) with these keys:
  - productName (string, Japanese)
  - minPrice (integer, JPY estimate low)
  - maxPrice (integer, JPY estimate high)
  - description (string, Japanese — compelling, 100–200 chars, flea-market style)
  - category (string, e.g. "家電","ファッション","おもちゃ","本・メディア","スポーツ","インテリア","その他")
  - tags (array of 3–6 Japanese keyword strings)
Price based on current Japanese secondhand market. No text outside JSON.
"""

# ─── SQLite ───────────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "history.db"

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(str(DB_PATH))
        db.row_factory = sqlite3.Row
    return db

def init_db():
    with sqlite3.connect(str(DB_PATH)) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT    NOT NULL,
                min_price    INTEGER NOT NULL DEFAULT 0,
                max_price    INTEGER NOT NULL DEFAULT 0,
                description  TEXT    NOT NULL DEFAULT '',
                category     TEXT    NOT NULL DEFAULT '',
                tags         TEXT    NOT NULL DEFAULT '[]',
                timestamp    TEXT    NOT NULL,
                image_b64    TEXT
            )
        """)

@app.teardown_appcontext
def close_db(_):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True)
    image_b64_full = data.get("image")
    if not image_b64_full:
        return jsonify({"error": "画像がありません"}), 400

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key == "YOUR_OPENAI_API_KEY_HERE":
        return jsonify({"error": ".env の OPENAI_API_KEY を設定してください"}), 500

    if "," in image_b64_full:
        header, b64data = image_b64_full.split(",", 1)
        mime_type = header.split(":")[1].split(";")[0]
    else:
        b64data = image_b64_full
        mime_type = "image/jpeg"

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=512,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{b64data}",
                                "detail": "high",
                            },
                        },
                        {"type": "text", "text": "この商品の情報と相場価格をJSONで返してください。"},
                    ],
                },
            ],
        )

        content = response.choices[0].message.content or ""
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        item = json.loads(content)

        now = datetime.now().isoformat()
        db = get_db()
        cur = db.execute(
            """INSERT INTO items
               (product_name, min_price, max_price, description, category, tags, timestamp, image_b64)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                item.get("productName", ""),
                int(item.get("minPrice", 0)),
                int(item.get("maxPrice", 0)),
                item.get("description", ""),
                item.get("category", "その他"),
                json.dumps(item.get("tags", []), ensure_ascii=False),
                now,
                image_b64_full,
            ),
        )
        db.commit()
        item["id"] = cur.lastrowid
        item["timestamp"] = now
        return jsonify(item)

    except json.JSONDecodeError:
        return jsonify({"error": "AI応答の解析に失敗しました。もう一度試してください。"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/history", methods=["GET"])
def history():
    db = get_db()
    rows = db.execute("SELECT * FROM items ORDER BY timestamp DESC LIMIT 100").fetchall()
    return jsonify([
        {
            "id": r["id"],
            "productName": r["product_name"],
            "minPrice": r["min_price"],
            "maxPrice": r["max_price"],
            "description": r["description"],
            "category": r["category"],
            "tags": json.loads(r["tags"]),
            "timestamp": r["timestamp"],
            "image_b64": r["image_b64"],
        }
        for r in rows
    ])

@app.route("/api/history/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    db = get_db()
    db.execute("DELETE FROM items WHERE id = ?", (item_id,))
    db.commit()
    return jsonify({"ok": True})

@app.route("/api/history", methods=["DELETE"])
def delete_all():
    db = get_db()
    db.execute("DELETE FROM items")
    db.commit()
    return jsonify({"ok": True})

if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", 5000))
    print(f"\n✅  InstantValue AI 起動中 (GPT-4o Vision) — port {port}")
    app.run(debug=False, host="0.0.0.0", port=port)
