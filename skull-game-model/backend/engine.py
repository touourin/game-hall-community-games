from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError


TARGET_WINS = 2
THEMES = (
    {"id": "player-1", "slug": "ember", "label": "余烬", "patternCode": "A1"},
    {"id": "player-2", "slug": "tide", "label": "潮汐", "patternCode": "B2"},
    {"id": "player-3", "slug": "moss", "label": "苔原", "patternCode": "C3"},
    {"id": "player-4", "slug": "orchid", "label": "兰影", "patternCode": "D4"},
    {"id": "player-5", "slug": "ochre", "label": "赭石", "patternCode": "E5"},
    {"id": "player-6", "slug": "slate", "label": "岩板", "patternCode": "F6"},
)


@dataclass
class Disc:
    id: str
    owner_id: str
    kind: str
    origin: str = "personal"
    face_up: bool = False


@dataclass
class SkullPlayerState:
    player_id: str
    display_name: str
    seat: int
    theme_index: int
    status: str = "active"
    challenge_wins: int = 0
    last_chance_used: bool = False
    passed_bid: bool = False
    hand: list[Disc] = field(default_factory=list)
    stack: list[Disc] = field(default_factory=list)
    removed: list[Disc] = field(default_factory=list)


@dataclass
class SkullRoundState:
    number: int
    first_player_id: str
    current_player_id: str | None = None
    pending_commits: dict[str, str] = field(default_factory=dict)
    current_bid: int = 0
    high_bidder_id: str | None = None
    passed_player_ids: list[str] = field(default_factory=list)
    challenger_id: str | None = None
    target_bid: int = 0
    revealed_disc_ids: list[str] = field(default_factory=list)
    failed_disc_id: str | None = None
    skull_owner_id: str | None = None
    penalty_mode: str | None = None
    penalty_chooser_id: str | None = None
    penalty_candidate_ids: list[str] = field(default_factory=list)
    penalty_slots: dict[str, str] = field(default_factory=dict)
    next_first_player_decision_by: str | None = None


@dataclass
class SkullState:
    phase: str = "round_setup"
    turn_order: list[str] = field(default_factory=list)
    players: dict[str, SkullPlayerState] = field(default_factory=dict)
    round: SkullRoundState | None = None
    last_chance_enabled: bool = True
    last_chance_holder_id: str | None = None
    last_chance_expires_after_round: int | None = None
    eliminated_order: list[str] = field(default_factory=list)
    public_history: list[dict[str, Any]] = field(default_factory=list)
    private_penalties: dict[str, dict[str, Any]] = field(default_factory=dict)
    result_reason: str | None = None


