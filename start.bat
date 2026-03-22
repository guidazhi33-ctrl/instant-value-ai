@echo off
chcp 65001 > nul
echo.
echo  ╔══════════════════════════════════════╗
echo  ║     InstantValue AI  起動中...       ║
echo  ║     GPT-4o Vision  /  PWA対応        ║
echo  ╚══════════════════════════════════════╝
echo.

python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [エラー] Python が見つかりません。
    echo https://www.python.org からインストールしてください。
    pause & exit /b 1
)

if not exist ".venv" (
    echo [1/4] 仮想環境を作成中...
    python -m venv .venv
)

echo [2/4] パッケージをインストール中...
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt

echo [3/4] アイコン生成中...
python generate_icons.py

REM APIキー確認
findstr /C:"YOUR_OPENAI_API_KEY_HERE" .env > nul
if %errorlevel% equ 0 (
    echo.
    echo  ⚠  .env の OPENAI_API_KEY を設定してください！
    echo     メモ帳で .env を開いて YOUR_OPENAI_API_KEY_HERE を
    echo     実際のキーに書き換えてから再起動してください。
    echo.
    pause & exit /b 1
)

echo [4/4] サーバー起動中...
echo.

REM PCのIPアドレスを表示
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4"') do (
    set IP=%%a
    goto :found
)
:found
set IP=%IP: =%
echo  ✅  PC ブラウザ:    http://localhost:5000
echo  📱  iPhone(Safari): http://%IP%:5000
echo.
echo  iPhoneでの「アプリ化」手順:
echo  1. SafariでURLを開く
echo  2. 下の共有ボタン →「ホーム画面に追加」
echo  3. アイコンをタップするとアプリとして起動！
echo.
echo  ※ iPhoneとPCが同じWiFiに繋がっている必要があります
echo  ※ このウィンドウを閉じるとアプリが停止します
echo.
start "" "http://localhost:5000"
python app.py
pause
