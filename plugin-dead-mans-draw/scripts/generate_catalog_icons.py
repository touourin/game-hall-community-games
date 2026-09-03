#!/usr/bin/env python3
"""Generate paired 768×768 catalog icons with identical geometry."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "frontend" / "assets"
SIZE = 768


def rounded_shadow(canvas: Image.Image, box: tuple[int, int, int, int], radius: int, color: str, blur: int) -> None:
    layer = Image.new("RGBA", canvas.size)
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle(box, radius=radius, fill=color)
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))


def card_layer(accent: str, icon: str, paper: str, ink: str) -> Image.Image:
    card = Image.new("RGBA", (210, 310))
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle((10, 12, 200, 300), radius=25, fill="#00000055")
    draw.rounded_rectangle((6, 6, 194, 294), radius=24, fill=paper, outline="#c8ad78", width=6)
    draw.rounded_rectangle((18, 18, 182, 84), radius=15, fill=accent)
    draw.ellipse((59, 112, 141, 194), fill=f"{accent}28")
    line = max(7, SIZE // 100)
    if icon == "anchor":
        draw.ellipse((91, 119, 109, 137), outline=accent, width=line)
        draw.line((100, 137, 100, 183), fill=accent, width=line)
        draw.arc((64, 148, 136, 211), 8, 172, fill=accent, width=line)
        draw.line((66, 169, 80, 163), fill=accent, width=line)
        draw.line((134, 169, 120, 163), fill=accent, width=line)
    elif icon == "cannon":
        draw.polygon([(61, 141), (136, 151), (130, 177), (56, 167)], outline=accent)
        draw.line((57, 141, 136, 151, 130, 177, 56, 167, 57, 141), fill=accent, width=line)
        draw.ellipse((78, 164, 108, 194), outline=accent, width=line)
        draw.line((136, 155, 160, 145), fill=accent, width=line)
    else:
        draw.polygon([(100, 116), (132, 137), (126, 177), (100, 202), (74, 177), (68, 137)], outline=accent)
        draw.line((100, 121, 100, 197), fill=accent, width=line)
        draw.arc((74, 139, 126, 171), 10, 170, fill=accent, width=line)
        draw.arc((74, 158, 126, 190), 10, 170, fill=accent, width=line)
    draw.rounded_rectangle((26, 240, 174, 268), radius=12, fill=f"{accent}24")
    draw.line((50, 254, 150, 254), fill=accent, width=5)
    draw.rounded_rectangle((32, 35, 67, 67), radius=8, outline="#fff8e9", width=5)
    return card


def build(theme: str) -> Image.Image:
    dark = theme == "dark"
    background = "#0c1617" if dark else "#e9e4da"
    outer = "#242828" if dark else "#d2cdc2"
    edge = "#80613e" if dark else "#8b7354"
    table = "#173b3a" if dark else "#d5ded9"
    inner = "#204947" if dark else "#eef2ed"
    paper = "#efe2c4" if dark else "#fff8e8"
    ink = "#162323" if dark else "#26302e"
    image = Image.new("RGBA", (SIZE, SIZE), background)
    rounded_shadow(image, (92, 126, 676, 672), 86, "#00000088" if dark else "#30403945", 34)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((76, 106, 692, 660), radius=94, fill=outer)
    draw.rounded_rectangle((91, 120, 677, 646), radius=82, fill=edge)
    draw.rounded_rectangle((108, 136, 660, 628), radius=70, fill=table)
    draw.rounded_rectangle((130, 158, 638, 606), radius=56, fill=inner, outline="#63827b" if dark else "#97aaa4", width=4)

    glow = Image.new("RGBA", image.size)
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((238, 190, 530, 524), fill="#f2c96d24")
    image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(46)))

    cards = [
        (card_layer("#2e7480", "anchor", paper, ink), -11, (178, 230)),
        (card_layer("#9d4b3d", "cannon", paper, ink), 0, (279, 194)),
        (card_layer("#985173", "mermaid", paper, ink), 11, (378, 230)),
    ]
    for card, angle, position in cards:
        rotated = card.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
        x = position[0] - (rotated.width - card.width) // 2
        y = position[1] - (rotated.height - card.height) // 2
        image.alpha_composite(rotated, (x, y))

    draw = ImageDraw.Draw(image)
    draw.ellipse((315, 545, 365, 595), fill="#a3473d", outline="#e4b8a8", width=4)
    draw.ellipse((376, 545, 426, 595), fill="#4f7f78", outline="#b8ddd5", width=4)
    draw.line((329, 570, 351, 570), fill="#fff8e9", width=6)
    draw.line((401, 558, 401, 582), fill="#fff8e9", width=5)
    draw.line((389, 570, 413, 570), fill="#fff8e9", width=5)
    return image.convert("RGB")


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for theme in ("dark", "light"):
        path = OUTPUT / f"catalog-{theme}.webp"
        build(theme).save(path, "WEBP", quality=90, method=6)
        print(f"Generated {path.relative_to(ROOT)} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
