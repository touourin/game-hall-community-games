"""Generate the paired opaque catalog icons from one shared geometry."""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont


SIZE = 1536
OUT = Path(__file__).resolve().parents[1] / "frontend" / "assets"
EUROPE = [
    (164, 472), (221, 313), (414, 238), (553, 274), (670, 190), (869, 164),
    (1047, 213), (1238, 341), (1317, 522), (1268, 702), (1350, 862),
    (1241, 1046), (1058, 1071), (902, 1222), (725, 1165), (566, 1260),
    (374, 1165), (218, 1008), (269, 806), (142, 653),
]
ROUTES = [
    ((277, 557), (533, 505), "ruby"), ((533, 505), (762, 645), "gold"),
    ((762, 645), (1029, 474), "blue"), ((1029, 474), (1242, 604), "jade"),
    ((371, 937), (629, 824), "blue"), ((629, 824), (882, 934), "ruby"),
    ((882, 934), (1179, 812), "gold"), ((458, 353), (700, 313), "jade"),
    ((700, 313), (973, 329), "ruby"), ((533, 505), (629, 824), "jade"),
    ((762, 645), (882, 934), "blue"), ((1029, 474), (1179, 812), "gold"),
]
CITY_POINTS = sorted({point for route in ROUTES for point in route[:2]})


def font(path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def gradient(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGB", (SIZE, SIZE), top)
    pixels = image.load()
    for y in range(SIZE):
        ratio = y / (SIZE - 1)
        color = tuple(round(a + (b - a) * ratio) for a, b in zip(top, bottom))
        for x in range(SIZE):
            pixels[x, y] = color
    return image


def render(theme: str) -> None:
    dark = theme == "dark"
    image = gradient(
        (8, 31, 41) if dark else (225, 222, 202),
        (3, 12, 18) if dark else (170, 184, 173),
    ).convert("RGBA")
    draw = ImageDraw.Draw(image)
    gold = (232, 190, 103) if dark else (126, 88, 42)
    sea = (10, 39, 50) if dark else (151, 187, 191)
    land = (43, 67, 60) if dark else (196, 193, 161)
    ink = (241, 235, 211) if dark else (28, 47, 49)
    colors = {"ruby": (205, 78, 70), "blue": (55, 128, 181), "jade": (63, 146, 101), "gold": (221, 169, 53)}

    # Architectural frame and sea chart.
    draw.rounded_rectangle((56, 56, 1480, 1480), 104, fill=sea, outline=gold, width=18)
    draw.rounded_rectangle((86, 86, 1450, 1450), 83, outline=(*ink, 120), width=4)
    for radius, alpha in [(620, 34), (480, 25), (340, 18)]:
        ring = Image.new("RGBA", (SIZE, SIZE))
        ImageDraw.Draw(ring).ellipse((768-radius, 768-radius, 768+radius, 768+radius), outline=(*gold, alpha), width=4)
        image = Image.alpha_composite(image, ring)
    draw = ImageDraw.Draw(image)

    # Europe is deliberately schematic and original, matching the in-game model.
    draw.polygon([(x + 10, y + 22) for x, y in EUROPE], fill=(0, 0, 0, 70))
    draw.polygon(EUROPE, fill=land, outline=(*ink, 150), width=8)
    for x in range(175, 1330, 84):
        draw.line((x, 270, x + 330, 1180), fill=(*ink, 11), width=3)

    # Rail network and ties.
    for start, end, color_name in ROUTES:
        color = colors[color_name]
        draw.line((*start, *end), fill=(5, 15, 18), width=28)
        draw.line((*start, *end), fill=color, width=15)
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = max(1, (dx * dx + dy * dy) ** 0.5)
        nx, ny = -dy / length, dx / length
        for step in range(1, 6):
            t = step / 6
            cx, cy = start[0] + dx * t, start[1] + dy * t
            draw.line((cx - nx * 18, cy - ny * 18, cx + nx * 18, cy + ny * 18), fill=color, width=9)
    for x, y in CITY_POINTS:
        draw.ellipse((x-21, y-21, x+21, y+21), fill=(6, 19, 23), outline=ink, width=6)
        draw.ellipse((x-8, y-8, x+8, y+8), fill=gold)

    # Central locomotive plaque, with a soft lift and identical geometry per theme.
    shadow = Image.new("RGBA", (SIZE, SIZE))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((322, 545, 1214, 1005), 82, fill=(0, 0, 0, 170))
    shadow = shadow.filter(ImageFilter.GaussianBlur(35))
    image = Image.alpha_composite(image.convert("RGBA"), shadow)
    draw = ImageDraw.Draw(image)
    plaque = (14, 37, 44, 245) if dark else (235, 226, 197, 245)
    draw.rounded_rectangle((300, 515, 1236, 975), 82, fill=plaque, outline=gold, width=14)
    draw.line((386, 844, 1150, 844), fill=gold, width=14)
    draw.rectangle((496, 700, 934, 838), fill=(24, 45, 51) if dark else (49, 69, 69), outline=ink, width=8)
    draw.rounded_rectangle((850, 624, 1077, 838), 30, fill=(26, 48, 54) if dark else (54, 73, 72), outline=ink, width=8)
    draw.rectangle((904, 552, 1018, 624), fill=(26, 48, 54) if dark else (54, 73, 72), outline=gold, width=8)
    draw.polygon(((1055, 661), (1151, 714), (1151, 838), (1030, 838)), fill=colors["ruby"], outline=ink)
    for cx in (556, 820, 1024):
        draw.ellipse((cx-56, 790, cx+56, 902), fill=(5, 14, 18), outline=ink, width=13)
        draw.ellipse((cx-23, 823, cx+23, 869), fill=gold)
    for wx in (541, 663, 785):
        draw.rounded_rectangle((wx, 735, wx+76, 787), 8, fill=gold)

    title_font = font("C:/Windows/Fonts/georgiab.ttf", 73)
    sub_font = font("C:/Windows/Fonts/seguisb.ttf", 29)
    title = "EUROPE RAIL"
    box = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((SIZE - (box[2] - box[0])) / 2, 1036), title, font=title_font, fill=ink)
    sub = "47 CITIES  •  101 TRACKS"
    sub_box = draw.textbbox((0, 0), sub, font=sub_font)
    draw.text(((SIZE - (sub_box[2] - sub_box[0])) / 2, 1131), sub, font=sub_font, fill=gold)
    draw.line((415, 1213, 1121, 1213), fill=gold, width=7)
    draw.ellipse((745, 1189, 791, 1235), fill=sea, outline=gold, width=7)

    image = image.convert("RGB").resize((768, 768), Image.Resampling.LANCZOS)
    OUT.mkdir(parents=True, exist_ok=True)
    image.save(OUT / f"catalog-{theme}.webp", "WEBP", quality=94, method=6)


if __name__ == "__main__":
    render("dark")
    render("light")
