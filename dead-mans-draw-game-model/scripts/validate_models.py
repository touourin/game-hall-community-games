#!/usr/bin/env python3
"""Validate JSON Schemas and cross-model invariants for Dead Man's Draw."""

from __future__ import annotations

import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as exc:  # pragma: no cover - dependency diagnostic
    raise SystemExit("jsonschema is required: install it with `python -m pip install jsonschema`") from exc


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "model"
EXAMPLE_DIR = ROOT / "examples"
ASSET_DIR = ROOT / "assets"

EXPECTED_SUITS = [
    "anchor",
    "hook",
    "cannon",
    "key",
    "chest",
    "map",
    "oracle",
    "sword",
    "kraken",
    "mermaid",
]


class ValidationFailure(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationFailure(f"Cannot read {path.relative_to(ROOT)}: {exc}") from exc


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def combined_source_sha() -> str:
    data = (MODEL_DIR / "card-catalog.json").read_bytes()
    data += b"\n" + (MODEL_DIR / "scene-catalog.json").read_bytes()
    return hashlib.sha256(data).hexdigest()


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def unique(values: Iterable[str], label: str) -> list[str]:
    items = list(values)
    assert_true(len(items) == len(set(items)), f"{label} contains duplicate IDs")
    return items


def schema_validate(data_path: Path, schema_path: Path) -> dict[str, Any]:
    data = load_json(data_path)
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(data), key=lambda item: list(item.absolute_path))
    if errors:
        messages = []
        for error in errors[:12]:
            location = "/".join(str(part) for part in error.absolute_path) or "<root>"
            messages.append(f"  - {location}: {error.message}")
        suffix = f"\n  ... {len(errors) - 12} more" if len(errors) > 12 else ""
        raise ValidationFailure(
            f"Schema validation failed for {data_path.relative_to(ROOT)}:\n"
            + "\n".join(messages)
            + suffix
        )
    return data


def card_id(suit_id: str, value: int) -> str:
    return f"loot-{suit_id}-{value}"


def split_card_id(value: str) -> tuple[str, int]:
    stem, raw_value = value.removeprefix("loot-").rsplit("-", 1)
    return stem, int(raw_value)


def expected_pool(catalog: dict[str, Any], profile_id: str) -> set[str]:
    value_key = "mermaidVariant" if profile_id == "tabletop_mermaid_variant" else "base"
    return {
        card_id(suit["id"], value)
        for suit in catalog["suits"]
        for value in suit["values"][value_key]
    }


def validate_catalog(catalog: dict[str, Any]) -> None:
    suits = catalog["suits"]
    suit_ids = unique((suit["id"] for suit in suits), "suits")
    assert_true(suit_ids == EXPECTED_SUITS, f"suit order must be {EXPECTED_SUITS}")
    assert_true(len(suits) == catalog["componentSummary"]["suits"] == 10, "expected ten suits")

    base_cards = expected_pool(catalog, "tabletop_base_2015")
    mermaid_cards = expected_pool(catalog, "tabletop_mermaid_variant")
    assert_true(len(base_cards) == 60, "base catalog must derive exactly 60 loot cards")
    assert_true(len(mermaid_cards) == 60, "Mermaid profile must derive exactly 60 loot cards")
    for suit in suits:
        assert_true(len(suit["values"]["base"]) == 6, f"{suit['id']} must have six base values")
        assert_true(suit["values"]["base"] == sorted(suit["values"]["base"]), f"{suit['id']} base values must be sorted")
        assert_true(suit["values"]["mermaidVariant"] == sorted(suit["values"]["mermaidVariant"]), f"{suit['id']} Mermaid values must be sorted")

    trait_ids = unique((trait["id"] for trait in catalog["traits"]), "base traits")
    assert_true(len(trait_ids) == 17, "expected 17 base traits")
    assert_true(catalog["mermaidVariant"]["addedTrait"]["id"] == "trait-siren", "Mermaid variant must add Siren")
    assert_true(catalog["mermaidVariant"]["removedLootCardIds"] == ["loot-mermaid-8", "loot-mermaid-9"], "Mermaid removals changed")
    assert_true(catalog["mermaidVariant"]["addedLootCardIds"] == ["loot-mermaid-2", "loot-mermaid-3"], "Mermaid additions changed")
    assert_true(base_cards - mermaid_cards == set(catalog["mermaidVariant"]["removedLootCardIds"]), "Mermaid removed cards do not match value sets")
    assert_true(mermaid_cards - base_cards == set(catalog["mermaidVariant"]["addedLootCardIds"]), "Mermaid added cards do not match value sets")

    variant_ids = unique((variant["id"] for variant in catalog["variants"]), "variants")
    assert_true(len(variant_ids) == 7, "expected seven official-web variants")
    assert_true(sum(bool(item["requiresDigitalRuling"]) for item in catalog["variants"]) == 1, "exactly one variant should require a digital ruling")


