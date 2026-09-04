#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT.parent / "halli-galli-game-model" / "model"
PROJECT_ROOT = ROOT.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.games.plugins import (  # noqa: E402
    _load_engine_factory,
    _read_manifest,
    _validate_engine,
    _validate_required_files,
)


MODEL_HASHES = {
    "card-catalog.json": "ded50f65d1bf2396a1d2922dc67f84480449b044a2b0a14c36be647181b0bf67",
    "scene-catalog.json": "9b41149d6f328a8db818a1e71d6556b5a42500022ea42d2a7cdd74357a89ce23",
    "state-machine.json": "d689563d837f02df3696f7790a9c2e4ff0563666e012399a37fdc22d91db8688",
    "rules-profiles.json": "92182de949a9119509e1fd5788aed9571c07f93ec0923aa75987c56e78bf6000",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_catalog_module() -> Any:
    path = ROOT / "backend" / "catalog.py"
    spec = importlib.util.spec_from_file_location("halli_galli_validation_catalog", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_model_lock() -> None:
    for name, expected in MODEL_HASHES.items():
        path = MODEL_ROOT / name
        assert path.is_file(), f"missing source model: {path}"
        assert digest(path) == expected, f"model changed without implementation review: {name}"


def validate_catalog() -> None:
    model = read_json(MODEL_ROOT / "card-catalog.json")
    catalog = load_catalog_module()
    assert catalog.MODEL_VERSION == model["modelVersion"]
    assert tuple(item["id"] for item in model["fruits"]) == catalog.FRUIT_ORDER
    assert {item["fruitCount"]: item["copies"] for item in model["copyDistribution"]} == catalog.COPY_DISTRIBUTION
    modeled_specs = {
        item["id"]: {
            "nameZh": item["nameZh"],
            "nameEn": item["nameEn"],
            "shape": item["shape"],
            "pattern": item["pattern"],
            "palette": item["palette"],
        }
        for item in model["fruits"]
    }
    assert catalog.FRUIT_SPECS == modeled_specs
    public_faces = catalog.public_catalog()
    assert len(public_faces) == len(model["faces"]) == 20
    comparable_keys = {"faceId", "fruitId", "fruitCount", "copies", "labelZh", "altZh"}
    expected_faces = [
        {
            "faceId": face["id"],
            "fruitId": face["fruitId"],
            "fruitCount": face["fruitCount"],
            "copies": face["copies"],
            "labelZh": face["labelZh"],
            "altZh": face["altZh"],
        }
        for face in model["faces"]
    ]
    assert [{key: face[key] for key in comparable_keys} for face in public_faces] == expected_faces
    assert len(catalog.ALL_CARDS) == 56
    assert len({card.id for card in catalog.ALL_CARDS}) == 56


def validate_rules_and_state_machine() -> None:
    profiles = read_json(MODEL_ROOT / "rules-profiles.json")
    profile = next(item for item in profiles["profiles"] if item["id"] == profiles["defaultProfileId"])
    engine_source = (ROOT / "backend" / "engine.py").read_text(encoding="utf-8")
    rules_source = (ROOT / "backend" / "rules.py").read_text(encoding="utf-8")
    assert profile["id"] == "official_last_bell"
    assert (profile["playerMin"], profile["playerMax"], profile["deckSize"], profile["bellTarget"]) == (2, 6, 56, 5)
    assert f'MINIMUM_FLIP_DELAY_MS = {profile["digital"]["minimumNextFlipDelayMs"]}' in engine_source
    assert f'NO_PROGRESS_TIMEOUT_MS = {profile["digital"]["noProgressTimeoutMs"]:,}'.replace(",", "_") in engine_source
    assert "totals[fruit_id] == 5" in rules_source
    for token in ("STALE_BOARD", "BELL_ALREADY_RESOLVED", "NOT_ELIGIBLE", "NOT_YOUR_TURN", "FLIP_TOO_EARLY"):
        assert token in engine_source, f"modeled rejection missing: {token}"
    for action in ("flip_card", "ring_bell", "resign", "settle_no_progress"):
        assert f'action == "{action}"' in engine_source, f"implemented action missing: {action}"


def validate_scene() -> None:
    scene = read_json(MODEL_ROOT / "scene-catalog.json")
    vue_source = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "frontend").rglob("*.vue"))
    css_source = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "frontend").rglob("*.css")) + "\n" + vue_source
    literal_zones = {"table_stage", "bell_zone", "fruit_legend", "turn_banner", "reaction_banner", "self_controls", "event_strip", "rules_drawer", "result_overlay"}
    for zone_id in literal_zones:
        assert f'data-zone="{zone_id}"' in vue_source, f"modeled zone missing: {zone_id}"
    assert 'class="sr-live"' in vue_source
    assert 'data-zone="player_seat"' in vue_source
    positions = (ROOT / "frontend" / "GameView.vue").read_text(encoding="utf-8")
    for count in range(2, 7):
        assert f"  {count}: [" in positions, f"seat layout missing for {count} players"
    for cue in scene["animationCues"]:
        assert cue["id"] in vue_source or cue["id"].replace("_", "-") in css_source, f"animation cue missing: {cue['id']}"
    for color in scene["theme"].values():
        if isinstance(color, str) and color.startswith("#"):
            assert color.lower() in css_source.lower(), f"theme color missing from UI: {color}"
    breakpoints = scene["breakpoints"]
    for width in (breakpoints["mediumMax"], breakpoints["compactMax"], breakpoints["narrowMax"]):
        assert f"max-width:{width}px" in css_source.replace(" ", ""), f"breakpoint missing: {width}px"
    assert "136px" in css_source and "88px" in css_source and "64px" in css_source
    assert "pointer-events:none" in css_source.replace(" ", "")
    assert "prefers-reduced-motion:reduce" in css_source.replace(" ", "")
    for fruit in read_json(MODEL_ROOT / "card-catalog.json")["fruits"]:
        assert fruit["id"] in vue_source
    for count in range(1, 6):
        assert f"  {count}: [" in vue_source, f"card symbol layout missing: {count}"


def validate_assets_and_manifest() -> None:
    from PIL import Image

    manifest = read_json(ROOT / "manifest.json")
    assert manifest["players"] == {"min": 2, "max": 6, "label": "2–6 人"}
    assert manifest["roomLayout"] == "immersive"
    assert manifest["defaultOptions"]["rulesProfile"] == "official_last_bell"
    for name in ("catalog-dark.webp", "catalog-light.webp"):
        with Image.open(ROOT / "frontend" / "assets" / name) as image:
            assert image.size == (768, 768)
            assert image.mode == "RGB"
    host_manifest = _read_manifest(ROOT / "manifest.json")
    _validate_required_files(ROOT)
    engine_factory = _load_engine_factory(ROOT, host_manifest["id"])
    _validate_engine(engine_factory(), host_manifest)


def main() -> None:
    validate_model_lock()
    validate_catalog()
    validate_rules_and_state_machine()
    validate_scene()
    validate_assets_and_manifest()
    print("Halli Galli plugin/model/host consistency valid: 56 cards, 20 faces, 2–6 players, 17 zones, 8 modeled cues.")


if __name__ == "__main__":
    main()
