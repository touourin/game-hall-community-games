from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "components.json"


@lru_cache(maxsize=1)
def component_catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def fund_cards() -> dict[str, dict[str, Any]]:
    return {
        card["id"]: card
        for card in component_catalog()["fundCards"]
    }


@lru_cache(maxsize=1)
def industries() -> dict[str, dict[str, Any]]:
    return {
        industry["id"]: industry
        for industry in component_catalog()["industries"]
    }


@lru_cache(maxsize=1)
def luxuries() -> dict[str, dict[str, Any]]:
    return {
        luxury["id"]: luxury
        for luxury in component_catalog()["luxuries"]
    }


def card_view(card_id: str) -> dict[str, Any]:
    card = fund_cards()[card_id]
    return {
        "id": card["id"],
        "amount": card["amount"],
        "period": card["period"],
        "interest": card["interest"],
        "averageBurden": card["averageBurden"],
        "yieldPercent": card["yieldPercent"],
        "kind": card["kind"],
        "isBear": card["kind"] == "bear",
    }
