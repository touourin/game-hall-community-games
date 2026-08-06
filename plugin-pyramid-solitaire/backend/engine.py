from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from backend.app.arcade.models import ArcadePlayer, ArcadeRoom, utc_now_iso
from backend.app.games.base import GameRuleError


PYRAMID_ROWS = 7
PYRAMID_SIZE = 28
DECK_SIZE = 52
TARGET_SUM = 13
SUITS = ("spades", "hearts", "diamonds", "clubs")
SUIT_SYMBOLS = {
    "spades": "♠",
    "hearts": "♥",
    "diamonds": "♦",
    "clubs": "♣",
}
RANK_LABELS = {1: "A", 11: "J", 12: "Q", 13: "K"}


def _build_coverers() -> tuple[tuple[int, ...], ...]:
    coverers: list[tuple[int, ...]] = []
    for row in range(PYRAMID_ROWS):
        row_start = row * (row + 1) // 2
        next_row_start = (row + 1) * (row + 2) // 2
        for column in range(row + 1):
            if row == PYRAMID_ROWS - 1:
                coverers.append(())
            else:
                coverers.append(
                    (next_row_start + column, next_row_start + column + 1)
                )
        assert len(coverers) == row_start + row + 1
    return tuple(coverers)


PYRAMID_COVERERS = _build_coverers()


@dataclass(frozen=True)
class Card:
    id: str
    suit: str
    rank: int


@dataclass
class PyramidSolitaireState:
    pyramid: list[Card | None] = field(default_factory=list)
    # The next stock card is at the end, so drawing never needs to shift the list.
    stock: list[Card] = field(default_factory=list)
    waste: list[Card] = field(default_factory=list)
    removal_moves: int = 0
    draws: int = 0
    cards_removed: int = 0
    elapsed_ms: int = 0
    started_monotonic: float = 0.0
    last_removed_ids: list[str] = field(default_factory=list)


