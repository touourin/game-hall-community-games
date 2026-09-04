from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


SIZE = 768
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "frontend" / "assets"
GEMS = [(232, 227, 216), (58, 115, 154), (78, 128, 104), (168, 82, 75), (53, 58, 61)]


def shadow(image: Image.Image, box: tuple[int, int, int, int], radius: int = 28) -> None:
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    shifted = (box[0] + 12, box[1] + 18, box[2] + 12, box[3] + 18)
    draw.rounded_rectangle(shifted, radius=radius, fill=(0, 0, 0, 118))
    image.alpha_composite(layer.filter(ImageFilter.GaussianBlur(16)))


def draw_card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: tuple[int, int, int], level: int) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=22, fill=(244, 240, 231), outline=(221, 200, 151), width=5)
    draw.rounded_rectangle((x1, y1, x2, y1 + 72), radius=20, fill=color)
    draw.rectangle((x1, y1 + 50, x2, y1 + 72), fill=color)
    draw.ellipse((x2 - 57, y1 + 12, x2 - 17, y1 + 52), outline=(255, 250, 225), width=4)
    draw.polygon([(x1 + 45, y1 + 112), (x1 + 88, y1 + 82), (x1 + 132, y1 + 112), (x1 + 114, y1 + 171), (x1 + 62, y1 + 171)], outline=color, width=7)
    draw.line((x1 + 48, y1 + 185, x2 - 26, y1 + 185), fill=(180, 169, 147), width=4)
    for index in range(level + 1):
        cx = x1 + 38 + index * 40
        draw.ellipse((cx, y2 - 49, cx + 28, y2 - 21), fill=GEMS[(index + level) % 5], outline=(74, 74, 67), width=2)


def icon(theme: str) -> Image.Image:
    dark = theme == "dark"
    background = (10, 29, 30) if dark else (225, 222, 212)
    table = (23, 59, 58) if dark else (55, 91, 87)
    edge = (106, 81, 56)
    brass = (183, 138, 63)
    paper = (244, 240, 231)
    image = Image.new("RGBA", (SIZE, SIZE), (*background, 255))
    draw = ImageDraw.Draw(image)
    board = (72, 66, 696, 702)
    shadow(image, board, 72)
    draw.rounded_rectangle(board, radius=72, fill=(*table, 255), outline=(*edge, 255), width=12)
    draw.rounded_rectangle((94, 88, 674, 680), radius=54, outline=(*brass, 190), width=4)

    card_boxes = [(167, 151, 337, 411), (299, 119, 469, 379), (431, 151, 601, 411)]
    for box in card_boxes:
        shadow(image, box, 22)
    for level, (box, color) in enumerate(zip(card_boxes, (GEMS[1], GEMS[2], GEMS[3])), start=1):
        draw_card(draw, box, color, level)

    noble_box = (112, 114, 243, 245)
    draw.rounded_rectangle(noble_box, radius=20, fill=(235, 218, 177), outline=(*brass, 255), width=5)
    draw.ellipse((151, 139, 202, 190), fill=(177, 158, 117))
    draw.pieslice((132, 171, 222, 251), 180, 360, fill=(177, 158, 117))

    for index, color in enumerate((*GEMS, (199, 155, 67))):
        cx = 148 + index * 94
        cy = 548 + (index % 2) * 22
        draw.ellipse((cx - 39, cy - 39, cx + 39, cy + 39), fill=color, outline=paper, width=5)
        draw.ellipse((cx - 27, cy - 27, cx + 27, cy + 27), outline=(*edge, 220), width=4)

    highlight = Image.new("RGBA", image.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(highlight)
    hd.ellipse((80, 60, 560, 340), fill=(255, 255, 255, 25 if dark else 35))
    image.alpha_composite(highlight.filter(ImageFilter.GaussianBlur(32)))
    return image.convert("RGB")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for theme in ("dark", "light"):
        icon(theme).save(OUTPUT / f"catalog-{theme}.webp", "WEBP", quality=92, method=6)
    print("Generated 768×768 Splendor catalog icons.")


if __name__ == "__main__":
    main()
