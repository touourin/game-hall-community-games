from __future__ import annotations

from collections.abc import Iterable

from .catalog import SUIT_ORDER, value_of
from .state import PlayerBoard, ScoreRow


def score_board(player_id: str, board: PlayerBoard) -> ScoreRow:
    subtotals: dict[str, int] = {}
    adjustments = 0
    for suit in SUIT_ORDER:
        pile = board.bank[suit]
        if not pile:
            subtotals[suit] = 0
            continue
        subtotal = max(value_of(card_id) for card_id in pile)
        if suit == "mermaid" and board.trait_id == "trait-golden-scales":
            subtotal += 5
            adjustments += 5
        subtotals[suit] = subtotal
    return ScoreRow(
        player_id=player_id,
        suit_subtotals=subtotals,
        card_adjustments=adjustments,
        total=sum(subtotals.values()),
        bank_card_count=sum(len(pile) for pile in board.bank.values()),
        eligible=not board.forfeited,
    )


def rank_scores(rows: Iterable[ScoreRow]) -> tuple[list[ScoreRow], list[str]]:
    scored = list(rows)
    eligible = [row for row in scored if row.eligible]
    if not eligible:
        return scored, []

    ordered_keys = sorted(
        {(row.total, row.bank_card_count) for row in eligible},
        reverse=True,
    )
    ranks = {key: index + 1 for index, key in enumerate(ordered_keys)}
    winning_key = ordered_keys[0]
    winners: list[str] = []
    for row in scored:
        if not row.eligible:
            row.rank = None
            continue
        key = (row.total, row.bank_card_count)
        row.rank = ranks[key]
        row.winner = key == winning_key
        if row.winner:
            winners.append(row.player_id)
    return scored, winners

