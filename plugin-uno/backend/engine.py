from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError


COLORS = ("red", "yellow", "green", "blue")
COLOR_LABELS = {
    "red": "赤红",
    "yellow": "琥珀",
    "green": "翠绿",
    "blue": "湛蓝",
}
ACTION_LABELS = {
    "skip": "跳过",
    "reverse": "反转",
    "draw_two": "+2",
    "wild": "变色",
    "wild_draw_four": "变色 +4",
}


@dataclass(frozen=True)
class Card:
    id: str
    color: str | None
    kind: str
    value: int | None = None

    @property
    def label(self) -> str:
        if self.kind == "number":
            return f"{COLOR_LABELS[self.color or 'red']} {self.value}"
        color = f"{COLOR_LABELS[self.color]} " if self.color else ""
        return f"{color}{ACTION_LABELS[self.kind]}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "color": self.color,
            "kind": self.kind,
            "value": self.value,
            "label": self.label,
        }


@dataclass
class UnoState:
    turn_order: list[str] = field(default_factory=list)
    hands: dict[str, list[Card]] = field(default_factory=dict)
    draw_pile: list[Card] = field(default_factory=list)
    discard_pile: list[Card] = field(default_factory=list)
    current_player_id: str | None = None
    direction: int = 1
    active_color: str | None = None
    stage: str = "turn"
    drawn_card_id: str | None = None
    pending_draw_total: int = 0
    pending_draw_target_id: str | None = None
    pending_draw_source_id: str | None = None
    uno_vulnerable_player_id: str | None = None
    forfeited_player_ids: list[str] = field(default_factory=list)
    event_sequence: int = 0
    latest_event: dict[str, Any] | None = None
    history: list[dict[str, Any]] = field(default_factory=list)


