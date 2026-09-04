from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "card-catalog.json"
STANDARD_COLORS = ("white", "blue", "green", "red", "black")
PIECE_COLORS = (*STANDARD_COLORS, "gold")


@lru_cache(maxsize=1)
def catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def cards() -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in catalog()["developmentCards"]}


@lru_cache(maxsize=1)
def nobles() -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in catalog()["nobles"]}


@lru_cache(maxsize=1)
def colors() -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in catalog()["colors"]}


def development_ids(level: int | None = None) -> list[str]:
    return [
        item["id"]
        for item in catalog()["developmentCards"]
        if level is None or item["level"] == level
    ]


def noble_ids() -> list[str]:
    return [item["id"] for item in catalog()["nobles"]]


def card(identifier: str) -> dict[str, Any]:
    try:
        return cards()[identifier]
    except KeyError as error:
        raise KeyError(f"unknown development card: {identifier}") from error


def noble(identifier: str) -> dict[str, Any]:
    try:
        return nobles()[identifier]
    except KeyError as error:
        raise KeyError(f"unknown noble tile: {identifier}") from error


def color_catalog_view() -> list[dict[str, Any]]:
    return [dict(colors()[identifier]) for identifier in PIECE_COLORS]


def card_view(identifier: str) -> dict[str, Any]:
    item = card(identifier)
    serial = int(identifier.rsplit("-", 1)[1])
    return {
        "id": item["id"],
        "level": item["level"],
        "bonusColor": item["bonusColor"],
        "prestige": item["prestige"],
        "cost": dict(item["cost"]),
        "totalCost": item["totalCost"],
        "artVariant": ((item["level"] * 7 + serial) % 6) + 1,
        "labelZh": item["accessibility"]["labelZh"],
        "compactLabelZh": item["accessibility"]["compactLabelZh"],
    }


def noble_view(identifier: str) -> dict[str, Any]:
    item = noble(identifier)
    serial = noble_ids().index(identifier) + 1
    return {
        "id": item["id"],
        "prestige": item["prestige"],
        "requirement": dict(item["requirement"]),
        "portraitVariant": serial,
        "labelZh": item["accessibility"]["labelZh"],
    }
