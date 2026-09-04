#!/usr/bin/env python3
"""Generate deterministic authoritative and safe-view examples for the model."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "model"
EXAMPLES = ROOT / "examples"
COLORS = ("white", "blue", "green", "red", "black")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def derived(player: dict, cards: dict[str, dict], nobles: dict[str, dict]) -> tuple[dict, int]:
    bonuses = Counter(cards[card_id]["bonusColor"] for card_id in player["purchasedCardIds"])
    vector = {color: bonuses[color] for color in COLORS}
    score = sum(cards[card_id]["prestige"] for card_id in player["purchasedCardIds"])
    score += sum(nobles[noble_id]["prestige"] for noble_id in player["nobleIds"])
    return vector, score


def build_internal(catalog: dict) -> dict:
    card_map = {item["id"]: item for item in catalog["developmentCards"]}
    noble_map = {item["id"]: item for item in catalog["nobles"]}
    by_level = {
        level: [item["id"] for item in catalog["developmentCards"] if item["level"] == level]
        for level in (1, 2, 3)
    }
    markets = {level: by_level[level][:4] for level in (1, 2, 3)}
    remaining = {level: by_level[level][4:] for level in (1, 2, 3)}

    p1_cards = [remaining[1].pop(0), remaining[1].pop(0)]
    p2_cards = [remaining[1].pop(0)]
    p3_cards = [remaining[1].pop(0)]
    p1_blind = remaining[2].pop(0)
    p2_public = remaining[2].pop(0)

    players = [
        {
            "playerId": "p1",
            "seatIndex": 0,
            "name": "青岚",
            "pieces": {"white": 1, "blue": 1, "green": 0, "red": 0, "black": 0, "gold": 1},
            "purchasedCardIds": p1_cards,
            "reservations": [{"reservationId": "reservation-p1-001", "cardId": p1_blind, "level": 2, "source": "deck", "knownToAll": False, "reservedAtAction": 4}],
            "nobleIds": [],
        },
        {
            "playerId": "p2",
            "seatIndex": 1,
            "name": "赤羽",
            "pieces": {"white": 0, "blue": 1, "green": 1, "red": 1, "black": 0, "gold": 0},
            "purchasedCardIds": p2_cards,
            "reservations": [{"reservationId": "reservation-p2-001", "cardId": p2_public, "level": 2, "source": "market", "knownToAll": True, "reservedAtAction": 2}],
            "nobleIds": [],
        },
        {
            "playerId": "p3",
            "seatIndex": 2,
            "name": "墨石",
            "pieces": {"white": 0, "blue": 0, "green": 0, "red": 0, "black": 1, "gold": 0},
            "purchasedCardIds": p3_cards,
            "reservations": [],
            "nobleIds": [],
        },
    ]
    for player in players:
        bonuses, score = derived(player, card_map, noble_map)
        player["cachedBonuses"] = bonuses
        player["cachedScore"] = score

    nobles = [item["id"] for item in catalog["nobles"]]
    seed = "example-seed-splendor-model-v1"
    events = [
        {
            "eventId": "event-0005",
            "revision": 5,
            "actionNumber": 4,
            "kind": "reserve_blind",
            "actorId": "p1",
            "publicTextZh": "青岚从 2 级牌堆盲保留一张牌并取得一枚黄金。",
            "publicData": {"level": 2, "goldTaken": 1},
        },
        {
            "eventId": "event-0006",
            "revision": 6,
            "actionNumber": 5,
            "kind": "take_different",
            "actorId": "p2",
            "publicTextZh": "赤羽拿取蓝宝石、祖母绿和红宝石各一枚。",
            "publicData": {"pieces": {"blue": 1, "green": 1, "red": 1}},
        },
    ]
    last_action = deepcopy(events[-1])
    return {
        "$schema": "../model/game-state.schema.json",
        "schemaVersion": 1,
        "modelVersion": "1.0.0",
        "gameId": "splendor",
        "gameNumber": 1,
        "revision": 6,
        "phase": "turn_action",
        "rulesProfile": "base-2024-refresh",
        "turnOrder": ["p1", "p2", "p3"],
        "turn": {
            "firstPlayerId": "p1",
            "activePlayerId": "p3",
            "roundNumber": 2,
            "actionNumber": 5,
            "pendingReturnCount": 0,
            "eligibleNobleIds": [],
            "endTriggeredBy": None,
            "finalTurnPlayerId": None,
            "lastAction": last_action,
        },
        "supply": {"white": 4, "blue": 3, "green": 4, "red": 4, "black": 4, "gold": 4},
        "tiers": {
            str(level): {"level": level, "deck": remaining[level], "market": markets[level]}
            for level in (1, 2, 3)
        },
        "availableNobleIds": nobles[:4],
        "unusedNobleIds": nobles[4:],
        "players": players,
        "rng": {
            "algorithm": "deterministic-example-only",
            "seed": seed,
            "seedCommitment": hashlib.sha256(seed.encode("utf-8")).hexdigest(),
        },
        "events": events,
    }


def project(internal: dict, mode: str, viewer_id: str | None) -> dict:
    players = []
    for source in internal["players"]:
        reservations = []
        for item in source["reservations"]:
            can_see = item["knownToAll"] or (mode == "player" and viewer_id == source["playerId"])
            reservations.append(
                {
                    "reservationId": item["reservationId"],
                    "cardId": item["cardId"] if can_see else None,
                    "level": item["level"],
                    "source": item["source"],
                    "knownToAll": item["knownToAll"],
                }
            )
        players.append(
            {
                "playerId": source["playerId"],
                "seatIndex": source["seatIndex"],
                "name": source["name"],
                "pieces": source["pieces"],
                "purchasedCardIds": source["purchasedCardIds"],
                "reservations": reservations,
                "nobleIds": source["nobleIds"],
                "bonuses": source["cachedBonuses"],
                "score": source["cachedScore"],
            }
        )
    active = internal["turn"]["activePlayerId"]
    legal = []
    if mode == "player" and viewer_id == active:
        legal = [
            {"name": "take_different", "optionCount": 10, "reasonZh": "五种宝石均有供应，任选三种。"},
            {"name": "take_same", "optionCount": 4, "reasonZh": "除蓝宝石外，四种宝石供应至少四枚。"},
            {"name": "reserve_face_up", "optionCount": 12, "reasonZh": "本人保留区少于三张。"},
            {"name": "reserve_blind", "optionCount": 3, "reasonZh": "三个等级牌堆均未抽空。"},
        ]
    turn = {key: value for key, value in internal["turn"].items() if key != "lastAction"}
    return {
        "$schema": "../model/view-state.schema.json",
        "schemaVersion": 1,
        "modelVersion": "1.0.0",
        "gameId": "splendor",
        "revision": internal["revision"],
        "phase": internal["phase"],
        "viewer": {"mode": mode, "playerId": viewer_id},
        "self": viewer_id if mode == "player" else None,
        "turnOrder": internal["turnOrder"],
        "turn": turn,
        "supply": internal["supply"],
        "tiers": {
            key: {"level": value["level"], "deckCount": len(value["deck"]), "market": value["market"]}
            for key, value in internal["tiers"].items()
        },
        "availableNobleIds": internal["availableNobleIds"],
        "players": players,
        "legalActions": legal,
        "events": internal["events"],
        "privacy": {
            "deckOrder": "hidden",
            "unusedNobles": "hidden",
            "blindReservations": "owner-only" if mode == "player" else "hidden",
            "spectatorCanSeePrivate": False,
        },
    }


def main() -> None:
    catalog = load_json(MODEL / "card-catalog.json")
    internal = build_internal(catalog)
    write_json(EXAMPLES / "internal-turn.json", internal)
    write_json(EXAMPLES / "player-active-view.json", project(internal, "player", "p3"))
    write_json(EXAMPLES / "player-owner-reserve-view.json", project(internal, "player", "p1"))
    write_json(EXAMPLES / "spectator-view.json", project(internal, "spectator", None))
    print("Generated 1 authoritative state and 3 safe-view examples.")


if __name__ == "__main__":
    main()