class UnoEngine:
    key = "plugin-uno"
    name = "UNO · 光域对决"
    min_players = 2
    max_players = 8

    def __init__(self, rng: random.Random | random.SystemRandom | None = None) -> None:
        self.rng = rng or random.SystemRandom()

    def initial_state(self) -> UnoState:
        return UnoState()

    def start(self, room: ArcadeRoom) -> None:
        players = [player for player in room.players if not player.left_room]
        if not self.min_players <= len(players) <= self.max_players:
            raise GameRuleError("UNO · 光域对决需要 2–8 位玩家")

        if room.options.get("firstPlayer") == "host":
            starter = next(
                (player for player in players if player.id == room.host_id),
                players[0],
            )
        else:
            starter = self.rng.choice(players)

        starter_index = players.index(starter)
        ordered = players[starter_index:] + players[:starter_index]
        turn_order = [player.id for player in ordered]
        hands = {player.id: [] for player in ordered}
        deck = self._new_deck()
        self.rng.shuffle(deck)

        for _ in range(7):
            for player_id in turn_order:
                hands[player_id].append(deck.pop())

        held_aside: list[Card] = []
        first_card = deck.pop()
        while first_card.kind != "number":
            held_aside.append(first_card)
            first_card = deck.pop()
        deck.extend(held_aside)
        self.rng.shuffle(deck)

        room.state = UnoState(
            turn_order=turn_order,
            hands=hands,
            draw_pile=deck,
            discard_pile=[first_card],
            current_player_id=starter.id,
            active_color=first_card.color,
            history=[{
                "type": "start",
                "message": f"{starter.name} 先手，翻开 {first_card.label}",
            }],
        )
        room.phase = "playing"
        self._emit(
            room.state,
            "start",
            player_id=starter.id,
            card=first_card,
            color=first_card.color,
            message=f"{starter.name} 先手",
        )

    def act(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        action: str,
        payload: dict[str, Any],
    ) -> None:
        if room.phase != "playing":
            raise GameRuleError("当前对局不能继续操作")
        state: UnoState = room.state
        if player.id not in state.turn_order:
            raise GameRuleError("你已不在本局的行动序列中")

        if action == "catch_uno":
            self._catch_uno(room, state, player)
            return
        if state.current_player_id != player.id:
            raise GameRuleError("还没有轮到你")

        if action == "play_card":
            self._play_card(room, state, player, payload)
        elif action == "take_penalty":
            self._take_penalty(room, state, player)
        elif action == "draw_card":
            self._draw_card(room, state, player)
        elif action == "keep_drawn":
            self._keep_drawn(room, state, player)
        else:
            raise GameRuleError("不支持这个 UNO 操作")

    def view(self, room: ArcadeRoom, viewer: ArcadePlayer) -> dict[str, Any]:
        state: UnoState = room.state
        hand = state.hands.get(viewer.id, [])
        can_act = room.phase == "playing" and state.current_player_id == viewer.id
        playable_ids: list[str] = []
        if can_act:
            candidates = hand
            if state.stage == "after_draw":
                candidates = [card for card in hand if card.id == state.drawn_card_id]
            playable_ids = [
                card.id
                for card in candidates
                if self._can_play_card(state, hand, card)
            ]

        return {
            "colors": [
                {"id": color, "label": COLOR_LABELS[color]}
                for color in COLORS
            ],
            "turnOrder": list(state.turn_order),
            "currentPlayerId": state.current_player_id,
            "direction": state.direction,
            "activeColor": state.active_color,
            "stage": state.stage,
            "topCard": (
                state.discard_pile[-1].as_dict() if state.discard_pile else None
            ),
            "hand": [card.as_dict() for card in hand],
            "cardCounts": {
                player_id: len(state.hands.get(player_id, []))
                for player_id in state.turn_order
            },
            "drawPileCount": len(state.draw_pile),
            "discardPileCount": len(state.discard_pile),
            "drawnCardId": (
                state.drawn_card_id
                if state.current_player_id == viewer.id
                else None
            ),
            "playableCardIds": playable_ids,
            "pendingDrawTotal": state.pending_draw_total,
            "pendingDrawTargetPlayerId": state.pending_draw_target_id,
            "pendingDrawSourcePlayerId": state.pending_draw_source_id,
            "canTakePenalty": (
                can_act
                and state.stage == "turn"
                and state.pending_draw_total > 0
                and state.pending_draw_target_id == viewer.id
            ),
            "canDraw": (
                can_act
                and state.stage == "turn"
                and state.pending_draw_total == 0
            ),
            "canKeepDrawn": (
                can_act
                and state.stage == "after_draw"
                and state.pending_draw_total == 0
            ),
            "canCatchUno": (
                can_act
                and state.uno_vulnerable_player_id is not None
                and state.uno_vulnerable_player_id != viewer.id
            ),
            "unoVulnerablePlayerId": state.uno_vulnerable_player_id,
            "forfeitedPlayerIds": list(state.forfeited_player_ids),
            "winnerPlayerIds": list(room.winner_player_ids),
            "latestEvent": state.latest_event,
            "history": list(state.history[-18:]),
        }

    def player_result(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
    ) -> tuple[str, str, bool]:
        won = player.id in room.winner_player_ids
        return ("光域胜者" if won else "挑战者"), "solo", won

    def record_state(self, room: ArcadeRoom) -> dict[str, Any]:
        state: UnoState = room.state
        return {
            "turnOrder": list(state.turn_order),
            "direction": state.direction,
            "activeColor": state.active_color,
            "pendingDrawTotal": state.pending_draw_total,
            "pendingDrawTargetPlayerId": state.pending_draw_target_id,
            "pendingDrawSourcePlayerId": state.pending_draw_source_id,
            "topCard": (
                state.discard_pile[-1].as_dict() if state.discard_pile else None
            ),
            "cardCounts": {
                player_id: len(state.hands.get(player_id, []))
                for player_id in state.turn_order
            },
            "forfeitedPlayerIds": list(state.forfeited_player_ids),
            "history": list(state.history),
        }

    def manual_forfeit(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        state: UnoState = room.state
        if room.phase != "playing" or player.id not in state.turn_order:
            return False

        was_current = state.current_player_id == player.id
        was_pending_target = state.pending_draw_target_id == player.id
        old_order = list(state.turn_order)
        old_index = old_order.index(player.id)
        state.draw_pile.extend(state.hands.pop(player.id, []))
        self.rng.shuffle(state.draw_pile)
        state.turn_order.remove(player.id)
        state.forfeited_player_ids.append(player.id)
        if state.uno_vulnerable_player_id == player.id:
            state.uno_vulnerable_player_id = None

        state.history.append({
            "type": "forfeit",
            "playerId": player.id,
            "message": f"{player.name} 已退出本局",
        })
        if len(state.turn_order) == 1:
            winner_id = state.turn_order[0]
            winner = room.player(winner_id)
            room.finish("completed", [winner_id], f"{winner.name} 成为最后留在牌桌的玩家")
            return True

        if was_current:
            next_index = old_index if state.direction == 1 else old_index - 1
            state.current_player_id = state.turn_order[next_index % len(state.turn_order)]
        if was_pending_target:
            state.pending_draw_target_id = state.current_player_id
        self._emit(
            state,
            "forfeit",
            player_id=player.id,
            message=f"{player.name} 退出牌桌",
        )
        return True

    def _play_card(
        self,
        room: ArcadeRoom,
        state: UnoState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        card_id = payload.get("cardId")
        if not isinstance(card_id, str):
            raise GameRuleError("请选择要打出的牌")
        call_uno = payload.get("callUno", False)
        if not isinstance(call_uno, bool):
            raise GameRuleError("UNO 宣告状态无效")

        hand = state.hands[player.id]
        card = next((held for held in hand if held.id == card_id), None)
        if card is None:
            raise GameRuleError("这张牌不在你的手牌中")
        if state.stage == "after_draw" and card.id != state.drawn_card_id:
            raise GameRuleError("摸牌后只能立即打出刚摸到的牌")
        if len(hand) == 1 and card.kind != "number":
            raise GameRuleError("最后一张必须是数字牌，功能牌或万能牌不能用于收尾")
        if not self._can_play_card(state, hand, card):
            if state.pending_draw_total > 0 and card.kind not in {
                "draw_two",
                "wild_draw_four",
            }:
                raise GameRuleError("累计摸牌尚未结算，只能继续打出 +2 / +4 或接牌")
            if card.kind == "wild_draw_four":
                raise GameRuleError("手中仍有当前颜色的牌，不能打出变色 +4")
            raise GameRuleError("这张牌与当前颜色、数字或功能均不匹配")

        chosen_color = payload.get("chosenColor")
        if card.color is None and chosen_color not in COLORS:
            raise GameRuleError("万能牌必须选择下一种颜色")
        if card.color is not None:
            chosen_color = card.color

        remaining_count = len(hand) - 1
        if call_uno and remaining_count != 1:
            raise GameRuleError("只有出牌后恰好剩 1 张时才能宣告 UNO")

        state.uno_vulnerable_player_id = None
        state.hands[player.id] = [held for held in hand if held.id != card.id]
        state.discard_pile.append(card)
        state.active_color = chosen_color
        state.stage = "turn"
        state.drawn_card_id = None

        event_type = card.kind if card.kind != "number" else "play"
        target_id: str | None = None
        contribution = 0
        stack_total = 0
        stacked = False
        advance_steps = 1

        if card.kind == "skip":
            target_id = self._advance_id(state, player.id)
            advance_steps = 2
        elif card.kind == "reverse":
            state.direction *= -1
            advance_steps = 2 if len(state.turn_order) == 2 else 1
        elif card.kind == "draw_two":
            target_id = self._advance_id(state, player.id)
            contribution = 2
            stacked = state.pending_draw_total > 0
            state.pending_draw_total += contribution
            stack_total = state.pending_draw_total
            state.pending_draw_target_id = target_id
            state.pending_draw_source_id = player.id
        elif card.kind == "wild_draw_four":
            target_id = self._advance_id(state, player.id)
            contribution = 4
            stacked = state.pending_draw_total > 0
            state.pending_draw_total += contribution
            stack_total = state.pending_draw_total
            state.pending_draw_target_id = target_id
            state.pending_draw_source_id = player.id

        if contribution:
            state.current_player_id = target_id
        else:
            state.current_player_id = self._advance_id(state, player.id, advance_steps)
        if remaining_count == 1 and not call_uno:
            state.uno_vulnerable_player_id = player.id

        message = f"{player.name} 打出 {card.label}"
        if card.color is None:
            message += f"，指定{COLOR_LABELS[chosen_color]}"
        if contribution and target_id:
            target = room.player(target_id)
            message += (
                f"；惩罚累计至 +{stack_total}，"
                f"{target.name} 可继续叠加或接牌"
            )
        if call_uno:
            message += "，并宣告 UNO"

        state.history.append({
            "type": event_type,
            "playerId": player.id,
            "targetPlayerId": target_id,
            "card": card.as_dict(),
            "color": chosen_color,
            "count": contribution,
            "stackTotal": stack_total,
            "stacked": stacked,
            "calledUno": call_uno,
            "message": message,
        })
        self._emit(
            state,
            event_type,
            player_id=player.id,
            target_player_id=target_id,
            card=card,
            color=chosen_color,
            count=contribution,
            stack_total=stack_total,
            stacked=stacked,
            called_uno=call_uno,
            message=message,
        )

        if remaining_count == 0:
            state.uno_vulnerable_player_id = None
            room.finish("completed", [player.id], f"{player.name} 率先清空手牌")

    def _take_penalty(
        self,
        room: ArcadeRoom,
        state: UnoState,
        player: ArcadePlayer,
    ) -> None:
        if (
            state.pending_draw_total <= 0
            or state.pending_draw_target_id != player.id
            or state.stage != "turn"
        ):
            raise GameRuleError("当前没有需要接下的累计惩罚")

        requested = state.pending_draw_total
        source_id = state.pending_draw_source_id
        state.uno_vulnerable_player_id = None
        drawn = self._draw_cards(state, player.id, requested)
        actual = len(drawn)
        state.pending_draw_total = 0
        state.pending_draw_target_id = None
        state.pending_draw_source_id = None
        state.drawn_card_id = None
        state.stage = "turn"
        state.current_player_id = self._advance_id(state, player.id)

        message = f"{player.name} 接下累计惩罚，摸 {actual} 张并跳过"
        state.history.append({
            "type": "take_penalty",
            "playerId": player.id,
            "targetPlayerId": player.id,
            "sourcePlayerId": source_id,
            "count": actual,
            "stackTotal": requested,
            "message": message,
        })
        self._emit(
            state,
            "take_penalty",
            player_id=player.id,
            target_player_id=player.id,
            count=actual,
            stack_total=requested,
            message=message,
        )

    def _draw_card(
        self,
        room: ArcadeRoom,
        state: UnoState,
        player: ArcadePlayer,
    ) -> None:
        if state.pending_draw_total > 0:
            raise GameRuleError("请继续叠加 +2 / +4，或接下累计惩罚")
        if state.stage != "turn":
            raise GameRuleError("你已经摸过牌，请打出该牌或选择保留")

        state.uno_vulnerable_player_id = None
        drawn = self._draw_cards(state, player.id, 1)
        if not drawn:
            raise GameRuleError("牌堆中已没有可摸的牌")
        card = drawn[0]
        hand = state.hands[player.id]
        playable = self._can_play_card(state, hand, card)

        if playable:
            state.stage = "after_draw"
            state.drawn_card_id = card.id
            message = f"{player.name} 摸 1 张牌，可选择立即打出或保留"
        else:
            state.stage = "turn"
            state.drawn_card_id = None
            state.current_player_id = self._advance_id(state, player.id)
            message = f"{player.name} 摸 1 张牌后结束回合"

        state.history.append({
            "type": "draw",
            "playerId": player.id,
            "count": 1,
            "message": message,
        })
        self._emit(
            state,
            "draw",
            player_id=player.id,
            count=1,
            message=message,
        )

    def _keep_drawn(
        self,
        room: ArcadeRoom,
        state: UnoState,
        player: ArcadePlayer,
    ) -> None:
        if state.stage != "after_draw" or state.drawn_card_id is None:
            raise GameRuleError("当前没有需要保留的摸牌")
        state.stage = "turn"
        state.drawn_card_id = None
        state.current_player_id = self._advance_id(state, player.id)
        message = f"{player.name} 保留摸到的牌并结束回合"
        state.history.append({
            "type": "pass",
            "playerId": player.id,
            "message": message,
        })
        self._emit(state, "pass", player_id=player.id, message=message)

    def _catch_uno(
        self,
        room: ArcadeRoom,
        state: UnoState,
        player: ArcadePlayer,
    ) -> None:
        target_id = state.uno_vulnerable_player_id
        if state.current_player_id != player.id:
            raise GameRuleError("只有当前行动玩家可以抓漏喊")
        if target_id is None or target_id == player.id:
            raise GameRuleError("当前没有可以抓到的漏喊 UNO")
        count = len(self._draw_cards(state, target_id, 2))
        state.uno_vulnerable_player_id = None
        target = room.player(target_id)
        message = f"{player.name} 抓到 {target.name} 漏喊 UNO；后者摸 {count} 张"
        state.history.append({
            "type": "catch_uno",
            "playerId": player.id,
            "targetPlayerId": target_id,
            "count": count,
            "message": message,
        })
        self._emit(
            state,
            "catch_uno",
            player_id=player.id,
            target_player_id=target_id,
            count=count,
            message=message,
        )

    def _can_play_card(self, state: UnoState, hand: list[Card], card: Card) -> bool:
        if len(hand) == 1 and card.kind != "number":
            return False
        if state.pending_draw_total > 0:
            if card.kind not in {"draw_two", "wild_draw_four"}:
                return False
            if card.kind != "wild_draw_four":
                return True
            return not any(
                other.id != card.id and other.color == state.active_color
                for other in hand
            )
        if not self._matches_top(state, card):
            return False
        if card.kind != "wild_draw_four":
            return True
        return not any(
            other.id != card.id and other.color == state.active_color
            for other in hand
        )

    @staticmethod
    def _matches_top(state: UnoState, card: Card) -> bool:
        if card.color is None:
            return True
        if card.color == state.active_color:
            return True
        if not state.discard_pile:
            return True
        top = state.discard_pile[-1]
        if card.kind == "number" and top.kind == "number":
            return card.value == top.value
        return card.kind == top.kind

    def _draw_cards(self, state: UnoState, player_id: str, count: int) -> list[Card]:
        drawn: list[Card] = []
        for _ in range(count):
            if not state.draw_pile:
                self._recycle_discard(state)
            if not state.draw_pile:
                break
            card = state.draw_pile.pop()
            state.hands[player_id].append(card)
            drawn.append(card)
        return drawn

    def _recycle_discard(self, state: UnoState) -> None:
        if len(state.discard_pile) <= 1:
            return
        top = state.discard_pile[-1]
        state.draw_pile = list(state.discard_pile[:-1])
        state.discard_pile = [top]
        self.rng.shuffle(state.draw_pile)

    @staticmethod
    def _advance_id(state: UnoState, player_id: str, steps: int = 1) -> str:
        index = state.turn_order.index(player_id)
        return state.turn_order[(index + state.direction * steps) % len(state.turn_order)]

    @staticmethod
    def _emit(
        state: UnoState,
        event_type: str,
        *,
        player_id: str | None = None,
        target_player_id: str | None = None,
        card: Card | None = None,
        color: str | None = None,
        count: int = 0,
        stack_total: int = 0,
        stacked: bool = False,
        called_uno: bool = False,
        message: str = "",
    ) -> None:
        state.event_sequence += 1
        state.latest_event = {
            "sequence": state.event_sequence,
            "type": event_type,
            "playerId": player_id,
            "targetPlayerId": target_player_id,
            "card": card.as_dict() if card else None,
            "color": color,
            "count": count,
            "stackTotal": stack_total,
            "stacked": stacked,
            "calledUno": called_uno,
            "message": message,
        }

    @staticmethod
    def _new_deck() -> list[Card]:
        deck: list[Card] = []
        for color in COLORS:
            deck.append(Card(f"{color}-0", color, "number", 0))
            for value in range(1, 10):
                for copy in ("a", "b"):
                    deck.append(
                        Card(f"{color}-{value}-{copy}", color, "number", value)
                    )
            for kind in ("skip", "reverse", "draw_two"):
                for copy in ("a", "b"):
                    deck.append(Card(f"{color}-{kind}-{copy}", color, kind))
        for index in range(1, 5):
            deck.append(Card(f"wild-{index}", None, "wild"))
            deck.append(
                Card(f"wild-draw-four-{index}", None, "wild_draw_four")
            )
        return deck
