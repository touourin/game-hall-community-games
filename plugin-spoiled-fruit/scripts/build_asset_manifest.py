from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = PLUGIN_ROOT / "assets"
OUTPUT_PATH = ASSET_ROOT / "asset-manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def describe(path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        width, height = image.size
        mode = image.mode
        has_alpha = "A" in image.getbands()
        alpha_extrema = list(image.getchannel("A").getextrema()) if has_alpha else None

    relative = path.relative_to(PLUGIN_ROOT).as_posix()
    return {
        "path": relative,
        "kind": "card" if relative.startswith("assets/cards/") else "scene",
        "width": width,
        "height": height,
        "mode": mode,
        "hasAlpha": has_alpha,
        "alphaExtrema": alpha_extrema,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def main() -> None:
    paths = sorted((ASSET_ROOT / "cards").glob("*.png"))
    paths += sorted((ASSET_ROOT / "scenes").glob("*.png"))
    payload = {
        "schemaVersion": 1,
        "gameKey": "spoiled-fruit",
        "generatedBy": "scripts/build_asset_manifest.py",
        "assetCount": len(paths),
        "assets": [describe(path) for path in paths],
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT_PATH} ({len(paths)} assets)")


if __name__ == "__main__":
    main()