def validate_profiles(profiles: dict[str, Any], catalog: dict[str, Any]) -> None:
    profile_ids = unique((profile["id"] for profile in profiles["profiles"]), "profiles")
    assert_true(set(profile_ids) == {"tabletop_base_2015", "digital_safe_2014", "tabletop_mermaid_variant"}, "profile IDs changed")
    assert_true(profiles["defaultProfileId"] in profile_ids, "default profile is missing")
    variant_ids = {item["id"] for item in catalog["variants"]}
    trait_ids = {item["id"] for item in catalog["traits"]} | {catalog["mermaidVariant"]["addedTrait"]["id"]}
    profile_map = {item["id"]: item for item in profiles["profiles"]}
    for profile in profiles["profiles"]:
        assert_true(set(profile["allowedVariantIds"]) == variant_ids, f"{profile['id']} variant list must match catalog")
    assert_true(profile_map["tabletop_base_2015"]["mermaidValues"] == [4, 5, 6, 7, 8, 9], "base Mermaid values changed")
    assert_true(profile_map["tabletop_mermaid_variant"]["mermaidValues"] == [2, 3, 4, 5, 6, 7], "variant Mermaid values changed")
    assert_true(profile_map["digital_safe_2014"]["forcedChoicePolicy"] == "filter-immediate-bust", "digital safe policy changed")

    known_rule_ids = variant_ids | trait_ids
    for conflict in profiles["conflicts"]:
        assert_true(conflict["left"] in known_rule_ids, f"unknown conflict left: {conflict['left']}")
        assert_true(conflict["right"] in known_rule_ids, f"unknown conflict right: {conflict['right']}")
    orders = [item["order"] for item in profiles["priorityRules"]]
    assert_true(orders == list(range(1, len(orders) + 1)), "priority rule order must be contiguous from one")


def validate_scene(scene: dict[str, Any]) -> None:
    zone_ids = unique((zone["id"] for zone in scene["zones"]), "scene zones")
    zone_set = set(zone_ids)
    for zone in scene["zones"]:
        rect = zone["rect"]
        assert_true(rect["x"] + rect["width"] <= 1.000001, f"zone {zone['id']} exceeds canvas width")
        assert_true(rect["y"] + rect["height"] <= 1.000001, f"zone {zone['id']} exceeds canvas height")
    for layout in scene["seatLayouts"]:
        seats = layout["seats"]
        assert_true(len(seats) == layout["playerCount"], f"seat count mismatch for {layout['playerCount']} players")
        assert_true({seat["relativeSeat"] for seat in seats} == set(range(layout["playerCount"])), f"relative seats mismatch for {layout['playerCount']} players")
        assert_true(all(seat["zoneId"] in zone_set for seat in seats), f"seat layout references unknown zone for {layout['playerCount']} players")
    scene_ids = unique((item["id"] for item in scene["scenes"]), "scenes")
    expected_scenes = {"trait_selection", "turn_ready", "effect_choice", "forced_draw", "bust_resolution", "collect_resolution", "finished"}
    assert_true(set(scene_ids) == expected_scenes, "stable scene set changed")
    for item in scene["scenes"]:
        assert_true(set(item["requiredZones"]).issubset(zone_set), f"scene {item['id']} references an unknown zone")
    for cue in scene["animationCues"]:
        assert_true(cue["fromZone"] is None or cue["fromZone"] in zone_set, f"cue {cue['id']} has unknown fromZone")
        assert_true(cue["toZone"] is None or cue["toZone"] in zone_set, f"cue {cue['id']} has unknown toZone")


def state_zone_cards(state: dict[str, Any]) -> list[str]:
    cards = list(state["drawPile"]) + list(state["discardPile"]) + list(state["removedFromGame"])
    cards += [entry["cardId"] for entry in state["playArea"]]
    for player in state["players"]:
        for stack in player["bank"].values():
            cards += stack
    turn = state["turn"]
    if turn is not None:
        cards += turn["mapRevealCardIds"]
        if turn["bustingCardId"] is not None:
            cards.append(turn["bustingCardId"])
    return cards


