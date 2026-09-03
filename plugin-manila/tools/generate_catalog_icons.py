from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


SIZE = 768
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "frontend" / "assets"


def rounded_shadow(image: Image.Image, box: tuple[int, int, int, int], radius: int) -> None:
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    shadow_box = (box[0] + 12, box[1] + 20, box[2] + 12, box[3] + 20)
    draw.rounded_rectangle(shadow_box, radius=radius, fill=(0, 0, 0, 115))
    image.alpha_composite(layer.filter(ImageFilter.GaussianBlur(18)))


def draw_icon(theme: str) -> Image.Image:
    dark = theme == "dark"
    background = (18, 24, 25) if dark else (224, 222, 214)
    base_outer = (37, 44, 45) if dark else (71, 75, 74)
    base_inner = (27, 37, 38) if dark else (238, 236, 226)
    route = (126, 137, 135) if dark else (98, 106, 105)
    ink = (228, 221, 201) if dark else (48, 55, 55)
    accent = (71, 126, 117)
    accent_light = (103, 157, 145)
    brass = (177, 149, 91)

    image = Image.new("RGBA", (SIZE, SIZE), (*background, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((72, 92, 696, 716), fill=(0, 0, 0, 25))
    base = (86, 74, 682, 680)
    rounded_shadow(image, base, 92)
    draw.rounded_rectangle(base, radius=92, fill=(*base_outer, 255), outline=(*brass, 255), width=7)
    inset = (110, 98, 658, 652)
    draw.rounded_rectangle(inset, radius=72, fill=(*base_inner, 255), outline=(*route, 255), width=4)

    # Subtle wooden/water material bands.
    for y in range(126, 630, 22):
        alpha = 20 if dark else 13
        draw.arc((132, y - 12, 636, y + 38), 8, 172, fill=(*route, alpha), width=3)

    lane_y = (248, 361, 474)
    for index, y in enumerate(lane_y):
        draw.line((163, y, 603, y), fill=(*route, 255), width=10)
        for tick in range(8):
            x = 164 + tick * 63
            width = 5 if tick == 7 else 3
            color = brass if tick == 7 else route
            draw.line((x, y - 15, x, y + 15), fill=(*color, 255), width=width)
        # One neutral punt on each route, arranged diagonally like the game state.
        x = 230 + index * 87
        hull = [(x, y - 43), (x + 126, y - 43), (x + 109, y + 17), (x + 25, y + 17)]
        draw.polygon(hull, fill=(*accent, 255), outline=(*ink, 255), width=5)
        draw.line((x + 30, y - 57, x + 30, y - 23), fill=(*brass, 255), width=5)
        draw.polygon(
            [(x + 33, y - 55), (x + 72, y - 45), (x + 33, y - 34)],
            fill=(*accent_light, 255),
        )
        for seat in range(3):
            sx = x + 52 + seat * 24
            draw.ellipse((sx, y - 54, sx + 16, y - 38), fill=(*ink, 255))

    # Share stack and harbor seal clarify the investment/port identity.
    card_shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(card_shadow)
    sd.rounded_rectangle((164, 132, 275, 286), radius=16, fill=(0, 0, 0, 110))
    image.alpha_composite(card_shadow.filter(ImageFilter.GaussianBlur(9)))
    draw.rounded_rectangle((147, 117, 258, 271), radius=16, fill=(*ink, 255), outline=(*brass, 255), width=5)
    draw.rounded_rectangle((161, 133, 244, 255), radius=10, outline=(*accent, 255), width=5)
    draw.line((176, 161, 229, 161), fill=(*accent, 255), width=5)
    draw.polygon([(202, 181), (226, 198), (217, 230), (187, 230), (178, 198)], outline=(*accent, 255), width=5)

    seal_center = (561, 568)
    draw.ellipse((509, 516, 613, 620), fill=(*base_outer, 255), outline=(*brass, 255), width=7)
    draw.ellipse((528, 535, 594, 601), outline=(*route, 255), width=4)
    draw.line((seal_center[0], 541, seal_center[0], 590), fill=(*brass, 255), width=7)
    draw.line((536, 565, 586, 565), fill=(*brass, 255), width=7)
    draw.arc((536, 563, 586, 598), 0, 180, fill=(*brass, 255), width=6)

    # Highlight and vignette are identical between themes.
    light = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(light)
    ld.ellipse((126, 92, 544, 326), fill=(255, 255, 255, 25 if dark else 34))
    image.alpha_composite(light.filter(ImageFilter.GaussianBlur(28)))
    return image.convert("RGB")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for theme in ("dark", "light"):
        draw_icon(theme).save(
            OUTPUT / f"catalog-{theme}.webp",
            format="WEBP",
            quality=90,
            method=6,
        )


if __name__ == "__main__":
    main()

