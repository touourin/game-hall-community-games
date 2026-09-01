from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "炸弹人素材"
ASSETS = ROOT / "frontend" / "assets"

MAPS = {
    "01-magma-crucible.webp": "exec-21f2b7bc-4233-4677-836a-1094d176f80a.png",
    "02-frost-fracture.webp": "exec-94697080-0ff4-4aad-aac0-bfa5598264f7.png",
    "03-neon-reactor.webp": "exec-b33087d4-61e9-4ba0-8dce-21a1f83feaa1.png",
    "04-jungle-ziggurat.webp": "exec-f2011321-08cf-4e11-be10-d155edfeedf4.png",
    "05-sky-citadel.webp": "exec-e941fe9e-893f-4f71-8712-55004d264fc1.png",
    "06-clockwork-foundry.webp": "exec-9e49a26a-f46b-45d6-be2a-d4d525b9d0c7.png",
    "07-haunted-catacombs.webp": "exec-355441e8-f671-41c4-b76b-e925670d00d3.png",
    "08-storm-dockyard.webp": "exec-fa308aa8-76d4-4144-9671-f61a1f153d89.png",
    "09-crystal-rift.webp": "exec-a9bcd024-5950-4199-b564-8b2cffa1adc5.png",
    "10-solar-collapse.webp": "exec-c724988d-ed2b-4fa4-8fd7-6212741b2689.png",
}

PLAYERS = {
    "player-01-red.png": "exec-cd021621-0309-406b-8bf6-821efd820bf4.png",
    "player-02-blue.png": "exec-06434f70-300e-4edd-9bfa-b7e098e4e610.png",
    "player-03-yellow.png": "exec-5346051a-4814-4a26-9525-e7ac2bd0be11.png",
    "player-04-green.png": "exec-0d12f5c0-7484-4a38-a95c-27cae2a4dc39.png",
    "player-05-orange.png": "exec-09965beb-2583-4d27-bcf6-92754fd529a3.png",
    "player-06-cyan.png": "exec-201ecd1e-37ef-41ad-bb45-e1051de49480.png",
    "player-07-violet.png": "exec-5dbaa613-5c79-4bc3-88ff-8a3d915420c7.png",
    "player-08-black-gold.png": "exec-48fb6673-ab09-4702-8284-3f23e6193e51.png",
}

ATLASES = {
    "exec-87ab4f3a-1da4-409a-a151-9356821dec71.png": (
        "bomb_up", "flame_up", "speed", "kick",
    ),
    "exec-80800fba-3ecd-4a2d-b68f-f2c301fbbec0.png": (
        "punch", "remote", "throw", "chain",
    ),
    "exec-1146ad83-bdaa-4bff-bf34-f54c6934c036.png": (
        "timer", "shield", "skull", "ghost",
    ),
    "exec-512ad9d8-be91-4eeb-b119-66e98d6e89c4.png": (
        "magnet", "ice", "swap", "star",
    ),
}


def chroma_key(image: Image.Image) -> Image.Image:
    rgba = np.asarray(image.convert("RGBA")).copy()
    background = rgba[0, 0, :3].astype(np.float32)
    rgb = rgba[:, :, :3].astype(np.float32)
    if background[1] > background[0] + background[2]:
        # Green-screen renders contain compression/noise, so key by chroma
        # dominance instead of exact RGB distance.
        strength = rgb[:, :, 1] - np.maximum(rgb[:, :, 0], rgb[:, :, 2])
    else:
        # Magenta-screen renders use red + blue dominance over green.
        strength = np.minimum(rgb[:, :, 0], rgb[:, :, 2]) - rgb[:, :, 1]
    alpha = np.clip((88.0 - strength) * (255.0 / 68.0), 0, 255).astype(np.uint8)
    rgba[:, :, 3] = np.minimum(rgba[:, :, 3], alpha)
    return Image.fromarray(rgba, "RGBA")


