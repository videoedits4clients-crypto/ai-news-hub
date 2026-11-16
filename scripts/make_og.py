#!/usr/bin/env python3
"""Renders og-image.png (1200x630) — the card shown when a link to
AI Pulse is pasted into WhatsApp, X, Reddit, LinkedIn, Slack, Discord.

Run:  python scripts/make_og.py
Output: og-image.png in the repo root (served by GitHub Pages).
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1200, 630
BG = (14, 17, 22)
SURFACE = (22, 27, 34)
BORDER = (42, 49, 60)
MINT = (110, 231, 183)
WHITE = (230, 237, 243)
MUTED = (154, 164, 175)

ROOT = Path(__file__).resolve().parent.parent
BOLD = "C:/Windows/Fonts/segoeuib.ttf"
SEMI = "C:/Windows/Fonts/seguisb.ttf"
REG = "C:/Windows/Fonts/segoeui.ttf"


def f(path, size):
    return ImageFont.truetype(path, size)


def add_glow(base, center, radius, color, alpha=34):
    """Soft radial light behind the wordmark."""
    mask = Image.new("L", (W // 4, H // 4), 0)
    d = ImageDraw.Draw(mask)
    cx, cy, r = center[0] // 4, center[1] // 4, radius // 4
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(45)).resize((W, H), Image.BICUBIC)
    mask = mask.point(lambda v: int(v * alpha / 255))
    tint = Image.new("RGB", (W, H), color)
    base.paste(tint, (0, 0), mask)


def bolt(d, box, fill):
    """Lightning bolt drawn as a polygon inside box=(x, y, w, h)."""
    x, y, w, h = box
    pts = [(0.60, 0.00), (0.16, 0.57), (0.47, 0.57),
           (0.38, 1.00), (0.86, 0.42), (0.53, 0.42)]
    d.polygon([(x + px * w, y + py * h) for px, py in pts], fill=fill)


def pill(d, x, y, text, font):
    tw = d.textlength(text, font=font)
    h, pad = 46, 24
    d.rounded_rectangle([x, y, x + tw + pad * 2, y + h], radius=h // 2,
                        outline=MINT, width=2)
    d.text((x + pad, y + h / 2), text, font=font, fill=MINT, anchor="lm")
    return x + tw + pad * 2 + 14


def feed_card(d, x, y, widths):
    """A stylised news card — reads as 'this is a feed' at a glance."""
    w, h = 430, 126
    d.rounded_rectangle([x, y, x + w, y + h], radius=18,
                        fill=SURFACE, outline=BORDER, width=2)
    d.rounded_rectangle([x + 26, y + 30, x + 60, y + 64], radius=8, fill=(23, 54, 46))
    d.ellipse([x + 37, y + 41, x + 49, y + 53], fill=MINT)
    for i, bw in enumerate(widths):
        by = y + 32 + i * 22
        col = (70, 80, 92) if i == 0 else (52, 60, 72)
        d.rounded_rectangle([x + 78, by, x + 78 + bw, by + 11], radius=5, fill=col)
    d.rounded_rectangle([x + 26, y + 86, x + 26 + 340, y + 97], radius=5, fill=(42, 49, 60))


def main():
    img = Image.new("RGB", (W, H), BG)
    add_glow(img, (240, 250), 520, (26, 92, 72), alpha=70)
    add_glow(img, (1080, 560), 420, (44, 74, 66), alpha=40)
    d = ImageDraw.Draw(img)

    # brand mark
    d.rounded_rectangle([80, 88, 156, 164], radius=22, fill=(23, 54, 46))
    bolt(d, (106, 102, 24, 48), MINT)

    # wordmark
    x = 80
    f_word = f(BOLD, 94)
    d.text((x, 196), "AI", font=f_word, fill=MINT)
    d.text((x + d.textlength("AI ", font=f_word), 196), "Pulse", font=f_word, fill=WHITE)

    # rule
    d.rounded_rectangle([80, 340, 186, 344], radius=2, fill=MINT)

    # tagline
    f_sub = f(REG, 30)
    d.text((80, 372), "Every AI story that matters, in one feed.",
           font=f_sub, fill=WHITE, anchor="lm")
    d.text((80, 414), "35 sources. Refreshed every 15 minutes.",
           font=f_sub, fill=MUTED, anchor="lm")

    # pills
    f_pill = f(SEMI, 21)
    px = 80
    for label in ("Live feed", "Daily digest", "Newsletter"):
        px = pill(d, px, 500, label, f_pill)

    # feed cards
    feed_card(d, 680, 112, (196, 250))
    feed_card(d, 680, 262, (240, 168))
    feed_card(d, 680, 412, (170, 268))

    img.save(ROOT / "og-image.png", optimize=True)
    print("wrote og-image.png (1200x630)")


if __name__ == "__main__":
    main()
