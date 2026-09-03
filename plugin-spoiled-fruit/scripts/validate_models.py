from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = PLUGIN_ROOT / "model"
ASSET_ROOT = PLUGIN_ROOT / "assets"
FRONTEND_ROOT = PLUGIN_ROOT / "frontend"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_cards() -> tuple[set[str], set[str]]:
    catalog = load_json(MODEL_ROOT / "card-catalog.json")
    cards = catalog["cards"]
    normals = [card for card in cards if card["kind"] == "normal"]
    old_maids = [card for card in cards if card["kind"] == "old_maid"]

    require(len(cards) == 34, "catalog must contain 30 normal identities and 4 old maids")
    require(len(normals) == 30, "normal fruit identity count must be 30")
    require(sum(card["copies"] for card in normals) == 60, "normal physical card count must be 60")
    require(len(old_maids) == 4, "old-maid identity count must be 4")
    require(all(card["copies"] == 2 for card in normals), "every normal fruit must have exactly two copies")
    require(all(card["copies"] == 1 for card in old_maids), "every old maid must have one copy")
    require([card["sortIndex"] for card in normals] == list(range(1, 31)), "normal sort indexes must be 1..30")
    require(all(card["pairKey"] == card["id"] for card in normals), "normal pairKey must equal catalog id")
    require(all(card["pairKey"] is None for card in old_maids), "old maids must never have pair keys")

    for key in ("id", "cardCode", "slug", "nameZh", "asset"):
        values = [card[key] for card in cards]
        require(len(values) == len(set(values)), f"card {key} values must be unique")

    for player_count in range(4, 9):
        expected_old_maids = math.floor(player_count / 2)
        included_old_maids = sum(
            card["copies"] for card in old_maids if player_count in card["includeAtPlayerCounts"]
        )
        included_normals = sum(
            card["copies"] for card in normals if player_count in card["includeAtPlayerCounts"]
        )
        require(included_normals == 60, f"{player_count} players must always use all 60 normal cards")
        require(included_old_maids == expected_old_maids, f"wrong old-maid count for {player_count} players")
        declared_total = catalog["deckRule"]["totalCardsByPlayerCount"][str(player_count)]
        require(declared_total == 60 + expected_old_maids, f"wrong declared total for {player_count} players")

    for card in cards:
        asset_path = (MODEL_ROOT / card["asset"]).resolve()
        require(asset_path.is_relative_to(PLUGIN_ROOT), f"card asset escapes plugin root: {card['asset']}")
        require(asset_path.is_file(), f"missing card asset: {card['asset']}")

    return {card["id"] for card in normals}, {card["effectId"] for card in cards}


def validate_effects(normal_ids: set[str]) -> set[str]:
    catalog = load_json(MODEL_ROOT / "effect-catalog.json")
    policy = catalog["triggerPolicy"]
    require(policy["setupPairsTrigger"] is False, "initial deal pairs must not trigger skills")
    require(policy["postSetupPairsTrigger"] is True, "post-setup pairs must trigger")
    require(policy["effectCreatedPairsTrigger"] is True, "effect-created pairs must trigger")
    require(policy["queueDiscipline"] == "fifo", "effect queue must be FIFO")

    effects = catalog["effects"]
    require(len(effects) == 10, "exactly ten normal-pair effect categories are expected")
    require(sum(effect["pairCount"] for effect in effects) == 30, "effect pair counts must total 30")
    effect_ids = [effect["id"] for effect in effects]
    require(len(effect_ids) == len(set(effect_ids)), "effect ids must be unique")

    assigned = [fruit_id for effect in effects for fruit_id in effect["fruitIds"]]
    require(len(assigned) == 30, "effects must assign exactly 30 fruit identities")
    require(set(assigned) == normal_ids, "effects must cover every normal fruit exactly once")
    require(len(assigned) == len(set(assigned)), "normal fruits cannot appear in multiple effects")

    shake = next(effect for effect in effects if effect["id"] == "shake_basket")
    require(shake["labelZh"] == "摇匀果篮", "09-11 effect must be named 摇匀果篮")
    require(shake["fruitIds"] == ["fruit-09", "fruit-10", "fruit-11"], "shake-basket fruit mapping changed")
    return set(effect_ids) | {catalog["oldMaidRule"]["id"]}


