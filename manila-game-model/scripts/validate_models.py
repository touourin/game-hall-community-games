#!/usr/bin/env python3
"""Validate Manila rule constants, schemas, examples, assets, and privacy."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "model"
EXAMPLES = ROOT / "examples"
ASSETS = ROOT / "assets"
PDF = ROOT / "output" / "pdf" / "manila-rulebook-zh-CN.pdf"
COMMODITY_IDS = {"ginseng", "nutmeg", "silk", "jade"}
SHARE_PATTERN = re.compile(
    r"^share-(ginseng|nutmeg|silk|jade)-0[1-5]$"
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def walk_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_keys(item)


def validate_with_jsonschema(schema: dict, instance: dict, label: str) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print(f"jsonschema unavailable; skipped schema validation for {label}.")
        return
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(instance)


def validate_all_json_files() -> None:
    for path in sorted(ROOT.rglob("*.json")):
        load_json(path)


def validate_rule_constants(component: dict) -> None:
    assert component["marketTrack"] == [0, 5, 10, 20, 30]
    assert component["navigation"]["dice"] == {
        "kind": "standard-d6",
        "faces": [1, 2, 3, 4, 5, 6],
        "serverAuthoritative": True,
    }
    assert component["navigation"]["routeMaximum"] == 13
    assert component["navigation"]["arrivalCondition"] == "position > 13"
    assert component["navigation"]["startPositionSum"] == 9
    assert component["navigation"]["movementRounds"] == 3
    assert component["finance"] == {
        "loanAdvance": 12,
        "redemptionCost": 15,
        "unredeemedEndPenalty": 15,
        "loanIsSecuredByOneShare": True,
        "mortgagedShareStillCountsMarketValue": True,
    }
    assert component["players"]["accomplicesByPlayerCount"] == {
        "3": 4,
        "4": 3,
        "5": 3,
    }
    expected_commodities = {
        "ginseng": ([1, 2, 3], 18),
        "nutmeg": ([2, 3, 4], 24),
        "silk": ([3, 4, 5], 30),
        "jade": ([3, 4, 5, 5], 36),
    }
    actual = {
        item["id"]: (item["placementCosts"], item["boatProfit"])
        for item in component["commodities"]
    }
    assert actual == expected_commodities
    assert sum(item["shareCount"] for item in component["commodities"]) == 20

    for destination in component["destinations"]:
        slots = destination["slots"]
        assert [slot["id"] for slot in slots] == ["A", "B", "C"]
        assert [slot["placementCost"] for slot in slots] == [4, 3, 2]
        assert [slot["payout"] for slot in slots] == [6, 8, 15]

    specials = {
        item["id"]: item for item in component["specialPositions"]
    }
    assert specials["pirate-captain"]["placementCost"] == 5
    assert specials["pirate-crew"]["placementCost"] == 5
    assert specials["pilot-small"]["movementBudget"] == 1
    assert specials["pilot-large"]["movementBudget"] == 2
    assert specials["insurance"]["immediateIncome"] == 10
    assert specials["insurance"]["blindPassengerAllowed"] is False

    schedules = component["placementSchedules"]
    assert schedules["3"].count("placement") == 4
    assert schedules["4"].count("placement") == 3
    assert schedules["5"].count("placement") == 3
    for schedule in schedules.values():
        assert schedule.count("movement") == 3
        assert schedule.count("pilots") == 1


def validate_cards(component: dict, card_model: dict, catalog: dict) -> None:
    assert card_model["copiesPerCommodity"] == 5
    assert card_model["back"]["sharedAcrossAllCommodities"] is True
    assert card_model["back"]["containsCommodityHint"] is False
    component_map = {
        item["id"]: item for item in component["commodities"]
    }
    card_map = {
        item["id"]: item for item in card_model["commodities"]
    }
    assert set(component_map) == set(card_map) == COMMODITY_IDS
    for commodity_id in COMMODITY_IDS:
        assert (
            component_map[commodity_id]["semanticColor"]
            == card_map[commodity_id]["semanticColor"]
        )
        assert (
            component_map[commodity_id]["pattern"]
            == card_map[commodity_id]["pattern"]
        )

    cards = catalog["cards"]
    assert catalog["cardCount"] == len(cards) == 20
    assert len({card["id"] for card in cards}) == 20
    assert Counter(card["commodityId"] for card in cards) == Counter(
        {commodity_id: 5 for commodity_id in COMMODITY_IDS}
    )
    for card in cards:
        assert SHARE_PATTERN.fullmatch(card["id"])
        assert card["id"].endswith(f"-{card['copyIndex']:02d}")
        assert card["ariaLabel"].endswith(f"第 {card['copyIndex']} 张")


def validate_machine_and_scenes(machine: dict, scenes: dict) -> None:
    stages = set(machine["states"])
    actions = set(machine["actions"])
    scene_ids = [scene["id"] for scene in scenes["scenes"]]
    assert len(scene_ids) == len(set(scene_ids)) == 14
    assert scenes["viewportPolicy"]["pageLevelHorizontalOverflow"] is False
    for scene in scenes["scenes"]:
        assert scene["stage"] in stages
        assert set(scene["actions"]) <= actions
    for action_name, action in machine["actions"].items():
        assert action["stages"]
        assert set(action["stages"]) <= stages
        assert isinstance(action["payload"], list)
        assert isinstance(action["private"], bool)
        assert action_name in actions
    assert set(machine["globalFinanceActions"]) == {
        "take_loan",
        "repay_loan",
    }


def validate_internal_example(catalog: dict, state: dict) -> None:
    card_ids = {card["id"] for card in catalog["cards"]}
    held = []
    for key, player in state["players"].items():
        assert key == player["playerId"]
        assert set(player["mortgagedShareIds"]) <= set(player["shareIds"])
        held.extend(player["shareIds"])
    assert len(held) == len(set(held))
    assert set(held) | set(state["shareSupply"]) == card_ids
    assert set(held).isdisjoint(state["shareSupply"])
    assert len(state["shareSupply"]) == 14
    assert state["placement"]["totalRounds"] == 4
    assert len(state["turnOrder"]) == 3


def validate_player_view(view: dict) -> None:
    assert view["viewer"] == {"mode": "player", "playerId": "p1"}
    assert view["self"]["playerId"] == "p1"
    assert all("shareIds" not in player for player in view["players"])
    assert all(
        "mortgagedShareIds" not in player for player in view["players"]
    )
    positions = [
        punt["position"]
        for punt in view["punts"]
        if punt["status"] == "sailing"
    ]
    lanes = [
        punt["laneId"]
        for punt in view["punts"]
        if punt["status"] == "sailing"
    ]
    assert sum(positions) == 9
    assert len(lanes) == len(set(lanes)) == 3
    assert view["privacy"]["shareIdentities"] == "self-only"


def validate_public_view(view: dict) -> None:
    assert view["viewer"]["mode"] == "spectator"
    assert view["self"] is None
    serialized = json.dumps(view, ensure_ascii=False)
    assert "share-" not in serialized
    assert "shareIds" not in set(walk_keys(view))
    assert "mortgagedShareIds" not in set(walk_keys(view))
    assert view["legalActions"] == []


def validate_assets() -> None:
    for filename in ("share-card-sheet.svg", "table-scene-blueprint.svg"):
        path = ASSETS / filename
        text = path.read_text(encoding="utf-8")
        assert 'data-model-version="1.0.0"' in text
        assert "official" not in text.lower()
        ET.fromstring(text)


def validate_documents_and_pdf() -> None:
    expected_docs = [
        ROOT / "README.md",
        ROOT / "SOURCES.md",
        ROOT / "docs" / "RULEBOOK.md",
        ROOT / "docs" / "IMPLEMENTATION_PLAN.md",
        ROOT / "docs" / "DIGITAL_ADAPTATIONS.md",
        ROOT / "docs" / "CARD_AND_SCENE_MODEL.md",
    ]
    for path in expected_docs:
        assert path.exists() and path.stat().st_size > 500
    assert PDF.exists() and PDF.stat().st_size > 20_000
    assert PDF.read_bytes()[:5] == b"%PDF-"


def main() -> None:
    validate_all_json_files()
    component = load_json(MODEL / "component-catalog.json")
    card_model = load_json(MODEL / "card-model.json")
    card_catalog = load_json(MODEL / "card-catalog.json")
    machine = load_json(MODEL / "state-machine.json")
    scenes = load_json(MODEL / "scene-catalog.json")
    game_schema = load_json(MODEL / "game-state.schema.json")
    view_schema = load_json(MODEL / "view-state.schema.json")
    card_schema = load_json(MODEL / "card-model.schema.json")
    internal = load_json(EXAMPLES / "internal-auction.json")
    player_view = load_json(EXAMPLES / "player-placement-view.json")
    public_view = load_json(EXAMPLES / "public-movement-view.json")

    validate_with_jsonschema(card_schema, card_model, "card model")
    validate_with_jsonschema(game_schema, internal, "internal state")
    validate_with_jsonschema(view_schema, player_view, "player view")
    validate_with_jsonschema(view_schema, public_view, "public view")

    validate_rule_constants(component)
    validate_cards(component, card_model, card_catalog)
    validate_machine_and_scenes(machine, scenes)
    validate_internal_example(card_catalog, internal)
    validate_player_view(player_view)
    validate_public_view(public_view)
    validate_assets()
    validate_documents_and_pdf()

    print(
        "Manila models valid: 20 shares, 4 commodities, 14 scenes, "
        "3 schema-checked examples, 2 SVG sheets, and 1 PDF rulebook."
    )


if __name__ == "__main__":
    main()

