#!/usr/bin/env python3
"""Render docs/wiki/assets/og.png — 1200×630 social card with exact type."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "wiki" / "assets" / "og.png"

W, H = 1200, 630
BOARD = (22, 48, 40)
CHALK = (233, 242, 234)
CHALK_DIM = (157, 181, 166)
YELLOW = (243, 224, 138)
SHEET = (251, 246, 234)
INK = (27, 36, 55)
MUTED = (92, 103, 120)
ACCENT = (196, 92, 44)
FOREST = (36, 92, 61)
GRID = (233, 242, 234, 18)

PRIME = "9223372036854775783"


def font(size: int, *, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    if mono:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        ]
    elif bold:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for path in candidates:
        p = Path(path)
        if p.is_file():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def main() -> int:
    img = Image.new("RGB", (W, H), BOARD)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(overlay)
    for x in range(0, W, 28):
        g.line([(x, 0), (x, H)], fill=GRID, width=1)
    for y in range(0, H, 28):
        g.line([(0, y), (W, y)], fill=GRID, width=1)
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(img)

    card = (64, 70, W - 64, H - 70)
    d.rounded_rectangle(card, radius=4, fill=SHEET)
    d.rectangle((card[0] + 10, card[1] + 10, card[2] - 10, card[3] - 10), outline=(228, 217, 196), width=1)

    kicker = font(18)
    serif = font(64, bold=True)
    sub = font(26)
    mono = font(34, mono=True)
    small = font(18)
    doctrine = font(17)

    left, top = 104, 108
    d.text((left, top), "ACTA PRIMORUM", font=kicker, fill=ACCENT)
    d.text((card[2] - 104, top), "DETERMINISTIC", font=kicker, fill=FOREST, anchor="ra")

    d.text((left, 168), "Best Prime", font=serif, fill=INK)
    d.text((left, 250), "Fully deterministic primality for every natural number.", font=sub, fill=MUTED)

    d.line([(left, 308), (card[2] - 104, 308)], fill=(228, 217, 196), width=1)

    d.text((left, 334), PRIME, font=mono, fill=INK)
    d.text((left, 390), "near  2⁶³   ·   exact wheel trial   ·   OpenMP C in the library", font=small, fill=MUTED)

    d.text(
        (left, 478),
        "deterministic trial  ·  no stochastic Miller–Rabin",
        font=doctrine,
        fill=FOREST,
    )
    d.text((card[2] - 104, 478), "burakahmet.github.io", font=small, fill=MUTED, anchor="ra")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, format="PNG", optimize=True)
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
