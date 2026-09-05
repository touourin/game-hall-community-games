from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from random import SystemRandom
from typing import Any

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError


CARD_MIN = 1
CARD_MAX = 104
HAND_SIZE = 10
ROW_COUNT = 4
ROW_LIMIT = 5
TARGET_PENALTY = 66


def bullhead_value(number: int) -> int:
    """Return the base game's penalty value for a numbered card."""
    if not CARD_MIN <= number <= CARD_MAX:
        raise ValueError("card number must be between 1 and 104")
    if number == 55:
        return 7
    if number % 11 == 0:
        return 5
    if number % 10 == 0:
        return 3
    if number % 5 == 0:
        return 2
    return 1


def bullhead_tier(points: int) -> str:
    return {
        1: "single",
        2: "double",
        3: "triple",
        5: "quintuple",
        7: "royal",
    }[points]


@dataclass(frozen=True)
class NumberCard:
    number: int

    @property
    def id(self) -> str:
        return f"card-{self.number:03d}"

    @property
    def bullheads(self) -> int:
        return bullhead_value(self.number)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "number": self.number,
            "bullheads": self.bullheads,
            "tier": bullhead_tier(self.bullheads),
        }


@dataclass(frozen=True)
class PendingPlay:
    player_id: str
    card: NumberCard


@dataclass
class BullheadKingState:
    player_ids: list[str] = field(default_factory=list)
    hands: dict[str, list[NumberCard]] = field(default_factory=dict)
    rows: list[list[NumberCard]] = field(default_factory=list)
    captured: dict[str, list[NumberCard]] = field(default_factory=dict)
    scores: dict[str, int] = field(default_factory=dict)
    round_penalties: dict[str, int] = field(default_factory=dict)
    forfeited_ids: list[str] = field(default_factory=list)
    stage: str = "setup"
    round_number: int = 0
    turn_number: int = 0
    selections: dict[str, NumberCard] = field(default_factory=dict)
    revealed: list[PendingPlay] = field(default_factory=list)
    resolution_queue: list[PendingPlay] = field(default_factory=list)
    animation_serial: int = 0
    animation: dict[str, Any] | None = None
    round_summary: dict[str, Any] | None = None
    history: list[dict[str, Any]] = field(default_factory=list)
    rankings: list[str] = field(default_factory=list)


