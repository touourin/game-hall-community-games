from __future__ import annotations

from dataclasses import dataclass
from typing import Any


MODEL_VERSION = "1.0.0"
FRUIT_ORDER = ("banana", "strawberry", "lime", "plum")
COPY_DISTRIBUTION = {1: 5, 2: 3, 3: 3, 4: 2, 5: 1}
FRUIT_SPECS: dict[str, dict[str, Any]] = {
    "banana": {
        "nameZh": "香蕉",
        "nameEn": "Banana",
        "shape": "crescent-stem",
        "pattern": "diagonal-stripe",
        "palette": {"base": "#F3C94A", "dark": "#8A6512", "light": "#FFF1A8"},
    },
    "strawberry": {
        "nameZh": "草莓",
        "nameEn": "Strawberry",
        "shape": "seeded-heart",
        "pattern": "dot-seeds",
        "palette": {"base": "#E9545B", "dark": "#8F2330", "light": "#FFC0BD"},
    },
    "lime": {
        "nameZh": "青柠",
        "nameEn": "Lime",
        "shape": "segmented-round",
        "pattern": "radial-wedge",
        "palette": {"base": "#79B94B", "dark": "#386A28", "light": "#C8E89D"},
    },
    "plum": {
        "nameZh": "李子",
        "nameEn": "Plum",
        "shape": "oval-leaf",
        "pattern": "offset-highlight",
        "palette": {"base": "#7D5AA6", "dark": "#432965", "light": "#CDB8E8"},
    },
}

ZH_NUMERALS = {1: "一", 2: "两", 3: "三", 4: "四", 5: "五"}


def alt_zh(fruit_id: str, fruit_count: int) -> str:
    classifier = "根" if fruit_id == "banana" else "个"
    return f"{ZH_NUMERALS[fruit_count]}{classifier}{FRUIT_SPECS[fruit_id]['nameZh']}"


@dataclass(frozen=True)
class FruitCard:
    id: str
    face_id: str
    fruit_id: str
    fruit_count: int
    copy_index: int

    def public(self) -> dict[str, Any]:
        spec = FRUIT_SPECS[self.fruit_id]
        noun = spec["nameZh"]
        return {
            "faceId": self.face_id,
            "fruitId": self.fruit_id,
            "fruitCount": self.fruit_count,
            "labelZh": f"{noun} ×{self.fruit_count}",
            "altZh": alt_zh(self.fruit_id, self.fruit_count),
            "shape": spec["shape"],
            "pattern": spec["pattern"],
            "palette": dict(spec["palette"]),
        }


def build_deck() -> list[FruitCard]:
    cards: list[FruitCard] = []
    for fruit_id in FRUIT_ORDER:
        for fruit_count, copies in COPY_DISTRIBUTION.items():
            for copy_index in range(1, copies + 1):
                cards.append(
                    FruitCard(
                        id=f"{fruit_id}-{fruit_count}-{copy_index:02d}",
                        face_id=f"face-{fruit_id}-{fruit_count}",
                        fruit_id=fruit_id,
                        fruit_count=fruit_count,
                        copy_index=copy_index,
                    )
                )
    return cards


ALL_CARDS = tuple(build_deck())
CARD_INDEX = {card.id: card for card in ALL_CARDS}
EXPECTED_CARD_IDS = frozenset(CARD_INDEX)


def public_catalog() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for fruit_id in FRUIT_ORDER:
        spec = FRUIT_SPECS[fruit_id]
        for fruit_count, copies in COPY_DISTRIBUTION.items():
            result.append(
                {
                    "faceId": f"face-{fruit_id}-{fruit_count}",
                    "fruitId": fruit_id,
                    "fruitCount": fruit_count,
                    "copies": copies,
                    "labelZh": f"{spec['nameZh']} ×{fruit_count}",
                    "altZh": alt_zh(fruit_id, fruit_count),
                    "shape": spec["shape"],
                    "pattern": spec["pattern"],
                    "palette": dict(spec["palette"]),
                }
            )
    return result
