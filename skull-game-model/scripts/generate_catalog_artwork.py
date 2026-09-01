from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "frontend" / "assets"
CANVAS = 768
SCALE = 2


PALETTES = {
    "dark": {
        "background_top": "#121715",
        "background_bottom": "#252a26",
        "glow": (179, 143, 82, 34),
        "shadow": (0, 0, 0, 120),
        "base_side": "#171b19",
        "base_top": "#333834",
        "base_edge": "#65645d",
        "felt": "#28372f",
        "felt_edge": "#8b806a",
    },
    "light": {
        "background_top": "#f2efe8",
        "background_bottom": "#d7d2c7",
        "glow": (169, 128, 67, 26),
        "shadow": (50, 43, 33, 72),
        "base_side": "#aaa59a",
        "base_top": "#d7d3ca",
        "base_edge": "#77746d",
        "felt": "#59685e",
        "felt_edge": "#857963",
    },
}


def scaled_box(box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    return tuple(value * SCALE for value in box)


def vertical_gradient(top: str, bottom: str) -> Image.Image:
    image = Image.new("RGB", (CANVAS * SCALE, CANVAS * SCALE))
    draw = ImageDraw.Draw(image)
    top_rgb = tuple(int(top[index:index + 2], 16) for index in (1, 3, 5))
    bottom_rgb = tuple(int(bottom[index:index + 2], 16) for index in (1, 3, 5))
    for y in range(CANVAS * SCALE):
        ratio = y / (CANVAS * SCALE - 1)
        color = tuple(round(a + (b - a) * ratio) for a, b in zip(top_rgb, bottom_rgb))
        draw.line((0, y, CANVAS * SCALE, y), fill=color)
    return image.convert("RGBA")


def add_ambient_glow(canvas: Image.Image, palette: dict[str, object]) -> None:
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    draw.ellipse(scaled_box((124, 70, 650, 618)), fill=palette["glow"])
    canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(90 * SCALE)))


def add_plinth(canvas: Image.Image, palette: dict[str, object]) -> None:
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        scaled_box((88, 246, 680, 651)),
        radius=78 * SCALE,
        fill=palette["shadow"],
    )
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(25 * SCALE)))

    base = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(base)
    draw.rounded_rectangle(
        scaled_box((94, 224, 674, 620)),
        radius=76 * SCALE,
        fill=palette["base_side"],
        outline=palette["base_edge"],
        width=4 * SCALE,
    )
    draw.rounded_rectangle(
        scaled_box((104, 194, 664, 585)),
        radius=70 * SCALE,
        fill=palette["base_top"],
        outline=palette["base_edge"],
        width=3 * SCALE,
    )
    draw.ellipse(
        scaled_box((145, 239, 623, 549)),
        fill=palette["felt"],
        outline=palette["felt_edge"],
        width=5 * SCALE,
    )
    draw.ellipse(
        scaled_box((164, 256, 604, 527)),
        outline=(224, 203, 160, 46),
        width=2 * SCALE,
    )
    canvas.alpha_composite(base)