class BullheadKingEngine:
    key = "plugin-bullhead-king"
    name = "谁是牛头王"
    min_players = 2
    max_players = 10

    def __init__(self, rng: Any | None = None) -> None:
        self.rng = rng or SystemRandom()

    def initial_state(self) -> BullheadKingState:
        return BullheadKingState()

    @staticmethod
    def can_start(room: ArcadeRoom, viewer: ArcadePlayer) -> bool:
        active = [player for player in room.players if not player.left_room]
        return 2 <= len(active) <= 10 and len(active) == len(room.players)

    def start(self, room: ArcadeRoom) -> None:
        players = sorted(
            (player for player in room.players if not player.left_room),
            key=lambda player: player.seat,
        )
        if not self.min_players <= len(players) <= self.max_players:
            raise GameRuleError("谁是牛头王需要 2–10 位玩家")
        if len(players) != len(room.players):
            raise GameRuleError("请先移除已经离开房间的玩家")

        player_ids = [player.id for player in players]
        room.state = BullheadKingState(
            player_ids=player_ids,
            scores={player_id: 0 for player_id in player_ids},
            captured={player_id: [] for player_id in player_ids},
            round_penalties={player_id: 0 for player_id in player_ids},
            history=[{
                "type": "game_start",
                "message": f"{len(player_ids)} 位玩家开始避开牛头分",
            }],
        )
        room.round_number = 1
        self._deal_round(room.state, 1)
        room.phase = "playing"

    @staticmethod
    def _member(room: ArcadeRoom, player: ArcadePlayer) -> None:
        if not any(member.id == player.id for member in room.players):
            raise GameRuleError("只有本局玩家可以操作")

    def act(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        action: str,
        payload: dict[str, Any],
    ) -> None:
        self._member(room, player)
        if room.phase != "playing":
            raise GameRuleError("当前牌局尚未开始或已经结束")
        state: BullheadKingState = room.state
        if action == "resign":
            self.manual_forfeit(room, player)
            return
        if player.id in state.forfeited_ids:
            raise GameRuleError("弃权后不能继续操作")
        if action == "select_card":
            self._select_card(room, state, player, payload)
        elif action == "take_row":
            raise GameRuleError("收牌行由系统自动判定")
        elif action == "next_round":
            self._next_round(room, state, player, payload)
        else:
            raise GameRuleError("不支持这个谁是牛头王操作")

    def _select_card(
        self,
        room: ArcadeRoom,
        state: BullheadKingState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        if state.stage != "select":
            raise GameRuleError("当前不是暗选手牌阶段")
        if player.id in state.selections:
            raise GameRuleError("本轮已经锁定过一张牌")
        if type(payload.get("turnNumber")) is not int:
            raise GameRuleError("必须提交当前轮次编号")
        if payload["turnNumber"] != state.turn_number:
            raise GameRuleError("桌面已更新，请重新选择手牌")
        card_id = payload.get("cardId")
        if not isinstance(card_id, str):
            raise GameRuleError("请选择一张有效手牌")
        hand = state.hands.get(player.id, [])
        card = next((candidate for candidate in hand if candidate.id == card_id), None)
        if card is None:
            raise GameRuleError("这张牌不在你的手牌中")

        state.hands[player.id] = [candidate for candidate in hand if candidate != card]
        state.selections[player.id] = card
        state.history.append({
            "type": "commit",
            "playerId": player.id,
            "message": f"{player.name} 已锁定第 {state.turn_number} 手",
        })
        if self._all_active_committed(state):
            self._begin_resolution(room, state)

    def _begin_resolution(
        self, room: ArcadeRoom, state: BullheadKingState,
    ) -> None:
        revealed = sorted(
            (
                PendingPlay(player_id, card)
                for player_id, card in state.selections.items()
                if player_id not in state.forfeited_ids
            ),
            key=lambda play: play.card.number,
        )
        state.selections = {}
        state.revealed = revealed
        state.resolution_queue = list(revealed)
        state.stage = "resolving"
        state.animation_serial += 1
        state.animation = {
            "id": state.animation_serial,
            "kind": "turn_resolution",
            "roundNumber": state.round_number,
            "turnNumber": state.turn_number,
            "revealed": [self._public_play(play) for play in revealed],
            "steps": [],
            "pendingChoice": None,
            "complete": False,
        }
        cards = "、".join(str(play.card.number) for play in revealed)
        state.history.append({
            "type": "reveal",
            "message": f"第 {state.turn_number} 手同时翻开：{cards}",
        })
        self._process_resolution(room, state)

    def _process_resolution(
        self, room: ArcadeRoom, state: BullheadKingState,
    ) -> None:
        self._sort_rows(state)
        while state.resolution_queue:
            play = state.resolution_queue.pop(0)
            row_index = self._target_row_index(state.rows, play.card)
            row = state.rows[row_index]
            must_replace = play.card.number < row[-1].number
            if must_replace or len(row) == ROW_LIMIT:
                taken = list(row)
                self._take_cards(state, play.player_id, taken)
                replacement = [play.card]
                state.rows[row_index] = replacement
                self._sort_rows(state)
                row_index = state.rows.index(replacement)
                kind = "take_low" if must_replace else "take_full"
                step = self._animation_step(
                    state, kind, play, row_index, taken,
                )
                if must_replace:
                    message = (
                        f"{room.player(play.player_id).name} 的 {play.card.number} "
                        f"无法接在目标行末，自动收走第 {row_index + 1} 行并重开"
                    )
                else:
                    message = (
                        f"{room.player(play.player_id).name} 用 {play.card.number} "
                        f"成为第六张，收走第 {row_index + 1} 行"
                    )
            else:
                state.rows[row_index].append(play.card)
                step = self._animation_step(
                    state, "place", play, row_index, [],
                )
                message = (
                    f"{room.player(play.player_id).name} 将 {play.card.number} "
                    f"接到第 {row_index + 1} 行"
                )
            if state.animation is not None:
                state.animation["steps"].append(step)
            state.history.append({
                "type": step["type"],
                "playerId": play.player_id,
                "rowIndex": row_index,
                "message": message,
            })

        self._complete_turn(room, state)

    def _complete_turn(
        self, room: ArcadeRoom, state: BullheadKingState,
    ) -> None:
        state.resolution_queue = []
        if state.animation is not None:
            state.animation["complete"] = True
        if all(
            not state.hands.get(player_id)
            for player_id in self._active_ids(state)
        ):
            self._complete_round(room, state)
            return
        state.turn_number += 1
        state.stage = "select"

    def _complete_round(
        self, room: ArcadeRoom, state: BullheadKingState,
    ) -> None:
        active_ids = self._active_ids(state)
        lowest = min((state.scores[player_id] for player_id in active_ids), default=0)
        state.round_summary = {
            "roundNumber": state.round_number,
            "penalties": dict(state.round_penalties),
            "totals": dict(state.scores),
            "leaderIds": [
                player_id for player_id in active_ids
                if state.scores[player_id] == lowest
            ],
            "thresholdReached": any(
                state.scores[player_id] >= TARGET_PENALTY
                for player_id in active_ids
            ),
        }
        state.history.append({
            "type": "round_end",
            "message": f"第 {state.round_number} 轮结束，牛头分已计入总分",
        })
        if len(active_ids) <= 1 or state.round_summary["thresholdReached"]:
            self._finish_game(room, state)
            return
        state.stage = "round_summary"

    def _next_round(
        self,
        room: ArcadeRoom,
        state: BullheadKingState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        if state.stage != "round_summary":
            raise GameRuleError("当前不能开始下一轮")
        if (
            type(payload.get("roundNumber")) is not int
            or payload["roundNumber"] != state.round_number
        ):
            raise GameRuleError("轮次已经更新")
        if player.id not in self._active_ids(state):
            raise GameRuleError("只有仍在牌局中的玩家可以继续")
        next_number = state.round_number + 1
        room.round_number = next_number
        self._deal_round(state, next_number)

    def _deal_round(
        self,
        state: BullheadKingState,
        round_number: int,
    ) -> None:
        active_ids = self._active_ids(state)
        deck = [NumberCard(number) for number in range(CARD_MIN, CARD_MAX + 1)]
        self.rng.shuffle(deck)
        offset = 0
        state.hands = {player_id: [] for player_id in state.player_ids}
        for player_id in active_ids:
            state.hands[player_id] = sorted(
                deck[offset:offset + HAND_SIZE], key=lambda card: card.number,
            )
            offset += HAND_SIZE
        state.rows = sorted(
            ([deck[offset + index]] for index in range(ROW_COUNT)),
            key=lambda row: row[0].number,
        )
        state.captured = {player_id: [] for player_id in state.player_ids}
        state.round_penalties = {player_id: 0 for player_id in state.player_ids}
        state.stage = "select"
        state.round_number = round_number
        state.turn_number = 1
        state.selections = {}
        state.revealed = []
        state.resolution_queue = []
        state.round_summary = None
        state.animation_serial += 1
        state.animation = {
            "id": state.animation_serial,
            "kind": "round_deal",
            "roundNumber": round_number,
            "turnNumber": 1,
            "revealed": [],
            "steps": [],
            "pendingChoice": None,
            "complete": True,
        }
        state.history.append({
            "type": "round_start",
            "message": f"第 {round_number} 轮发牌，四条数字行已经建立",
        })

    def _finish_game(
        self, room: ArcadeRoom, state: BullheadKingState,
    ) -> None:
        active_ids = self._active_ids(state)
        active_ids.sort(key=lambda player_id: (
            state.scores[player_id], state.player_ids.index(player_id),
        ))
        state.rankings = active_ids + list(reversed(state.forfeited_ids))
        if active_ids:
            best_score = state.scores[active_ids[0]]
            winner_ids = [
                player_id for player_id in active_ids
                if state.scores[player_id] == best_score
            ]
        else:
            best_score = 0
            winner_ids = []
        state.stage = "finished"
        winners = "、".join(room.player(player_id).name for player_id in winner_ids)
        threshold_note = (
            "有人达到 66 牛头分"
            if state.round_summary and state.round_summary.get("thresholdReached")
            else "其他玩家均已退出"
        )
        room.finish(
            "最低牛头分",
            winner_ids,
            f"{threshold_note}；{winners} 以 {best_score} 分获胜",
        )

    def manual_forfeit(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        self._member(room, player)
        state: BullheadKingState = room.state
        if room.phase != "playing" or player.id in state.forfeited_ids:
            return False
        state.forfeited_ids.append(player.id)
        state.selections.pop(player.id, None)
        state.history.append({
            "type": "forfeit",
            "playerId": player.id,
            "message": f"{player.name} 已退出本局",
        })
        if len(self._active_ids(state)) <= 1:
            self._finish_game(room, state)
            return True
        if state.stage == "select" and self._all_active_committed(state):
            self._begin_resolution(room, state)
        return True

    def disconnect_timeout(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        return self.manual_forfeit(room, player)

    def view(self, room: ArcadeRoom, viewer: ArcadePlayer) -> dict[str, Any]:
        state: BullheadKingState = room.state
        active_ids = self._active_ids(state)
        own_selection = state.selections.get(viewer.id)
        players = []
        for player_id in state.player_ids:
            player = room.player(player_id)
            players.append({
                "id": player_id,
                "name": player.name,
                "seat": player.seat,
                "status": (
                    "forfeited" if player_id in state.forfeited_ids else "active"
                ),
                "handCount": len(state.hands.get(player_id, [])) + (
                    1 if player_id in state.selections else 0
                ),
                "hasSelected": player_id in state.selections,
                "roundPenalty": state.round_penalties.get(player_id, 0),
                "totalPenalty": state.scores.get(player_id, 0),
                "capturedCount": len(state.captured.get(player_id, [])),
                "rank": self._rank_for(state, player_id),
            })
        actions = []
        if (
            room.phase == "playing"
            and state.stage == "select"
            and viewer.id in active_ids
            and viewer.id not in state.selections
        ):
            actions.append("select_card")
        if (
            room.phase == "playing"
            and state.stage == "round_summary"
            and viewer.id in active_ids
        ):
            actions.append("next_round")
        committed_ids = [
            player_id for player_id in state.player_ids
            if player_id in state.selections
        ]
        return {
            "schemaVersion": 1,
            "sceneId": self._scene_id(room, state, viewer.id),
            "stage": state.stage,
            "roundNumber": state.round_number,
            "turnNumber": state.turn_number,
            "rules": {
                "cardMinimum": CARD_MIN,
                "cardMaximum": CARD_MAX,
                "handSize": HAND_SIZE,
                "rowCount": ROW_COUNT,
                "rowLimit": ROW_LIMIT,
                "targetPenalty": TARGET_PENALTY,
            },
            "players": players,
            "activePlayerIds": active_ids,
            "rows": [
                [card.as_dict() for card in row] for row in state.rows
            ],
            "hand": [
                card.as_dict() for card in state.hands.get(viewer.id, [])
            ],
            "committedCard": own_selection.as_dict() if own_selection else None,
            "committedPlayerIds": committed_ids,
            "waitingForPlayerIds": [
                player_id for player_id in active_ids
                if player_id not in state.selections
            ] if state.stage == "select" else [],
            "revealed": [self._public_play(play) for play in state.revealed],
            "pendingLowCard": None,
            "rowChoices": [],
            "actions": actions,
            "animation": deepcopy(state.animation),
            "roundSummary": deepcopy(state.round_summary),
            "history": deepcopy(state.history[-16:]),
            "rankings": list(state.rankings),
            "canSelect": "select_card" in actions,
            "canChooseRow": False,
            "canStartNextRound": "next_round" in actions,
        }

    def player_result(
        self, room: ArcadeRoom, player: ArcadePlayer,
    ) -> tuple[str, str, bool]:
        state: BullheadKingState = room.state
        rank = self._rank_for(state, player.id)
        score = state.scores.get(player.id, 0)
        label = f"第 {rank} 名 · {score} 牛头分" if rank else f"{score} 牛头分"
        return label, "player", player.id in room.winner_player_ids

    def record_state(self, room: ArcadeRoom) -> dict[str, Any]:
        return asdict(room.state)

    @staticmethod
    def _active_ids(state: BullheadKingState) -> list[str]:
        return [
            player_id for player_id in state.player_ids
            if player_id not in state.forfeited_ids
        ]

    def _all_active_committed(self, state: BullheadKingState) -> bool:
        active_ids = self._active_ids(state)
        return bool(active_ids) and all(
            player_id in state.selections for player_id in active_ids
        )

    @staticmethod
    def _sort_rows(state: BullheadKingState) -> None:
        state.rows.sort(key=lambda row: row[0].number)

    @staticmethod
    def _target_row_index(
        rows: list[list[NumberCard]], card: NumberCard,
    ) -> int:
        eligible = [
            (row[0].number, index)
            for index, row in enumerate(rows)
            if row and row[0].number <= card.number
        ]
        return max(eligible)[1] if eligible else 0

    @staticmethod
    def _rank_for(state: BullheadKingState, player_id: str) -> int | None:
        if player_id not in state.rankings:
            return None
        if player_id in state.forfeited_ids:
            return state.rankings.index(player_id) + 1
        score = state.scores[player_id]
        return 1 + sum(
            state.scores[other_id] < score
            for other_id in BullheadKingEngine._active_ids(state)
        )

    @staticmethod
    def _take_cards(
        state: BullheadKingState,
        player_id: str,
        cards: list[NumberCard],
    ) -> None:
        state.captured[player_id].extend(cards)
        penalty = sum(card.bullheads for card in cards)
        state.round_penalties[player_id] += penalty
        state.scores[player_id] += penalty

    @staticmethod
    def _public_play(play: PendingPlay | None) -> dict[str, Any] | None:
        if play is None:
            return None
        return {"playerId": play.player_id, "card": play.card.as_dict()}

    @staticmethod
    def _animation_step(
        state: BullheadKingState,
        kind: str,
        play: PendingPlay,
        row_index: int,
        taken: list[NumberCard],
    ) -> dict[str, Any]:
        return {
            "id": (
                f"animation-{state.animation_serial}-"
                f"{play.card.number}-{row_index}"
            ),
            "type": kind,
            "playerId": play.player_id,
            "card": play.card.as_dict(),
            "rowIndex": row_index,
            "takenCards": [card.as_dict() for card in taken],
            "penalty": sum(card.bullheads for card in taken),
        }

    @staticmethod
    def _scene_id(
        room: ArcadeRoom, state: BullheadKingState, viewer_id: str,
    ) -> str:
        if room.phase == "finished":
            return "game.finished"
        if state.stage == "setup":
            return "setup.table"
        if state.stage == "select":
            return (
                "turn.waiting" if viewer_id in state.selections
                else "turn.select"
            )
        if state.stage == "round_summary":
            return "round.summary"
        return "turn.resolve"
