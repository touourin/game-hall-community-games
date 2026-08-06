from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "cards.json"
SUPPORTED_EFFECT_TYPES = {
    "spot_move",
    "persistent_spot",
    "seal",
    "peek_public",
    "loan_discount",
    "margin_buffer",
    "remove_persistent",
    "information_swap",
}
SUPPORTED_STRENGTHS = {"普通", "强烈", "危机", "趋势", "功能", "修正", "强修正"}


@dataclass(frozen=True)
class CardDefinition:
    id: str
    name: str
    kind: str
    category: str
    strength: str
    subtype: str
    target_label: str
    timing: str
    text: str
    duration_text: str
    keywords: tuple[str, ...]
    copies: int
    effect: dict[str, Any]

    def public_dict(self, instance_id: str | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {
            "cardId": self.id,
            "name": self.name,
            "kind": self.kind,
            "category": self.category,
            "strength": self.strength,
            "subtype": self.subtype,
            "targetLabel": self.target_label,
            "timing": self.timing,
            "text": self.text,
            "durationText": self.duration_text,
            "keywords": list(self.keywords),
        }
        if instance_id is not None:
            result["instanceId"] = instance_id
        return result


def _catalog_error(message: str) -> None:
    raise RuntimeError(f"疯狂期货卡牌目录无效：{message}")


def _validate_move(move: Any, commodity_ids: set[str], card_id: str) -> None:
    if not isinstance(move, dict) or move.get("commodity") not in commodity_ids:
        _catalog_error(f"{card_id} 包含未知商品目标")
    delta = move.get("delta")
    if isinstance(delta, bool) or not isinstance(delta, int) or delta == 0:
        _catalog_error(f"{card_id} 的价格移动必须是非零整数")


def _validate_card(
    card: Any,
    *,
    expected_kind: str,
    commodity_ids: set[str],
    zones: dict[str, Any],
) -> None:
    if not isinstance(card, dict):
        _catalog_error("卡牌定义必须是对象")
    card_id = card.get("id")
    if not isinstance(card_id, str) or not card_id:
        _catalog_error("卡牌必须包含非空 ID")
    if card.get("kind") != expected_kind:
        _catalog_error(f"{card_id} 的 kind 必须是 {expected_kind}")
    copies = card.get("copies")
    if isinstance(copies, bool) or not isinstance(copies, int) or copies <= 0:
        _catalog_error(f"{card_id} 的复制数量必须是正整数")
    for field in (
        "name",
        "category",
        "strength",
        "subtype",
        "targetLabel",
        "timing",
        "text",
        "durationText",
    ):
        if not isinstance(card.get(field), str) or not card[field].strip():
            _catalog_error(f"{card_id} 缺少 {field}")
    if card["strength"] not in SUPPORTED_STRENGTHS:
        _catalog_error(f"{card_id} 的强度分类无效")
    if not isinstance(card.get("keywords"), list):
        _catalog_error(f"{card_id} 的 keywords 必须是数组")

    effect = card.get("effect")
    if not isinstance(effect, dict) or effect.get("type") not in SUPPORTED_EFFECT_TYPES:
        _catalog_error(f"{card_id} 使用了未知牌效")
    effect_type = effect["type"]
    if effect_type in {"spot_move", "persistent_spot"}:
        if effect.get("choose"):
            targets = effect.get("targetOptions")
            delta = effect.get("delta")
            if (
                not isinstance(targets, list)
                or not targets
                or any(target not in commodity_ids for target in targets)
            ):
                _catalog_error(f"{card_id} 的可选目标范围无效")
            if isinstance(delta, bool) or not isinstance(delta, int) or delta == 0:
                _catalog_error(f"{card_id} 的价格移动必须是非零整数")
            zone = effect.get("zone")
            if zone is not None and zone not in zones:
                _catalog_error(f"{card_id} 使用了未知价格区间")
        else:
            moves = effect.get("moves")
            if not isinstance(moves, list) or not moves:
                _catalog_error(f"{card_id} 必须至少影响一种商品")
            for move in moves:
                _validate_move(move, commodity_ids, card_id)
        if effect_type == "persistent_spot":
            triggers = effect.get("triggers")
            if isinstance(triggers, bool) or not isinstance(triggers, int) or triggers <= 0:
                _catalog_error(f"{card_id} 的持续次数必须是正整数")
            if effect.get("scope") not in {"personal", "public"}:
                _catalog_error(f"{card_id} 的持续效果范围无效")
    elif effect_type == "seal" and effect.get("side") not in {"up", "down"}:
        _catalog_error(f"{card_id} 的封板方向无效")
    elif effect_type == "peek_public":
        if not isinstance(effect.get("count"), int) or effect["count"] <= 0:
            _catalog_error(f"{card_id} 的预见数量无效")
    elif effect_type == "loan_discount":
        rate = effect.get("ratePercent")
        if isinstance(rate, bool) or not isinstance(rate, int) or not 0 <= rate < 10:
            _catalog_error(f"{card_id} 的优惠利率无效")
    elif effect_type == "margin_buffer":
        amount = effect.get("amount")
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            _catalog_error(f"{card_id} 的保证金缓冲无效")
    elif effect_type == "remove_persistent":
        if effect.get("scope") not in {"personal", "public"}:
            _catalog_error(f"{card_id} 的移除范围无效")
        if effect.get("direction") not in {None, "up", "down"}:
            _catalog_error(f"{card_id} 的移除方向无效")
        if effect.get("strategy") not in {
            None,
            "all",
            "latest",
            "most_remaining_oldest",
        }:
            _catalog_error(f"{card_id} 的移除顺序无效")
    elif effect_type == "information_swap":
        for field in ("draw", "discard"):
            value = effect.get(field)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                _catalog_error(f"{card_id} 的信息置换数量无效")

    movement_deltas = [
        move["delta"] for move in effect.get("moves", []) if "delta" in move
    ]
    if effect.get("choose") and isinstance(effect.get("delta"), int):
        movement_deltas.append(effect["delta"])
    subtype = card["subtype"]
    if effect_type in {"spot_move", "persistent_spot"} and (
        "上涨" in subtype or "扶升" in subtype
    ) and (
        not movement_deltas or any(delta <= 0 for delta in movement_deltas)
    ):
        _catalog_error(f"{card_id} 的上涨牌强度方向与牌效不一致")
    if effect_type in {"spot_move", "persistent_spot"} and (
        "下跌" in subtype or "压降" in subtype
    ) and (
        not movement_deltas or any(delta >= 0 for delta in movement_deltas)
    ):
        _catalog_error(f"{card_id} 的下跌牌强度方向与牌效不一致")


def _load_catalog() -> dict[str, Any]:
    with CATALOG_PATH.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    ladder = payload.get("priceLadder", [])
    if len(ladder) != 51:
        raise RuntimeError("疯狂期货价格阶梯必须包含 51 格")
    if (
        any(isinstance(price, bool) or not isinstance(price, int) for price in ladder)
        or any(price % 2 for price in ladder)
        or any(left >= right for left, right in zip(ladder, ladder[1:]))
    ):
        raise RuntimeError("疯狂期货价格阶梯必须全部为偶数")

    commodities = payload.get("commodities", [])
    commodity_ids = {
        commodity.get("id")
        for commodity in commodities
        if isinstance(commodity, dict) and isinstance(commodity.get("id"), str)
    }
    if len(commodity_ids) != 4 or len(commodities) != 4:
        _catalog_error("必须恰好定义四种唯一商品")
    zones = payload.get("zones")
    if not isinstance(zones, dict) or set(zones) != {"low", "middle", "high"}:
        _catalog_error("价格区间必须包含 low、middle、high")
    previous_high = -1
    for name in ("low", "middle", "high"):
        bounds = zones[name]
        if (
            not isinstance(bounds, list)
            or len(bounds) != 2
            or any(isinstance(value, bool) or not isinstance(value, int) for value in bounds)
            or bounds[0] != previous_high + 1
            or bounds[0] > bounds[1]
            or bounds[1] >= len(ladder)
        ):
            _catalog_error(f"{name} 价格区间不连续或越界")
        previous_high = bounds[1]
    if previous_high != len(ladder) - 1:
        _catalog_error("价格区间必须覆盖全部 51 格")

    personal = payload.get("personal", [])
    public = payload.get("publicEvents", [])
    if not isinstance(personal, list) or sum(card.get("copies", 0) for card in personal) != 160:
        raise RuntimeError("疯狂期货个人牌必须合计 160 张")
    if not isinstance(public, list) or len(public) != 20:
        raise RuntimeError("疯狂期货公共事件牌必须为 20 张")
    for card in personal:
        _validate_card(
            card,
            expected_kind="personal",
            commodity_ids=commodity_ids,
            zones=zones,
        )
    for card in public:
        _validate_card(
            card,
            expected_kind="public",
            commodity_ids=commodity_ids,
            zones=zones,
        )
        if card.get("copies") != 1:
            _catalog_error(f"{card['id']} 公共事件必须只有一张")
    ids = [card["id"] for card in (*personal, *public)]
    if len(ids) != len(set(ids)):
        _catalog_error("卡牌 ID 不能重复")

    public_moves = [
        move["delta"]
        for card in public
        for move in card["effect"].get("moves", [])
    ]
    if not any(delta > 0 for delta in public_moves) or not any(
        delta < 0 for delta in public_moves
    ):
        _catalog_error("公共事件必须同时包含上涨与下跌影响")
    if not any(abs(delta) >= 2 for delta in public_moves):
        _catalog_error("公共事件必须包含至少一张强事件")
    persistent_directions = {
        "up" if sum(move["delta"] for move in card["effect"].get("moves", [])) > 0 else "down"
        for card in public
        if card["effect"]["type"] == "persistent_spot"
    }
    if persistent_directions != {"up", "down"}:
        _catalog_error("公共事件必须同时包含持续上涨与持续下跌")
    return payload


RAW_CATALOG = _load_catalog()
PRICE_LADDER: tuple[int, ...] = tuple(RAW_CATALOG["priceLadder"])
COMMODITIES: tuple[str, ...] = tuple(
    commodity["id"] for commodity in RAW_CATALOG["commodities"]
)
COMMODITY_LABELS: dict[str, str] = {
    commodity["id"]: commodity["name"]
    for commodity in RAW_CATALOG["commodities"]
}
COMMODITY_COLORS: dict[str, str] = {
    commodity["id"]: commodity["color"]
    for commodity in RAW_CATALOG["commodities"]
}
PRICE_ZONES: dict[str, tuple[int, int]] = {
    name: tuple(bounds)  # type: ignore[arg-type]
    for name, bounds in RAW_CATALOG["zones"].items()
}


def _definition(payload: dict[str, Any]) -> CardDefinition:
    return CardDefinition(
        id=payload["id"],
        name=payload["name"],
        kind=payload["kind"],
        category=payload["category"],
        strength=payload["strength"],
        subtype=payload["subtype"],
        target_label=payload["targetLabel"],
        timing=payload["timing"],
        text=payload["text"],
        duration_text=payload["durationText"],
        keywords=tuple(payload["keywords"]),
        copies=payload["copies"],
        effect=payload["effect"],
    )


PERSONAL_CARDS: tuple[CardDefinition, ...] = tuple(
    _definition(card) for card in RAW_CATALOG["personal"]
)
PUBLIC_CARDS: tuple[CardDefinition, ...] = tuple(
    _definition(card) for card in RAW_CATALOG["publicEvents"]
)
CARD_BY_ID: dict[str, CardDefinition] = {
    card.id: card for card in (*PERSONAL_CARDS, *PUBLIC_CARDS)
}


def card_id_from_instance(instance_id: str) -> str:
    return instance_id.split("#", 1)[0]


def card_for_instance(instance_id: str) -> CardDefinition:
    try:
        return CARD_BY_ID[card_id_from_instance(instance_id)]
    except KeyError as exc:
        raise ValueError(f"未知卡牌实例：{instance_id}") from exc


def new_personal_deck() -> list[str]:
    return [
        f"{card.id}#{copy_index}"
        for card in PERSONAL_CARDS
        for copy_index in range(1, card.copies + 1)
    ]


def new_public_deck() -> list[str]:
    return [f"{card.id}#1" for card in PUBLIC_CARDS]
