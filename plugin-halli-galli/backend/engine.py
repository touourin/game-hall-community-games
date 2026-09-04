from __future__ import annotations

from copy import deepcopy
from random import SystemRandom
import re
import time
from typing import Any, Callable

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError

from .catalog import (
    ALL_CARDS,
    CARD_INDEX,
    COPY_DISTRIBUTION,
    EXPECTED_CARD_IDS,
    FRUIT_ORDER,
    FRUIT_SPECS,
    MODEL_VERSION,
    FruitCard,
    public_catalog,
)
from .rules import (
    clockwise_ids,
    eligible_player_ids,
    flippable_player_ids,
    next_flipper,
    owned_count,
    recompute_fruit_totals,
)
from .state import HalliGalliPlayerState, HalliGalliState


MINIMUM_FLIP_DELAY_MS = 350
NO_PROGRESS_TIMEOUT_MS = 10_000
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,80}$")
ALLOWED_INPUT_METHODS = {"pointer", "touch", "keyboard", "button", "test"}


class HalliGalliEngine:
    key = "plugin-halli-galli"
    name = "德国心脏病"
    min_players = 2
    max_players = 6

    def __init__(
        self,
        rng: Any | None = None,
        clock_ms: Callable[[], int] | None = None,
    ) -> None:
        self.rng = rng or SystemRandom()
        self.clock_ms = clock_ms or (lambda: int(time.time() * 1000))

    def initial_state(self) -> HalliGalliState:
        return HalliGalliState()

    @staticmethod
    def can_start(room: ArcadeRoom, viewer: ArcadePlayer) -> bool:
        del viewer
        active = [player for player in room.players if not player.left_room]
        return 2 <= len(active) <= 6 and len(active) == len(room.players)

    def start(self, room: ArcadeRoom) -> None:
        members = sorted(
            (player for player in room.players if not player.left_room),
            key=lambda player: player.seat,
        )
        if not self.min_players <= len(members) <= self.max_players:
            raise GameRuleError("德国心脏病需要 2–6 位玩家")
        if len(members) != len(room.players):
            raise GameRuleError("请先移除已经离开房间的玩家")
        if [player.seat for player in members] != list(range(len(members))):
            raise GameRuleError("玩家座位必须连续且唯一")
        profile = room.options.get("rulesProfile", "official_last_bell")
        if profile != "official_last_bell":
            raise GameRuleError("当前实现固定使用常规的最终二人再响一铃规则")

        deck = list(ALL_CARDS)
        self.rng.shuffle(deck)
        deal_offset = self.rng.randrange(len(members))
        states = {
            player.id: HalliGalliPlayerState(
                id=player.id,
                seat=player.seat,
                display_name=player.name,
            )
            for player in members
        }
        for index, card in enumerate(deck):
            recipient = members[(deal_offset + index) % len(members)]
            states[recipient.id].draw_pile.append(card)

        if room.options.get("firstPlayer") == "host":
            starter = next(
                (player for player in members if player.id == room.host_id),
                members[0],
            )
        else:
            starter = self.rng.choice(members)
        state = HalliGalliState(
            model_version=MODEL_VERSION,
            stage="playing",
            player_ids=[player.id for player in members],
            players=states,
            starting_player_id=starter.id,
            current_player_id=starter.id,
            deal_offset=deal_offset,
            final_duel_armed=len(members) == 2,
            earliest_next_flip_at_ms=self._now(),
        )
        room.state = state
        room.phase = "playing"
        room.winner = None
        room.winner_player_ids = []
        room.win_reason = None
        room.round_number = max(1, room.round_number + 1)
        self._emit(
            state,
            "game_started",
            starter.id,
            [],
            f"{starter.name} 先翻牌；56 张水果牌已经全部发完",
            {
                "playerCount": len(members),
                "dealOffset": deal_offset,
                "finalDuelArmed": state.final_duel_armed,
            },
            "round_deal",
        )
        self.assert_invariants(room)

    def act(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        action: str,
        payload: dict[str, Any],
    ) -> None:
        self._member(room, player)
        action_id = self._action_id(action, payload)
        if action_id and self._is_duplicate(room.state, action_id, player.id, action):
            return
        if room.phase != "playing":
            raise GameRuleError("当前牌局尚未开始或已经结束")

        if action == "flip_card":
            self._flip_card(room, player, payload)
        elif action == "ring_bell":
            self._ring_bell(room, player, payload)
        elif action == "settle_no_progress":
            self._settle_no_progress(room, player, payload)
        elif action == "resign":
            self._resign(room, player)
        else:
            raise GameRuleError("不支持这个德国心脏病操作")

        if action_id:
            self._remember_action(room.state, action_id, player.id, action)
        self.assert_invariants(room)

    def _flip_card(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        state: HalliGalliState = room.state
        revision = self._int_payload(payload, "revision")
        expected_epoch = self._int_payload(payload, "expectedBoardEpoch")
        if revision != room.revision:
            raise GameRuleError("STALE_REVISION：房间已更新，请按最新桌面重试")
        if expected_epoch != state.board_epoch:
            raise GameRuleError("STALE_BOARD：牌面已经变化，本次翻牌未执行")
        if player.id != state.current_player_id:
            raise GameRuleError("NOT_YOUR_TURN：还没有轮到你翻牌")
        actor = state.players[player.id]
        if actor.status != "eligible" or not actor.draw_pile:
            raise GameRuleError("NOT_ELIGIBLE：你当前没有可翻的牌")
        now = self._now()
        if now < state.earliest_next_flip_at_ms:
            remaining = state.earliest_next_flip_at_ms - now
            raise GameRuleError(f"FLIP_TOO_EARLY：请等待 {remaining} 毫秒")

        card = actor.draw_pile.pop(0)
        actor.discard_pile.append(card)
        state.turn_number += 1
        state.board_epoch += 1
        state.fruit_totals, state.valid_fruit_ids = recompute_fruit_totals(state)
        state.current_player_id = next_flipper(state, player.id)
        state.earliest_next_flip_at_ms = now + MINIMUM_FLIP_DELAY_MS
        actor.last_action_seq = state.event_seq + 1
        self._emit(
            state,
            "card_flipped",
            player.id,
            [],
            f"{actor.display_name} 翻开了 {card.fruit_count} 个{FRUIT_SPECS[card.fruit_id]['nameZh']}",
            {
                "card": card.public(),
                "drawCount": len(actor.draw_pile),
                "discardCount": len(actor.discard_pile),
                "turnNumber": state.turn_number,
            },
            "card_flip",
        )
        self._update_no_progress(state, now)

    def _ring_bell(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        state: HalliGalliState = room.state
        request_epoch = self._int_payload(payload, "boardEpoch")
        input_method = payload.get("inputMethod", "button")
        if input_method not in ALLOWED_INPUT_METHODS:
            raise GameRuleError("inputMethod 只能是 pointer、touch、keyboard 或 button")
        if (
            state.bell_resolution is not None
            and state.bell_resolution.get("boardEpoch") == request_epoch
        ):
            raise GameRuleError("BELL_ALREADY_RESOLVED：这个牌面已经有人先按到铃")
        if request_epoch != state.board_epoch:
            raise GameRuleError("STALE_BOARD：你看到的牌面已经变化，本次不处罚")
        actor = state.players[player.id]
        if actor.status != "eligible":
            raise GameRuleError("NOT_ELIGIBLE：你已经失去抢铃资格")

        pre_final_duel = state.final_duel_armed
        if state.valid_fruit_ids:
            self._resolve_correct_bell(
                room, state, player.id, input_method, pre_final_duel,
            )
        else:
            self._resolve_wrong_bell(
                room, state, player.id, input_method, pre_final_duel,
            )

    def _resolve_correct_bell(
        self,
        room: ArcadeRoom,
        state: HalliGalliState,
        actor_id: str,
        input_method: str,
        pre_final_duel: bool,
    ) -> None:
        resolved_epoch = state.board_epoch
        valid_fruits = list(state.valid_fruit_ids)
        collected_count, source_counts = self._collect_all_discards(state, actor_id)
        eliminated: list[str] = []
        for player_id in state.player_ids:
            player = state.players[player_id]
            if player.status == "eligible" and not player.draw_pile:
                player.status = "eliminated"
                player.elimination_reason = "discard-captured"
                eliminated.append(player_id)
        winner = state.players[actor_id]
        winner.status = "eligible"
        winner.elimination_reason = None
        state.board_epoch += 1
        state.fruit_totals, state.valid_fruit_ids = recompute_fruit_totals(state)
        state.current_player_id = actor_id if winner.draw_pile else next_flipper(state, actor_id)
        state.earliest_next_flip_at_ms = self._now() + MINIMUM_FLIP_DELAY_MS
        state.no_progress_deadline_ms = None
        state.bell_resolution = {
            "kind": "correct",
            "boardEpoch": resolved_epoch,
            "resultBoardEpoch": state.board_epoch,
            "actorPlayerId": actor_id,
            "winnerPlayerId": actor_id,
            "validFruitIds": valid_fruits,
            "capturedCount": collected_count,
            "sourceCounts": source_counts,
            "penalties": [],
            "eliminatedPlayerIds": eliminated,
            "inputMethod": input_method,
            "preFinalDuel": pre_final_duel,
        }
        self._emit(
            state,
            "bell_correct",
            actor_id,
            eliminated,
            f"{winner.display_name} 正确抢铃，收走 {collected_count} 张明牌",
            deepcopy(state.bell_resolution),
            "collect_piles",
        )

        eligible = eligible_player_ids(state)
        if pre_final_duel:
            self._finish_game(room, state, "final_correct_bell")
            return
        if len(eligible) <= 1:
            self._finish_game(room, state, "last_player")
            return
        if len(eligible) == 2:
            state.final_duel_armed = True
            self._emit(
                state,
                "final_duel_armed",
                actor_id,
                eligible,
                "进入最终二人阶段：下一次被受理的按铃将结束游戏",
                {"eligiblePlayerIds": eligible},
                "final_duel_armed",
            )

    def _resolve_wrong_bell(
        self,
        room: ArcadeRoom,
        state: HalliGalliState,
        actor_id: str,
        input_method: str,
        pre_final_duel: bool,
    ) -> None:
        resolved_epoch = state.board_epoch
        actor = state.players[actor_id]
        if pre_final_duel:
            opponents = [
                player_id for player_id in eligible_player_ids(state)
                if player_id != actor_id
            ]
            if len(opponents) != 1:
                raise RuntimeError("最终二人标记与实际抢铃资格不一致")
            opponent_id = opponents[0]
            collected_count, source_counts = self._collect_all_discards(
                state, opponent_id,
            )
            state.board_epoch += 1
            state.fruit_totals, state.valid_fruit_ids = recompute_fruit_totals(state)
            state.current_player_id = None
            state.no_progress_deadline_ms = None
            state.bell_resolution = {
                "kind": "wrong_final",
                "boardEpoch": resolved_epoch,
                "resultBoardEpoch": state.board_epoch,
                "actorPlayerId": actor_id,
                "winnerPlayerId": opponent_id,
                "validFruitIds": [],
                "capturedCount": collected_count,
                "sourceCounts": source_counts,
                "penalties": [],
                "eliminatedPlayerIds": [],
                "inputMethod": input_method,
                "preFinalDuel": True,
            }
            self._emit(
                state,
                "bell_wrong_final",
                actor_id,
                [opponent_id],
                f"{actor.display_name} 在最终二人阶段误按；{state.players[opponent_id].display_name} 收走全部明牌",
                deepcopy(state.bell_resolution),
                "collect_piles",
            )
            self._finish_game(room, state, "final_wrong_bell")
            return

        targets = [
            player_id
            for player_id in clockwise_ids(state, actor_id)[1:]
            if state.players[player_id].status == "eligible"
        ]
        penalties: list[dict[str, Any]] = []
        for target_id in targets:
            if not actor.draw_pile:
                break
            card = actor.draw_pile.pop(0)
            state.players[target_id].draw_pile.append(card)
            penalties.append({"toPlayerId": target_id, "count": 1})

        eliminated: list[str] = []
        if not actor.draw_pile:
            actor.status = "eliminated"
            actor.elimination_reason = "wrong-bell-empty"
            eliminated.append(actor_id)
        if (
            state.current_player_id is None
            or state.players[state.current_player_id].status != "eligible"
            or not state.players[state.current_player_id].draw_pile
        ):
            state.current_player_id = next_flipper(state, actor_id)
        state.bell_resolution = {
            "kind": "wrong",
            "boardEpoch": resolved_epoch,
            "resultBoardEpoch": resolved_epoch,
            "actorPlayerId": actor_id,
            "winnerPlayerId": None,
            "validFruitIds": [],
            "capturedCount": 0,
            "sourceCounts": {},
            "penalties": penalties,
            "eliminatedPlayerIds": eliminated,
            "inputMethod": input_method,
            "preFinalDuel": False,
        }
        self._emit(
            state,
            "bell_wrong",
            actor_id,
            [item["toPlayerId"] for item in penalties],
            f"{actor.display_name} 误按，向其他玩家付出 {len(penalties)} 张牌",
            deepcopy(state.bell_resolution),
            "penalty_transfer",
        )
        eligible = eligible_player_ids(state)
        if len(eligible) <= 1:
            self._finish_game(room, state, "last_player")
            return
        if len(eligible) == 2:
            state.final_duel_armed = True
            self._emit(
                state,
                "final_duel_armed",
                actor_id,
                eligible,
                "进入最终二人阶段：下一次被受理的按铃将结束游戏",
                {"eligiblePlayerIds": eligible},
                "final_duel_armed",
            )
        self._update_no_progress(state, self._now())

    def _settle_no_progress(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        del player
        state: HalliGalliState = room.state
        expected_epoch = self._int_payload(payload, "boardEpoch")
        if expected_epoch != state.board_epoch:
            raise GameRuleError("STALE_BOARD：牌面已经变化，无进展裁决已取消")
        if state.no_progress_deadline_ms is None:
            raise GameRuleError("当前牌局仍可继续")
        if flippable_player_ids(state) or state.valid_fruit_ids:
            state.no_progress_deadline_ms = None
            raise GameRuleError("牌局已经恢复进展")
        now = self._now()
        if now < state.no_progress_deadline_ms:
            raise GameRuleError(
                f"安全裁决还需等待 {state.no_progress_deadline_ms - now} 毫秒",
            )
        self._finish_game(room, state, "no_progress")

    def _resign(self, room: ArcadeRoom, player: ArcadePlayer) -> None:
        state: HalliGalliState = room.state
        actor = state.players[player.id]
        if actor.status != "eligible":
            raise GameRuleError("你已经退出本局")
        before_count = len(eligible_player_ids(state))
        actor.status = "resigned"
        actor.elimination_reason = "resigned"
        if state.current_player_id == player.id:
            state.current_player_id = next_flipper(state, player.id)
        self._emit(
            state,
            "player_resigned",
            player.id,
            [],
            f"{actor.display_name} 退出了本局",
            {},
            "player_eliminated",
        )
        eligible = eligible_player_ids(state)
        if len(eligible) <= 1:
            self._finish_game(room, state, "resignation")
            return
        if before_count > 2 and len(eligible) == 2:
            state.final_duel_armed = True
            self._emit(
                state,
                "final_duel_armed",
                player.id,
                eligible,
                "进入最终二人阶段：下一次被受理的按铃将结束游戏",
                {"eligiblePlayerIds": eligible},
                "final_duel_armed",
            )
        self._update_no_progress(state, self._now())

    def manual_forfeit(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        if room.phase != "playing":
            return False
        state: HalliGalliState = room.state
        if player.id not in state.players or state.players[player.id].status != "eligible":
            return False
        self._resign(room, player)
        self.assert_invariants(room)
        return True

    def disconnect_timeout(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        return self.manual_forfeit(room, player)

    def view(self, room: ArcadeRoom, viewer: ArcadePlayer) -> dict[str, Any]:
        state: HalliGalliState = room.state
        if viewer.id not in state.players:
            raise GameRuleError("观看视角不是本局玩家")
        viewer_index = state.player_ids.index(viewer.id)
        now = self._now()
        players: list[dict[str, Any]] = []
        for absolute_index, player_id in enumerate(state.player_ids):
            domain = state.players[player_id]
            public_status = domain.status
            if domain.status == "eligible" and not domain.draw_pile:
                public_status = "last_chance"
            elif domain.status == "eligible" and player_id == state.current_player_id:
                public_status = "current_turn"
            arcade_player = room.player(player_id)
            players.append(
                {
                    "id": player_id,
                    "name": domain.display_name,
                    "seat": domain.seat,
                    "relativeSeat": (absolute_index - viewer_index) % len(state.player_ids),
                    "isSelf": player_id == viewer.id,
                    "isCurrent": player_id == state.current_player_id,
                    "connected": arcade_player.connected,
                    "status": domain.status,
                    "displayStatus": public_status,
                    "eliminationReason": domain.elimination_reason,
                    "drawCount": len(domain.draw_pile),
                    "discardCount": len(domain.discard_pile),
                    "ownedCount": owned_count(domain),
                    "topCard": domain.discard_pile[-1].public() if domain.discard_pile else None,
                }
            )
        self_domain = state.players[viewer.id]
        current_resolution = state.bell_resolution
        bell_open = not (
            current_resolution is not None
            and current_resolution.get("boardEpoch") == state.board_epoch
        )
        can_flip = (
            room.phase == "playing"
            and state.current_player_id == viewer.id
            and self_domain.status == "eligible"
            and bool(self_domain.draw_pile)
            and now >= state.earliest_next_flip_at_ms
        )
        can_flip_when_ready = (
            room.phase == "playing"
            and state.current_player_id == viewer.id
            and self_domain.status == "eligible"
            and bool(self_domain.draw_pile)
        )
        can_ring = room.phase == "playing" and self_domain.status == "eligible" and bell_open
        can_settle = (
            room.phase == "playing"
            and state.no_progress_deadline_ms is not None
            and now >= state.no_progress_deadline_ms
        )
        events = deepcopy(state.events[-18:])
        return {
            "schemaVersion": state.schema_version,
            "modelVersion": state.model_version,
            "profileId": state.profile_id,
            "sceneId": self._scene_id(room, state, viewer.id),
            "stage": state.stage,
            "revision": room.revision,
            "turnNumber": state.turn_number,
            "boardEpoch": state.board_epoch,
            "startingPlayerId": state.starting_player_id,
            "currentPlayerId": state.current_player_id,
            "selfPlayerId": viewer.id,
            "finalDuelArmed": state.final_duel_armed,
            "earliestNextFlipAtMs": state.earliest_next_flip_at_ms,
            "noProgressDeadlineMs": state.no_progress_deadline_ms,
            "players": players,
            "rules": {
                "playerMin": 2,
                "playerMax": 6,
                "deckSize": 56,
                "bellTarget": 5,
                "profileId": "official_last_bell",
                "minimumFlipDelayMs": MINIMUM_FLIP_DELAY_MS,
                "noProgressTimeoutMs": NO_PROGRESS_TIMEOUT_MS,
                "faithfulCounting": True,
            },
            "actions": {
                "canFlip": can_flip,
                "canFlipWhenReady": can_flip_when_ready,
                "canRing": can_ring,
                "canSettleNoProgress": can_settle,
                "flipDisabledReason": self._flip_disabled_reason(
                    room, state, viewer.id, now,
                ),
                "ringDisabledReason": self._ring_disabled_reason(
                    room, state, viewer.id, bell_open,
                ),
            },
            "bell": {
                "boardEpoch": state.board_epoch,
                "enabled": can_ring,
                "lastResolution": deepcopy(state.bell_resolution),
            },
            "cardCatalog": public_catalog(),
            "fruitLegend": [
                {
                    "fruitId": fruit_id,
                    "nameZh": FRUIT_SPECS[fruit_id]["nameZh"],
                    "shape": FRUIT_SPECS[fruit_id]["shape"],
                    "palette": dict(FRUIT_SPECS[fruit_id]["palette"]),
                }
                for fruit_id in FRUIT_ORDER
            ],
            "events": events,
            "latestEvent": deepcopy(events[-1]) if events else None,
            "result": deepcopy(state.result),
        }

    def player_result(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
    ) -> tuple[str, str, bool]:
        state: HalliGalliState = room.state
        total = owned_count(state.players[player.id])
        row = None
        if state.result:
            row = next(
                (item for item in state.result["rows"] if item["playerId"] == player.id),
                None,
            )
        rank = row["rank"] if row else None
        label = f"第 {rank} 名 · {total} 张牌" if rank else f"{total} 张牌"
        return label, "player", player.id in room.winner_player_ids

    def record_state(self, room: ArcadeRoom) -> dict[str, Any]:
        state: HalliGalliState = room.state
        return {
            "schemaVersion": state.schema_version,
            "modelVersion": state.model_version,
            "profileId": state.profile_id,
            "turnNumber": state.turn_number,
            "boardEpoch": state.board_epoch,
            "finalDuelArmed": state.final_duel_armed,
            "events": deepcopy(state.events),
            "result": deepcopy(state.result),
            "players": [
                {
                    "playerId": player_id,
                    "seat": state.players[player_id].seat,
                    "status": state.players[player_id].status,
                    "ownedCount": owned_count(state.players[player_id]),
                }
                for player_id in state.player_ids
            ],
        }

    def assert_invariants(self, room: ArcadeRoom) -> None:
        state: HalliGalliState = room.state
        if not 2 <= len(state.player_ids) <= 6:
            raise AssertionError("player count must remain in 2..6")
        if len(state.player_ids) != len(set(state.player_ids)):
            raise AssertionError("player ids must be unique")
        if [state.players[player_id].seat for player_id in state.player_ids] != list(
            range(len(state.player_ids)),
        ):
            raise AssertionError("seat order drifted")
        cards = [
            card
            for player_id in state.player_ids
            for card in (
                state.players[player_id].draw_pile
                + state.players[player_id].discard_pile
            )
        ]
        card_ids = [card.id for card in cards]
        if len(card_ids) != 56 or len(set(card_ids)) != 56:
            raise AssertionError("card conservation or uniqueness failed")
        if set(card_ids) != EXPECTED_CARD_IDS:
            raise AssertionError("unknown or missing card instance")
        totals, valid = recompute_fruit_totals(state)
        if state.fruit_totals != totals or state.valid_fruit_ids != valid:
            raise AssertionError("visible fruit cache drifted")
        if state.current_player_id is not None:
            current = state.players[state.current_player_id]
            if current.status != "eligible" or not current.draw_pile:
                raise AssertionError("current player cannot flip")
        elif room.phase == "playing" and flippable_player_ids(state):
            raise AssertionError("a live flippable table requires a current player")
        for player_id in state.player_ids:
            player = state.players[player_id]
            if player.status == "eligible" and not player.draw_pile and not player.discard_pile:
                raise AssertionError("empty eligible player should be eliminated")
            if player.status not in {"eligible", "eliminated", "resigned"}:
                raise AssertionError("invalid player status")
            for card in player.draw_pile + player.discard_pile:
                canonical = CARD_INDEX[card.id]
                if (
                    card.face_id,
                    card.fruit_id,
                    card.fruit_count,
                    card.copy_index,
                ) != (
                    canonical.face_id,
                    canonical.fruit_id,
                    canonical.fruit_count,
                    canonical.copy_index,
                ):
                    raise AssertionError("card semantic identity drifted")
        if state.final_duel_armed and len(eligible_player_ids(state)) > 2:
            raise AssertionError("final duel armed with more than two eligible players")
        if room.phase == "finished":
            if state.stage != "finished" or state.result is None:
                raise AssertionError("finished room requires a result")
            if sum(item["totalCount"] for item in state.result["rows"]) != 56:
                raise AssertionError("settlement must total 56 cards")
            if set(state.result["winnerPlayerIds"]) != set(room.winner_player_ids):
                raise AssertionError("room and game winners disagree")
        elif state.result is not None:
            raise AssertionError("live game cannot expose a final result")

    def _finish_game(
        self,
        room: ArcadeRoom,
        state: HalliGalliState,
        reason_code: str,
    ) -> None:
        scores = {
            player_id: owned_count(state.players[player_id])
            for player_id in state.player_ids
        }
        candidate_ids = eligible_player_ids(state)
        if not candidate_ids:
            candidate_ids = [
                player_id for player_id in state.player_ids
                if state.players[player_id].status != "resigned"
            ]
        if not candidate_ids:
            candidate_ids = list(state.player_ids)
        best = max(scores[player_id] for player_id in candidate_ids)
        winners = [
            player_id for player_id in candidate_ids
            if scores[player_id] == best
        ]
        ordered = sorted(state.player_ids, key=lambda player_id: (-scores[player_id], state.players[player_id].seat))
        ranks = {
            player_id: 1 + sum(scores[other_id] > scores[player_id] for other_id in state.player_ids)
            for player_id in state.player_ids
        }
        reason_map = {
            "final_correct_bell": "最终二人阶段正确抢铃，按持牌数结算",
            "final_wrong_bell": "最终二人阶段发生误按，对手收走明牌后结算",
            "last_player": "只剩一名玩家仍有抢铃资格",
            "resignation": "其他玩家退出，牌局无法继续",
            "no_progress": "无人能够翻牌且当前没有正确铃，执行数字安全裁决",
        }
        reason = reason_map[reason_code]
        state.stage = "finished"
        state.current_player_id = None
        state.no_progress_deadline_ms = None
        state.result = {
            "reasonCode": reason_code,
            "reasonZh": reason,
            "winnerPlayerIds": winners,
            "sharedWin": len(winners) > 1,
            "rows": [
                {
                    "playerId": player_id,
                    "name": state.players[player_id].display_name,
                    "seat": state.players[player_id].seat,
                    "status": state.players[player_id].status,
                    "drawCount": len(state.players[player_id].draw_pile),
                    "discardCount": len(state.players[player_id].discard_pile),
                    "totalCount": scores[player_id],
                    "rank": ranks[player_id],
                    "won": player_id in winners,
                }
                for player_id in ordered
            ],
        }
        self._emit(
            state,
            "game_finished",
            winners[0] if winners else None,
            winners,
            f"{reason}；{self._winner_names(state, winners)} 获胜",
            {
                "reasonCode": reason_code,
                "winnerPlayerIds": winners,
                "scores": scores,
                "sharedWin": len(winners) > 1,
            },
            "result_enter",
        )
        room.finish("cards", winners, reason)

    def _collect_all_discards(
        self,
        state: HalliGalliState,
        collector_id: str,
    ) -> tuple[int, dict[str, int]]:
        collector = state.players[collector_id]
        source_counts: dict[str, int] = {}
        captured: list[FruitCard] = []
        for source_id in clockwise_ids(state, collector_id):
            source = state.players[source_id]
            source_counts[source_id] = len(source.discard_pile)
            captured.extend(source.discard_pile)
            source.discard_pile = []
        collector.draw_pile.extend(captured)
        return len(captured), source_counts

    def _update_no_progress(self, state: HalliGalliState, now: int) -> None:
        if flippable_player_ids(state) or state.valid_fruit_ids:
            state.no_progress_deadline_ms = None
            return
        if state.no_progress_deadline_ms is None:
            state.no_progress_deadline_ms = now + NO_PROGRESS_TIMEOUT_MS
            self._emit(
                state,
                "no_progress_started",
                None,
                eligible_player_ids(state),
                "无人可继续翻牌；若十秒内没有正确抢铃，将按持牌数结算",
                {"deadlineMs": state.no_progress_deadline_ms},
                "final_duel_armed",
            )

    @staticmethod
    def _scene_id(room: ArcadeRoom, state: HalliGalliState, viewer_id: str) -> str:
        if room.phase == "finished":
            return "finished"
        latest = state.events[-1]["type"] if state.events else ""
        if latest == "bell_correct":
            return "bell_resolved_correct"
        if latest in {"bell_wrong", "bell_wrong_final"}:
            return "bell_resolved_wrong"
        viewer = state.players[viewer_id]
        if viewer.status == "eligible" and not viewer.draw_pile:
            return "last_chance_player"
        if state.valid_fruit_ids:
            return "exact_five_visible"
        if state.current_player_id == viewer_id:
            return "playing_self_turn"
        return "playing_other_turn"

    @staticmethod
    def _flip_disabled_reason(
        room: ArcadeRoom,
        state: HalliGalliState,
        viewer_id: str,
        now: int,
    ) -> str | None:
        player = state.players[viewer_id]
        if room.phase != "playing":
            return "本局已经结束"
        if player.status != "eligible":
            return "你已退出本局"
        if not player.draw_pile:
            return "抽牌堆为空，但只要明牌仍在你仍可抢铃"
        if state.current_player_id != viewer_id:
            current = state.players.get(state.current_player_id) if state.current_player_id else None
            return f"等待 {current.display_name if current else '其他玩家'} 翻牌"
        if now < state.earliest_next_flip_at_ms:
            return "翻牌保护时间尚未结束"
        return None

    @staticmethod
    def _ring_disabled_reason(
        room: ArcadeRoom,
        state: HalliGalliState,
        viewer_id: str,
        bell_open: bool,
    ) -> str | None:
        if room.phase != "playing":
            return "本局已经结束"
        if state.players[viewer_id].status != "eligible":
            return "你已失去抢铃资格"
        if not bell_open:
            return "这个牌面已经完成一次铃铛裁定"
        return None

    def _emit(
        self,
        state: HalliGalliState,
        event_type: str,
        actor_id: str | None,
        target_ids: list[str],
        message: str,
        data: dict[str, Any],
        cue: str,
    ) -> None:
        state.event_seq += 1
        state.events.append(
            {
                "seq": state.event_seq,
                "type": event_type,
                "cue": cue,
                "actorPlayerId": actor_id,
                "targetPlayerIds": list(target_ids),
                "messageZh": message,
                "boardEpoch": state.board_epoch,
                "data": deepcopy(data),
            },
        )
        state.events = state.events[-64:]

    @staticmethod
    def _winner_names(state: HalliGalliState, winner_ids: list[str]) -> str:
        return "、".join(state.players[player_id].display_name for player_id in winner_ids)

    @staticmethod
    def _member(room: ArcadeRoom, player: ArcadePlayer) -> None:
        if player.left_room or not any(member.id == player.id for member in room.players):
            raise GameRuleError("你不在这个房间中")

    def _now(self) -> int:
        return int(self.clock_ms())

    @staticmethod
    def _int_payload(payload: dict[str, Any], key: str) -> int:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise GameRuleError(f"{key} 必须是整数")
        return value

    @staticmethod
    def _action_id(action: str, payload: dict[str, Any]) -> str | None:
        if action == "resign":
            value = payload.get("actionId")
            if value is None:
                return None
        else:
            value = payload.get("actionId")
            if not isinstance(value, str) or not ACTION_ID_PATTERN.fullmatch(value):
                raise GameRuleError("actionId 必须是 8–80 位字母、数字、下划线或连字符")
        if not isinstance(value, str) or not ACTION_ID_PATTERN.fullmatch(value):
            raise GameRuleError("actionId 格式无效")
        return value

    @staticmethod
    def _is_duplicate(
        state: HalliGalliState,
        action_id: str,
        player_id: str,
        action: str,
    ) -> bool:
        existing = state.processed_actions.get(action_id)
        if existing is None:
            return False
        if existing != f"{player_id}:{action}":
            raise GameRuleError("actionId 已被另一个动作使用")
        return True

    @staticmethod
    def _remember_action(
        state: HalliGalliState,
        action_id: str,
        player_id: str,
        action: str,
    ) -> None:
        state.processed_actions[action_id] = f"{player_id}:{action}"
        state.processed_action_order.append(action_id)
        while len(state.processed_action_order) > 128:
            stale = state.processed_action_order.pop(0)
            state.processed_actions.pop(stale, None)
