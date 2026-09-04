from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "model"
EXAMPLE_DIR = ROOT / "examples"
ASSET_DIR = ROOT / "assets"

ERRORS: list[str] = []
CHECKS = 0


def check(condition: bool, message: str) -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        ERRORS.append(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - diagnostic path
        ERRORS.append(f"cannot parse {path.relative_to(ROOT)}: {exc}")
        return {}


def schema_validate(instance: dict[str, Any], schema_path: Path, label: str) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("jsonschema not installed; skipped Draft 2020-12 validation")
        return

    schema = load_json(schema_path)
    try:
        Draft202012Validator.check_schema(schema)
        errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda item: list(item.path))
    except Exception as exc:  # pragma: no cover - diagnostic path
        ERRORS.append(f"schema failure for {label}: {exc}")
        return
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        ERRORS.append(f"{label} at {location}: {error.message}")


def validate_catalog(catalog: dict[str, Any], profiles: dict[str, Any]) -> None:
    cards = catalog.get("cards", [])
    ids = [card.get("id") for card in cards]
    values = [card.get("value") for card in cards]
    opcodes = [card.get("effect", {}).get("opcode") for card in cards]

    check(len(cards) == 11, "card catalog must contain exactly 11 card types")
    check(len(ids) == len(set(ids)), "card type ids must be unique")
    check(set(values) == set(range(10)) | {7.5}, "card values must be 0 through 9 plus Queen 7.5")
    check(len(opcodes) == len(set(opcodes)), "effect opcodes must be unique")
    check(sum(card.get("count", 0) for card in cards) == 21, "current card counts must sum to 21")
    check(sum(card.get("classicCount", 0) for card in cards) == 16, "classic card counts must sum to 16")
    check(sum(card.get("queenVariantCount", 0) for card in cards) == 22, "Queen variant counts must sum to 22")
    check(next((card.get("provenance") for card in cards if card.get("id") == "queen"), None) == "user-directed-variant", "Queen must be marked as a user-directed variant")
    check(all(card.get("provenance") == "official-current" for card in cards if card.get("id") != "queen"), "base card types must be marked official-current")

    by_id = {card["id"]: card for card in cards if "id" in card}
    profile_items = profiles.get("profiles", [])
    profile_ids = [profile.get("id") for profile in profile_items]
    check(set(profile_ids) == {"queen_22", "current_21", "classic_16"}, "rules profiles must be queen_22, current_21 and classic_16")
    check(profiles.get("defaultProfileId") in profile_ids, "default profile must exist")

    expected_targets = {2: 6, 3: 5, 4: 4}
    for profile in profile_items:
        profile_id = profile.get("id", "<missing>")
        counts = profile.get("cardCounts", {})
        expected_field = {
            "queen_22": "queenVariantCount",
            "current_21": "count",
            "classic_16": "classicCount",
        }.get(profile_id, "count")
        check(set(counts) == set(ids), f"{profile_id} cardCounts must cover every card type")
        for card_id, count in counts.items():
            check(card_id in by_id, f"{profile_id} references unknown card type {card_id}")
            if card_id in by_id:
                check(count == by_id[card_id].get(expected_field), f"{profile_id} count mismatch for {card_id}")
        check(sum(counts.values()) == profile.get("deckSize"), f"{profile_id} counts must equal deckSize")

        supported = {str(number) for number in range(profile.get("playerMin", 2), profile.get("playerMax", 1) + 1)}
        favor = profile.get("favorTargetByPlayerCount", {})
        set_aside = profile.get("setup", {}).get("faceUpSetAsideByPlayerCount", {})
        check(set(favor) == supported, f"{profile_id} favor thresholds must match supported player counts")
        check(set(set_aside) == supported, f"{profile_id} setup counts must match supported player counts")
        for number in supported:
            check(favor.get(number) == expected_targets[int(number)], f"{profile_id} has wrong favor target for {number} players")
            check(set_aside.get(number) == (3 if number == "2" else 0), f"{profile_id} has wrong face-up set-aside count for {number} players")

        guesses = profile.get("guardGuessCardTypeIds", [])
        expected_guesses = {card_id for card_id, count in counts.items() if count > 0 and card_id != "guard"}
        check(set(guesses) == expected_guesses, f"{profile_id} guard guesses must be exactly present non-Guard card types")


