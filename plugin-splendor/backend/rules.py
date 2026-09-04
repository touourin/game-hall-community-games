from __future__ import annotations

from typing import Any

from .catalog import PIECE_COLORS, STANDARD_COLORS, card, noble
from .state import PlayerBoard, empty_piece_vector


def bonus_vector(board: PlayerBoard) -> dict[str, int]:
    result = {color: 0 for color in STANDARD_COLORS}
    for card_id in board.purchased_card_ids:
        result[card(card_id)["bonusColor"]] += 1
    return result


def score_breakdown(board: PlayerBoard) -> tuple[int, int, int]:
    card_score = sum(card(card_id)["prestige"] for card_id in board.purchased_card_ids)
    noble_score = sum(noble(noble_id)["prestige"] for noble_id in board.noble_ids)
    return card_score + noble_score, card_score, noble_score


def effective_cost(card_id: str, bonuses: dict[str, int]) -> dict[str, int]:
    cost = card(card_id)["cost"]
    return {
        color: max(int(cost[color]) - int(bonuses[color]), 0)
        for color in STANDARD_COLORS
    }


def can_afford(board: PlayerBoard, card_id: str) -> bool:
    need = effective_cost(card_id, bonus_vector(board))
    forced_gold = sum(max(need[color] - board.pieces[color], 0) for color in STANDARD_COLORS)
    return forced_gold <= board.pieces["gold"]


def recommended_payment(board: PlayerBoard, card_id: str) -> dict[str, int]:
    need = effective_cost(card_id, bonus_vector(board))
    payment = empty_piece_vector()
    for color in STANDARD_COLORS:
        payment[color] = min(board.pieces[color], need[color])
    payment["gold"] = sum(need[color] - payment[color] for color in STANDARD_COLORS)
    return payment


def validate_exact_payment(
    board: PlayerBoard,
    card_id: str,
    payment: dict[str, int],
) -> str | None:
    if set(payment) != set(PIECE_COLORS):
        return "支付必须包含五色宝石和黄金六个字段"
    for color in PIECE_COLORS:
        value = payment[color]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return "支付数量必须是非负整数"
        if value > board.pieces[color]:
            return "支付不能超过自己持有的棋子"
    need = effective_cost(card_id, bonus_vector(board))
    for color in STANDARD_COLORS:
        if payment[color] > need[color]:
            return "不能用同色宝石超额支付"
    remaining = sum(need[color] - payment[color] for color in STANDARD_COLORS)
    if payment["gold"] != remaining:
        return "黄金数量必须精确补足未支付的实际费用"
    return None


def eligible_nobles(board: PlayerBoard, noble_ids: list[str]) -> list[str]:
    bonuses = bonus_vector(board)
    return [
        noble_id
        for noble_id in noble_ids
        if all(
            bonuses[color] >= noble(noble_id)["requirement"][color]
            for color in STANDARD_COLORS
        )
    ]


def total_pieces(board: PlayerBoard) -> int:
    return sum(board.pieces.values())


def payment_preview(board: PlayerBoard, card_id: str) -> dict[str, Any]:
    bonuses = bonus_vector(board)
    need = effective_cost(card_id, bonuses)
    payment = recommended_payment(board, card_id)
    return {
        "effectiveCost": need,
        "recommendedPayment": payment,
        "minimumGold": payment["gold"],
        "affordable": payment["gold"] <= board.pieces["gold"],
    }
