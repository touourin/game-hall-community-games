from __future__ import annotations

import random
from typing import Any

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError

from .catalog import (
    SUIT_ORDER,
    all_card_ids,
    card,
    card_view,
    lowest_card_ids,
    suit_of,
    suits,
    trait_view,
    traits,
    value_of,
)
from .scoring import rank_scores, score_board
from .state import (
    ChoiceOption,
    DeadMansDrawState,
    GameResult,
    PendingChoice,
    PlayEntry,
    PlayerBoard,
    PublicEvent,
    ScoreRow,
    TurnState,
)


EVENT_LIMIT = 120
RULESET_ID = "tabletop_base_2015"


class DeadMansDrawEngine:
    key = "plugin-dead-mans-draw"
    name = "亡命神抽"
    min_players = 2
    max_players = 4
    action_phases = {"playing"}

    def __init__(self, rng: random.Random | random.SystemRandom | None = None) -> None:
        self.rng = rng or random.SystemRandom()

    def initial_state(self) -> DeadMansDrawState:
        return DeadMansDrawState()

    def start(self, room: ArcadeRoom) -> None:
        players = [player for player in room.players if not player.left_room]
        if not self.min_players <= len(players) <= self.max_players:
            raise GameRuleError("亡命神抽需要 2–4 位玩家")
        profile = room.options.get("rulesProfile", RULESET_ID)
        if profile != RULESET_ID:
            raise GameRuleError("当前实现只开放实体基础常规规则")
        if room.options.get("globalVariant") not in (None, ""):
            raise GameRuleError("常规规则不启用全局变体")
        traits_enabled = room.options.get("traitsEnabled", True)
        if not isinstance(traits_enabled, bool):
            raise GameRuleError("traitsEnabled 必须是布尔值")

        if room.options.get("firstPlayer") == "host":
            starter = next(
                (player for player in players if player.id == room.host_id),
                players[0],
            )
        else:
            starter = self.rng.choice(players)
        starter_index = players.index(starter)
        ordered = players[starter_index:] + players[:starter_index]

        initial_discard = lowest_card_ids()
        draw_pile = [
            identifier
            for identifier in all_card_ids()
            if identifier not in set(initial_discard)
        ]
        self.rng.shuffle(initial_discard)
        self.rng.shuffle(draw_pile)
        trait_deck = list(traits())
        self.rng.shuffle(trait_deck)

        boards = {player.id: PlayerBoard() for player in ordered}
        if traits_enabled:
            for player in ordered:
                boards[player.id].trait_offer = [trait_deck.pop(), trait_deck.pop()]

        state = DeadMansDrawState(
            phase="trait_selection" if traits_enabled else "turn",
            rules_profile_id=RULESET_ID,
            traits_enabled=traits_enabled,
            traits_revealed=not traits_enabled,
            turn_order=[player.id for player in ordered],
            players=boards,
            draw_pile=draw_pile,
            discard_pile=initial_discard,
            trait_deck=trait_deck,
            revision=1,
        )
        room.state = state
        room.phase = "playing"
        self._emit(
            state,
            "game_start",
            f"{starter.name} 成为首家；50 张牌进入抽牌堆，10 张最低牌进入弃牌堆",
            {"starterId": starter.id, "playerCount": len(ordered)},
        )
        if traits_enabled:
            self._emit(state, "trait_selection", "每位玩家从两项私密候选中选择一项特性")
        else:
            self._begin_turn(room, state)
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
        state: DeadMansDrawState = room.state
        board = state.players.get(player.id)
        if board is None or board.forfeited:
            raise GameRuleError("你已不在本局行动序列中")
        revision = payload.get("revision")
        if revision is not None and revision != state.revision:
            raise GameRuleError("操作基于旧状态，请刷新后重试")

        handlers = {
            "choose_trait": self._choose_trait,
            "choose_locker_target": self._choose_locker_target,
            "draw": self._draw,
            "collect": self._collect,
            "resolve_effect": self._resolve_effect,
            "resign": self._resign,
        }
        handler = handlers.get(action)
        if handler is None:
            raise GameRuleError("不支持这个亡命神抽操作")
        handler(room, state, player, payload)
        # manual_forfeit is also called directly by the host on disconnect and
        # therefore owns its revision bump.  Avoid advancing twice when the
        # same operation is reached through the explicit resign action.
        if action != "resign":
            state.revision += 1
        self.assert_invariants(state)

    def _choose_trait(
        self,
        room: ArcadeRoom,
        state: DeadMansDrawState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        if state.phase != "trait_selection":
            raise GameRuleError("当前不在特性选择阶段")
        board = state.players[player.id]
        trait_id = payload.get("traitId")
        if board.trait_id is not None:
            raise GameRuleError("你已经选择了特性")
        if not isinstance(trait_id, str) or trait_id not in board.trait_offer:
            raise GameRuleError("只能选择自己的两项特性候选")
        rejected = [candidate for candidate in board.trait_offer if candidate != trait_id]
        board.trait_id = trait_id
        board.trait_offer = []
        state.unused_traits.extend(rejected)
        self._emit(
            state,
            "trait_locked",
            f"{player.name} 已锁定特性",
            {"playerId": player.id},
        )
        self._maybe_finish_trait_selection(room, state)

    def _choose_locker_target(
        self,
        room: ArcadeRoom,
        state: DeadMansDrawState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        if state.phase != "trait_selection":
            raise GameRuleError("当前不在特性选择阶段")
        board = state.players[player.id]
        if board.trait_id != "trait-davy-jones-locker":
            raise GameRuleError("只有戴维·琼斯的魔柜需要指定对手")
        if board.locker_target_id is not None:
            raise GameRuleError("魔柜目标已经确定")
        target_id = payload.get("playerId")
        if (
            not isinstance(target_id, str)
            or target_id == player.id
            or target_id not in state.players
            or state.players[target_id].forfeited
        ):
            raise GameRuleError("请选择另一名仍在牌局中的玩家")
        board.locker_target_id = target_id
        self._emit(
            state,
            "locker_targeted",
            f"{player.name} 已为魔柜指定目标",
            {"playerId": player.id, "targetPlayerId": target_id},
        )
        self._maybe_finish_trait_selection(room, state)

    def _maybe_finish_trait_selection(
        self,
        room: ArcadeRoom,
        state: DeadMansDrawState,
    ) -> None:
        active = [
            (player_id, board)
            for player_id, board in state.players.items()
            if not board.forfeited
        ]
        if any(board.trait_id is None for _, board in active):
            return
        if any(
            board.trait_id == "trait-davy-jones-locker"
            and board.locker_target_id is None
            for _, board in active
        ):
            return
        state.traits_revealed = True
        state.phase = "turn"
        self._emit(
            state,
            "traits_revealed",
            "所有特性已经公开，牌局正式开始",
            {
                "traits": {
                    player_id: board.trait_id
                    for player_id, board in active
                }
            },
        )
        self._begin_turn(room, state)

    def _draw(
        self,
        room: ArcadeRoom,
        state: DeadMansDrawState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        turn = self._require_actor(state, player.id)
        if state.phase != "turn" or turn.pending_choice is not None:
            raise GameRuleError("必须先解决当前花色能力")
        if not state.draw_pile:
            raise GameRuleError("抽牌堆已经耗尽")
        turn.oracle_peek_card_ids = []
        identifier = state.draw_pile.pop(0)
        if not state.draw_pile:
            turn.deck_exhausted_during_turn = True
        self._emit(
            state,
            "card_drawn",
            f"{player.name} 从抽牌堆翻开{self._card_label(identifier)}",
            {"playerId": player.id, "card": card_view(identifier), "from": "draw_pile"},
        )
        self._enter_card(
            room,
            state,
            identifier,
            source_zone="draw",
            source_owner_id=None,
            parent_entry_id=None,
        )
        self._stabilize(room, state)

    def _collect(
        self,
        room: ArcadeRoom,
        state: DeadMansDrawState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        turn = self._require_actor(state, player.id)
        if state.phase != "turn" or turn.pending_choice is not None:
            raise GameRuleError("必须先解决当前花色能力")
        if not turn.play_area:
            raise GameRuleError("航道为空，当前没有可收取的牌")
        if turn.kraken_debt > 0:
            raise GameRuleError(f"海怪仍要求 {turn.kraken_debt} 张牌进入航道")
        batch = [entry.card_id for entry in turn.play_area]
        turn.play_area = []
        self._bank_cards(state, player.id, batch)
        self._emit(
            state,
            "card_transferred",
            f"{player.name} 收下航道中的 {len(batch)} 张战利品",
            {"playerId": player.id, "cardIds": batch, "from": "play_lane", "to": "self_bank"},
        )
        if self._trigger_key_chest_bonus(
            state,
            player.id,
            batch,
            after="end_turn",
        ):
            return
        self._end_turn(room, state)

    def _resolve_effect(
        self,
        room: ArcadeRoom,
        state: DeadMansDrawState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        turn = self._require_actor(state, player.id)
        choice = turn.pending_choice
        if state.phase != "effect_choice" or choice is None:
            raise GameRuleError("当前没有等待解决的花色能力")
        if choice.actor_id != player.id:
            raise GameRuleError("这不是你的效果选择")
        if payload.get("choiceId") != choice.choice_id:
            raise GameRuleError("效果选择已经过期")
        option_id = payload.get("optionId")
        option = next(
            (candidate for candidate in choice.options if candidate.option_id == option_id),
            None,
        )
        if option is None:
            raise GameRuleError("请选择服务端提供的合法选项")
        turn.pending_choice = None
        state.phase = "turn"

        if choice.kind == "hook-stack":
            self._resolve_hook_choice(room, state, choice, option)
        elif choice.kind == "cannon-target":
            self._resolve_cannon_choice(state, choice, option)
            self._drain_effect_stack(room, state)
        elif choice.kind == "map-card":
            self._resolve_map_choice(room, state, choice, option)
        elif choice.kind == "sword-target":
            self._resolve_sword_choice(room, state, choice, option)
        elif choice.kind == "plunderer-target":
            self._resolve_plunderer_choice(room, state, choice, option)
        else:
            raise GameRuleError("未知的效果选择")
        self._stabilize(room, state)

    def _resign(
        self,
        room: ArcadeRoom,
        state: DeadMansDrawState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        if not self.manual_forfeit(room, player):
            raise GameRuleError("当前不能退出这局游戏")

    def manual_forfeit(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        if room.phase != "playing":
            return False
        state: DeadMansDrawState = room.state
        board = state.players.get(player.id)
        if board is None or board.forfeited:
            return False
        board.forfeited = True
        board.trait_offer = []
        self._emit(
            state,
            "player_forfeit",
            f"{player.name} 退出牌局",
            {"playerId": player.id},
        )
        active_ids = self._active_player_ids(state)
        if len(active_ids) <= 1:
            self._abandon_current_turn(state)
            self._finish_game(room, state, "player-exit")
        elif state.phase == "trait_selection":
            self._maybe_finish_trait_selection(room, state)
        elif state.turn is not None and state.turn.actor_id == player.id:
            self._abandon_current_turn(state)
            if state.draw_pile:
                self._move_to_next_active(state)
                self._begin_turn(room, state)
            else:
                self._finish_game(room, state, "draw-pile-exhausted")
        state.revision += 1
        self.assert_invariants(state)
        return True

    def disconnect_timeout(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        return self.manual_forfeit(room, player)

    def request_voter_ids(self, room: ArcadeRoom, kind: str) -> set[str]:
        state: DeadMansDrawState = room.state
        return set(self._active_player_ids(state))

    def _enter_card(
        self,
        room: ArcadeRoom,
        state: DeadMansDrawState,
        identifier: str,
        *,
        source_zone: str,
        source_owner_id: str | None,
        parent_entry_id: str | None,
    ) -> None:
        turn = self._turn(state)
        actor_id = turn.actor_id
        actor_board = state.players[actor_id]
        suit = suit_of(identifier)

        direct_bank_trait = (
            source_zone == "draw"
            and (
                (suit == "mermaid" and actor_board.trait_id == "trait-casanova")
                or (suit == "kraken" and actor_board.trait_id == "trait-fisherman")
            )
        )
        if direct_bank_trait:
            self._bank_cards(state, actor_id, [identifier])
            self._emit(
                state,
                "card_transferred",
                f"{self._player_name(room, actor_id)} 的特性令{self._card_label(identifier)}直接进入银行",
                {"playerId": actor_id, "cardIds": [identifier], "from": "draw_pile", "to": "self_bank"},
            )
            return

        if any(suit_of(entry.card_id) == suit for entry in turn.play_area):
            turn.busting_card_id = identifier
            self._resolve_bust(room, state)
            return

        owed_before_entry = turn.kraken_debt > 0
        state.entry_counter += 1
        entry = PlayEntry(
            entry_id=f"entry-{state.entry_counter}",
            card_id=identifier,
            source_zone=source_zone,
            source_owner_id=source_owner_id,
            parent_entry_id=parent_entry_id,
        )
        turn.play_area.append(entry)
        if owed_before_entry:
            turn.kraken_debt -= 1
            self._emit_kraken_debt(state, actor_id)

        if turn.safe_harbor_slots > 0:
            entry.protection_reasons.add("safe-harbor-next")
            turn.safe_harbor_slots -= 1
        if actor_board.trait_id == "trait-miser":
            if suit == "hook":
                entry.protection_reasons.add("miser-hook")
            elif parent_entry_id is not None:
                parent = self._entry_by_id(turn, parent_entry_id)
                if parent is not None and suit_of(parent.card_id) == "hook":
                    entry.protection_reasons.add("miser-child")

        if suit == "anchor":
            for previous in turn.play_area[:-1]:
                previous.protection_reasons.add("anchor-prefix")
            if actor_board.trait_id == "trait-safe-harbor":
                entry.protection_reasons.add("safe-harbor-anchor")
                turn.safe_harbor_slots += 2

        self._emit(
            state,
            "card_entered",
            f"{self._card_label(identifier)}进入航道并发动{card(identifier)['nameZh']}能力",
            {
                "playerId": actor_id,
                "card": card_view(identifier),
                "entryId": entry.entry_id,
                "sourceZone": source_zone,
                "protected": bool(entry.protection_reasons),
            },
        )
        self._resolve_suit(room, state, entry)
        self._drain_effect_stack(room, state)

    def _resolve_suit(
        self,
        room: ArcadeRoom,
        state: DeadMansDrawState,
        entry: PlayEntry,
    ) -> None:
        suit = suit_of(entry.card_id)
        turn = self._turn(state)
        actor_id = turn.actor_id
        board = state.players[actor_id]

        if suit == "anchor":
            protected_count = sum(
                1 for candidate in turn.play_area if candidate.protection_reasons
            )
            self._emit(
                state,
                "effect_targeted",
                f"船锚建立保护，当前有 {protected_count} 张牌受保护",
                {"suit": suit, "protectedCount": protected_count},
            )
            return
        if suit == "hook":
            count = 2 if board.trait_id == "trait-captains-hook" else 1
            self._create_hook_choice(state, entry.entry_id, count)
            return
        if suit == "cannon":
            self._create_cannon_choice(room, state, entry)
            return
        if suit in {"key", "chest"}:
            return
        if suit == "map":
            self._create_map_choice(state, entry)
            return
        if suit == "oracle":
            count = 3 if board.trait_id == "trait-mystic" else 1
            turn.oracle_peek_card_ids = list(state.draw_pile[:count])
            if turn.oracle_peek_card_ids:
                self._emit(
                    state,
                    "oracle_revealed",
                    "水晶球公开了抽牌堆顶的牌",
                    {"cards": [card_view(item) for item in turn.oracle_peek_card_ids]},
                )
            return
        if suit == "sword":
            self._create_sword_choice(room, state, entry)
            return
        if suit == "kraken":
            debt = 4 if any(
                other_id != actor_id
                and not other_board.forfeited
                and other_board.trait_id == "trait-beastmaster"
                for other_id, other_board in state.players.items()
            ) else 2
            turn.kraken_debt += debt
            self._emit_kraken_debt(state, actor_id)

    def _create_hook_choice(
        self,
        state: DeadMansDrawState,
        source_entry_id: str,
        remaining: int,
    ) -> bool:
        turn = self._turn(state)
        board = state.players[turn.actor_id]
        options: list[ChoiceOption] = []
        for suit in SUIT_ORDER:
            if not board.bank[suit]:
                continue
            identifier = board.bank[suit][0]
            options.append(self._option(
                state,
                f"从自己的{card(identifier)['nameZh']}堆取出 {value_of(identifier)}",
                card_id=identifier,
                player_id=turn.actor_id,
                suit=suit,
                causes_bust=self._would_bust(turn, identifier),
            ))
        if not options:
            self._emit(state, "effect_targeted", "抓钩没有可取的银行牌", {"suit": "hook"})
            return False
        self._set_choice(
            state,
            kind="hook-stack",
            prompt="抓钩必须从自己的银行带入一张顶牌",
            source_entry_id=source_entry_id,
            options=options,
            context={"remaining": remaining},
        )
        return True

    def _create_cannon_choice(
        self,
        room: ArcadeRoom,
        state: DeadMansDrawState,
        entry: PlayEntry,
    ) -> None:
        turn = self._turn(state)
        actor_id = turn.actor_id
        actor_board = state.players[actor_id]
        misfire_owner = next((
            other_id
            for other_id, board in state.players.items()
            if other_id != actor_id
            and not board.forfeited
            and board.trait_id == "trait-misfire"
        ), None)
        target_ids = [actor_id] if misfire_owner else [
            player_id for player_id in state.turn_order
            if player_id != actor_id and not state.players[player_id].forfeited
        ]
        options: list[ChoiceOption] = []
        for target_id in target_ids:
            target = state.players[target_id]
            for suit in SUIT_ORDER:
                if not target.bank[suit]:
                    continue
                identifier = target.bank[suit][0]
                options.append(self._option(
                    state,
                    f"{self._player_name(room, target_id)}的{card(identifier)['nameZh']} {value_of(identifier)}",
                    card_id=identifier,
                    player_id=target_id,
                    suit=suit,
                ))
        if not options:
            self._emit(state, "effect_targeted", "火炮没有合法目标", {"suit": "cannon"})
            return
        context = {
            "quantity": "one" if misfire_owner else (
                "entire" if actor_board.trait_id == "trait-master-gunner" else "one"
            ),
            "destination": "discard" if misfire_owner else (
                "actor-bank" if actor_board.trait_id == "trait-scavenger" else "discard"
            ),
            "misfireOwnerId": misfire_owner,
        }
        prompt = "哑火迫使你选择自己的一个银行花色" if misfire_owner else "选择火炮攻击的银行花色"
        self._set_choice(
            state,
            kind="cannon-target",
            prompt=prompt,
            source_entry_id=entry.entry_id,
            options=options,
            context=context,
        )

    def _create_map_choice(self, state: DeadMansDrawState, entry: PlayEntry) -> None:
        if not state.discard_pile:
            self._emit(state, "map_revealed", "弃牌堆为空，藏宝图没有效果", {"cards": []})
            return
        turn = self._turn(state)
        board = state.players[turn.actor_id]
        self.rng.shuffle(state.discard_pile)
        count = len(state.discard_pile) if board.trait_id == "trait-navigator" else min(3, len(state.discard_pile))
        candidates = list(state.discard_pile[:count])
        del state.discard_pile[:count]
        turn.map_reveal_card_ids = candidates
        options = [
            self._option(
                state,
                f"选择{self._card_label(identifier)}",
                card_id=identifier,
                suit=suit_of(identifier),
                causes_bust=self._would_bust(turn, identifier),
            )
            for identifier in candidates
        ]
        self._emit(
            state,
            "map_revealed",
            f"藏宝图公开了 {len(candidates)} 张弃牌候选",
            {"cards": [card_view(item) for item in candidates]},
        )
        self._set_choice(
            state,
            kind="map-card",
            prompt="藏宝图必须选择一张牌放入航道",
            source_entry_id=entry.entry_id,
            options=options,
        )

    def _create_sword_choice(
        self,
        room: ArcadeRoom,
        state: DeadMansDrawState,
        entry: PlayEntry,
    ) -> None:
        turn = self._turn(state)
        actor_id = turn.actor_id
        actor_board = state.players[actor_id]
        parry_owner = next((
            other_id
            for other_id, board in state.players.items()
            if other_id != actor_id
            and not board.forfeited
            and board.trait_id == "trait-parry"
        ), None)
        options: list[ChoiceOption] = []
        if parry_owner is not None:
            pile = state.players[parry_owner].bank["kraken"]
            if not pile:
                self._remove_play_entry_to_discard(state, entry.entry_id)
                self._emit(
                    state,
                    "effect_targeted",
                    "格挡生效，但目标没有海怪；当前弯刀被弃掉",
                    {"suit": "sword", "traitOwnerId": parry_owner, "discardedCardId": entry.card_id},
                )
                return
            identifier = pile[0]
            options.append(self._option(
                state,
                f"格挡：从{self._player_name(room, parry_owner)}的海怪堆取出 {value_of(identifier)}",
                card_id=identifier,
                player_id=parry_owner,
                suit="kraken",
                causes_bust=self._would_bust(turn, identifier),
            ))
        else:
            unrestricted = actor_board.trait_id == "trait-swordsman"
            for target_id in state.turn_order:
                if target_id == actor_id or state.players[target_id].forfeited:
                    continue
                target = state.players[target_id]
                for suit in SUIT_ORDER:
                    if not target.bank[suit] or (not unrestricted and actor_board.bank[suit]):
                        continue
                    identifier = target.bank[suit][0]
                    options.append(self._option(
                        state,
                        f"从{self._player_name(room, target_id)}偷取{self._card_label(identifier)}",
                        card_id=identifier,
                        player_id=target_id,
                        suit=suit,
                        causes_bust=self._would_bust(turn, identifier),
                    ))
        if not options:
            self._emit(state, "effect_targeted", "弯刀没有合法目标", {"suit": "sword"})
            return
        self._set_choice(
            state,
            kind="sword-target",
            prompt="弯刀必须选择一张合法的对手银行顶牌",
            source_entry_id=entry.entry_id,
            options=options,
            context={"parryOwnerId": parry_owner},
        )

    def _resolve_hook_choice(
        self,
        room: ArcadeRoom,
        state: DeadMansDrawState,
        choice: PendingChoice,
        option: ChoiceOption,
    ) -> None:
        turn = self._turn(state)
        board = state.players[turn.actor_id]
        if option.suit is None or not board.bank[option.suit] or board.bank[option.suit][0] != option.card_id:
            raise GameRuleError("抓钩目标已经失效")
        identifier = board.bank[option.suit].pop(0)
        remaining = int(choice.context.get("remaining", 1))
        if remaining > 1:
            turn.effect_stack.append({
                "kind": "hook-next",
                "sourceEntryId": choice.source_entry_id,
                "remaining": remaining - 1,
            })
        self._emit(
            state,
            "effect_targeted",
            f"抓钩从银行带入{self._card_label(identifier)}",
            {"suit": "hook", "card": card_view(identifier), "from": "self_bank", "to": "play_lane"},
        )
        self._enter_card(
            room,
            state,
            identifier,
            source_zone="actor-bank",
            source_owner_id=turn.actor_id,
            parent_entry_id=choice.source_entry_id,
        )

    def _resolve_cannon_choice(
        self,
        state: DeadMansDrawState,
        choice: PendingChoice,
        option: ChoiceOption,
    ) -> None:
        if option.player_id is None or option.suit is None:
            raise GameRuleError("火炮目标无效")
        pile = state.players[option.player_id].bank[option.suit]
        if not pile or pile[0] != option.card_id:
            raise GameRuleError("火炮目标已经失效")
        quantity = choice.context.get("quantity", "one")
        removed = list(pile) if quantity == "entire" else [pile[0]]
        del pile[:len(removed)]
        destination = choice.context.get("destination", "discard")
        actor_id = self._turn(state).actor_id
        if destination == "actor-bank":
            self._bank_cards(state, actor_id, removed)
        else:
            state.discard_pile.extend(removed)
        self._emit(
            state,
            "effect_targeted",
            f"火炮移走 {len(removed)} 张{card(removed[0])['nameZh']}牌",
            {
                "suit": "cannon",
                "targetPlayerId": option.player_id,
                "cardIds": removed,
                "to": "self_bank" if destination == "actor-bank" else "discard_pile",
            },
        )

    def _resolve_map_choice(
        self,
        room: ArcadeRoom,
        state: DeadMansDrawState,
        choice: PendingChoice,
        option: ChoiceOption,
    ) -> None:
        turn = self._turn(state)
        if option.card_id is None or option.card_id not in turn.map_reveal_card_ids:
            raise GameRuleError("藏宝图目标已经失效")
        identifier = option.card_id
        remainder = [item for item in turn.map_reveal_card_ids if item != identifier]
        state.discard_pile.extend(remainder)
        self.rng.shuffle(state.discard_pile)
        turn.map_reveal_card_ids = []
        self._emit(
            state,
            "effect_targeted",
            f"藏宝图选择{self._card_label(identifier)}进入航道",
            {"suit": "map", "card": card_view(identifier), "from": "discard_pile", "to": "play_lane"},
        )
        self._enter_card(
            room,
            state,
            identifier,
            source_zone="discard",
            source_owner_id=None,
            parent_entry_id=choice.source_entry_id,
        )

    def _resolve_sword_choice(
        self,
        room: ArcadeRoom,
        state: DeadMansDrawState,
        choice: PendingChoice,
        option: ChoiceOption,
    ) -> None:
        if option.player_id is None or option.suit is None:
            raise GameRuleError("弯刀目标无效")
        pile = state.players[option.player_id].bank[option.suit]
        if not pile or pile[0] != option.card_id:
            raise GameRuleError("弯刀目标已经失效")
        identifier = pile.pop(0)
        self._emit(
            state,
            "effect_targeted",
            f"弯刀从{self._player_name(room, option.player_id)}偷取{self._card_label(identifier)}",
            {"suit": "sword", "targetPlayerId": option.player_id, "card": card_view(identifier)},
        )
        self._enter_card(
            room,
            state,
            identifier,
            source_zone="opponent-bank",
            source_owner_id=option.player_id,
            parent_entry_id=choice.source_entry_id,
        )

    def _resolve_plunderer_choice(
        self,
        room: ArcadeRoom,
        state: DeadMansDrawState,
        choice: PendingChoice,
        option: ChoiceOption,
    ) -> None:
        if option.player_id is None or option.player_id == self._turn(state).actor_id:
            raise GameRuleError("掠夺者目标无效")
        target = state.players[option.player_id]
        available = [identifier for pile in target.bank.values() for identifier in pile]
        self.rng.shuffle(available)
        count = min(int(choice.context.get("count", 0)), len(available))
        stolen = available[:count]
        for identifier in stolen:
            target.bank[suit_of(identifier)].remove(identifier)
        actor_id = self._turn(state).actor_id
        self._bank_cards(state, actor_id, stolen)
        self._emit(
            state,
            "key_chest_bonus",
            f"掠夺者从{self._player_name(room, option.player_id)}的银行随机取得 {len(stolen)} 张牌",
            {"playerId": actor_id, "targetPlayerId": option.player_id, "cardIds": stolen, "count": len(stolen)},
        )
        after = choice.context.get("after")
        if after == "finish_bust":
            self._finish_bust(room, state)
        else:
            self._end_turn(room, state)

    def _drain_effect_stack(
        self,
        room: ArcadeRoom,
        state: DeadMansDrawState,
    ) -> None:
        turn = state.turn
        while (
            room.phase == "playing"
            and turn is not None
            and turn.pending_choice is None
            and turn.busting_card_id is None
            and turn.effect_stack
        ):
            effect = turn.effect_stack.pop()
            if effect.get("kind") == "hook-next":
                if self._create_hook_choice(
                    state,
                    str(effect["sourceEntryId"]),
                    int(effect["remaining"]),
                ):
                    return

    def _resolve_bust(self, room: ArcadeRoom, state: DeadMansDrawState) -> None:
        turn = self._turn(state)
        busting = turn.busting_card_id
        if busting is None:
            raise RuntimeError("爆牌结算缺少触发牌")
        self._emit(
            state,
            "bust_detected",
            f"{card(busting)['nameZh']}花色重复，本回合爆牌",
            {"card": card_view(busting), "bustKey": suit_of(busting)},
        )
        protected = [entry for entry in turn.play_area if entry.protection_reasons]
        turn.play_area = [entry for entry in turn.play_area if not entry.protection_reasons]
        protected_cards = [entry.card_id for entry in protected]
        if protected_cards:
            self._bank_cards(state, turn.actor_id, protected_cards)
        self._emit(
            state,
            "protected_split",
            f"{len(protected_cards)} 张受保护牌进入当前玩家银行，其余牌按爆牌处理",
            {"playerId": turn.actor_id, "protectedCardIds": protected_cards, "count": len(protected_cards)},
        )
        turn.kraken_debt = 0
        turn.safe_harbor_slots = 0
        turn.oracle_peek_card_ids = []
        turn.map_reveal_card_ids = []
        turn.effect_stack = []
        if self._trigger_key_chest_bonus(
            state,
            turn.actor_id,
            protected_cards,
            after="finish_bust",
        ):
            return
        self._finish_bust(room, state)

    def _finish_bust(self, room: ArcadeRoom, state: DeadMansDrawState) -> None:
        turn = self._turn(state)
        cards_to_sink = [entry.card_id for entry in turn.play_area]
        if turn.busting_card_id is not None:
            cards_to_sink.append(turn.busting_card_id)
        turn.play_area = []
        turn.busting_card_id = None

        locker_owner_id = next((
            player_id
            for player_id, board in state.players.items()
            if not board.forfeited
            and board.trait_id == "trait-davy-jones-locker"
            and board.locker_target_id == turn.actor_id
        ), None)
        if locker_owner_id is not None:
            self._bank_cards(state, locker_owner_id, cards_to_sink)
            self._emit(
                state,
                "card_transferred",
                f"戴维·琼斯的魔柜收走 {len(cards_to_sink)} 张爆牌战利品",
                {"playerId": locker_owner_id, "cardIds": cards_to_sink, "from": "play_lane", "to": "opponent_bank"},
            )
        else:
            state.discard_pile.extend(cards_to_sink)
        self._end_turn(room, state)

    def _trigger_key_chest_bonus(
        self,
        state: DeadMansDrawState,
        actor_id: str,
        batch: list[str],
        *,
        after: str,
    ) -> bool:
        batch_suits = {suit_of(identifier) for identifier in batch}
        if not {"key", "chest"}.issubset(batch_suits):
            return False
        board = state.players[actor_id]
        count = len(batch)
        if board.trait_id == "trait-treasure-hunter":
            count *= 2
        if board.trait_id == "trait-plunderer":
            options = []
            for target_id in state.turn_order:
                if target_id == actor_id or state.players[target_id].forfeited:
                    continue
                target_count = sum(len(pile) for pile in state.players[target_id].bank.values())
                if target_count:
                    options.append(self._option(
                        state,
                        f"从玩家银行随机取得至多 {count} 张（现有 {target_count} 张）",
                        player_id=target_id,
                    ))
            if options:
                self._set_choice(
                    state,
                    kind="plunderer-target",
                    prompt="掠夺者必须选择一名对手作为钥匙宝箱奖励来源",
                    source_entry_id=None,
                    options=options,
                    context={"count": count, "after": after},
                )
                return True
            self._emit(
                state,
                "key_chest_bonus",
                "所有对手银行均为空，掠夺者没有获得奖励",
                {"playerId": actor_id, "cardIds": [], "count": 0},
            )
            return False

        self.rng.shuffle(state.discard_pile)
        bonus = list(state.discard_pile[:count])
        del state.discard_pile[:len(bonus)]
        self._bank_cards(state, actor_id, bonus)
        self._emit(
            state,
            "key_chest_bonus",
            f"钥匙与宝箱从弃牌堆带来 {len(bonus)} 张奖励牌",
            {"playerId": actor_id, "cardIds": bonus, "count": len(bonus)},
        )
        return False

    def _stabilize(self, room: ArcadeRoom, state: DeadMansDrawState) -> None:
        if room.phase != "playing" or state.turn is None:
            return
        turn = state.turn
        if turn.pending_choice is not None:
            state.phase = "effect_choice"
            return
        if turn.busting_card_id is not None:
            return
        self._drain_effect_stack(room, state)
        if turn.pending_choice is not None:
            state.phase = "effect_choice"
            return
        if not state.draw_pile and turn.kraken_debt > 0:
            turn.kraken_debt = 0
            self._emit(
                state,
                "kraken_debt_changed",
                "抽牌堆已空，无法完成的海怪要求按数字裁决清零",
                {"playerId": turn.actor_id, "count": 0},
            )
        if not state.draw_pile and not turn.play_area:
            self._finish_game(room, state, "draw-pile-exhausted")
            return
        state.phase = "turn"

    def _end_turn(self, room: ArcadeRoom, state: DeadMansDrawState) -> None:
        if not state.draw_pile:
            self._finish_game(room, state, "draw-pile-exhausted")
            return
        self._move_to_next_active(state)
        self._begin_turn(room, state)

    def _begin_turn(self, room: ArcadeRoom, state: DeadMansDrawState) -> None:
        active_ids = self._active_player_ids(state)
        if len(active_ids) <= 1:
            self._finish_game(room, state, "player-exit")
            return
        if not state.draw_pile:
            self._finish_game(room, state, "draw-pile-exhausted")
            return
        actor_id = state.turn_order[state.current_player_index]
        if state.players[actor_id].forfeited:
            self._move_to_next_active(state)
            actor_id = state.turn_order[state.current_player_index]
        state.turn_number += 1
        state.turn = TurnState(number=state.turn_number, actor_id=actor_id)
        state.phase = "turn"
        room.round_number = state.turn_number
        self._emit(
            state,
            "turn_changed",
            f"轮到{self._player_name(room, actor_id)}翻牌",
            {"playerId": actor_id, "turn": state.turn_number},
        )

    def _move_to_next_active(self, state: DeadMansDrawState) -> None:
        if not state.turn_order:
            return
        for _ in state.turn_order:
            state.current_player_index = (state.current_player_index + 1) % len(state.turn_order)
            if not state.players[state.turn_order[state.current_player_index]].forfeited:
                return

    def _abandon_current_turn(self, state: DeadMansDrawState) -> None:
        turn = state.turn
        if turn is None:
            return
        state.discard_pile.extend(entry.card_id for entry in turn.play_area)
        state.discard_pile.extend(turn.map_reveal_card_ids)
        if turn.busting_card_id is not None:
            state.discard_pile.append(turn.busting_card_id)
        state.turn = None

    def _finish_game(
        self,
        room: ArcadeRoom,
        state: DeadMansDrawState,
        reason: str,
    ) -> None:
        if room.phase == "finished":
            return
        rows, winner_ids = rank_scores(
            score_board(player_id, state.players[player_id])
            for player_id in state.turn_order
        )
        if not winner_ids:
            outcome = "shared-draw"
            summary = "所有玩家均已退出，本局无人获胜"
        else:
            winner_names = "、".join(self._player_name(room, player_id) for player_id in winner_ids)
            best = next(row for row in rows if row.player_id == winner_ids[0])
            if len(winner_ids) == 1:
                outcome = "win"
                summary = f"{winner_names} 以 {best.total} 分获胜"
            else:
                outcome = "shared-win"
                summary = f"{winner_names} 同为 {best.total} 分且牌数相同，共享胜利"
        state.result = GameResult(
            winner_ids=winner_ids,
            outcome=outcome,
            reason=reason,
            scores=rows,
            summary_zh=summary,
        )
        state.phase = "finished"
        state.turn = None
        for row in rows:
            self._emit(
                state,
                "score_resolved",
                f"{self._player_name(room, row.player_id)} 最终得到 {row.total} 分",
                {"playerId": row.player_id, "score": row.total, "winner": row.winner},
            )
        self._emit(
            state,
            "game_finished",
            summary,
            {"winnerPlayerIds": winner_ids, "reason": reason},
        )
        room.finish("draw" if not winner_ids else "treasure", winner_ids, summary)

    def view(self, room: ArcadeRoom, viewer: ArcadePlayer) -> dict[str, Any]:
        state: DeadMansDrawState = room.state
        viewer_board = state.players.get(viewer.id)
        turn = state.turn
        pending = turn.pending_choice if turn is not None else None
        is_actor = (
            room.phase == "playing"
            and viewer_board is not None
            and not viewer_board.forfeited
            and turn is not None
            and turn.actor_id == viewer.id
        )
        can_choose_trait = bool(
            state.phase == "trait_selection"
            and viewer_board is not None
            and viewer_board.trait_id is None
        )
        can_choose_locker = bool(
            state.phase == "trait_selection"
            and viewer_board is not None
            and viewer_board.trait_id == "trait-davy-jones-locker"
            and viewer_board.locker_target_id is None
        )
        can_resolve = bool(
            is_actor
            and state.phase == "effect_choice"
            and pending is not None
            and pending.actor_id == viewer.id
        )
        can_draw = bool(is_actor and state.phase == "turn" and state.draw_pile)
        can_collect = bool(
            is_actor
            and state.phase == "turn"
            and turn is not None
            and turn.play_area
            and turn.kraken_debt == 0
        )
        disabled_reason = None
        if is_actor and state.phase == "effect_choice":
            disabled_reason = "必须先解决当前花色能力"
        elif is_actor and turn is not None and turn.kraken_debt > 0:
            disabled_reason = f"海怪仍要求 {turn.kraken_debt} 张牌进入航道"

        public_players = []
        for room_player in room.players:
            board = state.players.get(room_player.id)
            if board is None:
                continue
            public_players.append({
                "id": room_player.id,
                "seat": room_player.seat,
                "displayName": room_player.name,
                "connected": room_player.connected,
                "isActive": bool(turn and turn.actor_id == room_player.id),
                "forfeited": board.forfeited,
                "traitId": board.trait_id if state.traits_revealed else None,
                "trait": trait_view(board.trait_id) if state.traits_revealed and board.trait_id else None,
                "selectingTrait": state.phase == "trait_selection" and board.trait_id is None,
                "lockerTargetId": board.locker_target_id if state.traits_revealed else None,
                "bank": [self._bank_stack_view(suit, board.bank[suit]) for suit in SUIT_ORDER],
                "liveScore": score_board(room_player.id, board).total,
                "bankCardCount": sum(len(pile) for pile in board.bank.values()),
            })

        discard_public = sorted(
            state.discard_pile,
            key=lambda identifier: (SUIT_ORDER.index(suit_of(identifier)), -value_of(identifier)),
        )
        result = self._result_view(state.result)
        return {
            "schemaVersion": 1,
            "modelVersion": state.model_version,
            "gameId": "dead-mans-draw",
            "revision": state.revision,
            "phase": state.phase,
            "rules": {
                "profileId": RULESET_ID,
                "profileNameZh": "实体基础版",
                "traitsEnabled": state.traits_enabled,
                "globalVariantId": None,
                "globalVariantNameZh": None,
            },
            "suitCatalog": [
                {
                    "id": suit_id,
                    "nameZh": suits()[suit_id]["nameZh"],
                    "nameEn": suits()[suit_id]["nameEn"],
                    "symbol": suits()[suit_id]["symbol"],
                    "icon": suits()[suit_id]["icon"],
                    "color": suits()[suit_id]["color"],
                    "summaryZh": suits()[suit_id]["ability"]["summaryZh"],
                }
                for suit_id in SUIT_ORDER
            ],
            "players": public_players,
            "currentPlayerId": turn.actor_id if turn else None,
            "turnNumber": turn.number if turn else state.turn_number,
            "drawCount": len(state.draw_pile),
            "discard": {
                "count": len(discard_public),
                "cardIds": discard_public,
                "cards": [card_view(identifier) for identifier in discard_public],
            },
            "playArea": [self._entry_view(entry) for entry in (turn.play_area if turn else [])],
            "turn": self._turn_view(turn, viewer.id, can_resolve),
            "self": {
                "playerId": viewer.id,
                "traitOffer": [trait_view(identifier) for identifier in (viewer_board.trait_offer if viewer_board else [])],
                "mustChooseLockerTarget": can_choose_locker,
            } if viewer_board is not None else None,
            "actions": {
                "canChooseTrait": can_choose_trait,
                "canChooseLockerTarget": can_choose_locker,
                "canDraw": can_draw,
                "canCollect": can_collect,
                "canResolveEffect": can_resolve,
                "canResign": bool(viewer_board and not viewer_board.forfeited and room.phase == "playing"),
                "disabledReasonZh": disabled_reason,
            },
            "result": result,
            "events": [
                {"seq": event.seq, "type": event.type, "textZh": event.text_zh, "data": event.data}
                for event in state.events
            ],
        }

    def player_result(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
    ) -> tuple[str, str, bool]:
        state: DeadMansDrawState = room.state
        board = state.players.get(player.id)
        if board is None:
            return "未参赛", "individual", False
        if board.forfeited:
            return "已退出", "individual", False
        won = player.id in room.winner_player_ids
        row = next((item for item in (state.result.scores if state.result else []) if item.player_id == player.id), None)
        if won and len(room.winner_player_ids) > 1:
            role = f"并列胜者 · {row.total if row else 0} 分"
        elif won:
            role = f"胜者 · {row.total if row else 0} 分"
        else:
            role = f"{row.total if row else score_board(player.id, board).total} 分"
        return role, "individual", won

    def record_state(self, room: ArcadeRoom) -> dict[str, Any]:
        state: DeadMansDrawState = room.state
        return {
            "version": "1.0.0",
            "rulesProfile": RULESET_ID,
            "traitsEnabled": state.traits_enabled,
            "turnsPlayed": state.turn_number,
            "winnerPlayerIds": list(room.winner_player_ids),
            "result": self._result_view(state.result),
            "players": [
                {
                    "playerId": player_id,
                    "traitId": state.players[player_id].trait_id,
                    "forfeited": state.players[player_id].forfeited,
                    "bankCardCount": sum(len(pile) for pile in state.players[player_id].bank.values()),
                }
                for player_id in state.turn_order
            ],
            "events": [
                {"seq": event.seq, "type": event.type, "textZh": event.text_zh}
                for event in state.events
            ],
        }

    def assert_invariants(self, state: DeadMansDrawState) -> None:
        if not state.players and not state.draw_pile and not state.discard_pile:
            return
        zones: list[str] = []
        zones.extend(state.draw_pile)
        zones.extend(state.discard_pile)
        zones.extend(state.removed_from_game)
        for board in state.players.values():
            for suit in SUIT_ORDER:
                pile = board.bank[suit]
                if pile != sorted(pile, key=value_of, reverse=True):
                    raise AssertionError(f"银行 {suit} 没有按点数降序排列")
                if any(suit_of(identifier) != suit for identifier in pile):
                    raise AssertionError(f"银行 {suit} 中出现错误花色")
                zones.extend(pile)
        if state.turn is not None:
            zones.extend(entry.card_id for entry in state.turn.play_area)
            zones.extend(state.turn.map_reveal_card_ids)
            if state.turn.busting_card_id is not None:
                zones.append(state.turn.busting_card_id)
            if state.turn.kraken_debt < 0:
                raise AssertionError("海怪债务不能为负数")
            if state.turn.pending_choice is not None and not state.turn.pending_choice.options:
                raise AssertionError("等待选择时必须存在合法选项")
        expected = set(all_card_ids())
        if len(zones) != len(expected):
            raise AssertionError(f"战利品牌数量不守恒：{len(zones)} != {len(expected)}")
        if len(set(zones)) != len(zones):
            raise AssertionError("同一张战利品牌同时出现在多个区域")
        if set(zones) != expected:
            missing = expected - set(zones)
            extra = set(zones) - expected
            raise AssertionError(f"战利品牌集合错误，缺失={missing}，额外={extra}")

    def _set_choice(
        self,
        state: DeadMansDrawState,
        *,
        kind: str,
        prompt: str,
        source_entry_id: str | None,
        options: list[ChoiceOption],
        context: dict[str, Any] | None = None,
    ) -> None:
        state.choice_counter += 1
        turn = self._turn(state)
        turn.pending_choice = PendingChoice(
            choice_id=f"choice-{state.choice_counter}",
            kind=kind,
            actor_id=turn.actor_id,
            prompt_zh=prompt,
            options=options,
            source_entry_id=source_entry_id,
            context=context or {},
        )
        state.phase = "effect_choice"

    def _option(
        self,
        state: DeadMansDrawState,
        label: str,
        *,
        card_id: str | None = None,
        player_id: str | None = None,
        suit: str | None = None,
        entry_id: str | None = None,
        causes_bust: bool = False,
    ) -> ChoiceOption:
        state.option_counter += 1
        return ChoiceOption(
            option_id=f"option-{state.option_counter}",
            label_zh=label,
            card_id=card_id,
            player_id=player_id,
            suit=suit,
            entry_id=entry_id,
            causes_immediate_bust=causes_bust,
        )

    def _bank_cards(self, state: DeadMansDrawState, player_id: str, identifiers: list[str]) -> None:
        board = state.players[player_id]
        for identifier in identifiers:
            board.bank[suit_of(identifier)].append(identifier)
        for suit in SUIT_ORDER:
            board.bank[suit].sort(key=value_of, reverse=True)

    def _remove_play_entry_to_discard(self, state: DeadMansDrawState, entry_id: str) -> None:
        turn = self._turn(state)
        entry = self._entry_by_id(turn, entry_id)
        if entry is None:
            return
        turn.play_area.remove(entry)
        state.discard_pile.append(entry.card_id)

    def _emit_kraken_debt(self, state: DeadMansDrawState, actor_id: str) -> None:
        count = self._turn(state).kraken_debt
        self._emit(
            state,
            "kraken_debt_changed",
            f"海怪仍要求 {count} 张牌成功进入航道",
            {"playerId": actor_id, "count": count, "suit": "kraken"},
        )

    def _emit(
        self,
        state: DeadMansDrawState,
        event_type: str,
        text: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        state.event_counter += 1
        state.events.append(PublicEvent(state.event_counter, event_type, text, data or {}))
        if len(state.events) > EVENT_LIMIT:
            state.events = state.events[-EVENT_LIMIT:]

    def _require_actor(self, state: DeadMansDrawState, player_id: str) -> TurnState:
        turn = state.turn
        if turn is None or turn.actor_id != player_id:
            raise GameRuleError("还没有轮到你")
        return turn

    @staticmethod
    def _turn(state: DeadMansDrawState) -> TurnState:
        if state.turn is None:
            raise RuntimeError("当前没有活动回合")
        return state.turn

    @staticmethod
    def _entry_by_id(turn: TurnState, entry_id: str) -> PlayEntry | None:
        return next((entry for entry in turn.play_area if entry.entry_id == entry_id), None)

    @staticmethod
    def _would_bust(turn: TurnState, identifier: str) -> bool:
        return any(suit_of(entry.card_id) == suit_of(identifier) for entry in turn.play_area)

    @staticmethod
    def _active_player_ids(state: DeadMansDrawState) -> list[str]:
        return [player_id for player_id in state.turn_order if not state.players[player_id].forfeited]

    @staticmethod
    def _card_label(identifier: str) -> str:
        item = card(identifier)
        return f"{item['nameZh']} {item['value']}"

    @staticmethod
    def _player_name(room: ArcadeRoom, player_id: str) -> str:
        try:
            return room.player(player_id).name
        except KeyError:
            return player_id

    @staticmethod
    def _bank_stack_view(suit: str, pile: list[str]) -> dict[str, Any]:
        subtotal = max((value_of(identifier) for identifier in pile), default=0)
        return {
            "suit": suit,
            "cardIds": list(pile),
            "cards": [card_view(identifier) for identifier in pile],
            "topValue": value_of(pile[0]) if pile else None,
            "count": len(pile),
            "subtotal": subtotal,
        }

    @staticmethod
    def _entry_view(entry: PlayEntry) -> dict[str, Any]:
        labels = {
            "anchor-prefix": "船锚前缀",
            "miser-hook": "守财奴·抓钩",
            "miser-child": "守财奴·带入牌",
            "safe-harbor-anchor": "安全港·船锚",
            "safe-harbor-next": "安全港·后续牌",
        }
        return {
            "entryId": entry.entry_id,
            "cardId": entry.card_id,
            "card": card_view(entry.card_id),
            "protected": bool(entry.protection_reasons),
            "protectionLabelsZh": [labels[item] for item in sorted(entry.protection_reasons)],
            "sourceLabelZh": {
                "draw": "抽牌堆",
                "discard": "弃牌堆",
                "actor-bank": "当前玩家银行",
                "opponent-bank": "对手银行",
            }.get(entry.source_zone, entry.source_zone),
        }

    def _turn_view(
        self,
        turn: TurnState | None,
        viewer_id: str,
        can_resolve: bool,
    ) -> dict[str, Any] | None:
        if turn is None:
            return None
        pending = turn.pending_choice
        pending_view = None
        if pending is not None:
            pending_view = {
                "choiceId": pending.choice_id if can_resolve else None,
                "kind": pending.kind,
                "actorId": pending.actor_id,
                "promptZh": pending.prompt_zh,
                "options": [
                    {
                        "optionId": option.option_id if can_resolve else None,
                        "labelZh": option.label_zh,
                        "cardId": option.card_id,
                        "card": card_view(option.card_id) if option.card_id else None,
                        "playerId": option.player_id,
                        "suit": option.suit,
                        "entryId": option.entry_id,
                        "causesImmediateBust": option.causes_immediate_bust,
                        "actionable": can_resolve,
                    }
                    for option in pending.options
                ],
            }
        return {
            "number": turn.number,
            "actorId": turn.actor_id,
            "krakenDebt": turn.kraken_debt,
            "bustKey": "suit",
            "presentBustKeys": [suit_of(entry.card_id) for entry in turn.play_area],
            "oraclePeekCardIds": list(turn.oracle_peek_card_ids),
            "oraclePeekCards": [card_view(identifier) for identifier in turn.oracle_peek_card_ids],
            "mapRevealCardIds": list(turn.map_reveal_card_ids),
            "mapRevealCards": [card_view(identifier) for identifier in turn.map_reveal_card_ids],
            "pendingChoice": pending_view,
        }

    @staticmethod
    def _score_row_view(row: ScoreRow) -> dict[str, Any]:
        return {
            "playerId": row.player_id,
            "suitSubtotals": dict(row.suit_subtotals),
            "cardAdjustments": row.card_adjustments,
            "variantAdjustment": 0,
            "total": row.total,
            "eligible": row.eligible,
            "bankCardCount": row.bank_card_count,
            "rank": row.rank,
            "winner": row.winner,
        }

    def _result_view(self, result: GameResult | None) -> dict[str, Any] | None:
        if result is None:
            return None
        return {
            "winnerIds": list(result.winner_ids),
            "outcome": result.outcome,
            "reason": result.reason,
            "scores": [self._score_row_view(row) for row in result.scores],
            "summaryZh": result.summary_zh,
        }