def validate_authoritative_state(state: dict[str, Any], profiles: dict[str, Any]) -> None:
    profile = next((item for item in profiles.get("profiles", []) if item.get("id") == state.get("profileId")), None)
    check(profile is not None, "authoritative example profile must exist")
    if profile is None:
        return

    registry = state.get("cardRegistry", [])
    registry_map = {item.get("instanceId"): item.get("cardTypeId") for item in registry}
    check(len(registry_map) == len(registry), "authoritative card registry ids must be unique")
    check(len(registry) == profile.get("deckSize"), "authoritative registry size must match profile")
    check(Counter(registry_map.values()) == Counter(profile.get("cardCounts", {})), "authoritative registry type counts must match profile")

    players = state.get("players", [])
    player_ids = [player.get("id") for player in players]
    seats = [player.get("seat") for player in players]
    check(len(player_ids) == len(set(player_ids)), "player ids must be unique")
    check(len(seats) == len(set(seats)), "player seats must be unique")
    check(profile.get("playerMin") <= len(players) <= profile.get("playerMax"), "player count must fit profile")

    locations: list[str] = []
    round_state = state.get("round", {})
    locations.extend(round_state.get("deck", []))
    if round_state.get("reserveCardId") is not None:
        locations.append(round_state["reserveCardId"])
    locations.extend(round_state.get("faceUpSetAside", []))
    pending = round_state.get("pendingChoice")
    if pending:
        locations.extend(pending.get("privateCardIds", []))
    for player in players:
        locations.extend(player.get("hand", []))
        for played in player.get("played", []):
            instance_id = played.get("cardInstanceId")
            locations.append(instance_id)
            check(registry_map.get(instance_id) == played.get("cardTypeId"), f"played card type mismatch for {instance_id}")
        if player.get("roundStatus") == "out":
            check(not player.get("hand"), f"out player {player.get('id')} must not retain a hand")
            check(not player.get("protected"), f"out player {player.get('id')} must not remain protected")

    check(len(locations) == len(set(locations)), "every card instance must appear in only one zone")
    check(set(locations) == set(registry_map), "card zones must conserve every registered instance")
    for instance_id in locations:
        check(instance_id in registry_map, f"zone references unknown card instance {instance_id}")

    refs = [round_state.get("startPlayerId"), round_state.get("currentPlayerId")]
    refs.extend(round_state.get("roundWinnerIds", []))
    refs.extend(state.get("gameWinnerIds", []))
    refs.extend(round_state.get("rewardDeltas", {}).keys())
    for player_id in refs:
        if player_id is not None:
            check(player_id in player_ids, f"state references unknown player {player_id}")

    phase = round_state.get("phase")
    choice_phases = {"effect_choice", "chancellor_choice"}
    check((pending is not None) == (phase in choice_phases), "pendingChoice presence must match choice phase")
    if pending:
        check(pending.get("actorPlayerId") == round_state.get("currentPlayerId"), "choice actor must be current player")
        for player_id in pending.get("candidatePlayerIds", []):
            check(player_id in player_ids, f"choice references unknown player {player_id}")

    for knowledge in round_state.get("privateKnowledge", []):
        for viewer_id in knowledge.get("viewerPlayerIds", []):
            check(viewer_id in player_ids, f"knowledge references unknown viewer {viewer_id}")
        check(knowledge.get("subjectPlayerId") in player_ids, "knowledge subject must be a player")
        check(knowledge.get("cardInstanceId") in registry_map, "knowledge card must be registered")


