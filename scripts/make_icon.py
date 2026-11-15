#!/usr/bin/env python3
"""Generates icon.png (512x512 app icon) with only the Python standard library."""
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIZE = 512
RADIUS = 96
BG = (14, 17, 22)          # #0e1116
ACCENT = (110, 231, 183)   # #6ee7b7
ACCENT_DIM = (110, 231, 183)

# Lightning bolt polygon (x, y)
BOLT = [(292, 44), (148, 288), (240, 288), (196, 468), (372, 226), (262, 226)]

# Neural-network dots radiating behind the bolt: (x, y, radius)
DOTS = [
    (96, 120, 7), (150, 74, 5), (420, 120, 7), (366, 70, 5),
    (86, 300, 6), (60, 210, 4), (430, 300, 6), (452, 210, 4),
    (130, 400, 5), (398, 396, 5),
]
# Thin connector lines between dots (pairs of indices into DOTS)
LINES = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 4), (2, 6), (8, 4), (9, 6), (0, 8), (2, 9)]


def inside_rounded(x, y):
    dx = max(RADIUS - x, 0, x - (SIZE - 1 - RADIUS))
    dy = max(RADIUS - y, 0, y - (SIZE - 1 - RADIUS))
    return dx * dx + dy * dy <= RADIUS * RADIUS


def inside_polygon(px, py, poly):
    n, inside = len(poly), False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def dist_to_segment(px, py, a, b):
    ax, ay = a
    bx, by = b
    abx, aby = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * abx + (py - ay) * aby) / (abx * abx + aby * aby)))
    cx, cy = ax + t * abx, ay + t * aby
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5


def main():
    raw = bytearray()
    for y in range(SIZE):
        raw.append(0)                                   # filter type 0
        for x in range(SIZE):
            r, g, b, a = 0, 0, 0, 0
            if inside_rounded(x + 0.5, y + 0.5):
                r, g, b, a = *BG, 255
                cx, cy = x + 0.5, y + 0.5

                # faint neural lines & dots behind the bolt
                for i, j in LINES:
                    if dist_to_segment(cx, cy, DOTS[i][:2], DOTS[j][:2]) <= 1.5:
                        r, g, b = 46, 64, 58
                for dx, dy, dr in DOTS:
                    if (cx - dx) ** 2 + (cy - dy) ** 2 <= dr * dr:
                        r, g, b = 40, 70, 58

                # the bolt, anti-aliased with 4x supersampling
                cover, total = 0, 16
                for sy in range(4):
                    for sx in range(4):
                        if inside_polygon(cx - 0.375 + 0.25 * sx, cy - 0.375 + 0.25 * sy, BOLT):
                            cover += 1
                if cover:
                    alpha = cover / total
                    r = int(r * (1 - alpha) + ACCENT[0] * alpha)
                    g = int(g * (1 - alpha) + ACCENT[1] * alpha)
                    b = int(b * (1 - alpha) + ACCENT[2] * alpha)

            raw += struct.pack("BBBB", r, g, b, a)

    # PNG encode
    ihdr = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)   # 8-bit RGBA
    chunk = lambda tag, data: (struct.pack(">I", len(data)) + tag + data
                               + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    out = ROOT / "icon.png"
    out.write_bytes(png)
    print(f"Wrote {out} ({len(png):,} bytes)")


if __name__ == "__main__":
    main()