def validate_internal_state(state: dict[str, Any], catalog: dict[str, Any]) -> None:
    player_ids = unique((player["id"] for player in state["players"]), "state players")
    seats = [player["seat"] for player in state["players"]]
    assert_true(seats == list(range(len(seats))), "player seats must be contiguous and ordered")
    assert_true(state["activePlayerId"] is None or state["activePlayerId"] in player_ids, "active player is unknown")
    cards = state_zone_cards(state)
    unique(cards, "authoritative loot zones")
    expected = expected_pool(catalog, state["rules"]["profileId"])
    assert_true(set(cards) == expected, f"authoritative state must conserve exactly {len(expected)} profile cards")

    for player in state["players"]:
        for suit_id, stack in player["bank"].items():
            parsed = [split_card_id(item) for item in stack]
            assert_true(all(suit == suit_id for suit, _ in parsed), f"{player['id']} bank stack {suit_id} contains another suit")
            values = [value for _, value in parsed]
            assert_true(values == sorted(values, reverse=True), f"{player['id']} bank stack {suit_id} is not descending")
        if player["traitId"] == "trait-davy-jones-locker":
            assert_true(player["lockerTargetId"] in player_ids and player["lockerTargetId"] != player["id"], "Davy Jones target must be one opponent")
        else:
            assert_true(player["lockerTargetId"] is None, "only Davy Jones may have lockerTargetId")

    trait_pool = {item["id"] for item in catalog["traits"]}
    if state["rules"]["profileId"] == "tabletop_mermaid_variant":
        trait_pool.add(catalog["mermaidVariant"]["addedTrait"]["id"])
    trait_locations = list(state["traitDeck"]) + list(state["unusedTraits"])
    for player in state["players"]:
        trait_locations += player["traitOffer"]
        if player["traitId"] is not None:
            trait_locations.append(player["traitId"])
    if state["rules"]["traitsEnabled"]:
        unique(trait_locations, "trait zones")
        assert_true(set(trait_locations) == trait_pool, "trait zones must conserve the selected profile trait pool")

    entry_ids = unique((entry["entryId"] for entry in state["playArea"]), "play entries")
    turn = state["turn"]
    if turn is not None:
        assert_true(turn["actorId"] == state["activePlayerId"], "turn actor must equal active player")
        assert_true(set(turn["protectedEntryIds"]).issubset(set(entry_ids)), "protected entries must exist in play area")
        for entry in state["playArea"]:
            assert_true(entry["protected"] == (entry["entryId"] in turn["protectedEntryIds"]), f"protected flag mismatch for {entry['entryId']}")
        if state["phase"] == "effect_choice":
            assert_true(turn["pendingChoice"] is not None, "effect_choice phase needs pendingChoice")
        if state["phase"] == "turn":
            assert_true(turn["pendingChoice"] is None, "turn phase cannot retain pendingChoice")
    else:
        assert_true(state["phase"] in {"waiting", "trait_selection", "finished"}, "active phase needs turn state")

    if state["rules"]["globalVariantId"] == "variant-thieves-island":
        assert_true(all(player["traitId"] != "trait-davy-jones-locker" for player in state["players"]), "Thieves Island conflicts with Davy Jones")


def recursive_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from recursive_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from recursive_keys(child)


def validate_view(view: dict[str, Any]) -> None:
    forbidden = {"drawPile", "traitDeck", "unusedTraits", "seedSecret", "commitment", "effectQueue", "rng"}
    leaked = forbidden.intersection(recursive_keys(view))
    assert_true(not leaked, f"safe view leaks internal keys: {sorted(leaked)}")
    assert_true(view["discard"]["count"] == len(view["discard"]["cardIds"]), "discard count must match public identities")
    player_ids = {item["id"] for item in view["players"]}
    assert_true(len(player_ids) == len(view["players"]), "view player IDs must be unique")
    for player in view["players"]:
        assert_true(len(player["bank"]) == 10, f"{player['id']} must expose ten bank summaries")
        suits = [item["suit"] for item in player["bank"]]
        assert_true(suits == EXPECTED_SUITS, f"{player['id']} bank summary order changed")
        for stack in player["bank"]:
            assert_true(stack["count"] == len(stack["cardIds"]), f"{player['id']} {stack['suit']} count mismatch")
            if stack["cardIds"]:
                values = [split_card_id(item)[1] for item in stack["cardIds"]]
                assert_true(stack["topValue"] == values[0], f"{player['id']} {stack['suit']} top value mismatch")
            else:
                assert_true(stack["topValue"] is None, f"{player['id']} empty {stack['suit']} must have null topValue")
    if view["viewer"]["mode"] == "spectator":
        assert_true(view["self"] is None, "spectator must not receive private self view")
    else:
        assert_true(view["self"] is not None and view["self"]["playerId"] == view["viewer"]["playerId"], "player self view mismatch")
    turn = view["turn"]
    if turn and turn["pendingChoice"]:
        actor_is_viewer = turn["pendingChoice"]["actorId"] == view["viewer"]["playerId"] and view["viewer"]["mode"] == "player"
        for option in turn["pendingChoice"]["options"]:
            assert_true(option["actionable"] == actor_is_viewer, "option actionable flag does not match viewer")
            assert_true((option["optionId"] is not None) == actor_is_viewer, "only acting player may receive option IDs")