def fitted_transparent(image: Image.Image, size: int, fill_ratio: float = 0.88) -> Image.Image:
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        return Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cropped = image.crop(bbox)
    maximum = round(size * fill_ratio)
    cropped.thumbnail((maximum, maximum), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - cropped.width) // 2
    y = (size - cropped.height) // 2
    canvas.alpha_composite(cropped, (x, y))
    return canvas


def build_maps() -> None:
    target = ASSETS / "maps"
    target.mkdir(parents=True, exist_ok=True)
    for output_name, source_name in MAPS.items():
        with Image.open(SOURCE / source_name) as image:
            rendered = image.convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS)
            rendered.save(target / output_name, "WEBP", quality=88, method=6)


def build_players() -> None:
    target = ASSETS / "players"
    target.mkdir(parents=True, exist_ok=True)
    for output_name, source_name in PLAYERS.items():
        with Image.open(SOURCE / source_name) as image:
            rendered = fitted_transparent(chroma_key(image), 384, 0.94)
            rendered.save(target / output_name, "PNG", optimize=True)


def build_items() -> None:
    target = ASSETS / "items"
    target.mkdir(parents=True, exist_ok=True)
    for source_name, item_names in ATLASES.items():
        with Image.open(SOURCE / source_name) as atlas_source:
            atlas = atlas_source.convert("RGBA")
            width, height = atlas.size
            for index, item_name in enumerate(item_names):
                column, row = index % 2, index // 2
                quadrant = atlas.crop((
                    column * width // 2,
                    row * height // 2,
                    (column + 1) * width // 2,
                    (row + 1) * height // 2,
                ))
                rendered = fitted_transparent(chroma_key(quadrant), 256, 0.84)
                rendered.save(target / f"item-{item_name}.png", "PNG", optimize=True)


def rounded_gradient(size: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    result = Image.new("RGB", (size, size))
    pixels = result.load()
    for y in range(size):
        ratio = y / max(1, size - 1)
        color = tuple(round(top[index] * (1 - ratio) + bottom[index] * ratio) for index in range(3))
        for x in range(size):
            pixels[x, y] = color
    return result


def build_catalog_icon(output_name: str, light: bool) -> None:
    size = 768
    if light:
        image = rounded_gradient(size, (244, 244, 240), (193, 198, 199))
        grid = (96, 105, 107)
        base = (223, 225, 219)
        edge = (75, 80, 80)
        hard = (86, 91, 90)
        soft = (164, 116, 58)
    else:
        image = rounded_gradient(size, (35, 38, 40), (9, 11, 13))
        grid = (85, 91, 92)
        base = (29, 32, 33)
        edge = (137, 143, 142)
        hard = (105, 111, 110)
        soft = (169, 112, 51)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((74, 74, 694, 694), radius=78, fill=base, outline=edge, width=8)
    for offset in range(136, 650, 64):
        draw.line((136, offset, 632, offset), fill=grid, width=2)
        draw.line((offset, 136, offset, 632), fill=grid, width=2)
    for x, y, color in (
        (152, 152, hard), (536, 152, soft), (152, 536, soft), (536, 536, hard),
        (216, 280, hard), (472, 408, soft),
    ):
        draw.rounded_rectangle((x, y, x + 60, y + 60), radius=12, fill=color, outline=edge, width=3)
    with Image.open(ASSETS / "items" / "item-bomb_up.png") as icon_source:
        icon = icon_source.convert("RGBA")
        icon.thumbnail((390, 390), Image.Resampling.LANCZOS)
        image.paste(icon, ((size - icon.width) // 2, (size - icon.height) // 2), icon)
    image.save(ASSETS / output_name, "WEBP", quality=90, method=6)


def main() -> None:
    build_maps()
    build_players()
    build_items()
    build_catalog_icon("catalog-dark.webp", light=False)
    build_catalog_icon("catalog-light.webp", light=True)
    print(f"Built assets in {ASSETS}")


if __name__ == "__main__":
    main()
