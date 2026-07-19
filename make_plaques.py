#!/usr/bin/env python3
"""Generate the five A5 dive-site QR plaques for Deep Signal.

    pip install qrcode pillow
    python make_plaques.py                          # uses PAGES_URL below
    python make_plaques.py --base https://user.github.io/deep-signal/
    python make_plaques.py --theme light            # toner-friendly

Each plaque encodes  <base>?site=CODE  so a scan drops the player straight
into that site's code-gate. The app still refuses a code for a site the
player hasn't reached, so the plaques can be hung in any physical order.

Output: plaques/deep-signal-plaques.pdf (5 pages, A5, 300 dpi) plus one PNG
per site for spot reprints.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- config

# Live site. sticasale-maker.github.io/deep-signal/ 301s here — the custom
# domain on the user Pages site covers every project repo at /<repo>/.
PAGES_URL = "https://app.viz.net.au/deep-signal/"

# Mirrors ROUTE[].site in index.html — verified against it at run time.
SITES = [
    (1, "The Wreck", "WRECK",   "Historical Diving Society — Booth 340"),
    (2, "The Reef",  "CORAL",   "Tech Stage — north end of the hall"),
    (3, "The Drift", "DRIFT",   "Forster Dive Center — Booth 134"),
    (4, "The Wall",  "ABYSS",   "South-east wall — bottom of the hall"),
    (5, "The Cave",  "CAVERN",  "Royal Australian Navy — Booth 512"),
    (6, "The Blue",  "PELAGIC", "Behind the Main Stage"),
]

DPI = 300
# A5 portrait: 148 x 210 mm
W, H = int(148 / 25.4 * DPI), int(210 / 25.4 * DPI)   # 1748 x 2480
MARGIN = int(W * 0.085)

THEMES = {
    "dark":  {"bg": (2, 20, 31), "band": (6, 40, 59), "ink": (223, 243, 255),
              "dim": (111, 147, 166), "accent": (57, 240, 200)},
    "light": {"bg": (255, 255, 255), "band": (6, 40, 59), "ink": (8, 32, 46),
              "dim": (108, 132, 148), "accent": (10, 106, 138)},
}

FONT_DIRS = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts"),
             Path("/Library/Fonts"), Path("/System/Library/Fonts")]
FONT_SANS = ["arial.ttf", "DejaVuSans.ttf", "Helvetica.ttc", "LiberationSans-Regular.ttf"]
FONT_BOLD = ["arialbd.ttf", "DejaVuSans-Bold.ttf", "Helvetica.ttc", "LiberationSans-Bold.ttf"]
FONT_MONO = ["consolab.ttf", "DejaVuSansMono-Bold.ttf", "Menlo.ttc", "LiberationMono-Bold.ttf"]


# ---------------------------------------------------------------- helpers

def find_font(names: list[str]) -> Path | None:
    for d in FONT_DIRS:
        if not d.exists():
            continue
        for n in names:
            hit = d / n
            if hit.exists():
                return hit
            for found in d.rglob(n):
                return found
    return None


def load(names: list[str], size: int) -> ImageFont.FreeTypeFont:
    p = find_font(names)
    if p:
        try:
            return ImageFont.truetype(str(p), size)
        except OSError:
            pass
    # Bitmap fallback: legible, just not pretty.
    return ImageFont.load_default(size)


def text_w(d: ImageDraw.ImageDraw, s: str, f) -> int:
    box = d.textbbox((0, 0), s, font=f)
    return box[2] - box[0]


def centred(d: ImageDraw.ImageDraw, y: int, s: str, f, fill, spacing: int = 0) -> None:
    """Draw `s` centred on the page, optionally letter-spaced."""
    if not spacing:
        d.text((W / 2, y), s, font=f, fill=fill, anchor="ma")
        return
    total = sum(text_w(d, c, f) + spacing for c in s) - spacing
    x = (W - total) / 2
    for c in s:
        d.text((x, y), c, font=f, fill=fill, anchor="la")
        x += text_w(d, c, f) + spacing


def verify_codes(index_html: Path) -> None:
    """Guard against SITES drifting away from ROUTE in index.html."""
    if not index_html.exists():
        print(f"  ! {index_html.name} not found — skipping code check", file=sys.stderr)
        return
    src = index_html.read_text(encoding="utf-8", errors="replace")
    found = set(re.findall(r'code\s*:\s*"([A-Z]+)"', src))
    ours = {c for _, _, c, _ in SITES}
    if found and found != ours:
        print(f"  ! code mismatch — index.html has {sorted(found)}, "
              f"this script has {sorted(ours)}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------- drawing

def qr_panel(url: str, box: int, theme: dict) -> Image.Image:
    """QR is always dark-on-white inside a white panel — inverted QR codes
    trip up a lot of phone scanners, so the theme never touches it."""
    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_H,
                       box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    inner = int(box * 0.88)
    img = img.resize((inner, inner), Image.NEAREST)

    panel = Image.new("RGB", (box, box), theme["bg"])
    d = ImageDraw.Draw(panel)
    d.rounded_rectangle((0, 0, box - 1, box - 1), radius=int(box * 0.045),
                        fill=(255, 255, 255))
    panel.paste(img, ((box - inner) // 2, (box - inner) // 2))
    return panel


def plaque(num: int, name: str, code: str, booth: str, base: str, theme: dict) -> Image.Image:
    T = theme
    img = Image.new("RGB", (W, H), T["bg"])
    d = ImageDraw.Draw(img)

    f_eyebrow = load(FONT_MONO, int(W * 0.020))
    f_num     = load(FONT_MONO, int(W * 0.030))
    f_title   = load(FONT_BOLD, int(W * 0.082))
    f_booth   = load(FONT_SANS, int(W * 0.025))
    f_code    = load(FONT_MONO, int(W * 0.088))
    f_label   = load(FONT_MONO, int(W * 0.018))
    f_foot    = load(FONT_SANS, int(W * 0.021))

    # Header band.
    band_h = int(H * 0.052)
    d.rectangle((0, 0, W, band_h), fill=T["band"])
    centred(d, int(band_h * 0.32), "DEEP SIGNAL", f_eyebrow, T["accent"], spacing=int(W * 0.009))

    y = band_h + int(H * 0.048)
    centred(d, y, f"SITE {num} OF {len(SITES)}", f_num, T["dim"], spacing=int(W * 0.006))

    y += int(H * 0.040)
    centred(d, y, name, f_title, T["ink"])

    y += int(H * 0.062)
    centred(d, y, booth, f_booth, T["dim"])

    # QR block.
    box = int(W * 0.60)
    y += int(H * 0.048)
    img.paste(qr_panel(f"{base}?site={code}", box, T), ((W - box) // 2, y))
    y += box + int(H * 0.026)

    centred(d, y, "SCAN TO LOG THIS FIND", f_label, T["dim"], spacing=int(W * 0.005))
    y += int(H * 0.030)

    # Code word — the manual fallback when a camera won't cooperate.
    cw = text_w(d, code, f_code)
    pad_x, pad_y = int(W * 0.055), int(H * 0.016)
    bw, bh = cw + pad_x * 2, int(W * 0.088) + pad_y * 2
    bx, by = (W - bw) // 2, y
    d.rounded_rectangle((bx, by, bx + bw, by + bh), radius=int(W * 0.022),
                        outline=T["accent"], width=max(3, int(W * 0.004)))
    d.text((W / 2, by + bh / 2), code, font=f_code, fill=T["ink"], anchor="mm")

    y = by + bh + int(H * 0.022)
    centred(d, y, "no camera? type this code into the app", f_foot, T["dim"])

    # Footer rule + URL.
    fy = H - MARGIN
    d.line((MARGIN, fy - int(H * 0.026), W - MARGIN, fy - int(H * 0.026)),
           fill=T["dim"], width=2)
    centred(d, fy - int(H * 0.014), base.replace("https://", ""), f_label, T["dim"])
    return img


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description="Build the Deep Signal A5 QR plaques.")
    ap.add_argument("--base", default=PAGES_URL, help="live site URL (default: %(default)s)")
    ap.add_argument("--theme", choices=sorted(THEMES), default="dark")
    ap.add_argument("--out", default="plaques", help="output directory")
    args = ap.parse_args()

    base = args.base if args.base.endswith("/") else args.base + "/"
    theme = THEMES[args.theme]
    here = Path(__file__).parent
    out = here / args.out
    out.mkdir(parents=True, exist_ok=True)

    verify_codes(here / "index.html")

    # Clear old PNGs first. Renumbering the route (5 sites -> 6) leaves stale
    # files like plaque-3-abyss.png next to the new plaque-3-drift.png, and
    # somebody will eventually print the wrong one.
    for old in out.glob("plaque-*.png"):
        old.unlink()

    print(f"  base URL : {base}")
    print(f"  theme    : {args.theme}   page: A5 portrait @ {DPI} dpi ({W}x{H}px)")

    pages = []
    for num, name, code, booth in SITES:
        p = plaque(num, name, code, booth, base, theme)
        png = out / f"plaque-{num}-{code.lower()}.png"
        p.save(png, "PNG", dpi=(DPI, DPI))
        pages.append(p)
        print(f"  site {num}: {code:<8} -> {base}?site={code}")

    pdf = out / "deep-signal-plaques.pdf"
    pages[0].save(pdf, "PDF", resolution=DPI, save_all=True, append_images=pages[1:])
    print(f"\n  PDF: {pdf}  ({len(pages)} pages)")


if __name__ == "__main__":
    main()
