from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "model"
EXAMPLES = ROOT / "examples"
ASSETS = ROOT / "assets"
MODEL_VERSION = "1.0.0"
FRUIT_IDS = ("banana", "strawberry", "lime", "plum")
EXPECTED_DISTRIBUTION = {1: 5, 2: 3, 3: 3, 4: 2, 5: 1}


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - CLI should show the offending file
        raise ValidationFailure(f"Cannot read JSON {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"{path.name} must contain a JSON object")
    return value


def optional_schema_validation(pairs: list[tuple[Path, Path]]) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("[skip] jsonschema is not installed; semantic checks still run")
        return
    for data_path, schema_path in pairs:
        data = load_json(data_path)
        schema = load_json(schema_path)
        errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda item: list(item.absolute_path))
        if errors:
            first = errors[0]
            location = ".".join(str(part) for part in first.absolute_path) or "<root>"
            raise ValidationFailure(f"Schema failure in {data_path.relative_to(ROOT)} at {location}: {first.message}")
        print(f"[ok] schema {data_path.relative_to(ROOT)}")


def build_instance_index(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for face in catalog["faces"]:
        for copy_index in range(1, int(face["copies"]) + 1):
            instance_id = f"{face['fruitId']}-{face['fruitCount']}-{copy_index:02d}"
            require(instance_id not in index, f"Duplicate generated card instance {instance_id}")
            index[instance_id] = {
                "faceId": face["id"],
                "fruitId": face["fruitId"],
                "fruitCount": int(face["fruitCount"]),
                "copyIndex": copy_index,
            }
    return index


def validate_catalog(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    require(catalog["modelVersion"] == MODEL_VERSION, "Card catalog modelVersion mismatch")
    fruit_ids = [fruit["id"] for fruit in catalog["fruits"]]
    require(tuple(fruit_ids) == FRUIT_IDS, f"Fruit order/ids must be {FRUIT_IDS}")
    require(len(set(fruit_ids)) == 4, "Fruit ids must be unique")

    distribution = {int(row["fruitCount"]): int(row["copies"]) for row in catalog["copyDistribution"]}
    require(distribution == EXPECTED_DISTRIBUTION, f"Copy distribution must be {EXPECTED_DISTRIBUTION}")

    faces = catalog["faces"]
    require(len(faces) == 20, "There must be 20 unique faces")
    require(len({face["id"] for face in faces}) == 20, "Face ids must be unique")
    seen_pairs = {(face["fruitId"], int(face["fruitCount"])) for face in faces}
    expected_pairs = {(fruit_id, count) for fruit_id in FRUIT_IDS for count in range(1, 6)}
    require(seen_pairs == expected_pairs, "Faces must cover every fruit/count pair exactly once")
    for face in faces:
        expected_id = f"face-{face['fruitId']}-{face['fruitCount']}"
        require(face["id"] == expected_id, f"Face id mismatch: expected {expected_id}")
        require(int(face["copies"]) == distribution[int(face["fruitCount"])], f"Copy mismatch for {face['id']}")
        layout = catalog["copyDistribution"][int(face["fruitCount"]) - 1]["layoutId"]
        require(face["layoutId"] == layout, f"Layout mismatch for {face['id']}")

    per_fruit = Counter()
    for face in faces:
        per_fruit[face["fruitId"]] += int(face["copies"])
    require(per_fruit == Counter({fruit_id: 14 for fruit_id in FRUIT_IDS}), f"Each fruit must total 14 cards: {per_fruit}")
    instances = build_instance_index(catalog)
    require(len(instances) == 56, f"Expected 56 instances, got {len(instances)}")
    print("[ok] card catalog: 4 fruits, 20 faces, 56 instances")
    return instances


def validate_profiles(profiles_doc: dict[str, Any]) -> None:
    require(profiles_doc["modelVersion"] == MODEL_VERSION, "Rules profiles modelVersion mismatch")
    require(profiles_doc["defaultProfileId"] == "official_last_bell", "Official last-bell profile must be default")
    profiles = {item["id"]: item for item in profiles_doc["profiles"]}
    require(set(profiles) == {"official_last_bell", "complete_collection"}, "Unexpected rules profiles")
    for profile in profiles.values():
        require(profile["playerMin"] == 2 and profile["playerMax"] == 6, f"Player range mismatch in {profile['id']}")
        require(profile["deckSize"] == 56 and profile["bellTarget"] == 5, f"Core constants mismatch in {profile['id']}")
        require(profile["setup"]["dealAllCards"] is True, "All 56 cards must be dealt")
        require(profile["digital"]["countAssistDefault"] is False, "Faithful mode must not auto-count")
        require(profile["digital"]["staleBellPenalty"] is False, "Stale bells must not be penalized")
    official = profiles["official_last_bell"]
    require(official["ending"]["mode"] == "last-accepted-bell-after-two", "Official ending mismatch")
    require(official["ending"]["twoPlayerStartsArmed"] is True, "Two-player official game must start final-duel armed")
    extended = profiles["complete_collection"]
    require(extended["ending"]["mode"] == "one-player-owns-all-cards", "Extended ending mismatch")
    print("[ok] rule profiles: official last bell + agreed complete collection")


def totals_from_players(players: list[dict[str, Any]], instances: dict[str, dict[str, Any]]) -> dict[str, int]:
    totals = {fruit_id: 0 for fruit_id in FRUIT_IDS}
    for player in players:
        discard = player["discardPile"]
        if discard:
            card = instances[discard[-1]]
            totals[card["fruitId"]] += card["fruitCount"]
    return totals


def validate_authoritative_example(path: Path, instances: dict[str, dict[str, Any]]) -> dict[str, Any]:
    state = load_json(path)
    require(state["modelVersion"] == MODEL_VERSION, f"{path.name}: modelVersion mismatch")
    players = state["players"]
    ids = [player["id"] for player in players]
    seats = [player["seat"] for player in players]
    require(len(ids) == len(set(ids)), f"{path.name}: duplicate player ids")
    require(sorted(seats) == list(range(len(players))), f"{path.name}: seats must cover 0..n-1")

    located: list[str] = []
    for player in players:
        located.extend(player["drawPile"])
        located.extend(player["discardPile"])
        if player["status"] == "eligible" and not player["drawPile"]:
            require(bool(player["discardPile"]), f"{path.name}: empty-draw eligible player must retain a discard pile")
        if player["status"] != "eligible":
            require(player["id"] != state["currentPlayerId"], f"{path.name}: current player cannot be eliminated")
    require(len(located) == 56, f"{path.name}: expected 56 located cards, got {len(located)}")
    require(len(located) == len(set(located)), f"{path.name}: a card appears in multiple zones")
    require(set(located) == set(instances), f"{path.name}: located card set differs from catalog")

    totals = totals_from_players(players, instances)
    require(totals == state["fruitTotals"], f"{path.name}: fruitTotals mismatch, computed {totals}")
    valid = sorted(fruit_id for fruit_id, total in totals.items() if total == 5)
    require(valid == sorted(state["validFruitIds"]), f"{path.name}: validFruitIds mismatch, computed {valid}")

    current = state["currentPlayerId"]
    if current is not None:
        player = next((item for item in players if item["id"] == current), None)
        require(player is not None and player["status"] == "eligible" and player["drawPile"], f"{path.name}: invalid current player")
    if state["finalDuelArmed"]:
        eligible_count = sum(player["status"] == "eligible" for player in players)
        require(state["profileId"] == "official_last_bell" and eligible_count <= 2, f"{path.name}: invalid finalDuelArmed")

    if state["lastFlip"] is not None:
        last = state["lastFlip"]
        require(last["cardId"] in instances, f"{path.name}: lastFlip references unknown card")
        require(instances[last["cardId"]]["faceId"] == last["faceId"], f"{path.name}: lastFlip face mismatch")
        require(last["boardEpoch"] == state["boardEpoch"], f"{path.name}: lastFlip epoch should match current example")
    require(state["eventSeq"] >= max((event["seq"] for event in state["events"]), default=0), f"{path.name}: eventSeq behind event log")
    print(f"[ok] authoritative example {path.name}: 56 cards conserved, totals {totals}")
    return state


def walk_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            keys.append(key)
            keys.extend(walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.extend(walk_keys(child))
    return keys


def validate_view_example(path: Path, catalog: dict[str, Any]) -> None:
    view = load_json(path)
    require(view["modelVersion"] == MODEL_VERSION, f"{path.name}: modelVersion mismatch")
    banned = {"drawPile", "discardPile", "rng", "seedSecret", "receivedAtNs", "cardId", "cardIds", "validFruitIds"}
    leaked = sorted(banned.intersection(walk_keys(view)))
    require(not leaked, f"{path.name}: private/internal keys leaked: {leaked}")

    faces = {face["id"]: face for face in catalog["faces"]}
    visible_totals = {fruit_id: 0 for fruit_id in FRUIT_IDS}
    for player in view["players"]:
        top = player["topDiscard"]
        if top:
            require(top["faceId"] in faces, f"{path.name}: unknown public face {top['faceId']}")
            face = faces[top["faceId"]]
            require(face["fruitId"] == top["fruitId"] and face["fruitCount"] == top["fruitCount"], f"{path.name}: public face fields disagree")
            visible_totals[top["fruitId"]] += int(top["fruitCount"])
    if not view["rules"]["countAssist"]:
        require(view["assistFruitTotals"] is None, f"{path.name}: faithful mode must not expose aggregate totals")
    if "exact-five" in path.stem:
        require(any(total == 5 for total in visible_totals.values()), f"{path.name}: fixture name promises an exact-five board")
    print(f"[ok] safe view {path.name}: no deck/order leak; visible tops {visible_totals}")


def validate_state_machine(machine: dict[str, Any]) -> None:
    require(machine["modelVersion"] == MODEL_VERSION, "State machine modelVersion mismatch")
    phase_ids = {phase["id"] for phase in machine["phases"]}
    require(phase_ids == {"waiting", "playing", "resolving_bell", "finished"}, "State machine phase set mismatch")
    require(machine["initialPhase"] in phase_ids, "Initial phase is unknown")
    transition_ids: set[str] = set()
    accepted_by_phase = {phase["id"]: set(phase["acceptedActions"]) for phase in machine["phases"]}
    for transition in machine["transitions"]:
        require(transition["id"] not in transition_ids, f"Duplicate transition {transition['id']}")
        transition_ids.add(transition["id"])
        require(transition["from"] in phase_ids and transition["to"] in phase_ids, f"Unknown phase in {transition['id']}")
        action = transition["action"]
        require(action.startswith("internal_") or action in accepted_by_phase[transition["from"]], f"Action {action} not accepted by {transition['from']}")
    rejection_codes = {item["code"] for item in machine["rejections"]}
    require({"STALE_BOARD", "BELL_ALREADY_RESOLVED", "NOT_ELIGIBLE"}.issubset(rejection_codes), "Missing safe bell rejection")
    arbitration = machine["raceArbitration"]
    require(arbitration["winner"] == "first-server-lock-acquisition" and arbitration["clientTimestampTrusted"] is False, "Unsafe race arbitration")
    print(f"[ok] state machine: {len(phase_ids)} phases, {len(transition_ids)} transitions")


def validate_scene(scene: dict[str, Any]) -> None:
    require(scene["modelVersion"] == MODEL_VERSION, "Scene modelVersion mismatch")
    zone_ids = [zone["id"] for zone in scene["zones"]]
    require(len(zone_ids) == len(set(zone_ids)), "Scene zone ids must be unique")
    zone_set = set(zone_ids)
    for zone in scene["zones"]:
        rect = zone["rect"]
        require(rect["x"] + rect["width"] <= 1.000001 and rect["y"] + rect["height"] <= 1.000001, f"Zone {zone['id']} exceeds canvas")

    layouts = {layout["playerCount"]: layout for layout in scene["seatLayouts"]}
    require(set(layouts) == set(range(2, 7)), "Seat layouts must cover 2-6 players")
    for count, layout in layouts.items():
        seats = layout["seats"]
        require(len(seats) == count, f"{count}-player layout must contain {count} seats")
        require(sorted(item["relativeSeat"] for item in seats) == list(range(count)), f"{count}-player relative seats mismatch")
        require(len({item["wideZoneId"] for item in seats}) == count, f"{count}-player wide seat zones repeat")
        require(len({item["compactSlot"] for item in seats}) == count, f"{count}-player compact slots repeat")
        require(all(item["wideZoneId"] in zone_set for item in seats), f"{count}-player layout references unknown zone")

    for scene_item in scene["scenes"]:
        require(set(scene_item["requiredZones"]).issubset(zone_set), f"Scene {scene_item['id']} references unknown zone")
        require(scene_item["focusTarget"] in zone_set, f"Scene {scene_item['id']} has unknown focus target")
    for cue in scene["animationCues"]:
        for field in ("fromZone", "toZone"):
            require(cue[field] is None or cue[field] in zone_set, f"Cue {cue['id']} references unknown {field}")
    require(scene["bellMetrics"]["minimumTarget"] >= 64, "Bell target is too small")
    fidelity = scene["fidelity"]
    require(fidelity["allTopCardsSimultaneouslyVisible"] is True, "All top cards must remain visible")
    require(fidelity["showAggregateFruitTotalsDefault"] is False, "Faithful scene must not auto-count")
    require(fidelity["highlightCorrectBellConditionDefault"] is False, "Faithful scene must not reveal the answer")
    print("[ok] scene catalog: 2-6 seats, references, fidelity and accessibility")


def validate_assets(catalog: dict[str, Any]) -> None:
    for name in ("card-atlas.svg", "table-scene.svg"):
        path = ASSETS / name
        require(path.is_file() and path.stat().st_size > 5000, f"Missing or implausibly small {name}; run generate_assets.py")
        try:
            tree = ET.parse(path)
        except ET.ParseError as exc:
            raise ValidationFailure(f"Invalid SVG {name}: {exc}") from exc
        root = tree.getroot()
        require(root.tag.endswith("svg"), f"{name} root is not svg")
        raw = path.read_text(encoding="utf-8")
        external_href = re.search(r'(?:href|xlink:href)=["\']https?://', raw, flags=re.IGNORECASE)
        require("<image" not in raw and external_href is None, f"{name} must not embed/link external artwork")
    atlas = (ASSETS / "card-atlas.svg").read_text(encoding="utf-8")
    for face in catalog["faces"]:
        require(f'id="{face["id"]}"' in atlas, f"card-atlas.svg missing {face['id']}")
    table = (ASSETS / "table-scene.svg").read_text(encoding="utf-8")
    for zone_id in ("table_stage", "bell_zone", "fruit_legend", "reaction_banner", "turn_banner", "seat_0", "seat_2", "seat_3", "seat_5"):
        require(f'id="{zone_id}"' in table, f"table-scene.svg missing {zone_id}")
    print("[ok] generated SVG assets: XML valid, no external images, semantic ids present")


def validate_docs() -> None:
    required = [
        ROOT / "README.md",
        ROOT / "SOURCES.md",
        ROOT / "docs" / "RULEBOOK.md",
        ROOT / "docs" / "IMPLEMENTATION_PLAN.md",
        ROOT / "docs" / "CARD_MODEL.md",
        ROOT / "docs" / "SCENE_MODEL.md",
        ROOT / "assets" / "README.md",
    ]
    for path in required:
        require(path.is_file() and path.stat().st_size > 300, f"Missing documentation {path.relative_to(ROOT)}")
    rulebook = (ROOT / "docs" / "RULEBOOK.md").read_text(encoding="utf-8")
    require("恰好 5" in rulebook and "不是 5 的倍数" in rulebook, "Rulebook must state exact-five, not multiples")
    require("抽牌堆用尽" in rulebook and "最后一次按铃" in rulebook, "Rulebook misses elimination/end rules")
    sources = (ROOT / "SOURCES.md").read_text(encoding="utf-8")
    require("AMIGO" in sources and "v3.1" in sources and "工程裁决" in sources, "Sources must identify baseline and rulings")
    print("[ok] documentation set and critical rule statements")


def validate_pdf_if_present() -> None:
    path = ROOT / "output" / "pdf" / "halli-galli-rulebook-zh-CN.pdf"
    if not path.exists():
        print("[skip] PDF not built yet")
        return
    raw = path.read_bytes()
    require(raw.startswith(b"%PDF-") and len(raw) > 20_000, "Built PDF is missing or implausibly small")
    try:
        from pypdf import PdfReader
    except ImportError:
        print(f"[ok] PDF signature/size ({len(raw)} bytes); pypdf unavailable for deeper check")
        return
    reader = PdfReader(str(path))
    require(len(reader.pages) >= 4, "Rulebook PDF should contain at least four pages")
    extracted = "\n".join((page.extract_text() or "") for page in reader.pages)
    require("德国心脏病" in extracted and "恰好" in extracted, "PDF text extraction misses key content")
    print(f"[ok] PDF: {len(reader.pages)} pages, text and signature verified")


def main() -> int:
    try:
        catalog = load_json(MODEL / "card-catalog.json")
        profiles = load_json(MODEL / "rules-profiles.json")
        state_machine = load_json(MODEL / "state-machine.json")
        scene = load_json(MODEL / "scene-catalog.json")

        schema_pairs = [
            (MODEL / "card-catalog.json", MODEL / "card-catalog.schema.json"),
            (MODEL / "rules-profiles.json", MODEL / "rules-profiles.schema.json"),
            (MODEL / "scene-catalog.json", MODEL / "scene-catalog.schema.json"),
            (EXAMPLES / "game-state-exact-five.json", MODEL / "game-state.schema.json"),
            (EXAMPLES / "game-state-last-chance.json", MODEL / "game-state.schema.json"),
            (EXAMPLES / "player-view-exact-five.json", MODEL / "view-state.schema.json"),
        ]
        optional_schema_validation(schema_pairs)
        instances = validate_catalog(catalog)
        validate_profiles(profiles)
        exact_state = validate_authoritative_example(EXAMPLES / "game-state-exact-five.json", instances)
        require(exact_state["fruitTotals"]["banana"] == 5, "Exact-five fixture must show five bananas")
        last_chance = validate_authoritative_example(EXAMPLES / "game-state-last-chance.json", instances)
        p1 = next(player for player in last_chance["players"] if player["id"] == "p1")
        require(p1["status"] == "eligible" and not p1["drawPile"] and p1["discardPile"], "Last-chance fixture does not model the rule")
        validate_view_example(EXAMPLES / "player-view-exact-five.json", catalog)
        validate_state_machine(state_machine)
        validate_scene(scene)
        validate_assets(catalog)
        validate_docs()
        validate_pdf_if_present()
    except (ValidationFailure, KeyError, TypeError, ValueError) as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    print("All Halli Galli model checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
