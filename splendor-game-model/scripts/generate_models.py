#!/usr/bin/env python3
"""Build the machine-readable Splendor card and noble catalog from reviewed CSV."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "model"
MODEL_VERSION = "1.0.0"
STANDARD_COLORS = ("white", "blue", "green", "red", "black")
COLOR_NAMES = {
    "white": "钻石",
    "blue": "蓝宝石",
    "green": "祖母绿",
    "red": "红宝石",
    "black": "缟玛瑙",
    "gold": "黄金百搭",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def integer_vector(row: dict[str, str]) -> dict[str, int]:
    return {color: int(row[color]) for color in STANDARD_COLORS}


def cost_label(cost: dict[str, int]) -> str:
    parts = [
        f"{COLOR_NAMES[color]} {amount}"
        for color, amount in cost.items()
        if amount
    ]
    return "、".join(parts) if parts else "免费"


def build_development_cards(rows: list[dict[str, str]]) -> list[dict]:
    cards = []
    for row in rows:
        level = int(row["level"])
        prestige = int(row["prestige"])
        bonus = row["bonusColor"]
        cost = integer_vector(row)
        cards.append(
            {
                "id": row["id"],
                "kind": "development",
                "level": level,
                "bonusColor": bonus,
                "prestige": prestige,
                "cost": cost,
                "totalCost": sum(cost.values()),
                "visual": {
                    "framePattern": f"{bonus}-functional",
                    "artworkSlot": f"original-level-{level}-merchant-scene",
                    "officialArtworkIncluded": False,
                },
                "accessibility": {
                    "labelZh": (
                        f"{level} 级{COLOR_NAMES[bonus]}奖励发展卡，"
                        f"{prestige} 点威望；费用：{cost_label(cost)}"
                    ),
                    "compactLabelZh": f"{level}级 {COLOR_NAMES[bonus]} +1，{prestige}分",
                },
            }
        )
    return cards


def build_nobles(rows: list[dict[str, str]]) -> list[dict]:
    nobles = []
    for index, row in enumerate(rows, start=1):
        requirement = integer_vector(row)
        nobles.append(
            {
                "id": row["id"],
                "kind": "noble",
                "prestige": int(row["prestige"]),
                "requirement": requirement,
                "requirementTotal": sum(requirement.values()),
                "visual": {
                    "portraitSlot": f"original-neutral-patron-{index:02d}",
                    "officialPortraitIncluded": False,
                },
                "accessibility": {
                    "labelZh": (
                        f"贵族板块，3 点威望；拜访要求："
                        f"{cost_label(requirement)}的永久奖励"
                    )
                },
            }
        )
    return nobles


def validate_source(cards: list[dict], nobles: list[dict]) -> None:
    if len(cards) != 90 or len({card["id"] for card in cards}) != 90:
        raise ValueError("development source must contain 90 unique cards")
    if Counter(card["level"] for card in cards) != Counter({1: 40, 2: 30, 3: 20}):
        raise ValueError("development level distribution must be 40/30/20")
    if Counter(card["bonusColor"] for card in cards) != Counter(
        {color: 18 for color in STANDARD_COLORS}
    ):
        raise ValueError("each bonus color must have 18 cards")
    expected_per_color_level = {
        (color, level): count
        for color in STANDARD_COLORS
        for level, count in ((1, 8), (2, 6), (3, 4))
    }
    actual_per_color_level = Counter(
        (card["bonusColor"], card["level"]) for card in cards
    )
    if actual_per_color_level != Counter(expected_per_color_level):
        raise ValueError("per-color level distribution must be 8/6/4")
    if len(nobles) != 10 or len({noble["id"] for noble in nobles}) != 10:
        raise ValueError("noble source must contain 10 unique tiles")
    noble_shapes = Counter(
        tuple(sorted(value for value in noble["requirement"].values() if value))
        for noble in nobles
    )
    if noble_shapes != Counter({(4, 4): 5, (3, 3, 3): 5}):
        raise ValueError("nobles must be five 4+4 and five 3+3+3 tiles")


def main() -> None:
    component_path = MODEL / "component-catalog.json"
    cards_path = MODEL / "development-cards.csv"
    nobles_path = MODEL / "nobles.csv"
    component = load_json(component_path)
    if component["modelVersion"] != MODEL_VERSION:
        raise ValueError("component model version does not match generator")

    cards = build_development_cards(load_csv(cards_path))
    nobles = build_nobles(load_csv(nobles_path))
    validate_source(cards, nobles)
    digest = hashlib.sha256(
        cards_path.read_bytes() + b"\n" + nobles_path.read_bytes()
    ).hexdigest()

    catalog = {
        "$schema": "./card-catalog.schema.json",
        "schemaVersion": 1,
        "modelVersion": MODEL_VERSION,
        "gameId": "splendor",
        "rulesEdition": "base-2024-refresh",
        "generatedFrom": ["./development-cards.csv", "./nobles.csv"],
        "sourceDigestSha256": digest,
        "sourceBasis": [
            "https://cdn.svc.asmodee.net/production-spacecowboys/uploads/2025/10/SCSPL01EN_SPLENDOR_RULES_LIGHT.pdf",
            "https://raw.githubusercontent.com/anicolao/splendor/main/data/verified_card_properties.csv",
            "https://raw.githubusercontent.com/bouk/splendimax/refs/heads/master/Splendor%20Cards.csv",
        ],
        "componentSummary": {
            "developmentCards": len(cards),
            "developmentCardsByLevel": {"1": 40, "2": 30, "3": 20},
            "developmentCardsPerBonusColor": 18,
            "nobleTiles": len(nobles),
        },
        "colors": component["colors"],
        "developmentCards": cards,
        "nobles": nobles,
        "rightsNoteZh": (
            "仅建模规则数值与原创功能占位；不含官方 Logo、插画、人物肖像、"
            "装饰边框或扫描素材。"
        ),
    }
    write_json(MODEL / "card-catalog.json", catalog)
    print("Generated card-catalog.json: 90 developments and 10 nobles.")


if __name__ == "__main__":
    main()