def walk_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.append(key)
            keys.extend(walk_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            keys.extend(walk_keys(nested))
    return keys


def validate_view(view: dict[str, Any]) -> None:
    forbidden = {"deck", "reserveCardId", "rngCommitment", "rngState", "cardRegistry", "privateCardIds"}
    leaked = forbidden.intersection(walk_keys(view))
    check(not leaked, f"safe view contains forbidden authoritative keys: {sorted(leaked)}")

    viewer = view.get("viewer", {})
    viewer_id = viewer.get("playerId") if viewer.get("kind") == "player" else None
    player_ids = [player.get("id") for player in view.get("players", [])]
    if viewer_id is not None:
        check(viewer_id in player_ids, "player viewer must exist in players")
    for player in view.get("players", []):
        visible = player.get("visibleHand", [])
        if player.get("id") == viewer_id:
            check(len(visible) == player.get("handCount"), "viewer must see every own hand card")
        else:
            check(not visible, f"viewer must not see {player.get('id')} hand")

    pending = view.get("pendingChoice")
    if pending:
        if pending.get("isActor"):
            check(viewer_id == pending.get("actorPlayerId"), "only choice actor may receive actionable choice")
            check(pending.get("choiceId") is not None, "choice actor must receive choiceId")
        else:
            check(pending.get("choiceId") is None, "non-actor must not receive choiceId")
            check(not pending.get("privateCards"), "non-actor must not receive private choice cards")

    for knowledge in view.get("privateInfo", {}).get("knownHands", []):
        check(viewer_id is not None, "spectator must not receive private knowledge")
        check(knowledge.get("subjectPlayerId") in player_ids, "view knowledge subject must exist")


def validate_scene(scene: dict[str, Any]) -> None:
    zones = scene.get("zones", [])
    zone_ids = [zone.get("id") for zone in zones]
    check(len(zone_ids) == len(set(zone_ids)), "scene zone ids must be unique")
    zone_set = set(zone_ids)
    for zone in zones:
        rect = zone.get("rect", {})
        check(rect.get("x", 0) + rect.get("width", 0) <= 1, f"zone {zone.get('id')} exceeds canvas width")
        check(rect.get("y", 0) + rect.get("height", 0) <= 1, f"zone {zone.get('id')} exceeds canvas height")

    layouts = scene.get("seatLayouts", [])
    check({layout.get("playerCount") for layout in layouts} == {2, 3, 4}, "seat layouts must cover 2 through 4 players")
    for layout in layouts:
        seats = layout.get("seats", [])
        relative = [seat.get("relativeSeat") for seat in seats]
        check(len(seats) == layout.get("playerCount"), f"layout {layout.get('playerCount')} seat count mismatch")
        check(relative == list(range(layout.get("playerCount", 0))), f"layout {layout.get('playerCount')} relative seats must be ordered 0..n-1")

    scene_ids = [item.get("id") for item in scene.get("scenes", [])]
    check(len(scene_ids) == len(set(scene_ids)), "scene ids must be unique")
    for item in scene.get("scenes", []):
        for zone_id in item.get("requiredZones", []):
            check(zone_id in zone_set, f"scene {item.get('id')} references unknown zone {zone_id}")
        check(item.get("focusTarget") in zone_set, f"scene {item.get('id')} has unknown focus target")

    cue_ids = [cue.get("id") for cue in scene.get("animationCues", [])]
    check(len(cue_ids) == len(set(cue_ids)), "animation cue ids must be unique")
    for cue in scene.get("animationCues", []):
        for field in ("fromZone", "toZone"):
            zone_id = cue.get(field)
            if zone_id is not None:
                check(zone_id in zone_set, f"cue {cue.get('id')} references unknown zone {zone_id}")


def validate_state_machine(machine: dict[str, Any]) -> None:
    phases = {phase.get("id") for phase in machine.get("phases", [])}
    check(machine.get("initialPhase") in phases, "state machine initial phase must exist")
    check(machine.get("terminalPhase") in phases, "state machine terminal phase must exist")
    check(len(phases) == len(machine.get("phases", [])), "state machine phase ids must be unique")
    for transition in machine.get("transitions", []):
        check(transition.get("from") in phases, f"transition has unknown source {transition.get('from')}")
        check(transition.get("to") in phases, f"transition has unknown target {transition.get('to')}")


def validate_assets(catalog: dict[str, Any]) -> None:
    atlas_path = ASSET_DIR / "card-atlas.svg"
    table_path = ASSET_DIR / "table-scene.svg"
    check(atlas_path.exists(), "card-atlas.svg must be generated")
    check(table_path.exists(), "table-scene.svg must be generated")
    if atlas_path.exists():
        atlas = atlas_path.read_text(encoding="utf-8")
        for card in catalog.get("cards", []):
            check(f'id="card-{card.get("id")}"' in atlas, f"card atlas missing {card.get('id')}")
        check("official" not in atlas.lower() or "非官方" in atlas, "card atlas must retain non-official marker")
    if table_path.exists():
        table = table_path.read_text(encoding="utf-8")
        check('data-player-count="4"' in table, "table scene must identify four-player prototype")
        for seat in range(4):
            check(f'id="seat-{seat}"' in table, f"table scene missing relative seat {seat}")


def validate_docs() -> None:
    required = [
        ROOT / "README.md",
        ROOT / "SOURCES.md",
        ROOT / "docs" / "RULEBOOK.md",
        ROOT / "docs" / "IMPLEMENTATION_PLAN.md",
        ROOT / "docs" / "CARD_MODEL.md",
        ROOT / "docs" / "SCENE_MODEL.md",
    ]
    for path in required:
        check(path.exists() and path.stat().st_size > 500, f"required document missing or too short: {path.relative_to(ROOT)}")
    sources = (ROOT / "SOURCES.md").read_text(encoding="utf-8") if (ROOT / "SOURCES.md").exists() else ""
    check("https://www.zmangames.com/game/love-letter/" in sources, "SOURCES.md must link the official product page")
    check("LL_Rulebook_with_Bag-1.pdf" in sources, "SOURCES.md must link the official rulebook")


def main() -> int:
    catalog = load_json(MODEL_DIR / "card-catalog.json")
    profiles = load_json(MODEL_DIR / "rules-profiles.json")
    scene = load_json(MODEL_DIR / "scene-catalog.json")
    machine = load_json(MODEL_DIR / "state-machine.json")
    state_example = load_json(EXAMPLE_DIR / "game-state-mid-round.json")
    view_example = load_json(EXAMPLE_DIR / "player-view-guard-choice.json")

    schema_validate(catalog, MODEL_DIR / "card-catalog.schema.json", "card-catalog.json")
    schema_validate(profiles, MODEL_DIR / "rules-profiles.schema.json", "rules-profiles.json")
    schema_validate(scene, MODEL_DIR / "scene-catalog.schema.json", "scene-catalog.json")
    schema_validate(state_example, MODEL_DIR / "game-state.schema.json", "game-state-mid-round.json")
    schema_validate(view_example, MODEL_DIR / "view-state.schema.json", "player-view-guard-choice.json")

    validate_catalog(catalog, profiles)
    validate_authoritative_state(state_example, profiles)
    validate_view(view_example)
    validate_scene(scene)
    validate_state_machine(machine)
    validate_assets(catalog)
    validate_docs()

    if ERRORS:
        print(f"FAILED: {len(ERRORS)} issue(s) across {CHECKS} custom checks")
        for error in ERRORS:
            print(f"- {error}")
        return 1
    print(f"OK: 5 JSON documents passed Schema validation and {CHECKS} custom checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
