from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "card-catalog.json"


@lru_cache(maxsize=1)
def catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def suits() -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in catalog()["suits"]}


@lru_cache(maxsize=1)
def traits() -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in catalog()["traits"]}


SUIT_ORDER = (
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
)


def card_id(suit: str, value: int) -> str:
    return f"loot-{suit}-{value}"


@lru_cache(maxsize=1)
def cards() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for suit_id in SUIT_ORDER:
        suit = suits()[suit_id]
        for value in suit["values"]["base"]:
            identifier = card_id(suit_id, value)
            result[identifier] = {
                "id": identifier,
                "suit": suit_id,
                "value": value,
                "nameZh": suit["nameZh"],
                "nameEn": suit["nameEn"],
                "symbol": suit["symbol"],
                "icon": suit["icon"],
                "color": suit["color"],
                "summaryZh": suit["ability"]["summaryZh"],
            }
    return result


def all_card_ids() -> list[str]:
    return list(cards())


def lowest_card_ids() -> list[str]:
    return [
        card_id(suit_id, min(suits()[suit_id]["values"]["base"]))
        for suit_id in SUIT_ORDER
    ]


def card(identifier: str) -> dict[str, Any]:
    try:
        return cards()[identifier]
    except KeyError as error:
        raise ValueError(f"未知战利品牌：{identifier}") from error


def card_view(identifier: str) -> dict[str, Any]:
    return dict(card(identifier))


def suit_of(identifier: str) -> str:
    return str(card(identifier)["suit"])


def value_of(identifier: str) -> int:
    return int(card(identifier)["value"])


def trait_view(identifier: str) -> dict[str, Any]:
    item = traits()[identifier]
    return {
        "id": item["id"],
        "nameZh": item["nameZh"],
        "nameEn": item["nameEn"],
        "summaryZh": item["summaryZh"],
        "appliesTo": list(item["appliesTo"]),
    }