def validate_assets(catalog: dict[str, Any], scene: dict[str, Any]) -> None:
    manifest_path = ASSET_DIR / "manifest.json"
    assert_true(manifest_path.is_file(), "assets/manifest.json missing; run scripts/generate_assets.py")
    manifest = load_json(manifest_path)
    assert_true(manifest["modelVersion"] == catalog["modelVersion"], "asset model version is stale")
    assert_true(manifest["combinedSourceSha256"] == combined_source_sha(), "asset source hash is stale")
    for relative, expected_hash in manifest["sourceFiles"].items():
        source_path = ROOT / relative
        assert_true(source_path.is_file(), f"asset source missing: {relative}")
        assert_true(sha256_file(source_path) == expected_hash, f"asset source hash mismatch: {relative}")
    output_names = set()
    for item in manifest["outputs"]:
        path = ROOT / item["path"]
        assert_true(path.is_file(), f"generated asset missing: {item['path']}")
        assert_true(sha256_file(path) == item["sha256"], f"generated asset hash mismatch: {item['path']}")
        assert_true(path.stat().st_size == item["bytes"], f"generated asset byte count mismatch: {item['path']}")
        ET.parse(path)
        output_names.add(path.name)
    assert_true(output_names == {"loot-card-atlas.svg", "trait-card-atlas.svg", "table-scene.svg"}, "asset output set changed")

    loot_svg = (ASSET_DIR / "loot-card-atlas.svg").read_text(encoding="utf-8")
    trait_svg = (ASSET_DIR / "trait-card-atlas.svg").read_text(encoding="utf-8")
    table_svg = (ASSET_DIR / "table-scene.svg").read_text(encoding="utf-8")
    base_ids = expected_pool(catalog, "tabletop_base_2015")
    assert_true(loot_svg.count("data-card-id=") == 60, "loot atlas must contain 60 card groups")
    assert_true(all(f'data-card-id="{item}"' in loot_svg for item in base_ids), "loot atlas is missing a base card")
    assert_true(trait_svg.count("data-trait-id=") == 17, "trait atlas must contain 17 trait groups")
    assert_true(table_svg.count("data-zone-id=") == len(scene["zones"]), "table scene zone markers do not match scene catalog")


def main() -> int:
    try:
        catalog = schema_validate(MODEL_DIR / "card-catalog.json", MODEL_DIR / "card-catalog.schema.json")
        profiles = schema_validate(MODEL_DIR / "rules-profiles.json", MODEL_DIR / "rules-profiles.schema.json")
        scene = schema_validate(MODEL_DIR / "scene-catalog.json", MODEL_DIR / "scene-catalog.schema.json")
        validate_catalog(catalog)
        validate_profiles(profiles, catalog)
        validate_scene(scene)

        state = schema_validate(EXAMPLE_DIR / "internal-trait-selection.json", MODEL_DIR / "game-state.schema.json")
        validate_internal_state(state, catalog)
        for filename in ["effect-choice-physical-map.json", "anchor-key-chest-bust.json"]:
            schema_validate(EXAMPLE_DIR / filename, MODEL_DIR / "scenario.schema.json")
        view = schema_validate(EXAMPLE_DIR / "player-view-effect-choice.json", MODEL_DIR / "view-state.schema.json")
        validate_view(view)
        validate_assets(catalog, scene)
    except ValidationFailure as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print("Validated 10 suits, 60 loot cards, 17 base traits, 7 variants and 3 rules profiles.")
    print("Validated authoritative state, transition scenarios, safe view and generated SVG assets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
