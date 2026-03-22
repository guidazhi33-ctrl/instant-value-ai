"""
アプリアイコンを生成するスクリプト。
Pillowが必要: pip install pillow
"""
import struct, zlib, math

def create_png(size):
    """Pure Python で neon green スキャンアイコン PNG を生成"""
    img = [[(10, 10, 15, 255)] * size for _ in range(size)]  # bg #0a0a0f

    cx, cy = size / 2, size / 2
    r = size * 0.35
    neon = (0, 255, 156, 255)
    neon_dim = (0, 255, 156, 60)

    def draw_circle(px, py, radius, color, fill=False):
        for y in range(size):
            for x in range(size):
                d = math.sqrt((x - px) ** 2 + (y - py) ** 2)
                if fill:
                    if d <= radius:
                        img[y][x] = color
                else:
                    if abs(d - radius) < max(1.5, size * 0.01):
                        img[y][x] = color

    def draw_rect_border(x0, y0, x1, y1, color, w=2):
        for x in range(x0, x1):
            for t in range(w):
                if 0 <= x < size:
                    if 0 <= y0 + t < size: img[y0 + t][x] = color
                    if 0 <= y1 - 1 - t < size: img[y1 - 1 - t][x] = color
        for y in range(y0, y1):
            for t in range(w):
                if 0 <= y < size:
                    if 0 <= x0 + t < size: img[y][x0 + t] = color
                    if 0 <= x1 - 1 - t < size: img[y][x1 - 1 - t] = color

    def draw_corner(ox, oy, dx, dy, length, color, w=3):
        for i in range(length):
            for t in range(w):
                nx, ny = ox + dx * i, oy + t * (1 if dy == 0 else 0)
                if 0 <= nx < size and 0 <= ny < size:
                    img[ny][nx] = color
            for t in range(w):
                nx, ny = ox + t * (1 if dx == 0 else 0), oy + dy * i
                if 0 <= nx < size and 0 <= ny < size:
                    img[ny][nx] = color

    bw = int(size * 0.38)
    bx0, by0 = int(cx - bw), int(cy - bw)
    bx1, by1 = int(cx + bw), int(cy + bw)
    clen = int(size * 0.12)
    lw = max(2, int(size * 0.025))

    # Corner brackets
    for (ox, oy, dx, dy) in [
        (bx0, by0, 1, 1),
        (bx1, by0, -1, 1),
        (bx0, by1, 1, -1),
        (bx1, by1, -1, -1),
    ]:
        for i in range(clen):
            for t in range(lw):
                if dx == 1:
                    x, y = ox + i, oy + t * (1 if dy == -1 else 0)
                else:
                    x, y = ox - i, oy + t * (1 if dy == -1 else 0)
                if 0 <= x < size and 0 <= y < size:
                    img[y][x] = neon
            for i2 in range(clen):
                for t in range(lw):
                    if dy == 1:
                        x, y = ox + t * (1 if dx == -1 else 0), oy + i2
                    else:
                        x, y = ox + t * (1 if dx == -1 else 0), oy - i2
                    if 0 <= x < size and 0 <= y < size:
                        img[y][x] = neon

    # Scan line (center)
    for x in range(bx0, bx1):
        for t in range(lw):
            y = int(cy) + t
            if 0 <= x < size and 0 <= y < size:
                alpha = int(255 * (1 - abs(x - cx) / bw))
                img[y][x] = (0, 255, 156, alpha)

    # Center dot
    dot_r = int(size * 0.06)
    for y in range(size):
        for x in range(size):
            if math.sqrt((x - cx)**2 + (y - cy)**2) <= dot_r:
                img[y][x] = neon

    # Encode PNG
    def to_bytes(img):
        rows = []
        for row in img:
            rows.append(b'\x00' + b''.join(struct.pack('4B', *p) for p in row))
        raw = b''.join(rows)
        compressed = zlib.compress(raw, 9)
        def chunk(name, data):
            c = name + data
            return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
        ihdr = struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)
        return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')

    return to_bytes(img)


if __name__ == '__main__':
    import os
    out = os.path.join(os.path.dirname(__file__), 'static')
    os.makedirs(out, exist_ok=True)
    for size, name in [(192, 'icon-192.png'), (512, 'icon-512.png')]:
        data = create_png(size)
        path = os.path.join(out, name)
        with open(path, 'wb') as f:
            f.write(data)
        print(f'Generated: {path}')
    print('Done!')