def validate_scenes(effect_ids: set[str]) -> None:
    catalog = load_json(MODEL_ROOT / "scene-catalog.json")
    scenes = catalog["scenes"]
    require(len(scenes) == 7, "scene catalog must contain seven high-level scenes")
    ids = [scene["id"] for scene in scenes]
    require(len(ids) == len(set(ids)), "scene ids must be unique")
    arts = [scene["art"] for scene in scenes]
    require(len(arts) == len(set(arts)), "each high-level scene needs its own image")
    for scene in scenes:
        art_path = (MODEL_ROOT / scene["art"]).resolve()
        require(art_path.is_relative_to(PLUGIN_ROOT), f"scene art escapes plugin root: {scene['art']}")
        require(art_path.is_file(), f"missing scene art: {scene['art']}")

    routing = catalog["effectSceneRouting"]
    require(set(routing) == effect_ids - {"old_maid"}, "every normal effect needs exactly one scene route")
    require(set(routing.values()).issubset(set(ids)), "effect route references an unknown scene")
    require(
        scenes[0]["art"] == "../assets/scenes/scene-runtime-market-table-8p.png",
        "setup scene must use the generated eight-seat runtime table",
    )
    require(
        scenes[-1]["art"] == "../assets/scenes/scene-07-final-reveal-v2.png",
        "finish scene must use the generated four-Old-Maid reveal",
    )


def validate_animations() -> None:
    catalog = load_json(MODEL_ROOT / "animation-catalog.json")
    animations = catalog["animations"]
    expected_kinds = {
        "deal", "pair", "draw", "shuffle", "skip", "peek", "exchange",
        "protect", "move", "conveyor", "safe", "finish",
    }
    require({item["kind"] for item in animations} == expected_kinds, "animation kinds changed")
    expected_events = {
        "deal", "initial_sweep", "pair", "draw", "extra_draw", "shuffle", "skip",
        "peek", "sweet_share", "half_exchange", "protect", "move", "conveyor_start",
        "market_conveyor", "safe", "finish",
    }
    routed_events = [event for item in animations for event in item["eventTypes"]]
    require(set(routed_events) == expected_events, "public animation event routing is incomplete")
    require(len(routed_events) == len(set(routed_events)), "an animation event is routed more than once")
    layers = catalog["layers"]
    require(layers["animationPlane"]["zIndex"] < layers["seatRing"]["zIndex"], "animation plane must stay below seats")
    require(layers["seatRing"]["zIndex"] < layers["marketCore"]["zIndex"], "seats must stay below controls")
    require(layers["marketCore"]["zIndex"] < layers["selfHand"]["zIndex"], "controls must stay below the self hand")
    require(layers["selfHand"]["zIndex"] < layers["modalOverlay"]["zIndex"], "self hand must stay below modals")
    require(layers["animationPlane"]["pointerEvents"] == "none", "animation plane cannot capture input")
    require(layers["animationPlane"]["overflow"] == "hidden", "animation plane must clip moving cards")
    frontend = (FRONTEND_ROOT / "GameView.vue").read_text(encoding="utf-8")
    for event in expected_events:
        require(f"'{event}'" in frontend, f"frontend animation mapper is missing {event}")


def validate_runtime_contracts() -> None:
    game_schema = load_json(MODEL_ROOT / "game-state.schema.json")
    view_schema = load_json(MODEL_ROOT / "view-state.schema.json")
    for name, schema in (("game", game_schema), ("view", view_schema)):
        require(schema["properties"]["schemaVersion"]["const"] == 1, f"{name} schema version must be 1")
        require(schema["properties"]["gameKey"]["const"] == "spoiled-fruit", f"{name} game key changed")
        require(set(schema["required"]).issubset(schema["properties"]), f"{name} schema requires undeclared fields")
    card_fields = set(view_schema["$defs"]["cardView"]["properties"])
    require(
        {"instanceId", "catalogId", "effectTextZh", "slug"}.issubset(card_fields),
        "view card contract is missing rendered card data",
    )


