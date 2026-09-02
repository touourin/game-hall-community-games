#!/usr/bin/env python3
"""Validate Skull model JSON, cross-field invariants, and SVG syntax.

The script intentionally uses only the Python standard library so the design
package can be checked before it becomes a full game-hall plugin.
"""

from __future__ import annotations

import json
import hashlib
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "model"
EXAMPLE_DIR = ROOT / "examples"
ASSET_DIR = ROOT / "assets"

PHASES = {
    "round_setup",
    "placement",
    "bidding",
    "reveal",
    "penalty",
    "round_end",
    "finished",
}

ACTION_NAMES = {
    "commit_initial",
    "place_disc",
    "open_bid",
    "raise_bid",
    "pass_bid",
    "reveal_disc",
    "choose_penalty",
    "choose_self_penalty",
    "choose_next_first",
    "show_unrevealed",
}


class ValidationFailure(Exception):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationFailure(f"{path.relative_to(ROOT)}: invalid JSON: {exc}") from exc


def json_type_matches(value: Any, type_name: str) -> bool:
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "null":
        return value is None
    return True


def resolve_ref(root_schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValidationFailure(f"unsupported non-local schema reference: {ref}")
    target: Any = root_schema
    for raw_part in ref[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        target = target[part]
    if not isinstance(target, dict):
        raise ValidationFailure(f"schema reference does not resolve to an object: {ref}")
    return target


def schema_errors(
    value: Any,
    schema: dict[str, Any],
    root_schema: dict[str, Any],
    path: str = "$",
) -> list[str]:
    """Validate the JSON Schema subset used by this package."""

    if "$ref" in schema:
        return schema_errors(value, resolve_ref(root_schema, schema["$ref"]), root_schema, path)

    errors: list[str] = []

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}, got {value!r}")

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} is not in {schema['enum']!r}")

    expected_types = schema.get("type")
    if isinstance(expected_types, str):
        expected_types = [expected_types]
    if expected_types and not any(json_type_matches(value, item) for item in expected_types):
        errors.append(f"{path}: expected type {expected_types}, got {type(value).__name__}")
        return errors

    if "oneOf" in schema:
        variants = [schema_errors(value, variant, root_schema, path) for variant in schema["oneOf"]]
        valid_count = sum(not variant_errors for variant_errors in variants)
        if valid_count != 1:
            errors.append(f"{path}: expected exactly one oneOf branch, matched {valid_count}")

    for part in schema.get("allOf", []):
        errors.extend(schema_errors(value, part, root_schema, path))

    if "if" in schema:
        condition_errors = schema_errors(value, schema["if"], root_schema, path)
        if not condition_errors and "then" in schema:
            errors.extend(schema_errors(value, schema["then"], root_schema, path))
        elif condition_errors and "else" in schema:
            errors.extend(schema_errors(value, schema["else"], root_schema, path))

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required property {key!r}")

        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extras = sorted(set(value) - set(properties))
            for key in extras:
                errors.append(f"{path}: unexpected property {key!r}")

        for key, child_schema in properties.items():
            if key in value:
                errors.extend(
                    schema_errors(value[key], child_schema, root_schema, f"{path}.{key}")
                )

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: needs at least {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: allows at most {schema['maxItems']} items")
        if schema.get("uniqueItems"):
            normalized = [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in value]
            if len(normalized) != len(set(normalized)):
                errors.append(f"{path}: items must be unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(schema_errors(item, item_schema, root_schema, f"{path}[{index}]"))

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: string is shorter than {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: string is longer than {schema['maxLength']}")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            errors.append(f"{path}: {value!r} does not match {schema['pattern']!r}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} is below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} is above maximum {schema['maximum']}")

    return errors


def validate_schema_document(path: Path, schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        errors.append(f"{path.name}: schema must declare JSON Schema draft 2020-12")
    if "$defs" not in schema or not isinstance(schema["$defs"], dict):
        errors.append(f"{path.name}: schema must contain an object-valued $defs")

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str):
                try:
                    resolve_ref(schema, ref)
                except (KeyError, TypeError, ValidationFailure) as exc:
                    errors.append(f"{path.name}: broken $ref {ref!r}: {exc}")
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(schema)
    return errors


def player_discs(player: dict[str, Any]) -> list[dict[str, Any]]:
    return [*player["hand"], *player["stack"], *player["removed"]]


def validate_internal_state(state: dict[str, Any], filename: str) -> list[str]:
    errors: list[str] = []
    label = filename
    players = state["players"]
    player_ids = [player["id"] for player in players]
    seats = [player["seat"] for player in players]

    if len(player_ids) != len(set(player_ids)):
        errors.append(f"{label}: player ids must be unique")
    if len(seats) != len(set(seats)):
        errors.append(f"{label}: seats must be unique")

    all_discs: list[dict[str, Any]] = list(state["sharedDiscs"])
    owner_by_disc: dict[str, str | None] = {disc["id"]: None for disc in state["sharedDiscs"]}

    for player in players:
        personal = [disc for disc in player_discs(player) if disc["origin"] == "personal"]
        kinds = Counter(disc["kind"] for disc in personal)
        if len(personal) != 4 or kinds != Counter({"flower": 3, "skull": 1}):
            errors.append(
                f"{label}: {player['id']} must retain a 3-flower/1-skull personal set across all zones"
            )

        active_personal = [
            disc
            for disc in [*player["hand"], *player["stack"]]
            if disc["origin"] == "personal"
        ]
        if player["status"] == "eliminated" and active_personal:
            errors.append(f"{label}: eliminated player {player['id']} still has active personal discs")

        expected_mat = "flower" if player["challengeWins"] >= 1 else "blank"
        if player["matSide"] != expected_mat:
            errors.append(f"{label}: {player['id']} mat side does not match challenge wins")

        if any(disc["faceUp"] for disc in player["hand"]):
            errors.append(f"{label}: {player['id']} has a face-up disc in hand")
        if any(disc["faceUp"] for disc in player["removed"]):
            errors.append(f"{label}: {player['id']} has a publicly face-up removed disc")

        for disc in player_discs(player):
            all_discs.append(disc)
            if disc["id"] in owner_by_disc:
                errors.append(f"{label}: duplicate disc id {disc['id']}")
            owner_by_disc[disc["id"]] = player["id"]

    disc_ids = [disc["id"] for disc in all_discs]
    if len(disc_ids) != len(set(disc_ids)):
        errors.append(f"{label}: every disc id must appear in exactly one zone")

    last_chance = [disc for disc in all_discs if disc["origin"] == "last_chance"]
    expected_last_chance = 1 if state["rules"]["lastChanceEnabled"] else 0
    if len(last_chance) != expected_last_chance:
        errors.append(f"{label}: expected {expected_last_chance} last-chance disc, found {len(last_chance)}")

    round_state = state["roundState"]
    active_ids = {player["id"] for player in players if player["status"] == "active"}
    known_ids = set(player_ids)
    for ref_name in ("firstPlayerId", "currentPlayerId", "lastChanceHolderId"):
        ref = round_state[ref_name]
        if ref is not None and ref not in known_ids:
            errors.append(f"{label}: {ref_name} references unknown player {ref!r}")
    if round_state["firstPlayerId"] not in active_ids:
        errors.append(f"{label}: first player must be active")

    actual_placed = sum(len(player["stack"]) for player in players)
    if round_state["totalPlaced"] != actual_placed:
        errors.append(
            f"{label}: totalPlaced is {round_state['totalPlaced']}, but stacks contain {actual_placed}"
        )

    bid = round_state["bid"]
    if state["phase"] in {"bidding", "reveal", "penalty", "round_end"}:
        if not 1 <= bid["currentBid"] <= max(1, actual_placed):
            errors.append(f"{label}: active bid is outside the legal table range")
        if bid["highBidderId"] not in active_ids:
            errors.append(f"{label}: high bidder must be active")
    elif bid["currentBid"] != 0 or bid["highBidderId"] is not None:
        errors.append(f"{label}: pre-bid state must have zero bid and no high bidder")

    if not set(bid["passedPlayerIds"]).issubset(active_ids):
        errors.append(f"{label}: passedPlayerIds contains a non-active player")
    for player in players:
        expected_passed = player["id"] in bid["passedPlayerIds"]
        if player["passedBid"] != expected_passed:
            errors.append(f"{label}: {player['id']} passedBid disagrees with bid state")

    challenge = round_state["challenge"]
    if challenge["challengerId"] is not None and challenge["challengerId"] not in active_ids:
        errors.append(f"{label}: challenger must be active")
    if challenge["targetBid"] > actual_placed:
        errors.append(f"{label}: challenge target exceeds cards in play")
    for disc_id in challenge["revealedDiscIds"]:
        if disc_id not in owner_by_disc:
            errors.append(f"{label}: revealed disc {disc_id!r} does not exist")
        else:
            disc = next(item for item in all_discs if item["id"] == disc_id)
            if not disc["faceUp"]:
                errors.append(f"{label}: revealed disc {disc_id!r} is not face up")

    failed_id = challenge["failedDiscId"]
    if failed_id is not None:
        failed_disc = next((item for item in all_discs if item["id"] == failed_id), None)
        if failed_disc is None or failed_disc["kind"] != "skull":
            errors.append(f"{label}: failedDiscId must identify a skull")
        elif owner_by_disc[failed_id] != challenge["skullOwnerId"]:
            errors.append(f"{label}: skullOwnerId does not own failedDiscId")

    penalty = challenge["pendingPenalty"]
    if state["phase"] == "penalty" and penalty is None:
        errors.append(f"{label}: penalty phase requires pendingPenalty")
    if penalty is not None:
        challenger_id = penalty["challengerId"]
        challenger = next((player for player in players if player["id"] == challenger_id), None)
        if challenger is None:
            errors.append(f"{label}: pending penalty challenger does not exist")
        else:
            personal_ids = {
                disc["id"]
                for disc in player_discs(challenger)
                if disc["origin"] == "personal" and disc not in challenger["removed"]
            }
            if set(penalty["candidateDiscIds"]) != personal_ids:
                errors.append(f"{label}: penalty candidates must be all remaining challenger personal discs")
        if penalty["mode"] == "blind":
            if penalty["chooserId"] != challenge["skullOwnerId"]:
                errors.append(f"{label}: blind chooser must be the revealed skull owner")
            if len(penalty["opaqueSlots"]) != len(penalty["candidateDiscIds"]):
                errors.append(f"{label}: blind penalty needs one opaque slot per candidate")

    holder_id = round_state["lastChanceHolderId"]
    last_chance_owner = owner_by_disc.get("last-chance")
    if holder_id is None:
        if state["rules"]["lastChanceEnabled"] and last_chance_owner is not None:
            errors.append(f"{label}: last-chance disc is held but holder id is null")
        if round_state["lastChanceExpiresAfterRound"] is not None:
            errors.append(f"{label}: last-chance expiry exists without a holder")
    else:
        holder = next(player for player in players if player["id"] == holder_id)
        if last_chance_owner != holder_id:
            errors.append(f"{label}: last-chance disc is not located with the declared holder")
        if not holder["lastChanceUsed"]:
            errors.append(f"{label}: holder must be marked as having used their once-per-game chance")
        if round_state["lastChanceExpiresAfterRound"] != round_state["number"]:
            errors.append(f"{label}: last-chance disc must expire after the current round")

    if state["phase"] == "finished":
        if state["result"] is None:
            errors.append(f"{label}: finished state requires a result")
    elif state["result"] is not None:
        errors.append(f"{label}: non-finished state cannot contain a result")

    return errors


def validate_view_state(state: dict[str, Any], filename: str) -> list[str]:
    errors: list[str] = []
    label = filename
    viewer = state["viewer"]
    player_ids = {player["id"] for player in state["players"]}

    if viewer["mode"] == "player" and viewer["playerId"] not in player_ids:
        errors.append(f"{label}: player viewer must reference a player in the view")
    if viewer["mode"] == "public" and viewer["playerId"] is not None:
        errors.append(f"{label}: public viewer must have null playerId")

    all_projected: list[tuple[str | None, str, dict[str, Any]]] = []
    for player in state["players"]:
        if player["handCount"] != len(player["hand"]):
            errors.append(f"{label}: {player['id']} handCount does not match projected hand")
        if player["removedCount"] != len(player["removed"]):
            errors.append(f"{label}: {player['id']} removedCount does not match projected removed zone")
        for zone in ("hand", "stack", "removed"):
            all_projected.extend((player["id"], zone, disc) for disc in player[zone])
    all_projected.extend((None, "shared", disc) for disc in state["sharedDiscs"])

    ids = [disc["id"] for _, _, disc in all_projected]
    if len(ids) != len(set(ids)):
        errors.append(f"{label}: projected opaque ids must be unique within one view")

    for owner_id, zone, disc in all_projected:
        knowledge = disc["knowledge"]
        kind = disc["kind"]
        if knowledge == "hidden" and kind != "unknown":
            errors.append(f"{label}: hidden disc {disc['id']} leaks kind {kind}")
        if kind == "unknown" and knowledge != "hidden":
            errors.append(f"{label}: unknown disc {disc['id']} must be marked hidden")
        if disc["faceUp"] and knowledge != "public":
            errors.append(f"{label}: face-up disc {disc['id']} must be public")
        if knowledge == "self":
            if viewer["mode"] != "player" or viewer["playerId"] != owner_id:
                errors.append(f"{label}: self knowledge leaked outside the owning player")
        if viewer["mode"] == "public" and knowledge == "self":
            errors.append(f"{label}: public view contains self-only knowledge")
        if kind == "last_chance_flower" and knowledge != "public":
            errors.append(f"{label}: last-chance disc must always be public knowledge")
        if zone in {"hand", "removed"} and disc["faceUp"]:
            errors.append(f"{label}: {zone} disc {disc['id']} cannot be face up")

    actual_placed = sum(len(player["stack"]) for player in state["players"])
    if state["round"]["totalPlaced"] != actual_placed:
        errors.append(f"{label}: projected totalPlaced does not match stack lengths")

    actions = set(state["actions"])
    if viewer["mode"] == "public" and actions:
        errors.append(f"{label}: public spectator view must be read-only")
    if "choose_penalty" in actions and not state["round"]["penaltySlots"]:
        errors.append(f"{label}: blind chooser needs opaque penalty slots")
    if state["round"]["penaltySlots"] and "choose_penalty" not in actions:
        errors.append(f"{label}: penalty slots must only be sent to the active blind chooser")

    return errors


def validate_catalogs() -> list[str]:
    errors: list[str] = []
    cards = load_json(MODEL_DIR / "card-catalog.json")
    if cards.get("schemaVersion") != 1 or cards.get("gameKey") != "skull":
        errors.append("card-catalog.json: incorrect identity")
    composition = cards.get("personalSet", {}).get("composition", {})
    if composition != {"flower": 3, "skull": 1}:
        errors.append("card-catalog.json: personal set must be exactly 3 flowers and 1 skull")
    if cards.get("sharedSupply", {}).get("lastChanceDiscCount") != 1:
        errors.append("card-catalog.json: shared supply must contain one last-chance disc")
    type_ids = [item.get("id") for item in cards.get("discTypes", [])]
    if set(type_ids) != {"flower", "skull", "last_chance_flower"}:
        errors.append("card-catalog.json: disc type catalog is incomplete")
    themes = cards.get("placeholderThemes", [])
    theme_ids = [item.get("id") for item in themes]
    if len(themes) != 6 or len(theme_ids) != len(set(theme_ids)):
        errors.append("card-catalog.json: exactly six unique placeholder themes are required")

    scenes = load_json(MODEL_DIR / "scene-catalog.json")
    scene_items = scenes.get("scenes", [])
    scene_ids = [item.get("id") for item in scene_items]
    if len(scene_ids) != len(set(scene_ids)):
        errors.append("scene-catalog.json: scene ids must be unique")
    for scene in scene_items:
        if scene.get("phase") not in PHASES:
            errors.append(f"scene-catalog.json: invalid phase for {scene.get('id')}")
        unknown_actions = set(scene.get("actions", [])) - ACTION_NAMES
        if unknown_actions:
            errors.append(
                f"scene-catalog.json: {scene.get('id')} contains unknown actions {sorted(unknown_actions)}"
            )
    required_scenes = {
        "setup.table",
        "round.commit",
        "round.place-or-bid",
        "bid.raise-or-pass",
        "challenge.reveal-own",
        "challenge.reveal-others",
        "penalty.blind-pick",
        "penalty.self-pick",
        "round.summary",
        "game.finished",
    }
    if set(scene_ids) != required_scenes:
        errors.append("scene-catalog.json: expected scene coverage is incomplete or contains extras")

    return errors


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_player_card_models(
    model: dict[str, Any],
    model_schema: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    label = "player-card-models.json"
    errors.extend(f"{label}: {item}" for item in schema_errors(model, model_schema, model_schema))

    players = model.get("players", [])
    seats = [player.get("seatIndex") for player in players]
    ids = [player.get("id") for player in players]
    slugs = [player.get("slug") for player in players]
    patterns = [player.get("accessibility", {}).get("patternCode") for player in players]
    back_motifs = [player.get("back", {}).get("motif") for player in players]
    center_marks = [player.get("back", {}).get("centerMark") for player in players]
    flower_motifs = [player.get("flowerFront", {}).get("motif") for player in players]
    skull_pairs = [
        (
            player.get("skullFront", {}).get("silhouette"),
            player.get("skullFront", {}).get("ornament"),
        )
        for player in players
    ]

    if seats != list(range(6)):
        errors.append(f"{label}: players must be ordered by seats 0 through 5")
    if ids != [f"player-{index}" for index in range(1, 7)]:
        errors.append(f"{label}: player ids must map one-to-one to seats")
    for name, values in (
        ("slugs", slugs),
        ("accessibility pattern codes", patterns),
        ("back motifs", back_motifs),
        ("back center marks", center_marks),
        ("flower motifs", flower_motifs),
        ("skull silhouette/ornament pairs", skull_pairs),
    ):
        if len(values) != len(set(values)):
            errors.append(f"{label}: {name} must be unique across all six players")

    for index, player in enumerate(players, start=1):
        expected_pattern = f"{chr(64 + index)}{index}"
        actual_pattern = player.get("accessibility", {}).get("patternCode")
        if actual_pattern != expected_pattern:
            errors.append(
                f"{label}: seat {index} must use accessibility code {expected_pattern}, got {actual_pattern}"
            )

    renderer = model.get("renderer", {})
    if renderer.get("viewBox") != [0, 0, 512, 512] or renderer.get("outputSize") != 512:
        errors.append(f"{label}: renderer must produce 512 x 512 SVG assets")
    radii = [renderer.get("safeRadius", 0), renderer.get("innerRadius", 0), renderer.get("outerRadius", 0)]
    if not radii[0] < radii[1] < radii[2] < renderer.get("center", 0):
        errors.append(f"{label}: radii must satisfy safe < inner < outer < center")

    card_catalog = load_json(MODEL_DIR / "card-catalog.json")
    catalog_refs = [theme.get("playerModelId") for theme in card_catalog.get("placeholderThemes", [])]
    if catalog_refs != ids:
        errors.append("card-catalog.json: placeholder themes must reference all player models in seat order")
    if card_catalog.get("playerCardModelRef") != "./player-card-models.json":
        errors.append("card-catalog.json: playerCardModelRef is missing or incorrect")

    asset_root = ASSET_DIR / "player-cards"
    generated_dir = asset_root / "generated"
    manifest_path = asset_root / "manifest.json"
    atlas_path = asset_root / "player-card-atlas.svg"
    if not manifest_path.is_file():
        return [*errors, "assets/player-cards/manifest.json: missing generated manifest"]
    manifest = load_json(manifest_path)
    if manifest.get("modelVersion") != model.get("modelVersion"):
        errors.append("player-cards/manifest.json: model version does not match canonical model")
    if manifest.get("generatorVersion") != renderer.get("generatorVersion"):
        errors.append("player-cards/manifest.json: generator version does not match model")
    canonical_text = (MODEL_DIR / "player-card-models.json").read_text(encoding="utf-8")
    if manifest.get("sourceSha256") != sha256_text(canonical_text):
        errors.append("player-cards/manifest.json: source model hash is stale")
    if manifest.get("assetCount") != 18:
        errors.append("player-cards/manifest.json: assetCount must be 18")

    expected_names: set[str] = set()
    manifest_asset_paths: set[str] = set()
    generated_hashes: dict[str, list[str]] = {"back": [], "flower": [], "skull": []}
    manifest_players = manifest.get("players", [])
    if len(manifest_players) != 6:
        errors.append("player-cards/manifest.json: expected six player entries")
    for player in players:
        seat = player["seatIndex"] + 1
        entry = next((item for item in manifest_players if item.get("id") == player["id"]), None)
        if entry is None:
            errors.append(f"player-cards/manifest.json: missing {player['id']}")
            continue
        if entry.get("patternCode") != player["accessibility"]["patternCode"]:
            errors.append(f"player-cards/manifest.json: stale pattern code for {player['id']}")
        assets = entry.get("assets", {})
        if set(assets) != {"back", "flower", "skull"}:
            errors.append(f"player-cards/manifest.json: {player['id']} needs back, flower, and skull")
            continue
        for face in ("back", "flower", "skull"):
            filename = f"seat-{seat}-{player['slug']}-{face}.svg"
            expected_names.add(filename)
            rel_path = f"generated/{filename}"
            manifest_asset_paths.add(assets[face].get("path", ""))
            if assets[face].get("path") != rel_path:
                errors.append(f"player-cards/manifest.json: incorrect path for {player['id']} {face}")
            asset_path = asset_root / rel_path
            if not asset_path.is_file():
                errors.append(f"assets/player-cards/{rel_path}: missing generated SVG")
                continue
            content = asset_path.read_text(encoding="utf-8")
            content_hash = sha256_text(content)
            generated_hashes[face].append(content_hash)
            if assets[face].get("sha256") != content_hash:
                errors.append(f"assets/player-cards/{rel_path}: hash differs from manifest")
            try:
                svg_root = ET.fromstring(content)
            except ET.ParseError as exc:
                errors.append(f"assets/player-cards/{rel_path}: invalid SVG/XML: {exc}")
                continue
            if svg_root.get("width") != "512" or svg_root.get("height") != "512":
                errors.append(f"assets/player-cards/{rel_path}: expected 512 x 512 dimensions")
            if svg_root.get("viewBox") != "0 0 512 512":
                errors.append(f"assets/player-cards/{rel_path}: expected canonical viewBox")
            if f'data-face="{face}"' not in content or f'data-player="{player["id"]}"' not in content:
                errors.append(f"assets/player-cards/{rel_path}: identity metadata is stale")
            if face == "back" and ('data-face="flower"' in content or 'data-face="skull"' in content):
                errors.append(f"assets/player-cards/{rel_path}: back asset leaks a card kind")

    actual_names = {path.name for path in generated_dir.glob("*.svg")} if generated_dir.is_dir() else set()
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        extra = sorted(actual_names - expected_names)
        errors.append(f"assets/player-cards/generated: missing={missing}, extra={extra}")
    if manifest_asset_paths != {f"generated/{name}" for name in expected_names}:
        errors.append("player-cards/manifest.json: generated asset paths are incomplete")
    for face, hashes in generated_hashes.items():
        if len(hashes) != 6 or len(set(hashes)) != 6:
            errors.append(f"assets/player-cards/generated: all six {face} assets must be distinct")
    all_hashes = [item for hashes in generated_hashes.values() for item in hashes]
    if len(all_hashes) != 18 or len(set(all_hashes)) != 18:
        errors.append("assets/player-cards/generated: all 18 generated face/back files must be distinct")

    if not atlas_path.is_file():
        errors.append("assets/player-cards/player-card-atlas.svg: missing atlas")
    else:
        atlas = atlas_path.read_text(encoding="utf-8")
        atlas_info = manifest.get("atlas", {})
        if atlas_info.get("sha256") != sha256_text(atlas):
            errors.append("assets/player-cards/player-card-atlas.svg: hash differs from manifest")
        try:
            atlas_root = ET.fromstring(atlas)
        except ET.ParseError as exc:
            errors.append(f"assets/player-cards/player-card-atlas.svg: invalid SVG/XML: {exc}")
        else:
            if atlas_root.get("width") != "1900" or atlas_root.get("height") != "1090":
                errors.append("assets/player-cards/player-card-atlas.svg: unexpected dimensions")
        for player in players:
            for face in ("back", "flower", "skull"):
                marker = f'data-player="{player["id"]}" data-face="{face}"'
                if marker not in atlas:
                    errors.append(f"player-card-atlas.svg: missing {player['id']} {face}")

    return errors


def validate_assets_and_docs() -> list[str]:
    errors: list[str] = []
    expected = [
        ROOT / "README.md",
        ROOT / "SOURCES.md",
        ROOT / "docs" / "RULEBOOK.md",
        ROOT / "docs" / "SCENE_MODEL.md",
        ROOT / "docs" / "PLAYER_CARD_MODEL.md",
        ASSET_DIR / "card-components.svg",
        ASSET_DIR / "table-scene.svg",
    ]
    for path in expected:
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing or empty required file: {path.relative_to(ROOT)}")

    for svg in ASSET_DIR.rglob("*.svg"):
        try:
            root = ET.parse(svg).getroot()
        except ET.ParseError as exc:
            errors.append(f"{svg.name}: invalid SVG/XML: {exc}")
            continue
        if not root.tag.endswith("svg"):
            errors.append(f"{svg.name}: root element is not svg")

    rulebook = (ROOT / "docs" / "RULEBOOK.md").read_text(encoding="utf-8")
    for source_host in ("spacecowboys-games.com", "asmodee.com.cn", "skull-and-roses.com"):
        if source_host not in rulebook:
            errors.append(f"RULEBOOK.md: missing human-readable source link for {source_host}")
    return errors


def main() -> int:
    errors: list[str] = []

    game_schema_path = MODEL_DIR / "game-state.schema.json"
    view_schema_path = MODEL_DIR / "view-state.schema.json"
    card_model_schema_path = MODEL_DIR / "player-card-model.schema.json"
    game_schema = load_json(game_schema_path)
    view_schema = load_json(view_schema_path)
    card_model_schema = load_json(card_model_schema_path)
    errors.extend(validate_schema_document(game_schema_path, game_schema))
    errors.extend(validate_schema_document(view_schema_path, view_schema))
    errors.extend(validate_schema_document(card_model_schema_path, card_model_schema))

    internal_count = 0
    view_count = 0
    for path in sorted(EXAMPLE_DIR.glob("*.json")):
        state = load_json(path)
        if "viewer" in state:
            view_count += 1
            errors.extend(f"{path.name}: {item}" for item in schema_errors(state, view_schema, view_schema))
            errors.extend(validate_view_state(state, path.name))
        else:
            internal_count += 1
            errors.extend(f"{path.name}: {item}" for item in schema_errors(state, game_schema, game_schema))
            errors.extend(validate_internal_state(state, path.name))

    errors.extend(validate_catalogs())
    card_model = load_json(MODEL_DIR / "player-card-models.json")
    errors.extend(validate_player_card_models(card_model, card_model_schema))
    errors.extend(validate_assets_and_docs())

    if errors:
        print(f"Skull model validation failed with {len(errors)} issue(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        "Skull model validation passed: "
        f"3 schemas, {internal_count} authoritative examples, {view_count} safe-view examples, "
        "3 catalogs/models, 18 generated player cards, 3 overview SVG assets."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
