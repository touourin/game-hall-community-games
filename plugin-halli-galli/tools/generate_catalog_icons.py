#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "frontend" / "assets"
CANVAS = 1536


def gradient(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGB", size)
    pixels = image.load()
    for y in range(size[1]):
        ratio = y / max(1, size[1] - 1)
        color = tuple(round(a + (b - a) * ratio) for a, b in zip(top, bottom, strict=True))
        for x in range(size[0]):
            pixels[x, y] = color
    return image


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    paths = [
        Path("C:/Windows/Fonts/georgiab.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
    ]
    for path in paths:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def card_layer(theme: str, motif: str) -> Image.Image:
    image = Image.new("RGBA", (410, 610), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    paper = (236, 232, 221, 255) if theme == "dark" else (253, 251, 244, 255)
    ink = (80, 76, 69, 255) if theme == "dark" else (48, 53, 52, 255)
    gold = (186, 143, 64, 255)
    draw.rounded_rectangle((18, 18, 386, 586), radius=42, fill=(0, 0, 0, 65))
    draw.rounded_rectangle((5, 5, 373, 573), radius=42, fill=paper, outline=(174, 158, 126, 255), width=8)
    draw.rounded_rectangle((28, 28, 350, 550), radius=30, outline=(196, 167, 104, 185), width=5)
    draw.text((47, 32), "5", fill=ink, font=font(72))
    if motif == "lime":
        for cx, cy in [(127, 222), (246, 222), (187, 344), (127, 455), (246, 455)]:
            draw.ellipse((cx - 48, cy - 48, cx + 48, cy + 48), fill=(207, 194, 160, 255), outline=gold, width=11)
            draw.ellipse((cx - 31, cy - 31, cx + 31, cy + 31), outline=ink, width=4)
            draw.line((cx - 28, cy, cx + 28, cy), fill=ink, width=3)
            draw.line((cx, cy - 28, cx, cy + 28), fill=ink, width=3)
    else:
        for cx, cy in [(127, 222), (246, 222), (187, 344), (127, 455), (246, 455)]:
            draw.ellipse((cx - 42, cy - 38, cx + 42, cy + 52), fill=(190, 178, 148, 255), outline=gold, width=10)
            draw.polygon([(cx - 36, cy - 32), (cx, cy - 62), (cx + 36, cy - 32), (cx, cy - 17)], fill=ink)
            for dx, dy in [(-15, -3), (14, -3), (0, 21)]:
                draw.ellipse((cx + dx - 4, cy + dy - 6, cx + dx + 4, cy + dy + 6), fill=paper)
    return image


def paste_rotated(base: Image.Image, layer: Image.Image, center: tuple[int, int], angle: float) -> None:
    rotated = layer.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    base.alpha_composite(rotated, (center[0] - rotated.width // 2, center[1] - rotated.height // 2))


def draw_icon(theme: str) -> Image.Image:
    if theme == "dark":
        base = gradient((CANVAS, CANVAS), (29, 34, 35), (8, 15, 16)).convert("RGBA")
        stage_outer, stage_inner = (66, 69, 67, 255), (30, 38, 38, 255)
        edge = (150, 121, 70, 255)
    else:
        base = gradient((CANVAS, CANVAS), (246, 244, 238), (211, 211, 204)).convert("RGBA")
        stage_outer, stage_inner = (206, 204, 195, 255), (232, 231, 223, 255)
        edge = (145, 115, 66, 255)

    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.ellipse((205, 1170, 1331, 1435), fill=(0, 0, 0, 115 if theme == "dark" else 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(44))
    base.alpha_composite(shadow)

    draw = ImageDraw.Draw(base)
    draw.rounded_rectangle((168, 1130, 1368, 1420), radius=118, fill=stage_outer, outline=edge, width=16)
    draw.rounded_rectangle((235, 1172, 1301, 1360), radius=84, fill=stage_inner, outline=(255, 255, 255, 35), width=5)
    draw.ellipse((360, 1195, 1176, 1358), fill=(0, 0, 0, 50))

    paste_rotated(base, card_layer(theme, "lime"), (590, 692), -18)
    paste_rotated(base, card_layer(theme, "berry"), (955, 692), 17)

    bell_shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    bell_shadow_draw = ImageDraw.Draw(bell_shadow)
    bell_shadow_draw.ellipse((420, 980, 1120, 1265), fill=(0, 0, 0, 130))
    bell_shadow = bell_shadow.filter(ImageFilter.GaussianBlur(34))
    base.alpha_composite(bell_shadow)

    mask = Image.new("L", base.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((476, 382, 1060, 1080), fill=255)
    mask_draw.rectangle((476, 725, 1060, 1085), fill=255)
    mask_draw.polygon([(476, 730), (1060, 730), (1170, 1110), (366, 1110)], fill=255)
    metal = gradient(base.size, (255, 238, 164), (128, 84, 27)).convert("RGBA")
    metal.putalpha(mask)
    base.alpha_composite(metal)
    draw = ImageDraw.Draw(base)
    draw.line([(476, 730), (418, 956), (366, 1110), (1170, 1110), (1118, 956), (1060, 730)], fill=(103, 67, 25, 255), width=18, joint="curve")
    draw.arc((476, 382, 1060, 1080), 183, 357, fill=(103, 67, 25, 255), width=18)
    draw.arc((520, 430, 900, 1050), 122, 242, fill=(255, 247, 193, 125), width=30)
    draw.rounded_rectangle((320, 1050, 1216, 1224), radius=72, fill=(116, 76, 29, 255), outline=(77, 48, 18, 255), width=18)
    lip = gradient((820, 120), (246, 216, 126), (157, 103, 37)).convert("RGBA")
    lip_mask = Image.new("L", lip.size, 0)
    ImageDraw.Draw(lip_mask).rounded_rectangle((0, 0, 819, 119), radius=52, fill=255)
    lip.putalpha(lip_mask)
    base.alpha_composite(lip, (358, 1070))
    draw.rounded_rectangle((358, 1070, 1178, 1190), radius=52, outline=(92, 58, 22, 255), width=14)
    draw.ellipse((620, 330, 916, 545), fill=(121, 79, 28, 255), outline=(77, 48, 18, 255), width=16)
    draw.rounded_rectangle((665, 208, 871, 480), radius=78, fill=(186, 142, 59, 255), outline=(91, 57, 20, 255), width=17)
    draw.ellipse((697, 231, 839, 319), fill=(250, 222, 137, 255))
    draw.ellipse((716, 250, 816, 297), fill=(255, 244, 186, 180))
    draw.rounded_rectangle((455, 1100, 1081, 1137), radius=18, fill=(255, 235, 157, 105))

    highlight = Image.new("RGBA", base.size, (0, 0, 0, 0))
    highlight_draw = ImageDraw.Draw(highlight)
    highlight_draw.ellipse((523, 470, 720, 974), fill=(255, 255, 219, 42))
    highlight = highlight.filter(ImageFilter.GaussianBlur(24))
    base.alpha_composite(highlight)

    return base.convert("RGB").resize((768, 768), Image.Resampling.LANCZOS)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for theme in ("dark", "light"):
        target = OUTPUT / f"catalog-{theme}.webp"
        draw_icon(theme).save(target, "WEBP", quality=90, method=6)
        print(f"Generated {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