def validate_implementation() -> None:
    manifest = load_json(PLUGIN_ROOT / "manifest.json")
    require(manifest["id"] == "plugin-spoiled-fruit", "plugin id changed")
    require(manifest["players"] == {"min": 4, "max": 8, "label": "4–8 人"}, "manifest player range changed")
    require(manifest["roomLayout"] == "immersive", "plugin must use the immersive room layout")
    require(manifest["defaultOptions"].get("mode") == "standard", "standard must be the only default mode")
    required_files = (
        "backend/plugin.py", "backend/engine.py", "frontend/GameView.vue",
        "frontend/components/FruitCard.vue", "frontend/assets/catalog-dark.webp",
        "frontend/assets/catalog-light.webp", "docs/RULEBOOK.md",
    )
    for relative in required_files:
        path = PLUGIN_ROOT / relative
        require(path.is_file() and path.stat().st_size > 0, f"missing implementation file: {relative}")
    frontend_catalog = (FRONTEND_ROOT / "catalog.ts").read_text(encoding="utf-8")
    cards = load_json(MODEL_ROOT / "card-catalog.json")["cards"]
    for card in cards:
        filename = Path(card["asset"]).name
        require(filename in frontend_catalog, f"frontend card art mapping is missing {filename}")
    require("scene-runtime-market-table-8p.png" in frontend_catalog, "frontend runtime table art is missing")


def validate_assets() -> None:
    manifest_path = ASSET_ROOT / "asset-manifest.json"
    require(manifest_path.is_file(), "run scripts/build_asset_manifest.py first")
    manifest = load_json(manifest_path)
    assets = manifest["assets"]
    require(manifest["assetCount"] == 44, "asset manifest must contain 44 generated PNG files")
    require(len(assets) == 44, "asset entry count must be 44")

    card_assets = [asset for asset in assets if asset["kind"] == "card"]
    scene_assets = [asset for asset in assets if asset["kind"] == "scene"]
    require(len(card_assets) == 35, "expected 30 fruits + 4 old maids + 1 card back")
    require(len(scene_assets) == 9, "expected seven original concepts + runtime table + updated four-Old-Maid finale")
    actual_paths = {
        path.relative_to(PLUGIN_ROOT).as_posix()
        for folder in (ASSET_ROOT / "cards", ASSET_ROOT / "scenes")
        for path in folder.glob("*.png")
    }
    require({asset["path"] for asset in assets} == actual_paths, "asset manifest paths are stale")

    for asset in assets:
        path = PLUGIN_ROOT / asset["path"]
        require(path.is_file(), f"manifest path missing: {asset['path']}")
        require(path.stat().st_size == asset["bytes"], f"byte size changed: {asset['path']}")
        require(sha256(path) == asset["sha256"], f"hash changed: {asset['path']}")
        if path.name.startswith(("fruit-", "old-maid-")):
            require(asset["width"] == 1254 and asset["height"] == 1254, f"unexpected fruit size: {path.name}")
            require(asset["mode"] == "RGBA" and asset["alphaExtrema"] == [0, 255], f"invalid alpha: {path.name}")
        if path.name.startswith("scene-"):
            require(asset["width"] == 1672 and asset["height"] == 941, f"unexpected scene size: {path.name}")


def validate_docs() -> None:
    rulebook = (PLUGIN_ROOT / "docs" / "RULEBOOK.md").read_text(encoding="utf-8")
    effect_catalog = (MODEL_ROOT / "effect-catalog.json").read_text(encoding="utf-8")
    require("转个弯" not in rulebook, "legacy effect name remains in rulebook")
    require("转个弯" not in effect_catalog, "legacy effect name remains in effect catalog")
    require("摇匀果篮" in rulebook, "new effect name missing from rulebook")
    require("开局弃掉的所有对子均不发动技能" in rulebook, "initial no-trigger rule missing")


def validate_json_syntax() -> None:
    for path in sorted(MODEL_ROOT.glob("*.json")):
        load_json(path)
    load_json(PLUGIN_ROOT / "manifest.json")


def main() -> None:
    validate_json_syntax()
    validate_implementation()
    validate_runtime_contracts()
    normal_ids, card_effect_ids = validate_cards()
    effect_ids = validate_effects(normal_ids)
    require(card_effect_ids == effect_ids, "card and effect catalogs disagree on effect ids")
    validate_scenes(effect_ids)
    validate_animations()
    validate_assets()
    validate_docs()
    print("spoiled-fruit models valid: 60 normal cards, 4 old maids, 10 effects, 7 live scenes, 44 images")


if __name__ == "__main__":
    main()
