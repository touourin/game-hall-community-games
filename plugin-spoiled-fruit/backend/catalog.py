from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CATALOG_PATH = Path(__file__).resolve().parents[1] / "model" / "card-catalog.json"
EFFECT_PATH = Path(__file__).resolve().parents[1] / "model" / "effect-catalog.json"


@dataclass(frozen=True)
class CardDefinition:
    id: str
    code: str
    sort_index: int
    kind: str
    name_zh: str
    effect_id: str
    slug: str


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


_card_data = _load(CATALOG_PATH)
_effect_data = _load(EFFECT_PATH)

CARD_DEFINITIONS = {
    item["id"]: CardDefinition(
        id=item["id"],
        code=item["cardCode"],
        sort_index=item["sortIndex"],
        kind=item["kind"],
        name_zh=item["nameZh"],
        effect_id=item["effectId"],
        slug=item["slug"],
    )
    for item in _card_data["cards"]
}

NORMAL_DEFINITIONS = tuple(
    sorted(
        (card for card in CARD_DEFINITIONS.values() if card.kind == "normal"),
        key=lambda card: card.sort_index,
    )
)
OLD_MAID_DEFINITIONS = tuple(
    sorted(
        (card for card in CARD_DEFINITIONS.values() if card.kind == "old_maid"),
        key=lambda card: card.sort_index,
    )
)
EFFECT_LABELS = {
    effect["id"]: effect["labelZh"] for effect in _effect_data["effects"]
}
EFFECT_TEXTS = {
    effect["id"]: effect["cardTextZh"] for effect in _effect_data["effects"]
}
EFFECT_LABELS["old_maid"] = _effect_data["oldMaidRule"]["labelZh"]
EFFECT_TEXTS["old_maid"] = _effect_data["oldMaidRule"]["cardTextZh"]


def definition_view(catalog_id: str) -> dict[str, Any]:
    card = CARD_DEFINITIONS[catalog_id]
    return {
        "catalogId": card.id,
        "cardCode": card.code,
        "sortIndex": card.sort_index,
        "kind": card.kind,
        "nameZh": card.name_zh,
        "effectId": card.effect_id,
        "effectLabelZh": EFFECT_LABELS[card.effect_id],
        "effectTextZh": EFFECT_TEXTS[card.effect_id],
        "slug": card.slug,
    }
