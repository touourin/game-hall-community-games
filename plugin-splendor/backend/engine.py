from __future__ import annotations

import random
from dataclasses import asdict
from typing import Any

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError

from .catalog import (
    PIECE_COLORS,
    STANDARD_COLORS,
    card,
    card_view,
    color_catalog_view,
    development_ids,
    noble,
    noble_ids,
    noble_view,
)
from .rules import (
    bonus_vector,
    can_afford,
    eligible_nobles,
    payment_preview,
    score_breakdown,
    total_pieces,
    validate_exact_payment,
)
from .state import (
    GameResult,
    PlayerBoard,
    PublicEvent,
    Reservation,
    ScoreRow,
    SplendorState,
    TierState,
    TurnState,
    empty_piece_vector,
)


RULES_PROFILE = "base-2024-refresh"
EVENT_LIMIT = 96
RESERVATION_LIMIT = 3
PIECE_LIMIT = 10
TARGET_PRESTIGE = 15
SUPPLY_BY_PLAYER_COUNT = {2: 4, 3: 5, 4: 7}
PRIMARY_ACTIONS = {
    "take_different",
    "take_same",
    "reserve_face_up",
    "reserve_blind",
    "purchase_face_up",
    "purchase_reserved",
}


class SplendorEngine:
    key = "plugin-splendor"
    name = "璀璨宝石"
    min_players = 2
    max_players = 4
    action_phases = {"playing"}

    def __init__(self, rng: random.Random | random.SystemRandom | None = None) -> None:
        self.rng = rng or random.SystemRandom()

    def initial_state(self) -> SplendorState:
        return SplendorState()

    def start(self, room: ArcadeRoom) -> None:
        members = [player for player in room.players if not player.left_room]
        if not self.min_players <= len(members) <= self.max_players:
            raise GameRuleError("璀璨宝石需要 2–4 位玩家")
        if room.options.get("rulesProfile", RULES_PROFILE) != RULES_PROFILE:
            raise GameRuleError("当前实现只支持 2024 基础常规规则")

        if room.options.get("firstPlayer") == "host":
            starter = next((player for player in members if player.id == room.host_id), members[0])
        else:
            starter = self.rng.choice(members)
        starter_index = members.index(starter)
        ordered = members[starter_index:] + members[:starter_index]

        tiers: dict[int, TierState] = {}
        for level in (1, 2, 3):
            deck = development_ids(level)
            self.rng.shuffle(deck)
            market = [deck.pop(0) for _ in range(4)]
            tiers[level] = TierState(level=level, deck=deck, market=market)

        shuffled_nobles = noble_ids()
        self.rng.shuffle(shuffled_nobles)
        visible_count = len(ordered) + 1
        visible_nobles = shuffled_nobles[:visible_count]
        unused_nobles = shuffled_nobles[visible_count:]

        colored_count = SUPPLY_BY_PLAYER_COUNT[len(ordered)]
        supply = {color: colored_count for color in STANDARD_COLORS}
        supply["gold"] = 5
        state = SplendorState(
            phase="turn_action",
            revision=1,
            market_revision=1,
            turn_order=[player.id for player in ordered],
            current_player_index=0,
            turn=TurnState(
                first_player_id=starter.id,
                active_player_id=starter.id,
                round_number=1,
            ),
            supply=dict(supply),
            initial_supply=dict(supply),
            tiers=tiers,
            available_noble_ids=visible_nobles,
            unused_noble_ids=unused_nobles,
            players={player.id: PlayerBoard(display_name=player.name) for player in ordered},
        )
        room.state = state
        room.phase = "playing"
        room.round_number = 1
        self._emit(
            state,
            "game_started",
            f"{starter.name} 持有首位玩家标记，{len(ordered)} 人常规局开始",
            {"firstPlayerId": starter.id, "playerCount": len(ordered)},
        )
        self.assert_invariants(state)

    def act(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        action: str,
        payload: dict[str, Any],
    ) -> None:
        if room.phase != "playing":
            raise GameRuleError("当前牌局不能继续操作")
        state: SplendorState = room.state
        board = state.players.get(player.id)
        if board is None or board.forfeited:
            raise GameRuleError("你已不在本局行动序列中")
        self._check_revision(state, payload)

        handlers = {
            "take_different": self._take_different,
            "take_same": self._take_same,
            "reserve_face_up": self._reserve_face_up,
            "reserve_blind": self._reserve_blind,
            "purchase_face_up": self._purchase_face_up,
            "purchase_reserved": self._purchase_reserved,
            "return_tokens": self._return_tokens,
            "choose_noble": self._choose_noble,
            "resign": self._resign,
        }
        handler = handlers.get(action)
        if handler is None:
            raise GameRuleError("不支持这个璀璨宝石操作")
        if action in PRIMARY_ACTIONS:
            self._require_actor(state, player.id, "turn_action")
        handler(room, state, player, payload)
        if action != "resign":
            state.revision += 1
        self.assert_invariants(state)

    # ------------------------------------------------------------------
    # Main actions

    def _take_different(
        self,
        room: ArcadeRoom,
        state: SplendorState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        raw_colors = payload.get("colors")
        if not isinstance(raw_colors, list) or any(not isinstance(item, str) for item in raw_colors):
            raise GameRuleError("请选择要拿取的不同颜色宝石")
        colors = list(raw_colors)
        if len(colors) != len(set(colors)) or any(color not in STANDARD_COLORS for color in colors):
            raise GameRuleError("不同色行动只能选择互不相同的五种宝石色")
        available = [color for color in STANDARD_COLORS if state.supply[color] > 0]
        required = min(3, len(available))
        if required == 0:
            raise GameRuleError("供应中没有可拿取的彩色宝石")
        if len(colors) != required:
            raise GameRuleError(f"当前必须选择 {required} 种不同颜色")
        if any(color not in available for color in colors):
            raise GameRuleError("所选颜色供应不足")

        board = state.players[player.id]
        for color in colors:
            state.supply[color] -= 1
            board.pieces[color] += 1
        self._emit(
            state,
            "pieces_taken",
            f"{player.name} 拿取 {self._piece_label({color: 1 for color in colors})}",
            {"playerId": player.id, "pieces": {color: 1 for color in colors}},
        )
        self._after_primary(room, state, player.id, "take_different")

    def _take_same(
        self,
        room: ArcadeRoom,
        state: SplendorState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        color = payload.get("color")
        if color not in STANDARD_COLORS:
            raise GameRuleError("同色行动只能选择一种彩色宝石")
        if state.supply[color] < 4:
            raise GameRuleError("选择同色两枚前，供应中必须至少有 4 枚该色宝石")
        state.supply[color] -= 2
        state.players[player.id].pieces[color] += 2
        self._emit(
            state,
            "pieces_taken",
            f"{player.name} 拿取 2 枚{self._color_name(color)}",
            {"playerId": player.id, "pieces": {color: 2}},
        )
        self._after_primary(room, state, player.id, "take_same")

    def _reserve_face_up(
        self,
        room: ArcadeRoom,
        state: SplendorState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._check_market_revision(state, payload)
        board = state.players[player.id]
        if len(board.reservations) >= RESERVATION_LIMIT:
            raise GameRuleError("每位玩家最多保留 3 张发展卡")
        card_id = payload.get("cardId")
        if not isinstance(card_id, str):
            raise GameRuleError("请选择市场中的发展卡")
        level, slot = self._locate_market(state, card_id)
        gold_taken = state.supply["gold"] > 0

        state.tiers[level].market[slot] = None
        reservation = self._new_reservation(state, card_id, level, "market", True)
        board.reservations.append(reservation)
        if gold_taken:
            state.supply["gold"] -= 1
            board.pieces["gold"] += 1
        self._emit(
            state,
            "card_reserved_public",
            f"{player.name} 保留一张公开的 {level} 级发展卡" + ("并取得 1 枚黄金" if gold_taken else ""),
            {
                "playerId": player.id,
                "reservationId": reservation.reservation_id,
                "card": card_view(card_id),
                "level": level,
                "goldTaken": gold_taken,
            },
        )
        self._refill_market(state, level, slot)
        self._after_primary(room, state, player.id, "reserve_face_up")

    def _reserve_blind(
        self,
        room: ArcadeRoom,
        state: SplendorState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._check_market_revision(state, payload)
        board = state.players[player.id]
        if len(board.reservations) >= RESERVATION_LIMIT:
            raise GameRuleError("每位玩家最多保留 3 张发展卡")
        level = payload.get("level")
        if isinstance(level, bool) or not isinstance(level, int) or level not in state.tiers:
            raise GameRuleError("请选择 1、2 或 3 级牌堆")
        tier = state.tiers[level]
        if not tier.deck:
            raise GameRuleError("该等级牌堆已经抽空")

        card_id = tier.deck.pop(0)
        state.market_revision += 1
        reservation = self._new_reservation(state, card_id, level, "deck", False)
        board.reservations.append(reservation)
        gold_taken = state.supply["gold"] > 0
        if gold_taken:
            state.supply["gold"] -= 1
            board.pieces["gold"] += 1
        self._emit(
            state,
            "card_reserved_blind",
            f"{player.name} 从 {level} 级牌堆盲保留一张牌" + ("并取得 1 枚黄金" if gold_taken else ""),
            {
                "playerId": player.id,
                "reservationId": reservation.reservation_id,
                "level": level,
                "goldTaken": gold_taken,
            },
        )
        self._after_primary(room, state, player.id, "reserve_blind")

    def _purchase_face_up(
        self,
        room: ArcadeRoom,
        state: SplendorState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._check_market_revision(state, payload)
        card_id = payload.get("cardId")
        if not isinstance(card_id, str):
            raise GameRuleError("请选择市场中的发展卡")
        level, slot = self._locate_market(state, card_id)
        payment = self._validated_payment(state.players[player.id], card_id, payload.get("payment"))

        state.tiers[level].market[slot] = None
        self._apply_purchase(state, player.id, card_id, payment)
        self._emit_purchase(state, player, card_id, payment, "market")
        self._refill_market(state, level, slot)
        self._after_primary(room, state, player.id, "purchase_face_up")

    def _purchase_reserved(
        self,
        room: ArcadeRoom,
        state: SplendorState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        board = state.players[player.id]
        reservation_id = payload.get("reservationId")
        reservation = next(
            (item for item in board.reservations if item.reservation_id == reservation_id),
            None,
        )
        if reservation is None:
            raise GameRuleError("只能购买自己保留区中的牌")
        payment = self._validated_payment(board, reservation.card_id, payload.get("payment"))

        board.reservations.remove(reservation)
        self._apply_purchase(state, player.id, reservation.card_id, payment)
        self._emit_purchase(state, player, reservation.card_id, payment, "reservation")
        self._after_primary(room, state, player.id, "purchase_reserved")

    # ------------------------------------------------------------------
    # Mandatory post-action resolution

    def _return_tokens(
        self,
        room: ArcadeRoom,
        state: SplendorState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_actor(state, player.id, "return_tokens")
        pieces = self._piece_vector(payload.get("pieces"), "归还")
        required = state.turn.pending_return_count
        if sum(pieces.values()) != required:
            raise GameRuleError(f"必须恰好归还 {required} 枚棋子")
        board = state.players[player.id]
        if any(pieces[color] > board.pieces[color] for color in PIECE_COLORS):
            raise GameRuleError("不能归还超过自己持有数量的棋子")
        for color in PIECE_COLORS:
            board.pieces[color] -= pieces[color]
            state.supply[color] += pieces[color]
        state.turn.pending_return_count = 0
        self._emit(
            state,
            "pieces_returned",
            f"{player.name} 归还 {self._piece_label(pieces)}，回到 10 枚上限",
            {"playerId": player.id, "pieces": pieces},
        )
        self._resolve_noble_or_complete(room, state, player.id)

    def _choose_noble(
        self,
        room: ArcadeRoom,
        state: SplendorState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_actor(state, player.id, "choose_noble")
        noble_id = payload.get("nobleId")
        if noble_id not in state.turn.eligible_noble_ids or noble_id not in state.available_noble_ids:
            raise GameRuleError("请选择本回合服务端列出的合资格贵族")
        self._acquire_noble(state, player.id, noble_id)
        state.turn.eligible_noble_ids = []
        self._complete_turn(room, state, player.id)

    def _after_primary(
        self,
        room: ArcadeRoom,
        state: SplendorState,
        player_id: str,
        action: str,
    ) -> None:
        state.turn.action_number += 1
        state.turn.last_action = action
        overage = total_pieces(state.players[player_id]) - PIECE_LIMIT
        if overage > 0:
            state.phase = "return_tokens"
            state.turn.pending_return_count = overage
            state.turn.eligible_noble_ids = []
            self._emit(
                state,
                "token_return_required",
                f"当前持有超过上限，必须归还 {overage} 枚棋子",
                {"playerId": player_id, "count": overage},
            )
            return
        self._resolve_noble_or_complete(room, state, player_id)

    def _resolve_noble_or_complete(
        self,
        room: ArcadeRoom,
        state: SplendorState,
        player_id: str,
    ) -> None:
        candidates = eligible_nobles(state.players[player_id], state.available_noble_ids)
        if len(candidates) == 1:
            self._acquire_noble(state, player_id, candidates[0])
        elif len(candidates) > 1:
            state.phase = "choose_noble"
            state.turn.eligible_noble_ids = list(candidates)
            self._emit(
                state,
                "noble_choice_required",
                "同时满足多位贵族，必须选择其中一位",
                {"playerId": player_id, "nobleIds": list(candidates)},
            )
            return
        self._complete_turn(room, state, player_id)

    def _acquire_noble(self, state: SplendorState, player_id: str, noble_id: str) -> None:
        state.available_noble_ids.remove(noble_id)
        state.players[player_id].noble_ids.append(noble_id)
        self._emit(
            state,
            "noble_acquired",
            f"{self._player_label(state, player_id)} 获得一位贵族与 3 点威望",
            {"playerId": player_id, "noble": noble_view(noble_id)},
        )

    def _complete_turn(self, room: ArcadeRoom, state: SplendorState, player_id: str) -> None:
        state.turn.pending_return_count = 0
        state.turn.eligible_noble_ids = []
        prestige = score_breakdown(state.players[player_id])[0]
        if prestige >= TARGET_PRESTIGE and state.turn.end_triggered_by is None:
            state.turn.end_triggered_by = player_id
            state.turn.final_turn_player_id = self._active_player_ids(state)[-1]
            self._emit(
                state,
                "final_round_triggered",
                f"{self._player_label(state, player_id)} 达到 {prestige} 分，最终轮开始",
                {
                    "playerId": player_id,
                    "prestige": prestige,
                    "finalTurnPlayerId": state.turn.final_turn_player_id,
                },
            )
        if (
            state.turn.end_triggered_by is not None
            and player_id == state.turn.final_turn_player_id
        ):
            self._finish_game(room, state, "final-round-complete")
            return
        self._advance_turn(room, state)

    # ------------------------------------------------------------------
    # Market, payment and turn utilities

    def _new_reservation(
        self,
        state: SplendorState,
        card_id: str,
        level: int,
        source: str,
        known_to_all: bool,
    ) -> Reservation:
        state.reservation_counter += 1
        return Reservation(
            reservation_id=f"r-{state.reservation_counter:04d}",
            card_id=card_id,
            level=level,
            source=source,
            known_to_all=known_to_all,
        )

    def _refill_market(self, state: SplendorState, level: int, slot: int) -> None:
        tier = state.tiers[level]
        replacement = tier.deck.pop(0) if tier.deck else None
        tier.market[slot] = replacement
        state.market_revision += 1
        if replacement is not None:
            self._emit(
                state,
                "market_refilled",
                f"{level} 级市场补充一张发展卡",
                {"level": level, "slot": slot, "card": card_view(replacement)},
            )

    def _locate_market(self, state: SplendorState, card_id: str) -> tuple[int, int]:
        for level, tier in state.tiers.items():
            for slot, current in enumerate(tier.market):
                if current == card_id:
                    return level, slot
        raise GameRuleError("该牌已不在市场中，请刷新后重试")

    def _validated_payment(
        self,
        board: PlayerBoard,
        card_id: str,
        raw_payment: Any,
    ) -> dict[str, int]:
        payment = self._piece_vector(raw_payment, "支付")
        message = validate_exact_payment(board, card_id, payment)
        if message is not None:
            raise GameRuleError(message)
        return payment

    def _apply_purchase(
        self,
        state: SplendorState,
        player_id: str,
        card_id: str,
        payment: dict[str, int],
    ) -> None:
        board = state.players[player_id]
        for color in PIECE_COLORS:
            board.pieces[color] -= payment[color]
            state.supply[color] += payment[color]
        board.purchased_card_ids.append(card_id)

    def _emit_purchase(
        self,
        state: SplendorState,
        player: ArcadePlayer,
        card_id: str,
        payment: dict[str, int],
        source: str,
    ) -> None:
        self._emit(
            state,
            "card_purchased",
            f"{player.name} 购买一张 {card(card_id)['level']} 级发展卡",
            {
                "playerId": player.id,
                "source": source,
                "card": card_view(card_id),
                "payment": dict(payment),
            },
        )

    def _advance_turn(self, room: ArcadeRoom, state: SplendorState) -> None:
        old_index = state.current_player_index
        count = len(state.turn_order)
        next_index = old_index
        for offset in range(1, count + 1):
            candidate = (old_index + offset) % count
            if not state.players[state.turn_order[candidate]].forfeited:
                next_index = candidate
                break
        if next_index <= old_index:
            state.turn.round_number += 1
        state.current_player_index = next_index
        state.turn.active_player_id = state.turn_order[next_index]
        state.phase = "turn_action"
        room.round_number = state.turn.round_number
        self._emit(
            state,
            "turn_advanced",
            f"轮到 {self._player_label(state, state.turn.active_player_id)}",
            {
                "playerId": state.turn.active_player_id,
                "roundNumber": state.turn.round_number,
            },
        )

    # ------------------------------------------------------------------
    # Settlement and platform hooks

    def _finish_game(
        self,
        room: ArcadeRoom,
        state: SplendorState,
        reason: str,
        forced_winner_ids: list[str] | None = None,
    ) -> None:
        active_ids = self._active_player_ids(state)
        if forced_winner_ids is None:
            best_score = max(score_breakdown(state.players[player_id])[0] for player_id in active_ids)
            finalists = [
                player_id
                for player_id in active_ids
                if score_breakdown(state.players[player_id])[0] == best_score
            ]
            fewest_cards = min(len(state.players[player_id].purchased_card_ids) for player_id in finalists)
            winner_ids = [
                player_id
                for player_id in finalists
                if len(state.players[player_id].purchased_card_ids) == fewest_cards
            ]
        else:
            winner_ids = list(forced_winner_ids)

        ordered = sorted(
            state.turn_order,
            key=lambda player_id: (
                state.players[player_id].forfeited,
                -score_breakdown(state.players[player_id])[0],
                len(state.players[player_id].purchased_card_ids),
                state.turn_order.index(player_id),
            ),
        )
        rows: list[ScoreRow] = []
        previous_key: tuple[bool, int, int] | None = None
        previous_rank = 0
        for index, player_id in enumerate(ordered):
            board = state.players[player_id]
            prestige, card_score, noble_score = score_breakdown(board)
            # A forfeited player is always ranked behind every active player,
            # even when both happen to have identical score/card totals.
            key = (board.forfeited, prestige, len(board.purchased_card_ids))
            rank = previous_rank if previous_key == key else index + 1
            previous_key, previous_rank = key, rank
            rows.append(
                ScoreRow(
                    player_id=player_id,
                    prestige=prestige,
                    card_prestige=card_score,
                    noble_prestige=noble_score,
                    purchased_card_count=len(board.purchased_card_ids),
                    rank=rank,
                    winner=player_id in winner_ids,
                    forfeited=board.forfeited,
                )
            )
        winner_names = "、".join(self._player_label(state, player_id) for player_id in winner_ids)
        outcome = "shared-win" if len(winner_ids) > 1 else "win"
        if reason == "last-player-standing":
            summary = f"其他玩家已退出，{winner_names} 获胜"
        else:
            best_row = next(row for row in rows if row.player_id == winner_ids[0])
            suffix = "共同获胜" if len(winner_ids) > 1 else "获胜"
            summary = (
                f"{winner_names} 以 {best_row.prestige} 点威望、"
                f"{best_row.purchased_card_count} 张发展卡{suffix}"
            )
        state.result = GameResult(
            winner_ids=winner_ids,
            outcome=outcome,
            reason=reason,
            rows=rows,
            summary_zh=summary,
        )
        state.phase = "finished"
        state.turn.active_player_id = None
        self._emit(
            state,
            "game_finished",
            summary,
            {"winnerPlayerIds": winner_ids, "outcome": outcome},
        )
        room.finish("prestige", winner_ids, summary)

    def _resign(
        self,
        room: ArcadeRoom,
        state: SplendorState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        if not self.manual_forfeit(room, player):
            raise GameRuleError("当前不能退出这局游戏")

    def manual_forfeit(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        if room.phase != "playing":
            return False
        state: SplendorState = room.state
        board = state.players.get(player.id)
        if board is None or board.forfeited:
            return False
        was_current = state.turn.active_player_id == player.id
        was_final_turn_player = bool(
            state.turn.end_triggered_by is not None
            and state.turn.final_turn_player_id == player.id
        )
        for color in PIECE_COLORS:
            state.supply[color] += board.pieces[color]
            board.pieces[color] = 0
        board.forfeited = True
        self._emit(
            state,
            "player_forfeited",
            f"{player.name} 退出牌局",
            {"playerId": player.id},
        )
        remaining = self._active_player_ids(state)
        if len(remaining) == 1:
            self._finish_game(room, state, "last-player-standing", remaining)
        else:
            state.turn.final_turn_player_id = remaining[-1] if state.turn.end_triggered_by else None
            if was_current:
                state.turn.pending_return_count = 0
                state.turn.eligible_noble_ids = []
                state.phase = "turn_action"
                if was_final_turn_player:
                    self._finish_game(room, state, "final-round-complete")
                else:
                    self._advance_turn(room, state)
        state.revision += 1
        self.assert_invariants(state)
        return True

    def disconnect_timeout(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        return self.manual_forfeit(room, player)

    def request_voter_ids(self, room: ArcadeRoom, kind: str) -> set[str]:
        return set(self._active_player_ids(room.state))

    def player_result(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
    ) -> tuple[str, str, bool]:
        state: SplendorState = room.state
        board = state.players.get(player.id)
        if board is None:
            return "未参赛", "individual", False
        if board.forfeited:
            return "已退出", "individual", False
        prestige = score_breakdown(board)[0]
        won = player.id in room.winner_player_ids
        if won and len(room.winner_player_ids) > 1:
            label = f"共同胜者 · {prestige} 点威望"
        elif won:
            label = f"胜者 · {prestige} 点威望"
        else:
            label = f"{prestige} 点威望"
        return label, "individual", won

    def record_state(self, room: ArcadeRoom) -> dict[str, Any]:
        return asdict(room.state)

    # ------------------------------------------------------------------
    # Safe player view

    def view(self, room: ArcadeRoom, viewer: ArcadePlayer) -> dict[str, Any]:
        state: SplendorState = room.state
        viewer_board = state.players.get(viewer.id)
        can_submit = bool(
            room.phase == "playing"
            and viewer_board is not None
            and not viewer_board.forfeited
            and state.turn.active_player_id == viewer.id
        )
        actions = self._legal_actions(state, viewer.id, can_submit)
        viewer_bonuses = bonus_vector(viewer_board) if viewer_board else {color: 0 for color in STANDARD_COLORS}

        tiers_view = []
        for level in (3, 2, 1):
            slots = []
            for slot, card_id in enumerate(state.tiers[level].market):
                if card_id is None:
                    slots.append({"slot": slot, "card": None})
                    continue
                item = card_view(card_id)
                item["payment"] = payment_preview(viewer_board, card_id) if viewer_board else None
                item["legal"] = {
                    "buy": bool(can_submit and state.phase == "turn_action" and viewer_board and can_afford(viewer_board, card_id)),
                    "reserve": bool(can_submit and state.phase == "turn_action" and viewer_board and len(viewer_board.reservations) < RESERVATION_LIMIT),
                }
                slots.append({"slot": slot, "card": item})
            tiers_view.append(
                {
                    "level": level,
                    "deckCount": len(state.tiers[level].deck),
                    "slots": slots,
                }
            )

        players_view = []
        for player_id in state.turn_order:
            board = state.players[player_id]
            member = room.player(player_id)
            prestige, card_score, noble_score = score_breakdown(board)
            reservations = []
            for reservation in board.reservations:
                reveal = reservation.known_to_all or viewer.id == player_id
                reservation_card = card_view(reservation.card_id) if reveal else None
                if reservation_card is not None and viewer.id == player_id:
                    reservation_card["payment"] = payment_preview(board, reservation.card_id)
                    reservation_card["legal"] = {
                        "buy": bool(can_submit and state.phase == "turn_action" and can_afford(board, reservation.card_id)),
                        "reserve": False,
                    }
                reservations.append(
                    {
                        "reservationId": reservation.reservation_id,
                        "level": reservation.level,
                        "source": reservation.source,
                        "knownToAll": reservation.known_to_all,
                        "card": reservation_card,
                    }
                )
            players_view.append(
                {
                    "id": player_id,
                    "name": member.name,
                    "seat": member.seat,
                    "connected": member.connected,
                    "forfeited": board.forfeited,
                    "isActive": state.turn.active_player_id == player_id,
                    "isFirstPlayer": state.turn.first_player_id == player_id,
                    "pieces": dict(board.pieces),
                    "bonuses": bonus_vector(board),
                    "score": prestige,
                    "cardPrestige": card_score,
                    "noblePrestige": noble_score,
                    "purchasedCount": len(board.purchased_card_ids),
                    "purchasedCards": [card_view(card_id) for card_id in board.purchased_card_ids],
                    "nobles": [noble_view(noble_id) for noble_id in board.noble_ids],
                    "reservations": reservations,
                }
            )

        nobles_view = []
        for noble_id in state.available_noble_ids:
            item = noble_view(noble_id)
            item["progress"] = {
                color: min(viewer_bonuses[color], item["requirement"][color])
                for color in STANDARD_COLORS
            }
            item["eligible"] = noble_id in state.turn.eligible_noble_ids
            nobles_view.append(item)

        return {
            "schemaVersion": state.schema_version,
            "modelVersion": state.model_version,
            "gameId": "splendor",
            "rulesProfile": state.rules_profile,
            "sceneId": self._scene_id(room, state),
            "phase": state.phase,
            "revision": state.revision,
            "marketRevision": state.market_revision,
            "roundNumber": state.turn.round_number,
            "actionNumber": state.turn.action_number,
            "turnOrder": list(state.turn_order),
            "currentPlayerId": state.turn.active_player_id,
            "firstPlayerId": state.turn.first_player_id,
            "finalRound": {
                "triggeredBy": state.turn.end_triggered_by,
                "finalTurnPlayerId": state.turn.final_turn_player_id,
                "remainingPlayerIds": self._remaining_final_players(state),
            } if state.turn.end_triggered_by else None,
            "colors": color_catalog_view(),
            "supply": dict(state.supply),
            "tiers": tiers_view,
            "availableNobles": nobles_view,
            "players": players_view,
            "selfPlayerId": viewer.id if viewer_board is not None else None,
            "actions": actions,
            "events": [
                {"seq": event.seq, "type": event.type, "message": event.message, "data": event.data}
                for event in state.events
            ],
            "result": self._result_view(state.result),
            "rules": {
                "targetPrestige": TARGET_PRESTIGE,
                "pieceLimit": PIECE_LIMIT,
                "reservationLimit": RESERVATION_LIMIT,
                "marketCardsPerLevel": 4,
                "noblePrestige": 3,
            },
        }

    def _legal_actions(
        self,
        state: SplendorState,
        viewer_id: str,
        can_submit: bool,
    ) -> dict[str, Any]:
        board = state.players.get(viewer_id)
        available = [color for color in STANDARD_COLORS if state.supply[color] > 0]
        required = min(3, len(available))
        turn_action = bool(can_submit and state.phase == "turn_action" and board is not None)
        return {
            "canAct": turn_action,
            "canTakeDifferent": bool(turn_action and required > 0),
            "requiredDistinctCount": required,
            "differentColors": available,
            "sameColors": [
                color for color in STANDARD_COLORS
                if turn_action and state.supply[color] >= 4
            ],
            "canReserve": bool(turn_action and board and len(board.reservations) < RESERVATION_LIMIT),
            "blindReserveLevels": [
                level for level in (3, 2, 1)
                if turn_action and board and len(board.reservations) < RESERVATION_LIMIT and state.tiers[level].deck
            ],
            "canReturnTokens": bool(can_submit and state.phase == "return_tokens"),
            "returnCount": state.turn.pending_return_count if can_submit else 0,
            "canChooseNoble": bool(can_submit and state.phase == "choose_noble"),
            "eligibleNobleIds": list(state.turn.eligible_noble_ids) if can_submit else [],
            "canResign": bool(board and not board.forfeited and state.phase != "finished"),
            "disabledReasonZh": self._disabled_reason(state, viewer_id, can_submit),
        }

    @staticmethod
    def _result_view(result: GameResult | None) -> dict[str, Any] | None:
        if result is None:
            return None
        return {
            "winnerIds": list(result.winner_ids),
            "outcome": result.outcome,
            "reason": result.reason,
            "summaryZh": result.summary_zh,
            "rows": [asdict(row) for row in result.rows],
        }

    # ------------------------------------------------------------------
    # Validation and small helpers

    def assert_invariants(self, state: SplendorState) -> None:
        if state.phase == "waiting":
            return
        expected_cards = set(development_ids())
        located_cards: list[str] = []
        for level, tier in state.tiers.items():
            assert len(tier.market) == 4, "each market tier keeps four stable slots"
            assert all(card(card_id)["level"] == level for card_id in tier.deck)
            assert all(
                card_id is None or card(card_id)["level"] == level
                for card_id in tier.market
            )
            located_cards.extend(tier.deck)
            located_cards.extend(card_id for card_id in tier.market if card_id is not None)
        for board in state.players.values():
            assert set(board.pieces) == set(PIECE_COLORS)
            assert all(isinstance(value, int) and value >= 0 for value in board.pieces.values())
            located_cards.extend(board.purchased_card_ids)
            for reservation in board.reservations:
                assert reservation.level == card(reservation.card_id)["level"]
                located_cards.append(reservation.card_id)
            assert len(board.reservations) <= RESERVATION_LIMIT
        assert len(located_cards) == len(expected_cards)
        assert set(located_cards) == expected_cards
        assert len(located_cards) == len(set(located_cards)), "development card duplicated between zones"

        assert set(state.supply) == set(PIECE_COLORS)
        assert all(isinstance(value, int) and value >= 0 for value in state.supply.values())
        for color in PIECE_COLORS:
            total = state.supply[color] + sum(board.pieces[color] for board in state.players.values())
            assert total == state.initial_supply[color], f"{color} piece conservation failed"

        located_nobles = list(state.available_noble_ids) + list(state.unused_noble_ids)
        for board in state.players.values():
            located_nobles.extend(board.noble_ids)
        assert set(located_nobles) == set(noble_ids())
        assert len(located_nobles) == len(set(located_nobles)) == 10

        assert state.phase in {"turn_action", "return_tokens", "choose_noble", "finished"}
        if state.phase == "finished":
            assert state.turn.active_player_id is None
            assert state.result is not None
        else:
            assert state.turn.active_player_id in state.players
            assert not state.players[state.turn.active_player_id].forfeited
        if state.phase == "return_tokens":
            assert state.turn.pending_return_count > 0
        if state.phase == "choose_noble":
            assert len(state.turn.eligible_noble_ids) > 1

    @staticmethod
    def _check_revision(state: SplendorState, payload: dict[str, Any]) -> None:
        revision = payload.get("revision")
        if isinstance(revision, bool) or not isinstance(revision, int):
            raise GameRuleError("操作缺少有效的状态版本")
        if revision != state.revision:
            raise GameRuleError("操作基于旧状态，请刷新后重试")

    @staticmethod
    def _check_market_revision(state: SplendorState, payload: dict[str, Any]) -> None:
        revision = payload.get("marketRevision")
        if isinstance(revision, bool) or not isinstance(revision, int):
            raise GameRuleError("操作缺少有效的市场版本")
        if revision != state.market_revision:
            raise GameRuleError("市场已经变化，请刷新后重试")

    @staticmethod
    def _require_actor(state: SplendorState, player_id: str, phase: str) -> PlayerBoard:
        if state.turn.active_player_id != player_id:
            raise GameRuleError("还没有轮到你")
        if state.phase != phase:
            if state.phase == "return_tokens":
                raise GameRuleError("必须先归还超出上限的棋子")
            if state.phase == "choose_noble":
                raise GameRuleError("必须先选择一位贵族")
            raise GameRuleError("当前阶段不能执行这个操作")
        return state.players[player_id]

    @staticmethod
    def _piece_vector(value: Any, label: str) -> dict[str, int]:
        if not isinstance(value, dict) or set(value) != set(PIECE_COLORS):
            raise GameRuleError(f"{label}必须包含五色宝石和黄金六个字段")
        result: dict[str, int] = {}
        for color in PIECE_COLORS:
            amount = value[color]
            if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
                raise GameRuleError(f"{label}数量必须是非负整数")
            result[color] = amount
        return result

    def _active_player_ids(self, state: SplendorState) -> list[str]:
        return [player_id for player_id in state.turn_order if not state.players[player_id].forfeited]

    def _remaining_final_players(self, state: SplendorState) -> list[str]:
        if state.turn.end_triggered_by is None or state.turn.active_player_id is None:
            return []
        active = self._active_player_ids(state)
        try:
            start = active.index(state.turn.active_player_id)
            end = active.index(state.turn.final_turn_player_id)
        except ValueError:
            return []
        if start <= end:
            return active[start : end + 1]
        return active[start:] + active[: end + 1]

    @staticmethod
    def _scene_id(room: ArcadeRoom, state: SplendorState) -> str:
        if room.phase == "finished" or state.phase == "finished":
            return "game_finished"
        if state.phase == "return_tokens":
            return "return_tokens"
        if state.phase == "choose_noble":
            return "choose_noble"
        if state.turn.end_triggered_by is not None:
            return "final_round"
        return "turn_idle"

    @staticmethod
    def _disabled_reason(state: SplendorState, viewer_id: str, can_submit: bool) -> str | None:
        if state.phase == "finished":
            return "本局已经结算"
        if state.turn.active_player_id != viewer_id:
            return "等待当前玩家完成回合"
        if not can_submit:
            return "当前视角不能提交操作"
        if state.phase == "return_tokens":
            return "必须先归还棋子"
        if state.phase == "choose_noble":
            return "必须先选择贵族"
        return None

    def _emit(
        self,
        state: SplendorState,
        event_type: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        state.event_counter += 1
        state.events.append(
            PublicEvent(
                seq=state.event_counter,
                type=event_type,
                message=message,
                data=data or {},
            )
        )
        if len(state.events) > EVENT_LIMIT:
            state.events = state.events[-EVENT_LIMIT:]

    @staticmethod
    def _color_name(color: str) -> str:
        labels = {
            "white": "钻石",
            "blue": "蓝宝石",
            "green": "祖母绿",
            "red": "红宝石",
            "black": "缟玛瑙",
            "gold": "黄金",
        }
        return labels[color]

    def _piece_label(self, pieces: dict[str, int]) -> str:
        parts = [
            f"{amount} 枚{self._color_name(color)}"
            for color, amount in pieces.items()
            if amount > 0
        ]
        return "、".join(parts) if parts else "0 枚棋子"

    @staticmethod
    def _player_label(state: SplendorState, player_id: str | None) -> str:
        if player_id is None:
            return "未知玩家"
        board = state.players.get(player_id)
        return board.display_name if board and board.display_name else player_id
