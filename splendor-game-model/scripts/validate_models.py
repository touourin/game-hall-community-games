#!/usr/bin/env python3
"""Validate Splendor sources, generated models, examples, SVGs, docs, and PDF."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "model"
EXAMPLES = ROOT / "examples"
ASSETS = ROOT / "assets"
PDF = ROOT / "output" / "pdf" / "splendor-rulebook-zh-CN.pdf"
COLORS = ("white", "blue", "green", "red", "black")
PIECE_COLORS = (*COLORS, "gold")
CARD_ID = re.compile(r"^dev-(white|blue|green|red|black)-[123]-[0-9]{2}$")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def validate_with_schema(schema: dict, instance: dict, label: str) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print(f"jsonschema unavailable; skipped schema validation for {label}.")
        return
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda item: list(item.path))
    if errors:
        details = "\n".join(
            f"  {label} at {'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors[:12]
        )
        raise AssertionError(f"schema validation failed:\n{details}")


def walk_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_keys(item)


def source_digest() -> str:
    return hashlib.sha256(
        (MODEL / "development-cards.csv").read_bytes()
        + b"\n"
        + (MODEL / "nobles.csv").read_bytes()
    ).hexdigest()


def validate_sources_and_catalog(component: dict, catalog: dict) -> None:
    source_cards = load_csv(MODEL / "development-cards.csv")
    source_nobles = load_csv(MODEL / "nobles.csv")
    cards = catalog["developmentCards"]
    nobles = catalog["nobles"]

    assert catalog["sourceDigestSha256"] == source_digest()
    assert len(source_cards) == len(cards) == 90
    assert len(source_nobles) == len(nobles) == 10
    assert len({row["id"] for row in source_cards}) == 90
    assert len({card["id"] for card in cards}) == 90
    assert all(CARD_ID.fullmatch(card["id"]) for card in cards)

    source_map = {row["id"]: row for row in source_cards}
    for card in cards:
        source = source_map[card["id"]]
        assert card["level"] == int(source["level"])
        assert card["bonusColor"] == source["bonusColor"]
        assert card["prestige"] == int(source["prestige"])
        expected_cost = {color: int(source[color]) for color in COLORS}
        assert card["cost"] == expected_cost
        assert card["totalCost"] == sum(expected_cost.values())
        assert card["visual"]["officialArtworkIncluded"] is False
        assert card["visual"]["artworkSlot"].startswith("original-")
        assert str(card["level"]) in card["accessibility"]["labelZh"]
        assert str(card["prestige"]) in card["accessibility"]["labelZh"]

    assert Counter(card["level"] for card in cards) == Counter({1: 40, 2: 30, 3: 20})
    assert Counter(card["bonusColor"] for card in cards) == Counter({color: 18 for color in COLORS})
    assert Counter((card["bonusColor"], card["level"]) for card in cards) == Counter(
        {(color, level): count for color in COLORS for level, count in ((1, 8), (2, 6), (3, 4))}
    )
    assert Counter((card["level"], card["prestige"]) for card in cards) == Counter(
        {(1, 0): 35, (1, 1): 5, (2, 1): 10, (2, 2): 15, (2, 3): 5, (3, 3): 5, (3, 4): 10, (3, 5): 5}
    )
    assert sum(card["prestige"] for card in cards) == 140
    assert Counter((card["level"], card["totalCost"]) for card in cards) == Counter(
        {(1, 3): 10, (1, 4): 15, (1, 5): 15, (2, 5): 5, (2, 6): 5, (2, 7): 10, (2, 8): 10, (3, 7): 5, (3, 10): 5, (3, 12): 5, (3, 14): 5}
    )

    noble_shapes = Counter(
        tuple(sorted(amount for amount in noble["requirement"].values() if amount))
        for noble in nobles
    )
    assert noble_shapes == Counter({(4, 4): 5, (3, 3, 3): 5})
    assert all(noble["prestige"] == 3 for noble in nobles)
    assert all(noble["visual"]["officialPortraitIncluded"] is False for noble in nobles)

    assert component["components"]["developmentCards"]["byLevel"] == {"1": 40, "2": 30, "3": 20}
    expected_supply = {
        "2": {"white": 4, "blue": 4, "green": 4, "red": 4, "black": 4, "gold": 5},
        "3": {"white": 5, "blue": 5, "green": 5, "red": 5, "black": 5, "gold": 5},
        "4": {"white": 7, "blue": 7, "green": 7, "red": 7, "black": 7, "gold": 5},
    }
    assert component["components"]["pieces"]["supplyByPlayerCount"] == expected_supply
    assert component["rulesBaseline"]["targetPrestige"] == 15
    assert component["rulesBaseline"]["reservedCardLimit"] == 3
    assert component["rulesBaseline"]["heldPieceLimitAtTurnEnd"] == 10
    assert len(component["digitalRulings"]) == 4


def derived_player(player: dict, card_map: dict, noble_map: dict) -> tuple[dict[str, int], int]:
    bonuses = Counter(card_map[card_id]["bonusColor"] for card_id in player["purchasedCardIds"])
    vector = {color: bonuses[color] for color in COLORS}
    score = sum(card_map[card_id]["prestige"] for card_id in player["purchasedCardIds"])
    score += sum(noble_map[noble_id]["prestige"] for noble_id in player["nobleIds"])
    return vector, score


def validate_internal_state(catalog: dict, internal: dict, component: dict) -> None:
    card_map = {card["id"]: card for card in catalog["developmentCards"]}
    noble_map = {noble["id"]: noble for noble in catalog["nobles"]}
    located_cards = []
    for level, tier in internal["tiers"].items():
        assert tier["level"] == int(level)
        located_cards.extend(tier["deck"])
        located_cards.extend(card_id for card_id in tier["market"] if card_id is not None)
        assert all(card_map[card_id]["level"] == int(level) for card_id in tier["deck"])
        assert all(card_map[card_id]["level"] == int(level) for card_id in tier["market"] if card_id)
    for player in internal["players"]:
        located_cards.extend(player["purchasedCardIds"])
        located_cards.extend(item["cardId"] for item in player["reservations"])
        bonuses, score = derived_player(player, card_map, noble_map)
        assert player["cachedBonuses"] == bonuses
        assert player["cachedScore"] == score
        assert len(player["reservations"]) <= 3
    assert len(located_cards) == len(set(located_cards)) == 90
    assert set(located_cards) == set(card_map)

    located_nobles = list(internal["availableNobleIds"]) + list(internal["unusedNobleIds"])
    for player in internal["players"]:
        located_nobles.extend(player["nobleIds"])
    assert len(located_nobles) == len(set(located_nobles)) == 10
    assert set(located_nobles) == set(noble_map)

    initial = component["components"]["pieces"]["supplyByPlayerCount"][str(len(internal["players"]))]
    for color in PIECE_COLORS:
        actual = internal["supply"][color] + sum(player["pieces"][color] for player in internal["players"])
        assert actual == initial[color], (color, actual, initial[color])
    assert internal["turn"]["activePlayerId"] in internal["turnOrder"]
    assert [player["playerId"] for player in internal["players"]] == internal["turnOrder"]
    assert [player["seatIndex"] for player in internal["players"]] == list(range(len(internal["players"])))


def reservation_by_owner(view: dict, owner_id: str) -> dict:
    player = next(player for player in view["players"] if player["playerId"] == owner_id)
    return player["reservations"][0]


def validate_views(internal: dict, active: dict, owner: dict, spectator: dict) -> None:
    forbidden_keys = {"deck", "unusedNobleIds", "rng", "rngState", "seed", "seedCommitment", "cachedScore", "cachedBonuses"}
    for view in (active, owner, spectator):
        assert forbidden_keys.isdisjoint(set(walk_keys(view)))
        assert view["revision"] == internal["revision"]
        assert all("deckCount" in tier and "deck" not in tier for tier in view["tiers"].values())
        public = reservation_by_owner(view, "p2")
        assert public["knownToAll"] is True and public["cardId"] is not None

    assert active["viewer"] == {"mode": "player", "playerId": "p3"}
    assert active["self"] == "p3" and active["legalActions"]
    assert reservation_by_owner(active, "p1")["cardId"] is None

    assert owner["viewer"] == {"mode": "player", "playerId": "p1"}
    assert owner["self"] == "p1" and owner["legalActions"] == []
    assert reservation_by_owner(owner, "p1")["cardId"] is not None

    assert spectator["viewer"] == {"mode": "spectator", "playerId": None}
    assert spectator["self"] is None and spectator["legalActions"] == []
    assert reservation_by_owner(spectator, "p1")["cardId"] is None
    assert spectator["privacy"]["blindReservations"] == "hidden"
    serialized = json.dumps(spectator, ensure_ascii=False)
    hidden_card_id = next(
        item["cardId"]
        for player in internal["players"] if player["playerId"] == "p1"
        for item in player["reservations"] if not item["knownToAll"]
    )
    assert hidden_card_id not in serialized


def validate_machine_and_scene(machine: dict, scene: dict) -> None:
    state_ids = set(machine["stableStates"])
    action_ids = set(machine["actions"])
    zone_ids = {zone["id"] for zone in scene["zones"]}
    assert len(zone_ids) == len(scene["zones"]) == 13
    assert set(scene["viewportPolicy"]["localHorizontalScrollZones"]) <= zone_ids
    for zone in scene["zones"]:
        rect = zone["rect"]
        assert rect["x"] + rect["width"] <= 1.000001
        assert rect["y"] + rect["height"] <= 1.000001
    for layout in scene["seatLayouts"]:
        assert len(layout["seats"]) == layout["playerCount"]
        assert {seat["relativeSeat"] for seat in layout["seats"]} == set(range(layout["playerCount"]))
        assert all(seat["zoneId"] in zone_ids for seat in layout["seats"])
    for item in scene["scenes"]:
        assert set(item["requiredZones"]) <= zone_ids
        assert item["focusTarget"] in zone_ids
        assert set(item["primaryActions"]) <= action_ids
        if item["phase"] not in {"presentation"}:
            assert item["phase"] in state_ids
    cue_ids = [cue["id"] for cue in scene["animationCues"]]
    assert len(cue_ids) == len(set(cue_ids)) == 10
    assert scene["viewportPolicy"]["pageLevelHorizontalOverflow"] is False
    assert scene["accessibility"]["notColorOnly"] is True
    assert scene["accessibility"]["minimumTarget"] >= 44


def validate_svg_assets(catalog: dict, scene: dict) -> None:
    atlas_path = ASSETS / "development-card-atlas.svg"
    scene_path = ASSETS / "table-scene.svg"
    atlas_text = atlas_path.read_text(encoding="utf-8")
    scene_text = scene_path.read_text(encoding="utf-8")
    for text in (atlas_text, scene_text):
        assert f'data-model-version="{catalog["modelVersion"]}"' in text
        assert "<image" not in text.lower()
        ET.fromstring(text)
    assert len(re.findall(r'data-card-id="', atlas_text)) == 90
    assert len(re.findall(r'data-noble-id="', atlas_text)) == 10
    assert set(re.findall(r'data-card-id="([^"]+)"', atlas_text)) == {
        card["id"] for card in catalog["developmentCards"]
    }
    assert set(re.findall(r'data-noble-id="([^"]+)"', atlas_text)) == {
        noble["id"] for noble in catalog["nobles"]
    }
    assert set(re.findall(r'data-zone-id="([^"]+)"', scene_text)) == {
        zone["id"] for zone in scene["zones"]
    }


def validate_documents_and_pdf() -> None:
    expected_docs = [
        ROOT / "README.md",
        ROOT / "SOURCES.md",
        ROOT / "docs" / "RULEBOOK.md",
        ROOT / "docs" / "IMPLEMENTATION_PLAN.md",
        ROOT / "docs" / "CARD_MODEL.md",
        ROOT / "docs" / "SCENE_MODEL.md",
        ROOT / "assets" / "README.md",
    ]
    for path in expected_docs:
        assert path.exists() and path.stat().st_size > 500, path
    sources = (ROOT / "SOURCES.md").read_text(encoding="utf-8")
    assert "2026-09-03" in sources
    assert "spacecowboys" in sources.lower()
    assert "anicolao/splendor" in sources
    assert "bouk/splendimax" in sources

    assert PDF.exists() and PDF.stat().st_size > 40_000
    assert PDF.read_bytes()[:5] == b"%PDF-"
    try:
        from pypdf import PdfReader
        import pdfplumber
    except ImportError:
        print("pypdf/pdfplumber unavailable; skipped semantic PDF checks.")
        return
    reader = PdfReader(str(PDF))
    assert 8 <= len(reader.pages) <= 24
    assert reader.metadata.title == "《璀璨宝石》规则说明书"
    with pdfplumber.open(PDF) as document:
        text = "\n".join(page.extract_text() or "" for page in document.pages)
    for phrase in ("游戏准备", "取 2 枚同色宝石", "贵族拜访", "共同获胜", "数字版信息边界"):
        assert phrase in text, phrase


def main() -> None:
    for path in sorted(ROOT.rglob("*.json")):
        load_json(path)

    component = load_json(MODEL / "component-catalog.json")
    catalog = load_json(MODEL / "card-catalog.json")
    machine = load_json(MODEL / "state-machine.json")
    scene = load_json(MODEL / "scene-catalog.json")
    internal = load_json(EXAMPLES / "internal-turn.json")
    active = load_json(EXAMPLES / "player-active-view.json")
    owner = load_json(EXAMPLES / "player-owner-reserve-view.json")
    spectator = load_json(EXAMPLES / "spectator-view.json")

    validate_with_schema(load_json(MODEL / "component-catalog.schema.json"), component, "component catalog")
    validate_with_schema(load_json(MODEL / "card-catalog.schema.json"), catalog, "card catalog")
    validate_with_schema(load_json(MODEL / "scene-catalog.schema.json"), scene, "scene catalog")
    validate_with_schema(load_json(MODEL / "game-state.schema.json"), internal, "authoritative state")
    view_schema = load_json(MODEL / "view-state.schema.json")
    validate_with_schema(view_schema, active, "active player view")
    validate_with_schema(view_schema, owner, "owner reserve view")
    validate_with_schema(view_schema, spectator, "spectator view")

    validate_sources_and_catalog(component, catalog)
    validate_internal_state(catalog, internal, component)
    validate_views(internal, active, owner, spectator)
    validate_machine_and_scene(machine, scene)
    validate_svg_assets(catalog, scene)
    validate_documents_and_pdf()
    print(
        "Splendor model valid: 90 developments, 10 nobles, 13 zones, "
        "4 schema-checked examples, 2 SVG prototypes, and 1 PDF rulebook."
    )


if __name__ == "__main__":
    main()