class PyramidSolitaireEngine:
    key = "plugin-pyramid-solitaire"
    name = "金字塔纸牌"
    min_players = 1
    max_players = 1
    public_rooms = False

    def __init__(
        self,
        rng: random.Random | random.SystemRandom | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.rng = rng or random.SystemRandom()
        self.clock = clock or time.monotonic

    def initial_state(self) -> PyramidSolitaireState:
        return self._new_state()

    def start(self, room: ArcadeRoom) -> None:
        room.state = self._new_state()
        room.phase = "playing"

    def act(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        action: str,
        payload: dict[str, Any],
    ) -> None:
        if player.id != room.host_id:
            raise GameRuleError("只有挑战者本人可以操作纸牌")
        if room.phase != "playing":
            raise GameRuleError("当前牌局已经结束")

        if action == "reset":
            room.started_at = utc_now_iso()
            self.start(room)
            return

        state: PyramidSolitaireState = room.state
        if action == "draw":
            self._draw(state)
        elif action == "remove":
            self._remove(state, payload)
        else:
            raise GameRuleError("不支持这个纸牌操作")

        state.elapsed_ms = self._elapsed_ms(state)
        self._finish_if_needed(room, player)

    def view(self, room: ArcadeRoom, viewer: ArcadePlayer) -> dict[str, Any]:
        state: PyramidSolitaireState = room.state
        elapsed_ms = (
            self._elapsed_ms(state) if room.phase == "playing" else state.elapsed_ms
        )
        available = self._available_cards(state)
        pyramid = [
            None
            if card is None
            else self._card_view(card, card.id in available)
            for card in state.pyramid
        ]
        waste_top = state.waste[-1] if state.waste else None
        return {
            "targetSum": TARGET_SUM,
            "pyramid": pyramid,
            "pyramidCleared": self._pyramid_cleared(state),
            "stockRemaining": len(state.stock),
            "stockPass": 1,
            "maxStockPasses": 1,
            "wasteCount": len(state.waste),
            "wasteTop": (
                self._card_view(waste_top, True) if waste_top is not None else None
            ),
            "availableCardIds": list(available),
            "canDraw": room.phase == "playing" and bool(state.stock),
            "removalMoves": state.removal_moves,
            "draws": state.draws,
            "cardsRemoved": state.cards_removed,
            "elapsedMs": elapsed_ms,
            "lastRemovedIds": list(state.last_removed_ids),
            "won": viewer.id in room.winner_player_ids,
            "result": room.winner if room.phase == "finished" else None,
        }

    def player_result(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
    ) -> tuple[str, str, bool]:
        return "solver", "solo", player.id in room.winner_player_ids

    def player_score(self, room: ArcadeRoom, player: ArcadePlayer) -> int | None:
        if room.phase != "finished" or player.id not in room.winner_player_ids:
            return None
        state: PyramidSolitaireState = room.state
        return state.elapsed_ms

    def record_state(self, room: ArcadeRoom) -> dict[str, Any]:
        state: PyramidSolitaireState = room.state
        return {
            "pyramid_cleared": self._pyramid_cleared(state),
            "removal_moves": state.removal_moves,
            "draws": state.draws,
            "cards_removed": state.cards_removed,
            "elapsed_ms": state.elapsed_ms,
            "result": room.winner,
        }

    def _new_state(self) -> PyramidSolitaireState:
        deck = [
            Card(id=f"{suit}-{rank}", suit=suit, rank=rank)
            for suit in SUITS
            for rank in range(1, TARGET_SUM + 1)
        ]
        self.rng.shuffle(deck)
        return PyramidSolitaireState(
            pyramid=list(deck[:PYRAMID_SIZE]),
            stock=list(reversed(deck[PYRAMID_SIZE:])),
            started_monotonic=self.clock(),
        )

    @staticmethod
    def _draw(state: PyramidSolitaireState) -> None:
        if not state.stock:
            raise GameRuleError("牌库已经翻完，本局不能再次翻牌")
        state.waste.append(state.stock.pop())
        state.draws += 1
        state.last_removed_ids = []

    def _remove(
        self,
        state: PyramidSolitaireState,
        payload: dict[str, Any],
    ) -> None:
        card_ids = payload.get("cardIds")
        if (
            not isinstance(card_ids, list)
            or len(card_ids) not in {1, 2}
            or any(not isinstance(card_id, str) or not card_id for card_id in card_ids)
            or len(set(card_ids)) != len(card_ids)
        ):
            raise GameRuleError("请选择一张 K，或两张点数合计为 13 的牌")

        available = self._available_cards(state)
        try:
            selected = [available[card_id] for card_id in card_ids]
        except KeyError as exc:
            raise GameRuleError("只能选择没有被压住的牌或弃牌堆顶牌") from exc

        cards = [entry[2] for entry in selected]
        if len(cards) == 1 and cards[0].rank != TARGET_SUM:
            raise GameRuleError("只有 K 可以单独消除")
        if len(cards) == 2 and sum(card.rank for card in cards) != TARGET_SUM:
            raise GameRuleError("两张牌的点数合计必须为 13")

        for source, index, _card in selected:
            if source == "pyramid":
                state.pyramid[index] = None
            else:
                # There is only one available waste card and duplicate IDs were rejected.
                state.waste.pop()
        state.removal_moves += 1
        state.cards_removed += len(cards)
        state.last_removed_ids = list(card_ids)

    def _finish_if_needed(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
    ) -> None:
        state: PyramidSolitaireState = room.state
        cleared = self._pyramid_cleared(state)
        if cleared == PYRAMID_SIZE:
            room.finish(
                "completed",
                [player.id],
                (
                    f"清空 28 张金字塔牌，用时 {self._format_duration(state.elapsed_ms)}，"
                    f"完成 {state.removal_moves} 次消除"
                ),
            )
            return
        if not state.stock and not self._has_legal_removal(state):
            room.finish(
                "failed",
                [],
                f"牌库耗尽且没有可用组合，本轮清除了 {cleared}/28 张金字塔牌",
            )

    def _available_cards(
        self,
        state: PyramidSolitaireState,
    ) -> dict[str, tuple[str, int, Card]]:
        available: dict[str, tuple[str, int, Card]] = {}
        for index, card in enumerate(state.pyramid):
            if card is not None and self._is_exposed(state, index):
                available[card.id] = ("pyramid", index, card)
        if state.waste:
            card = state.waste[-1]
            available[card.id] = ("waste", len(state.waste) - 1, card)
        return available

    @staticmethod
    def _is_exposed(state: PyramidSolitaireState, index: int) -> bool:
        if not 0 <= index < len(PYRAMID_COVERERS):
            return False
        return all(state.pyramid[coverer] is None for coverer in PYRAMID_COVERERS[index])

    def _has_legal_removal(self, state: PyramidSolitaireState) -> bool:
        cards = [entry[2] for entry in self._available_cards(state).values()]
        if any(card.rank == TARGET_SUM for card in cards):
            return True
        ranks = {card.rank for card in cards}
        return any(TARGET_SUM - rank in ranks for rank in ranks)

    @staticmethod
    def _pyramid_cleared(state: PyramidSolitaireState) -> int:
        return sum(card is None for card in state.pyramid)

    def _elapsed_ms(self, state: PyramidSolitaireState) -> int:
        return max(0, round((self.clock() - state.started_monotonic) * 1_000))

    @staticmethod
    def _card_view(card: Card, exposed: bool) -> dict[str, Any]:
        return {
            "id": card.id,
            "suit": card.suit,
            "suitSymbol": SUIT_SYMBOLS[card.suit],
            "rank": card.rank,
            "label": RANK_LABELS.get(card.rank, str(card.rank)),
            "color": "red" if card.suit in {"hearts", "diamonds"} else "black",
            "exposed": exposed,
        }

    @staticmethod
    def _format_duration(elapsed_ms: int) -> str:
        total_tenths = elapsed_ms // 100
        minutes, tenths_in_minute = divmod(total_tenths, 600)
        seconds, tenths = divmod(tenths_in_minute, 10)
        if minutes:
            return f"{minutes} 分 {seconds:02d}.{tenths} 秒"
        return f"{seconds}.{tenths} 秒"