class SkullEngine:
    key = "plugin-skull"
    name = "骷髅牌"
    min_players = 3
    max_players = 6

    def __init__(self, rng: random.Random | random.SystemRandom | None = None) -> None:
        self.rng = rng or random.SystemRandom()

    def initial_state(self) -> SkullState:
        return SkullState()

    def start(self, room: ArcadeRoom) -> None:
        players = sorted(
            (player for player in room.players if not player.left_room),
            key=lambda player: (player.seat, player.id),
        )
        if not self.min_players <= len(players) <= self.max_players:
            raise GameRuleError("骷髅牌需要 3–6 位玩家")

        if room.options.get("firstPlayer") == "host":
            first_player = next(
                (player for player in players if player.id == room.host_id),
                players[0],
            )
        else:
            first_player = self.rng.choice(players)

        first_index = players.index(first_player)
        ordered = players[first_index:] + players[:first_index]
        player_states: dict[str, SkullPlayerState] = {}
        theme_by_player = {
            player.id: index for index, player in enumerate(players)
        }
        for player in players:
            player_states[player.id] = SkullPlayerState(
                player_id=player.id,
                display_name=player.name,
                seat=player.seat,
                theme_index=theme_by_player[player.id],
                hand=[
                    Disc(f"{player.id}-flower-{index}", player.id, "flower")
                    for index in range(1, 4)
                ] + [Disc(f"{player.id}-skull", player.id, "skull")],
            )

        state = SkullState(
            turn_order=[player.id for player in ordered],
            players=player_states,
            last_chance_enabled=room.options.get("lastChanceEnabled", True) is True,
            public_history=[{
                "type": "game_start",
                "message": f"{first_player.name} 成为首家，所有玩家开始秘密暗置",
            }],
        )
        room.state = state
        room.phase = "playing"
        self._begin_round(state, first_player.id, 1)

    def act(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        action: str,
        payload: dict[str, Any],
    ) -> None:
        if room.phase != "playing":
            raise GameRuleError("当前对局不能继续操作")
        if not isinstance(payload, dict):
            raise GameRuleError("操作参数必须是对象")
        state: SkullState = room.state
        if action == "resign":
            self._resign(room, state, player)
            return

        handlers: dict[str, Callable[..., None]] = {
            "commit_initial": self._commit_initial,
            "place_disc": self._place_disc,
            "open_bid": self._open_bid,
            "raise_bid": self._raise_bid,
            "pass_bid": self._pass_bid,
            "reveal_disc": self._reveal_disc,
            "choose_penalty": self._choose_penalty,
            "choose_self_penalty": self._choose_self_penalty,
            "choose_next_first": self._choose_next_first,
        }
        handler = handlers.get(action)
        if handler is None:
            raise GameRuleError("不支持这个骷髅牌操作")
        handler(room, state, player, payload)

    def manual_forfeit(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        state: SkullState = room.state
        if room.phase != "playing" or not self._is_active(state, player.id):
            return False
        self._resign(room, state, player)
        return True

    def view(self, room: ArcadeRoom, viewer: ArcadePlayer) -> dict[str, Any]:
        state: SkullState = room.state
        if state.round is None:
            return self._lobby_view(room, viewer, state)
        round_state = self._round(state)
        viewer_state = state.players.get(viewer.id)
        total_placed = self._total_placed(state)
        legal_reveal_owner_ids = self._legal_reveal_owner_ids(state, viewer.id)
        penalty_slots = (
            list(round_state.penalty_slots)
            if round_state.penalty_mode == "blind"
            and round_state.penalty_chooser_id == viewer.id
            else []
        )
        self_penalty_candidates: list[dict[str, Any]] = []
        if (
            round_state.penalty_mode == "self_known"
            and round_state.penalty_chooser_id == viewer.id
        ):
            challenger = state.players[round_state.challenger_id or ""]
            by_id = {
                disc.id: disc
                for disc in challenger.hand + challenger.stack
                if disc.origin == "personal"
            }
            self_penalty_candidates = [
                self._private_disc_view(by_id[disc_id])
                for disc_id in round_state.penalty_candidate_ids
                if disc_id in by_id
            ]

        can_commit = self._can_commit(state, viewer.id)
        can_act_turn = (
            self._is_active(state, viewer.id)
            and round_state.current_player_id == viewer.id
        )
        actions: list[str] = []
        if can_commit:
            actions.append("commit_initial")
        if state.phase == "placement" and can_act_turn:
            if viewer_state and viewer_state.hand:
                actions.append("place_disc")
            actions.append("open_bid")
        if state.phase == "bidding" and can_act_turn:
            if round_state.current_bid < total_placed:
                actions.append("raise_bid")
            actions.append("pass_bid")
        if state.phase == "reveal" and legal_reveal_owner_ids:
            actions.append("reveal_disc")
        if penalty_slots:
            actions.append("choose_penalty")
        if self_penalty_candidates:
            actions.append("choose_self_penalty")
        if (
            state.phase == "round_end"
            and round_state.next_first_player_decision_by == viewer.id
        ):
            actions.append("choose_next_first")

        players_view = [
            self._player_view(state, player_id, viewer.id)
            for player_id in state.turn_order
        ]
        own_hand = (
            [self._private_disc_view(disc) for disc in viewer_state.hand]
            if viewer_state
            else []
        )
        active_ids = self._active_ids(state)
        scene_id = self._scene_id(state)
        winner_ids = list(room.winner_player_ids)
        return {
            "schemaVersion": 1,
            "gameKey": "skull",
            "sceneId": scene_id,
            "phase": "finished" if room.phase == "finished" else state.phase,
            "rules": {
                "targetWins": TARGET_WINS,
                "lastChanceEnabled": state.last_chance_enabled,
            },
            "players": players_view,
            "activePlayerIds": active_ids,
            "hand": own_hand,
            "round": {
                "number": round_state.number,
                "firstPlayerId": round_state.first_player_id,
                "currentPlayerId": round_state.current_player_id,
                "committedCount": len(round_state.pending_commits),
                "activePlayerCount": len(active_ids),
                "hasCommitted": viewer.id in round_state.pending_commits,
                "firstPlayerCommitsLast": True,
                "totalPlaced": total_placed,
                "currentBid": round_state.current_bid,
                "highBidderId": round_state.high_bidder_id,
                "passedPlayerIds": list(round_state.passed_player_ids),
                "challengerId": round_state.challenger_id,
                "targetBid": round_state.target_bid,
                "revealedCount": len(round_state.revealed_disc_ids),
                "failed": round_state.failed_disc_id is not None,
                "skullOwnerId": (
                    round_state.skull_owner_id
                    if round_state.failed_disc_id is not None
                    else None
                ),
                "lastChanceHolderId": state.last_chance_holder_id,
                "lastChanceExpiresAfterRound": state.last_chance_expires_after_round,
                "penaltyMode": round_state.penalty_mode,
                "penaltyChooserId": round_state.penalty_chooser_id,
                "penaltySlots": penalty_slots,
                "selfPenaltyCandidates": self_penalty_candidates,
                "nextFirstPlayerDecisionBy": round_state.next_first_player_decision_by,
                "eligibleNextFirstPlayerIds": (
                    active_ids
                    if round_state.next_first_player_decision_by == viewer.id
                    else []
                ),
            },
            "actions": actions,
            "legalRevealOwnerIds": legal_reveal_owner_ids,
            "minimumBid": (
                round_state.current_bid + 1
                if state.phase == "bidding"
                else 1
            ),
            "maximumBid": total_placed,
            "lastPrivatePenalty": state.private_penalties.get(viewer.id),
            "history": list(state.public_history[-18:]),
            "stats": {
                "roundsPlayed": round_state.number,
                "activePlayers": len(active_ids),
                "eliminatedPlayers": len(state.eliminated_order),
                "challengeWins": {
                    player_id: state.players[player_id].challenge_wins
                    for player_id in state.turn_order
                },
            },
            "result": (
                {
                    "winnerIds": winner_ids,
                    "reason": state.result_reason,
                    "summary": room.win_reason,
                    "statsEligible": room.stats_eligible,
                }
                if room.phase == "finished"
                else None
            ),
        }

    def _lobby_view(
        self,
        room: ArcadeRoom,
        viewer: ArcadePlayer,
        state: SkullState,
    ) -> dict[str, Any]:
        seated = sorted(
            (player for player in room.players if not player.left_room),
            key=lambda player: (player.seat, player.id),
        )
        players = []
        for index, player in enumerate(seated):
            players.append({
                "id": player.id,
                "displayName": player.name,
                "seat": player.seat,
                "status": "active",
                "challengeWins": 0,
                "matSide": "blank",
                "lastChanceUsed": False,
                "passedBid": False,
                "handCount": 4,
                "stack": [],
                "removedCount": 0,
                "removed": [],
                "personalDiscCount": 4,
                "theme": dict(THEMES[index % len(THEMES)]),
            })
        active_ids = [player.id for player in seated]
        return {
            "schemaVersion": 1,
            "gameKey": "skull",
            "sceneId": "setup.table",
            "phase": "lobby",
            "rules": {
                "targetWins": TARGET_WINS,
                "lastChanceEnabled": room.options.get("lastChanceEnabled", True) is True,
            },
            "players": players,
            "activePlayerIds": active_ids,
            "hand": [],
            "round": {
                "number": 0,
                "firstPlayerId": "",
                "currentPlayerId": None,
                "committedCount": 0,
                "activePlayerCount": len(active_ids),
                "hasCommitted": False,
                "firstPlayerCommitsLast": True,
                "totalPlaced": 0,
                "currentBid": 0,
                "highBidderId": None,
                "passedPlayerIds": [],
                "challengerId": None,
                "targetBid": 0,
                "revealedCount": 0,
                "failed": False,
                "skullOwnerId": None,
                "lastChanceHolderId": None,
                "lastChanceExpiresAfterRound": None,
                "penaltyMode": None,
                "penaltyChooserId": None,
                "penaltySlots": [],
                "selfPenaltyCandidates": [],
                "nextFirstPlayerDecisionBy": None,
                "eligibleNextFirstPlayerIds": [],
            },
            "actions": [],
            "legalRevealOwnerIds": [],
            "minimumBid": 1,
            "maximumBid": 0,
            "lastPrivatePenalty": None,
            "history": list(state.public_history),
            "stats": {
                "roundsPlayed": 0,
                "activePlayers": len(active_ids),
                "eliminatedPlayers": 0,
                "challengeWins": {player_id: 0 for player_id in active_ids},
            },
            "result": None,
        }

    def player_result(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
    ) -> tuple[str, str, bool]:
        state: SkullState = room.state
        player_state = state.players[player.id]
        if player.id in room.winner_player_ids:
            role = "胜者"
        elif player_state.status == "eliminated":
            role = f"淘汰 · {player_state.challenge_wins} 次挑战"
        else:
            role = f"{player_state.challenge_wins} 次挑战"
        return role, "individual", player.id in room.winner_player_ids

    def record_state(self, room: ArcadeRoom) -> dict[str, Any]:
        state: SkullState = room.state
        round_state = self._round(state)
        return {
            "schemaVersion": 1,
            "rules": {
                "targetWins": TARGET_WINS,
                "lastChanceEnabled": state.last_chance_enabled,
            },
            "roundsPlayed": round_state.number,
            "firstPlayerId": state.turn_order[0] if state.turn_order else None,
            "players": [
                {
                    "playerId": player_id,
                    "themeId": THEMES[state.players[player_id].theme_index]["id"],
                    "challengeWins": state.players[player_id].challenge_wins,
                    "status": state.players[player_id].status,
                    "removedCount": len(state.players[player_id].removed),
                }
                for player_id in state.turn_order
            ],
            "eliminatedOrder": list(state.eliminated_order),
            "winnerPlayerIds": list(room.winner_player_ids),
            "resultReason": state.result_reason,
            "history": list(state.public_history),
        }

    def _commit_initial(
        self,
        _room: ArcadeRoom,
        state: SkullState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        if state.phase != "round_setup" or not self._is_active(state, player.id):
            raise GameRuleError("当前不能秘密暗置")
        round_state = self._round(state)
        if player.id in round_state.pending_commits:
            raise GameRuleError("你已经锁定了本轮暗置")
        active_ids = self._active_ids(state)
        if (
            player.id == round_state.first_player_id
            and len(round_state.pending_commits) < len(active_ids) - 1
        ):
            raise GameRuleError("首家需等待其他玩家锁定后再暗置")
        disc = self._disc_from_hand(state, player.id, payload.get("discId"))
        round_state.pending_commits[player.id] = disc.id
        if len(round_state.pending_commits) == len(active_ids):
            for player_id in active_ids:
                committed_id = round_state.pending_commits[player_id]
                committed = self._take_from_hand(state.players[player_id], committed_id)
                state.players[player_id].stack.append(committed)
            round_state.pending_commits.clear()
            state.phase = "placement"
            round_state.current_player_id = round_state.first_player_id
            state.public_history.append({
                "type": "commit_complete",
                "round": round_state.number,
                "message": "所有玩家已同时完成暗置，首家开始行动",
            })

    def _place_disc(
        self,
        _room: ArcadeRoom,
        state: SkullState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_turn(state, player.id, "placement", "还没有轮到你叠牌")
        disc = self._disc_from_hand(state, player.id, payload.get("discId"))
        placed = self._take_from_hand(state.players[player.id], disc.id)
        state.players[player.id].stack.append(placed)
        self._round(state).current_player_id = self._next_active_id(state, player.id)
        state.public_history.append({
            "type": "place",
            "playerId": player.id,
            "message": f"{player.name} 又叠放了 1 枚暗牌",
        })

    def _open_bid(
        self,
        room: ArcadeRoom,
        state: SkullState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_turn(state, player.id, "placement", "还没有轮到你开叫")
        count = self._validated_bid(payload.get("count"), 0, self._total_placed(state))
        round_state = self._round(state)
        state.phase = "bidding"
        round_state.current_bid = count
        round_state.high_bidder_id = player.id
        self._reset_bid_passes(state)
        round_state.current_player_id = self._next_bid_actor(state, player.id)
        state.public_history.append({
            "type": "open_bid",
            "playerId": player.id,
            "count": count,
            "message": f"{player.name} 开叫 {count} 枚",
        })
        if count == self._total_placed(state):
            self._begin_challenge(room, state)

    def _raise_bid(
        self,
        room: ArcadeRoom,
        state: SkullState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_turn(state, player.id, "bidding", "还没有轮到你加价")
        round_state = self._round(state)
        count = self._validated_bid(
            payload.get("count"),
            round_state.current_bid,
            self._total_placed(state),
        )
        round_state.current_bid = count
        round_state.high_bidder_id = player.id
        # 暂不跟价只针对上一口最高叫价。出现新叫价后，所有仍在场的
        # 玩家（包括此前暂不跟价者）都必须重新获得回应机会。
        self._reset_bid_passes(state)
        round_state.current_player_id = self._next_bid_actor(state, player.id)
        state.public_history.append({
            "type": "raise_bid",
            "playerId": player.id,
            "count": count,
            "message": f"{player.name} 将叫价提高到 {count} 枚",
        })
        if count == self._total_placed(state):
            self._begin_challenge(room, state)

    def _pass_bid(
        self,
        room: ArcadeRoom,
        state: SkullState,
        player: ArcadePlayer,
        _payload: dict[str, Any],
    ) -> None:
        self._require_turn(state, player.id, "bidding", "还没有轮到你回应当前叫价")
        round_state = self._round(state)
        if player.id == round_state.high_bidder_id:
            raise GameRuleError("当前最高叫价者无需回应自己的叫价")
        if player.id in round_state.passed_player_ids:
            raise GameRuleError("你已经暂不跟进当前叫价")
        round_state.passed_player_ids.append(player.id)
        state.players[player.id].passed_bid = True
        state.public_history.append({
            "type": "pass_bid",
            "playerId": player.id,
            "count": round_state.current_bid,
            "message": f"{player.name} 暂不跟进 {round_state.current_bid} 枚的叫价",
        })
        if not self._waiting_bid_actor_ids(state):
            self._begin_challenge(room, state)
        else:
            round_state.current_player_id = self._next_bid_actor(state, player.id)

    def _reveal_disc(
        self,
        room: ArcadeRoom,
        state: SkullState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        round_state = self._round(state)
        if (
            state.phase != "reveal"
            or round_state.challenger_id != player.id
            or round_state.current_player_id != player.id
        ):
            raise GameRuleError("只有当前挑战者可以翻牌")
        owner_id = payload.get("ownerId")
        if not isinstance(owner_id, str) or owner_id not in state.players:
            raise GameRuleError("请选择一个合法玩家牌堆")
        legal_owner_ids = self._legal_reveal_owner_ids(state, player.id)
        if owner_id not in legal_owner_ids:
            if player.id in legal_owner_ids:
                raise GameRuleError("必须先翻完自己需要翻开的牌")
            raise GameRuleError("这个牌堆当前不能翻开")
        disc = self._top_hidden_disc(state.players[owner_id].stack)
        if disc is None:
            raise GameRuleError("这个牌堆已经没有暗牌")
        disc.face_up = True
        round_state.revealed_disc_ids.append(disc.id)
        state.public_history.append({
            "type": "reveal",
            "playerId": player.id,
            "ownerId": owner_id,
            "kind": disc.kind,
            "message": (
                f"{player.name} 翻开一枚骷髅"
                if disc.kind == "skull"
                else f"{player.name} 翻开一枚花牌"
            ),
        })
        if disc.kind == "skull":
            self._prepare_penalty(room, state, disc)
        elif len(round_state.revealed_disc_ids) >= round_state.target_bid:
            self._complete_success(room, state, player)

    def _choose_penalty(
        self,
        room: ArcadeRoom,
        state: SkullState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        round_state = self._round(state)
        if (
            state.phase != "penalty"
            or round_state.penalty_mode != "blind"
            or round_state.penalty_chooser_id != player.id
        ):
            raise GameRuleError("当前不由你盲选处罚牌")
        slot_id = payload.get("slotId")
        if not isinstance(slot_id, str) or slot_id not in round_state.penalty_slots:
            raise GameRuleError("请选择一个有效的不透明槽位")
        disc_id = round_state.penalty_slots[slot_id]
        challenger_id = round_state.challenger_id or ""
        removed = self._remove_personal_disc(state.players[challenger_id], disc_id)
        self._finish_penalty(room, state, removed)

    def _choose_self_penalty(
        self,
        room: ArcadeRoom,
        state: SkullState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        round_state = self._round(state)
        if (
            state.phase != "penalty"
            or round_state.penalty_mode != "self_known"
            or round_state.penalty_chooser_id != player.id
        ):
            raise GameRuleError("当前不能秘密选择自己的处罚牌")
        disc_id = payload.get("discId")
        if (
            not isinstance(disc_id, str)
            or disc_id not in round_state.penalty_candidate_ids
        ):
            raise GameRuleError("只能选择自己仍持有的一枚个人牌")
        removed = self._remove_personal_disc(state.players[player.id], disc_id)
        self._finish_penalty(room, state, removed)

    def _choose_next_first(
        self,
        _room: ArcadeRoom,
        state: SkullState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        round_state = self._round(state)
        if (
            state.phase != "round_end"
            or round_state.next_first_player_decision_by != player.id
        ):
            raise GameRuleError("当前不需要你指定下一轮首家")
        next_id = payload.get("playerId")
        if not isinstance(next_id, str) or next_id not in self._active_ids(state):
            raise GameRuleError("请选择一名仍在场的玩家")
        next_round = round_state.number + 1
        state.public_history.append({
            "type": "next_first",
            "playerId": next_id,
            "message": f"{state.players[next_id].display_name} 被指定为下一轮首家",
        })
        self._begin_round(state, next_id, next_round)

    def _prepare_penalty(
        self,
        room: ArcadeRoom,
        state: SkullState,
        skull: Disc,
    ) -> None:
        round_state = self._round(state)
        challenger_id = round_state.challenger_id or ""
        challenger = state.players[challenger_id]
        round_state.failed_disc_id = skull.id
        round_state.skull_owner_id = skull.owner_id
        state.phase = "penalty"

        if (
            state.last_chance_enabled
            and state.last_chance_holder_id == challenger_id
            and state.last_chance_expires_after_round == round_state.number
        ):
            personal = self._remaining_personal_discs(challenger)
            if personal:
                removed = self._remove_personal_disc(challenger, personal[0].id)
                state.private_penalties[challenger_id] = {
                    "kind": removed.kind,
                    "message": "最后机会失败：你的最后一枚个人牌已被移除",
                }
            self._eliminate(state, challenger_id)
            state.public_history.append({
                "type": "last_chance_elimination",
                "playerId": challenger_id,
                "message": f"{challenger.display_name} 在最后机会轮挑战失败并被淘汰",
            })
            self._after_failed_challenge(room, state, award_last_chance=False)
            return

        candidates = [disc.id for disc in self._remaining_personal_discs(challenger)]
        round_state.penalty_candidate_ids = candidates
        if skull.owner_id == challenger_id:
            round_state.penalty_mode = "self_known"
            round_state.penalty_chooser_id = challenger_id
            round_state.current_player_id = challenger_id
            state.public_history.append({
                "type": "penalty_pending",
                "mode": "self_known",
                "playerId": challenger_id,
                "message": f"{challenger.display_name} 翻到自己的骷髅，需秘密弃掉一枚牌",
            })
            return

        shuffled = list(candidates)
        self.rng.shuffle(shuffled)
        round_state.penalty_mode = "blind"
        round_state.penalty_chooser_id = skull.owner_id
        round_state.current_player_id = skull.owner_id
        round_state.penalty_slots = {
            f"opaque-{round_state.number}-{index + 1}": disc_id
            for index, disc_id in enumerate(shuffled)
        }
        state.public_history.append({
            "type": "penalty_pending",
            "mode": "blind",
            "playerId": challenger_id,
            "chooserId": skull.owner_id,
            "message": (
                f"{state.players[skull.owner_id].display_name} 将盲选 "
                f"{challenger.display_name} 的一枚牌"
            ),
        })

    def _finish_penalty(
        self,
        room: ArcadeRoom,
        state: SkullState,
        removed: Disc,
    ) -> None:
        round_state = self._round(state)
        challenger_id = round_state.challenger_id or ""
        challenger = state.players[challenger_id]
        state.private_penalties[challenger_id] = {
            "kind": removed.kind,
            "message": (
                "你失去了一枚花牌"
                if removed.kind == "flower"
                else "你失去了自己的骷髅牌"
            ),
        }
        state.public_history.append({
            "type": "penalty_complete",
            "playerId": challenger_id,
            "message": f"{challenger.display_name} 永久失去 1 枚秘密牌",
        })
        if not self._remaining_personal_discs(challenger):
            self._eliminate(state, challenger_id)
            state.public_history.append({
                "type": "eliminated",
                "playerId": challenger_id,
                "message": f"{challenger.display_name} 已无个人牌，被淘汰出局",
            })
        award = (
            challenger.status == "active"
            and len(self._remaining_personal_discs(challenger)) == 1
            and state.last_chance_enabled
            and not challenger.last_chance_used
        )
        self._after_failed_challenge(room, state, award_last_chance=award)

    def _after_failed_challenge(
        self,
        room: ArcadeRoom,
        state: SkullState,
        *,
        award_last_chance: bool,
    ) -> None:
        round_state = self._round(state)
        challenger_id = round_state.challenger_id or ""
        skull_owner_id = round_state.skull_owner_id
        if self._finish_if_one_remaining(room, state):
            return

        grant_to = challenger_id if award_last_chance else None
        if self._is_active(state, challenger_id):
            self._settle_and_begin_next(state, challenger_id, grant_to)
            return
        if skull_owner_id and skull_owner_id != challenger_id and self._is_active(
            state, skull_owner_id
        ):
            self._settle_and_begin_next(state, skull_owner_id, grant_to)
            return

        current_round = round_state.number
        self._collect_round_discs(state)
        state.phase = "round_end"
        round_state.current_player_id = challenger_id
        round_state.next_first_player_decision_by = challenger_id
        round_state.penalty_mode = None
        round_state.penalty_chooser_id = None
        round_state.penalty_candidate_ids.clear()
        round_state.penalty_slots.clear()
        state.public_history.append({
            "type": "choose_next_first",
            "playerId": challenger_id,
            "round": current_round,
            "message": "被淘汰的挑战者需指定下一轮首家",
        })

    def _complete_success(
        self,
        room: ArcadeRoom,
        state: SkullState,
        challenger: ArcadePlayer,
    ) -> None:
        player_state = state.players[challenger.id]
        player_state.challenge_wins += 1
        state.public_history.append({
            "type": "challenge_success",
            "playerId": challenger.id,
            "wins": player_state.challenge_wins,
            "message": (
                f"{challenger.name} 完成挑战，累计 "
                f"{player_state.challenge_wins}/{TARGET_WINS} 次成功"
            ),
        })
        if player_state.challenge_wins >= TARGET_WINS:
            state.phase = "finished"
            state.result_reason = "two_challenges"
            room.finish(
                "skull",
                [challenger.id],
                f"{challenger.name} 率先完成两次无骷髅挑战",
            )
            return
        self._settle_and_begin_next(state, challenger.id, None)

    def _begin_challenge(self, _room: ArcadeRoom, state: SkullState) -> None:
        round_state = self._round(state)
        challenger_id = round_state.high_bidder_id
        if challenger_id is None or not self._is_active(state, challenger_id):
            raise GameRuleError("当前竞标没有合法最高叫价者")
        state.phase = "reveal"
        round_state.challenger_id = challenger_id
        round_state.target_bid = round_state.current_bid
        round_state.current_player_id = challenger_id
        state.public_history.append({
            "type": "challenge_start",
            "playerId": challenger_id,
            "count": round_state.target_bid,
            "message": (
                f"{state.players[challenger_id].display_name} 成为挑战者，"
                f"需要翻开 {round_state.target_bid} 枚花牌"
            ),
        })

    def _settle_and_begin_next(
        self,
        state: SkullState,
        next_first_id: str,
        grant_last_chance_to: str | None,
    ) -> None:
        next_round = self._round(state).number + 1
        self._collect_round_discs(state)
        if grant_last_chance_to is not None:
            self._grant_last_chance(state, grant_last_chance_to, next_round)
        self._begin_round(state, next_first_id, next_round)

    def _begin_round(
        self,
        state: SkullState,
        first_player_id: str,
        round_number: int,
    ) -> None:
        if not self._is_active(state, first_player_id):
            raise GameRuleError("下一轮首家必须仍在场")
        for player_state in state.players.values():
            player_state.passed_bid = False
            for disc in player_state.hand + player_state.stack:
                disc.face_up = False
        state.phase = "round_setup"
        state.round = SkullRoundState(
            number=round_number,
            first_player_id=first_player_id,
        )
        state.public_history.append({
            "type": "round_start",
            "round": round_number,
            "playerId": first_player_id,
            "message": (
                f"第 {round_number} 轮开始，"
                f"{state.players[first_player_id].display_name} 为首家"
            ),
        })

    def _collect_round_discs(self, state: SkullState) -> None:
        current_round = self._round(state).number
        for player_state in state.players.values():
            retained: list[Disc] = []
            for disc in player_state.hand + player_state.stack:
                disc.face_up = False
                if disc.origin == "personal" and player_state.status == "active":
                    retained.append(disc)
            player_state.hand = retained
            player_state.stack = []
            player_state.passed_bid = False
        if (
            state.last_chance_expires_after_round is not None
            and state.last_chance_expires_after_round <= current_round
        ):
            state.last_chance_holder_id = None
            state.last_chance_expires_after_round = None

    def _grant_last_chance(
        self,
        state: SkullState,
        player_id: str,
        expires_after_round: int,
    ) -> None:
        player_state = state.players[player_id]
        if player_state.status != "active" or player_state.last_chance_used:
            return
        player_state.last_chance_used = True
        player_state.hand.append(Disc(
            id=f"{player_id}-last-chance-{expires_after_round}",
            owner_id=player_id,
            kind="last_chance_flower",
            origin="last_chance",
        ))
        state.last_chance_holder_id = player_id
        state.last_chance_expires_after_round = expires_after_round
        state.public_history.append({
            "type": "last_chance_granted",
            "playerId": player_id,
            "round": expires_after_round,
            "message": (
                f"{player_state.display_name} 在下一轮获得一枚公开的最后机会花牌"
            ),
        })

    def _resign(
        self,
        room: ArcadeRoom,
        state: SkullState,
        player: ArcadePlayer,
    ) -> None:
        if not self._is_active(state, player.id):
            return
        round_state = self._round(state)
        phase = state.phase
        was_current = round_state.current_player_id == player.id
        was_high_bidder = round_state.high_bidder_id == player.id
        was_challenger = round_state.challenger_id == player.id
        was_penalty_chooser = round_state.penalty_chooser_id == player.id
        fallback = self._next_active_id(state, player.id)
        round_state.pending_commits.pop(player.id, None)
        self._eliminate(state, player.id, remove_all=True)
        state.public_history.append({
            "type": "resign",
            "playerId": player.id,
            "message": f"{player.name} 认输退出本局",
        })
        if self._finish_if_one_remaining(room, state):
            return
        active_ids = self._active_ids(state)
        fallback = fallback if fallback in active_ids else active_ids[0]

        if phase == "round_setup":
            if round_state.first_player_id == player.id:
                round_state.first_player_id = fallback
            if len(round_state.pending_commits) == len(active_ids):
                for player_id in active_ids:
                    disc_id = round_state.pending_commits[player_id]
                    state.players[player_id].stack.append(
                        self._take_from_hand(state.players[player_id], disc_id)
                    )
                round_state.pending_commits.clear()
                state.phase = "placement"
                round_state.current_player_id = round_state.first_player_id
            return

        if phase == "penalty" and was_penalty_chooser and not was_challenger:
            candidates = list(round_state.penalty_slots.values())
            if candidates:
                removed = self._remove_personal_disc(
                    state.players[round_state.challenger_id or ""],
                    self.rng.choice(candidates),
                )
                self._finish_penalty(room, state, removed)
                return

        if phase in {"reveal", "penalty", "round_end"} or was_high_bidder or was_challenger:
            self._collect_round_discs(state)
            self._begin_round(state, fallback, round_state.number + 1)
            return

        if phase == "placement":
            if was_current:
                round_state.current_player_id = fallback
            return

        if phase == "bidding":
            round_state.passed_player_ids = [
                player_id for player_id in round_state.passed_player_ids
                if player_id in active_ids
            ]
            state.players[player.id].passed_bid = False
            if not self._waiting_bid_actor_ids(state):
                self._begin_challenge(room, state)
            elif was_current:
                round_state.current_player_id = self._next_bid_actor(state, player.id)

    def _finish_if_one_remaining(self, room: ArcadeRoom, state: SkullState) -> bool:
        active_ids = self._active_ids(state)
        if len(active_ids) != 1:
            return False
        winner_id = active_ids[0]
        state.phase = "finished"
        state.result_reason = "last_player_remaining"
        room.finish(
            "skull",
            [winner_id],
            f"{state.players[winner_id].display_name} 成为最后仍持有个人牌的玩家",
        )
        return True

    def _eliminate(
        self,
        state: SkullState,
        player_id: str,
        *,
        remove_all: bool = False,
    ) -> None:
        player_state = state.players[player_id]
        if player_state.status == "eliminated":
            return
        if remove_all:
            for disc in list(player_state.hand + player_state.stack):
                if disc.origin == "personal":
                    disc.face_up = False
                    player_state.removed.append(disc)
            player_state.hand.clear()
            player_state.stack.clear()
        player_state.status = "eliminated"
        if player_id not in state.eliminated_order:
            state.eliminated_order.append(player_id)
        if state.last_chance_holder_id == player_id:
            state.last_chance_holder_id = None
            state.last_chance_expires_after_round = None

    def _player_view(
        self,
        state: SkullState,
        player_id: str,
        viewer_id: str,
    ) -> dict[str, Any]:
        player_state = state.players[player_id]
        theme = THEMES[player_state.theme_index]
        stack_view = [
            self._project_stack_disc(disc, player_id, viewer_id, index)
            for index, disc in enumerate(player_state.stack)
        ]
        removed_view = (
            [self._private_disc_view(disc) for disc in player_state.removed]
            if player_id == viewer_id
            else []
        )
        return {
            "id": player_id,
            "displayName": player_state.display_name,
            "seat": player_state.seat,
            "status": player_state.status,
            "challengeWins": player_state.challenge_wins,
            "matSide": "flower" if player_state.challenge_wins >= 1 else "blank",
            "lastChanceUsed": player_state.last_chance_used,
            "passedBid": player_state.passed_bid,
            "handCount": len(player_state.hand),
            "stack": stack_view,
            "removedCount": len(player_state.removed),
            "removed": removed_view,
            "personalDiscCount": len(self._remaining_personal_discs(player_state)),
            "theme": dict(theme),
        }

    @staticmethod
    def _private_disc_view(disc: Disc) -> dict[str, Any]:
        return {
            "id": disc.id,
            "kind": disc.kind,
            "origin": disc.origin,
            "faceUp": disc.face_up,
            "knowledge": "self" if disc.origin == "personal" else "public",
        }

    @staticmethod
    def _project_stack_disc(
        disc: Disc,
        owner_id: str,
        viewer_id: str,
        index: int,
    ) -> dict[str, Any]:
        if disc.face_up:
            kind = disc.kind
            knowledge = "public"
        elif disc.origin == "last_chance":
            kind = "last_chance_flower"
            knowledge = "public"
        elif owner_id == viewer_id:
            kind = disc.kind
            knowledge = "self"
        else:
            kind = "unknown"
            knowledge = "hidden"
        return {
            "id": disc.id if owner_id == viewer_id else f"opaque-{owner_id}-stack-{index}",
            "kind": kind,
            "origin": disc.origin,
            "faceUp": disc.face_up,
            "knowledge": knowledge,
        }

    def _legal_reveal_owner_ids(self, state: SkullState, viewer_id: str) -> list[str]:
        if state.phase != "reveal":
            return []
        round_state = self._round(state)
        if round_state.challenger_id != viewer_id:
            return []
        own = state.players[viewer_id]
        if self._top_hidden_disc(own.stack) is not None:
            return [viewer_id]
        return [
            player_id for player_id in self._active_ids(state)
            if player_id != viewer_id
            and self._top_hidden_disc(state.players[player_id].stack) is not None
        ]

    def _can_commit(self, state: SkullState, player_id: str) -> bool:
        if state.phase != "round_setup" or not self._is_active(state, player_id):
            return False
        round_state = self._round(state)
        if player_id in round_state.pending_commits:
            return False
        if player_id != round_state.first_player_id:
            return True
        return len(round_state.pending_commits) == len(self._active_ids(state)) - 1

    def _scene_id(self, state: SkullState) -> str:
        if state.phase == "round_setup":
            return "round.commit"
        if state.phase == "placement":
            return "round.place-or-bid"
        if state.phase == "bidding":
            return "bid.raise-or-pass"
        if state.phase == "reveal":
            challenger_id = self._round(state).challenger_id
            if challenger_id and self._top_hidden_disc(
                state.players[challenger_id].stack
            ) is not None:
                return "challenge.reveal-own"
            return "challenge.reveal-others"
        if state.phase == "penalty":
            return (
                "penalty.blind-pick"
                if self._round(state).penalty_mode == "blind"
                else "penalty.self-pick"
            )
        if state.phase == "round_end":
            return "round.summary"
        return "game.finished"

    def _require_turn(
        self,
        state: SkullState,
        player_id: str,
        phase: str,
        message: str,
    ) -> None:
        if (
            state.phase != phase
            or not self._is_active(state, player_id)
            or self._round(state).current_player_id != player_id
        ):
            raise GameRuleError(message)

    @staticmethod
    def _validated_bid(value: Any, current: int, maximum: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise GameRuleError("叫价必须是整数")
        if value <= current:
            raise GameRuleError("新叫价必须严格高于当前叫价")
        if value < 1 or value > maximum:
            raise GameRuleError(f"叫价必须介于 1 与 {maximum} 之间")
        return value

    def _disc_from_hand(
        self,
        state: SkullState,
        player_id: str,
        disc_id: Any,
    ) -> Disc:
        if not isinstance(disc_id, str) or not disc_id:
            raise GameRuleError("请选择自己手中的一枚牌")
        disc = next(
            (item for item in state.players[player_id].hand if item.id == disc_id),
            None,
        )
        if disc is not None:
            return disc
        raise GameRuleError("选择的牌不在你的手中")

    @staticmethod
    def _take_from_hand(player_state: SkullPlayerState, disc_id: str) -> Disc:
        for index, disc in enumerate(player_state.hand):
            if disc.id == disc_id:
                return player_state.hand.pop(index)
        raise GameRuleError("选择的牌不在你的手中")

    @staticmethod
    def _remove_personal_disc(
        player_state: SkullPlayerState,
        disc_id: str,
    ) -> Disc:
        for zone in (player_state.hand, player_state.stack):
            for index, disc in enumerate(zone):
                if disc.id == disc_id and disc.origin == "personal":
                    removed = zone.pop(index)
                    removed.face_up = False
                    player_state.removed.append(removed)
                    return removed
        raise GameRuleError("处罚牌已经不在玩家持有区")

    @staticmethod
    def _remaining_personal_discs(player_state: SkullPlayerState) -> list[Disc]:
        return [
            disc for disc in player_state.hand + player_state.stack
            if disc.origin == "personal"
        ]

    @staticmethod
    def _top_hidden_disc(stack: Iterable[Disc]) -> Disc | None:
        items = list(stack)
        return next((disc for disc in reversed(items) if not disc.face_up), None)

    @staticmethod
    def _round(state: SkullState) -> SkullRoundState:
        if state.round is None:
            raise RuntimeError("骷髅牌回合尚未初始化")
        return state.round

    @staticmethod
    def _total_placed(state: SkullState) -> int:
        return sum(len(player.stack) for player in state.players.values())

    @staticmethod
    def _active_ids(state: SkullState) -> list[str]:
        return [
            player_id for player_id in state.turn_order
            if state.players[player_id].status == "active"
        ]

    @classmethod
    def _is_active(cls, state: SkullState, player_id: str) -> bool:
        return player_id in cls._active_ids(state)

    @classmethod
    def _next_active_id(cls, state: SkullState, after_player_id: str) -> str:
        if after_player_id not in state.turn_order:
            active = cls._active_ids(state)
            if not active:
                raise GameRuleError("当前没有仍在场的玩家")
            return active[0]
        start = state.turn_order.index(after_player_id)
        for offset in range(1, len(state.turn_order) + 1):
            candidate = state.turn_order[(start + offset) % len(state.turn_order)]
            if cls._is_active(state, candidate):
                return candidate
        raise GameRuleError("当前没有仍在场的玩家")

    @classmethod
    def _next_bid_actor(cls, state: SkullState, after_player_id: str) -> str | None:
        round_state = cls._round(state)
        start = state.turn_order.index(after_player_id)
        for offset in range(1, len(state.turn_order) + 1):
            candidate = state.turn_order[(start + offset) % len(state.turn_order)]
            if (
                cls._is_active(state, candidate)
                and candidate not in round_state.passed_player_ids
                and candidate != round_state.high_bidder_id
            ):
                return candidate
        return None

    @classmethod
    def _waiting_bid_actor_ids(cls, state: SkullState) -> list[str]:
        """Players who have not answered the latest highest bid yet."""
        round_state = cls._round(state)
        return [
            player_id for player_id in cls._active_ids(state)
            if player_id != round_state.high_bidder_id
            and player_id not in round_state.passed_player_ids
        ]

    @classmethod
    def _reset_bid_passes(cls, state: SkullState) -> None:
        """Reactivate every player whenever a new highest bid is made."""
        cls._round(state).passed_player_ids.clear()
        for player_state in state.players.values():
            player_state.passed_bid = False
