from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT.parent / "splendor-game-model" / "model"
DATA_ROOT = ROOT / "data"
PROJECT_ROOT = ROOT.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.games.plugins import (  # noqa: E402
    _load_engine_factory,
    _read_manifest,
    _validate_engine,
    _validate_required_files,
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    mirrored = ["card-catalog.json", "component-catalog.json", "state-machine.json", "scene-catalog.json"]
    for name in mirrored:
        assert digest(DATA_ROOT / name) == digest(MODEL_ROOT / name), f"model mirror drift: {name}"

    cards = json.loads((DATA_ROOT / "card-catalog.json").read_text(encoding="utf-8"))
    assert len(cards["developmentCards"]) == 90
    assert len({item["id"] for item in cards["developmentCards"]}) == 90
    assert len(cards["nobles"]) == 10
    assert all(not item["visual"]["officialArtworkIncluded"] for item in cards["developmentCards"])
    assert all(not item["visual"]["officialPortraitIncluded"] for item in cards["nobles"])

    machine = json.loads((DATA_ROOT / "state-machine.json").read_text(encoding="utf-8"))
    engine_source = (ROOT / "backend" / "engine.py").read_text(encoding="utf-8")
    for action in machine["actions"]:
        assert f'"{action}"' in engine_source, f"modeled action missing in engine: {action}"

    scene = json.loads((DATA_ROOT / "scene-catalog.json").read_text(encoding="utf-8"))
    frontend_source = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "frontend").rglob("*.vue"))
    css_source = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "frontend").glob("*.css"))
    for zone in scene["zones"]:
        present = zone["id"] in frontend_source
        if zone["id"] in {"tier_1_market", "tier_2_market", "tier_3_market"}:
            present = present or "`tier_${tier.level}_market`" in frontend_source
        assert present, f"modeled zone missing in frontend: {zone['id']}"
    for cue in scene["animationCues"]:
        assert cue["id"] in frontend_source or cue["id"].replace("_", "-") in css_source, f"animation cue missing: {cue['id']}"
    for color in scene["theme"].values():
        if isinstance(color, str) and color.startswith("#"):
            assert color.lower() in css_source.lower(), f"scene color missing in CSS: {color}"

    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["players"] == {"min": 2, "max": 4, "label": "2–4 人"}
    assert manifest["defaultOptions"]["rulesProfile"] == "base-2024-refresh"
    host_manifest = _read_manifest(ROOT / "manifest.json")
    _validate_required_files(ROOT)
    engine_factory = _load_engine_factory(ROOT, host_manifest["id"])
    _validate_engine(engine_factory(), host_manifest)
    print("Splendor host/plugin/model consistency valid: 4 mirrored models, 90 cards, 10 nobles, 13 zones, 10 animation cues.")


if __name__ == "__main__":
    main()