def radial_disc_background(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    center = size / 2
    radius = size * 0.47
    draw = ImageDraw.Draw(image)
    for step in range(round(radius), 0, -1):
        ratio = step / radius
        color = (
            round(37 + 24 * (1 - ratio)),
            round(31 + 20 * (1 - ratio)),
            round(29 + 17 * (1 - ratio)),
            255,
        )
        draw.ellipse(
            (center - step, center - step, center + step, center + step),
            fill=color,
        )
    draw.ellipse(
        (center - radius, center - radius, center + radius, center + radius),
        outline="#b29a88",
        width=max(3, size // 45),
    )
    inset = radius * 0.88
    draw.ellipse(
        (center - inset, center - inset, center + inset, center + inset),
        outline="#c96852",
        width=max(2, size // 70),
    )
    return image


def make_disc(kind: str, size: int = 260 * SCALE) -> Image.Image:
    image = radial_disc_background(size)
    draw = ImageDraw.Draw(image)
    center = size / 2
    radius = size * 0.47
    accent = "#c96852"
    secondary = "#e4b27b"
    ink = "#f2e8da"
    dark = "#201a19"

    if kind == "back":
        for index in range(12):
            angle = math.radians(index * 30)
            inner = radius * 0.26
            outer = radius * 0.79
            start = (center + math.cos(angle) * inner, center + math.sin(angle) * inner)
            end = (center + math.cos(angle) * outer, center + math.sin(angle) * outer)
            draw.line((start, end), fill=secondary if index % 2 == 0 else accent, width=size // 60)
        draw.ellipse(
            (center - size * .105, center - size * .105, center + size * .105, center + size * .105),
            fill=accent,
            outline=secondary,
            width=size // 55,
        )
        draw.ellipse(
            (center - size * .036, center - size * .036, center + size * .036, center + size * .036),
            fill=dark,
        )
    elif kind == "flower":
        petal_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        for index in range(8):
            angle = index * 45
            petal = Image.new("RGBA", image.size, (0, 0, 0, 0))
            petal_draw = ImageDraw.Draw(petal)
            petal_draw.ellipse(
                (
                    center - size * .075,
                    center - size * .34,
                    center + size * .075,
                    center - size * .04,
                ),
                fill=secondary,
                outline=ink,
                width=size // 90,
            )
            petal_layer.alpha_composite(petal.rotate(angle, resample=Image.Resampling.BICUBIC, center=(center, center)))
        image.alpha_composite(petal_layer)
        draw = ImageDraw.Draw(image)
        draw.ellipse(
            (center - size * .105, center - size * .105, center + size * .105, center + size * .105),
            fill=accent,
            outline=ink,
            width=size // 60,
        )
        draw.ellipse(
            (center - size * .035, center - size * .035, center + size * .035, center + size * .035),
            fill=dark,
        )
    else:
        draw.rounded_rectangle(
            (center - size * .235, center - size * .30, center + size * .235, center + size * .16),
            radius=size * .19,
            fill=ink,
            outline="#b29a88",
            width=size // 55,
        )
        draw.polygon(
            (
                (center - size * .17, center + size * .09),
                (center + size * .17, center + size * .09),
                (center + size * .20, center + size * .31),
                (center - size * .20, center + size * .31),
            ),
            fill=ink,
            outline="#b29a88",
        )
        for x_offset in (-.12, .12):
            draw.ellipse(
                (
                    center + size * x_offset - size * .067,
                    center - size * .09 - size * .085,
                    center + size * x_offset + size * .067,
                    center - size * .09 + size * .085,
                ),
                fill=dark,
            )
        draw.polygon(
            (
                (center, center + size * .005),
                (center - size * .045, center + size * .095),
                (center + size * .045, center + size * .095),
            ),
            fill=dark,
        )
        for index in range(5):
            x = center - size * .14 + index * size * .07
            draw.line(
                (x, center + size * .19, x, center + size * .305),
                fill=dark,
                width=size // 80,
            )
        draw.line(
            (
                center + size * .03,
                center - size * .28,
                center - size * .04,
                center - size * .13,
                center + size * .035,
                center - size * .08,
            ),
            fill=accent,
            width=size // 42,
            joint="curve",
        )
    return image


def paste_disc(
    canvas: Image.Image,
    kind: str,
    center: tuple[int, int],
    angle: float,
    width: int,
) -> None:
    source = make_disc(kind)
    height = round(width * .79)
    face = source.resize((width * SCALE, height * SCALE), Image.Resampling.LANCZOS)
    edge = Image.new("RGBA", face.size, (0, 0, 0, 0))
    edge.alpha_composite(face)
    edge_draw = ImageDraw.Draw(edge)
    edge_draw.ellipse(
        (3 * SCALE, height * SCALE - 17 * SCALE, width * SCALE - 3 * SCALE, height * SCALE - 2 * SCALE),
        fill=(42, 32, 28, 230),
    )
    edge.alpha_composite(face)
    rotated = edge.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)

    shadow = Image.new("RGBA", rotated.size, (0, 0, 0, 0))
    shadow.alpha_composite(rotated)
    alpha = shadow.getchannel("A").filter(ImageFilter.GaussianBlur(12 * SCALE))
    shadow_color = Image.new("RGBA", shadow.size, (0, 0, 0, 115))
    shadow_color.putalpha(alpha.point(lambda value: round(value * .55)))
    x = center[0] * SCALE - rotated.width // 2
    y = center[1] * SCALE - rotated.height // 2
    canvas.alpha_composite(shadow_color, (x + 8 * SCALE, y + 15 * SCALE))
    canvas.alpha_composite(rotated, (x, y))


def render_variant(name: str) -> Path:
    palette = PALETTES[name]
    canvas = vertical_gradient(
        str(palette["background_top"]),
        str(palette["background_bottom"]),
    )
    add_ambient_glow(canvas, palette)
    add_plinth(canvas, palette)
    paste_disc(canvas, "back", (384, 300), -3, 226)
    paste_disc(canvas, "flower", (286, 443), -12, 236)
    paste_disc(canvas, "skull", (482, 443), 12, 236)

    highlight = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(highlight).arc(
        scaled_box((130, 108, 638, 654)),
        start=205,
        end=326,
        fill=(255, 244, 216, 30),
        width=7 * SCALE,
    )
    canvas.alpha_composite(highlight.filter(ImageFilter.GaussianBlur(2 * SCALE)))

    final = canvas.convert("RGB").resize((CANVAS, CANVAS), Image.Resampling.LANCZOS)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    destination = OUTPUT / f"catalog-{name}.webp"
    final.save(destination, "WEBP", quality=90, method=6, exact=True)
    return destination


def main() -> None:
    paths = [render_variant(name) for name in ("dark", "light")]
    for path in paths:
        with Image.open(path) as image:
            if image.size != (CANVAS, CANVAS) or image.mode != "RGB":
                raise RuntimeError(f"invalid catalog artwork: {path}")
    print("Generated " + ", ".join(str(path.relative_to(ROOT)) for path in paths))


if __name__ == "__main__":
    main()
