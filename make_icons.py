#!/usr/bin/env python3
"""Generate the PWA icon set for Deep Signal.

    python make_icons.py            # writes icons/*.png

Pure Pillow, no assets required — the mark is drawn: a lume-green sonar
return on the app's abyss-blue field.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).parent / "icons"

ABYSS = (2, 20, 31)
DEEP = (6, 40, 59)
LUME = (57, 240, 200)

# (filename, size, maskable) — maskable keeps the mark inside the safe circle
SPECS = [
    ("icon-180.png", 180, False),
    ("icon-192.png", 192, False),
    ("icon-512.png", 512, False),
    ("icon-maskable-512.png", 512, True),
]


def draw_icon(size: int, maskable: bool) -> Image.Image:
    # Supersample 4x, then downscale — cheap anti-aliasing.
    s = size * 4
    img = Image.new("RGB", (s, s), ABYSS)
    d = ImageDraw.Draw(img, "RGBA")

    # Radial-ish backdrop: a few concentric fills from DEEP out to ABYSS.
    for i in range(28, 0, -1):
        t = i / 28
        r = int(s * 0.78 * t)
        col = tuple(int(ABYSS[c] + (DEEP[c] - ABYSS[c]) * (1 - t) ** 1.6) for c in range(3))
        d.ellipse((s / 2 - r, s / 2 - r * 0.9, s / 2 + r, s / 2 + r * 0.9), fill=col)

    # Maskable icons get a 40% safe zone; plain icons can run wider.
    scale = 0.62 if maskable else 0.82
    cx = cy = s / 2
    R = s / 2 * scale

    # Sonar rings.
    for k, alpha in ((1.00, 235), (0.70, 120), (0.42, 70)):
        w = max(2, int(s * 0.016))
        r = R * k
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=LUME + (alpha,), width=w)

    # Bearing needle, pointing up-right like a heading indicator.
    ang = math.radians(-52)
    tip = (cx + R * 0.98 * math.cos(ang), cy + R * 0.98 * math.sin(ang))
    perp = ang + math.pi / 2
    half = R * 0.17
    base_l = (cx + half * math.cos(perp), cy + half * math.sin(perp))
    base_r = (cx - half * math.cos(perp), cy - half * math.sin(perp))
    tail = (cx - R * 0.34 * math.cos(ang), cy - R * 0.34 * math.sin(ang))
    d.polygon([tip, base_l, tail, base_r], fill=LUME + (255,))

    # Centre pip.
    p = R * 0.075
    d.ellipse((cx - p, cy - p, cx + p, cy + p), fill=(223, 243, 255))

    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, size, maskable in SPECS:
        draw_icon(size, maskable).save(OUT / name, "PNG", optimize=True)
        print(f"  wrote icons/{name}  ({size}x{size})")


if __name__ == "__main__":
    main()
