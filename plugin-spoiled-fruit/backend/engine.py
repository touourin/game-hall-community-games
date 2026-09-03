from __future__ import annotations

import math
import random
from collections import Counter
from typing import Any, Iterable

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError

from .catalog import (
    CARD_DEFINITIONS,
    EFFECT_LABELS,
    NORMAL_DEFINITIONS,
    OLD_MAID_DEFINITIONS,
    definition_view,
)
from .state import Card, EffectItem, PlayerBoard, SpoiledFruitState


OPTIONAL_EFFECTS = {"peek_hand", "sweet_share", "shell_guard", "careful_stocking"}
AUTOMATIC_EFFECTS = {"harvest", "shake_basket", "sour_skip"}
MAX_PUBLIC_EVENTS = 48


class SpoiledFruitEngine:
    key = "plugin-spoiled-fruit"
    name = "坏果别留手！"
    min_players = 4
    max_players = 8

    def __init__(self, rng: random.Random | random.SystemRandom | None = None) -> None:
        self.rng = rng or random.SystemRandom()

    def initial_state(self) -> SpoiledFruitState:
        return SpoiledFruitState()

    def start(self, room: ArcadeRoom) -> None:
        players = [player for player in room.players if not player.left_room]
        if not self.min_players <= len(players) <= self.max_players:
            raise GameRuleError("坏果别留手需要 4–8 位玩家")

        if room.options.get("firstPlayer") == "host":
            first = next(
                (player for player in players if player.id == room.host_id),
                players[0],
            )
        else:
            first = self.rng.choice(players)
        first_index = players.index(first)
        ordered = players[first_index:] + players[:first_index]
        turn_order = [player.id for player in ordered]
        old_maid_count = math.floor(len(players) / 2)
        deck = self._new_deck(old_maid_count)
        self.rng.shuffle(deck)
        # Instance ids are assigned only after shuffling, so a public id never encodes
        # a fruit identity. Opponents still never receive these ids before the reveal.
        deck = [Card(f"card-{index + 1:03d}", card.catalog_id) for index, card in enumerate(deck)]
        boards = {
            player.id: PlayerBoard(player.id, seat_index)
            for seat_index, player in enumerate(ordered)
        }
        for index, card in enumerate(deck):
            boards[turn_order[index % len(turn_order)]].hand.append(card)

        state = SpoiledFruitState(
            first_player_id=first.id,
            turn_order=turn_order,
            boards=boards,
            current_player_id=first.id,
            old_maid_count=old_maid_count,
            total_card_count=len(deck),
        )
        room.state = state
        room.phase = "playing"

        removed = self._sweep_pairs(state, turn_order, setup=True)
        state.initial_removed_pair_count = len(removed)
        self._emit(
            state,
            "deal",
            f"{len(deck)} 张牌按固定顺序发完，加入 {old_maid_count} 张坏果老鳖",
            playerCount=len(players),
            cardCount=len(deck),
            oldMaidCount=old_maid_count,
        )
        self._emit(
            state,
            "initial_sweep",
            f"开局收走 {len(removed)} 对水果；这些对子不发动技能",
            pairCount=len(removed),
        )
        self._mark_empty_players_safe(room, state, reason="开局收果后空篮")
        if state.removed_pair_count == len(NORMAL_DEFINITIONS):
            self._finish(room, state)
            return
        state.current_player_id = self._first_active_from(state, first.id)
        if state.current_player_id is None:
            raise RuntimeError("开局后没有可行动玩家，但正常水果尚未全部离场")
        self._emit_turn(room, state)

    def act(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        action: str,
        payload: dict[str, Any],
    ) -> None:
        if room.phase != "playing":
            raise GameRuleError("当前牌局已经结束")
        state: SpoiledFruitState = room.state
        if action == "draw_card":
            self._act_draw(room, state, player, payload)
        elif action == "resolve_optional":
            self._act_optional(room, state, player, payload)
        elif action == "draw_extra":
            self._act_extra_draw(room, state, player, payload)
        elif action == "select_exchange_cards":
            self._act_exchange_selection(room, state, player, payload)
        elif action == "place_received":
            self._act_place_received(room, state, player, payload)
        else:
            raise GameRuleError("不支持这个坏果牌桌操作")

    def view(self, room: ArcadeRoom, viewer: ArcadePlayer) -> dict[str, Any]:
        state: SpoiledFruitState = room.state
        if not state.turn_order:
            return self._empty_view(room, viewer)
        reveal_all = room.phase == "finished"
        player_views = []
        for player_id in state.turn_order:
            board = state.boards[player_id]
            can_see = reveal_all or viewer.id == player_id
            slots = []
            for index, card in enumerate(board.hand):
                slots.append({
                    "slotId": f"{player_id}:{state.event_sequence}:{index}",
                    "index": index,
                    "card": self._card_view(card) if can_see else None,
                    "protected": card.instance_id == board.protected_card_id,
                    "selectable": self._slot_is_selectable(state, viewer.id, player_id, index),
                })
            player_views.append({
                "playerId": player_id,
                "seatIndex": board.seat_index,
                "handCount": len(board.hand),
                "handSlots": slots,
                "safe": board.safe,
                "pendingEmpty": board.pending_empty,
                "protectedSlotIndex": self._protected_index(board),
                "harvestPairIds": list(board.harvest_pair_ids),
                "harvestCount": len(board.harvest_pair_ids),
            })

        draw_source = self._draw_source(state, state.current_player_id) if state.pending_choice is None else None
        pending = state.pending_choice
        return {
            "schemaVersion": 1,
            "gameKey": "spoiled-fruit",
            "mode": "standard",
            "phase": self._phase(room, state),
            "sceneId": self._scene_id(room, state),
            "firstPlayerId": state.first_player_id,
            "currentPlayerId": state.current_player_id,
            "playerCount": len(state.turn_order),
            "oldMaidCount": state.old_maid_count,
            "totalCardCount": state.total_card_count,
            "removedPairCount": state.removed_pair_count,
            "initialRemovedPairCount": state.initial_removed_pair_count,
            "normalDrawCount": state.normal_draw_count,
            "effectTransferCount": state.effect_transfer_count,
            "players": player_views,
            "drawSourcePlayerId": draw_source,
            "effectQueue": [self._effect_view(item) for item in state.effect_queue],
            "activeEffect": self._effect_view(state.effect_queue[0]) if state.effect_queue else None,
            "skipCount": state.skip_count,
            "pendingChoice": self._public_pending(pending),
            "privateChoice": self._private_choice(state, viewer.id),
            "privatePeek": state.private_peeks.get(viewer.id),
            "legalActions": self._legal_actions(room, state, viewer.id),
            "events": list(state.events),
            "eventSequence": state.event_sequence,
            "safeOrder": list(state.safe_order),
            "finished": state.finished,
            "won": viewer.id in room.winner_player_ids,
            "result": room.winner if room.phase == "finished" else None,
        }

    def player_result(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
    ) -> tuple[str, str, bool]:
        state: SpoiledFruitState = room.state
        loser_ids = set((state.finished or {}).get("loserIds", []))
        role = "坏果持有者" if player.id in loser_ids else "安全离场"
        return role, "fruit_market", player.id in room.winner_player_ids

    def record_state(self, room: ArcadeRoom) -> dict[str, Any]:
        state: SpoiledFruitState = room.state
        return {
            "playerCount": len(state.turn_order),
            "oldMaidCount": state.old_maid_count,
            "totalCardCount": state.total_card_count,
            "removedPairCount": state.removed_pair_count,
            "initialRemovedPairCount": state.initial_removed_pair_count,
            "normalDrawCount": state.normal_draw_count,
            "effectTransferCount": state.effect_transfer_count,
            "safeOrder": list(state.safe_order),
            "finished": state.finished,
            "events": list(state.events),
        }

    def _act_draw(
        self,
        room: ArcadeRoom,
        state: SpoiledFruitState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        if state.pending_choice is not None or state.effect_queue:
            raise GameRuleError("请先完成当前果效结算")
        if state.current_player_id != player.id:
            raise GameRuleError("还没有轮到你摘果")
        source_id = self._draw_source(state, player.id)
        if source_id is None:
            raise GameRuleError("当前没有合法的暗抽来源")
        slot_index = self._read_index(payload, "slotIndex")
        self._draw_one(
            state,
            owner_id=player.id,
            source_id=source_id,
            slot_index=slot_index,
            event_type="draw",
            message_prefix="顺时暗抽",
        )
        self._sweep_pairs(state, [player.id])
        self._resolve_until_blocked(room, state)

    def _act_optional(
        self,
        room: ArcadeRoom,
        state: SpoiledFruitState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        pending = self._require_pending(state, "optional", player.id)
        item = self._queue_head(state, pending["queueId"])
        use = payload.get("use")
        if not isinstance(use, bool):
            raise GameRuleError("请选择发动或放弃这个可选果效")
        if not use:
            self._emit(
                state,
                "effect_declined",
                f"{self._player_name(room, player.id)} 放弃了{EFFECT_LABELS[item.effect_id]}",
                effectId=item.effect_id,
                playerId=player.id,
            )
            self._complete_head(state, item)
            self._resolve_until_blocked(room, state)
            return

        if item.effect_id == "peek_hand":
            self._use_peek(room, state, item, payload)
        elif item.effect_id == "sweet_share":
            self._use_sweet_share(room, state, item, payload)
        elif item.effect_id == "shell_guard":
            self._use_shell_guard(room, state, item, payload)
        elif item.effect_id == "careful_stocking":
            self._use_careful_stocking(room, state, item, payload)
        else:
            raise RuntimeError(f"unknown optional effect: {item.effect_id}")

    def _act_extra_draw(
        self,
        room: ArcadeRoom,
        state: SpoiledFruitState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        pending = self._require_pending(state, "extra_draw", player.id)
        item = self._queue_head(state, pending["queueId"])
        source_id = pending["sourcePlayerId"]
        current_source = self._draw_source(state, player.id)
        if current_source != source_id:
            raise GameRuleError("追加暗抽来源已经失效")
        slot_index = self._read_index(payload, "slotIndex")
        self._draw_one(
            state,
            owner_id=player.id,
            source_id=source_id,
            slot_index=slot_index,
            event_type="extra_draw",
            message_prefix="顺手再摘",
        )
        self._complete_head(state, item)
        self._sweep_pairs(state, [player.id])
        self._resolve_until_blocked(room, state)

    def _act_exchange_selection(
        self,
        room: ArcadeRoom,
        state: SpoiledFruitState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        pending = self._require_pending(state, "half_select", player.id)
        card_ids = payload.get("cardIds")
        count = pending["selectionCount"]
        if (
            not isinstance(card_ids, list)
            or len(card_ids) != count
            or any(not isinstance(card_id, str) for card_id in card_ids)
            or len(set(card_ids)) != len(card_ids)
        ):
            raise GameRuleError(f"必须秘密锁定恰好 {count} 张不同的可用手牌")
        board = state.boards[player.id]
        available_ids = {card.instance_id for card in self._available_cards(board)}
        if not set(card_ids).issubset(available_ids):
            raise GameRuleError("只能锁定自己未受保护的现有手牌")
        pending["selections"][player.id] = list(card_ids)
        self._emit(
            state,
            "exchange_lock",
            f"{self._player_name(room, player.id)} 已锁定 {count} 张交换牌",
            effectId="half_exchange",
            playerId=player.id,
            count=count,
        )
        required = pending["requiredPlayerIds"]
        if not all(player_id in pending["selections"] for player_id in required):
            return

        selected: dict[str, list[Card]] = {}
        for player_id in required:
            ids = pending["selections"][player_id]
            by_id = {card.instance_id: card for card in state.boards[player_id].hand}
            selected[player_id] = [by_id[card_id] for card_id in ids]
            selected_set = set(ids)
            state.boards[player_id].hand = [
                card for card in state.boards[player_id].hand
                if card.instance_id not in selected_set
            ]
        owner_id, target_id = required
        state.pending_choice = self._insert_pending(
            queue_id=pending["queueId"],
            effect_id="half_exchange",
            transfer_type="half_exchange",
            required_player_ids=required,
            received={owner_id: selected[target_id], target_id: selected[owner_id]},
        )

    def _act_place_received(
        self,
        room: ArcadeRoom,
        state: SpoiledFruitState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        pending = self._require_pending(state, "insert", player.id)
        incoming: list[Card] = pending["received"][player.id]
        ordered_ids = payload.get("orderedCardIds")
        insertion_indexes = payload.get("insertionIndexes")
        expected_ids = {card.instance_id for card in incoming}
        if (
            not isinstance(ordered_ids, list)
            or len(ordered_ids) != len(incoming)
            or any(not isinstance(card_id, str) for card_id in ordered_ids)
            or set(ordered_ids) != expected_ids
        ):
            raise GameRuleError("必须为全部收到的牌指定且仅指定一次相对顺序")
        if (
            not isinstance(insertion_indexes, list)
            or len(insertion_indexes) != len(incoming)
            or any(type(index) is not int for index in insertion_indexes)
        ):
            raise GameRuleError("每张收到的牌都需要一个合法插入槽")
        size = len(state.boards[player.id].hand)
        for offset, index in enumerate(insertion_indexes):
            if not 0 <= index <= size + offset:
                raise GameRuleError("插入槽超出当前手牌范围")
        pending["placements"][player.id] = {
            "orderedCardIds": list(ordered_ids),
            "insertionIndexes": list(insertion_indexes),
        }
        self._emit(
            state,
            "placement_ready",
            f"{self._player_name(room, player.id)} 已安排收到牌的位置",
            effectId=pending["effectId"],
            playerId=player.id,
            count=len(incoming),
        )
        required = pending["requiredPlayerIds"]
        if not all(player_id in pending["placements"] for player_id in required):
            return

        for player_id in self._ordered_subset(state, required):
            incoming_by_id = {
                card.instance_id: card for card in pending["received"][player_id]
            }
            placement = pending["placements"][player_id]
            hand = state.boards[player_id].hand
            for card_id, index in zip(
                placement["orderedCardIds"],
                placement["insertionIndexes"],
                strict=True,
            ):
                hand.insert(index, incoming_by_id[card_id])
        transfer_count = sum(len(cards) for cards in pending["received"].values())
        state.effect_transfer_count += transfer_count
        event_type = pending["transferType"]
        placements = {
            player_id: pending["placements"][player_id]["insertionIndexes"]
            for player_id in required
        }
        item = self._queue_head(state, pending["queueId"])
        self._emit(
            state,
            event_type,
            f"{EFFECT_LABELS[item.effect_id]}完成，{transfer_count} 张牌按所选插槽落位",
            effectId=item.effect_id,
            playerIds=list(required),
            transferCount=transfer_count,
            insertionIndexes=placements,
        )
        self._complete_head(state, item)
        self._normalize_shields(state, required)
        self._sweep_pairs(state, required)
        self._resolve_until_blocked(room, state)

    def _use_peek(
        self,
        room: ArcadeRoom,
        state: SpoiledFruitState,
        item: EffectItem,
        payload: dict[str, Any],
    ) -> None:
        target_id = payload.get("targetPlayerId")
        legal = self._peek_targets(state, item.owner_player_id)
        if target_id not in legal:
            raise GameRuleError("请选择一名仍有手牌的其他未安全玩家")
        target = state.boards[target_id]
        state.private_peeks[item.owner_player_id] = {
            "effectOwnerId": item.owner_player_id,
            "targetPlayerId": target_id,
            "orderedCards": [self._card_view(card) for card in target.hand],
            "protectedSlotIndex": self._protected_index(target),
            "capturedAtEventSequence": state.event_sequence + 1,
        }
        self._emit(
            state,
            "peek",
            f"{self._player_name(room, item.owner_player_id)} 查看了{self._player_name(room, target_id)}的完整固定牌序",
            effectId=item.effect_id,
            playerId=item.owner_player_id,
            targetPlayerId=target_id,
            count=len(target.hand),
        )
        self._complete_head(state, item)
        self._resolve_until_blocked(room, state)

    def _use_sweet_share(
        self,
        room: ArcadeRoom,
        state: SpoiledFruitState,
        item: EffectItem,
        payload: dict[str, Any],
    ) -> None:
        owner_id = item.owner_player_id
        target_id = payload.get("targetPlayerId")
        legal_targets = self._sweet_targets(state, owner_id)
        if target_id not in legal_targets:
            raise GameRuleError("甜蜜分享的目标必须有至少一张可用手牌")
        outgoing_id = payload.get("outgoingCardId")
        owner_board = state.boards[owner_id]
        owner_by_id = {card.instance_id: card for card in self._available_cards(owner_board)}
        if outgoing_id not in owner_by_id:
            raise GameRuleError("请选择自己一张未受保护的手牌送出")
        target_board = state.boards[target_id]
        return_index = self._read_index(payload, "returnSlotIndex")
        if not 0 <= return_index < len(target_board.hand):
            raise GameRuleError("回礼暗抽位置超出目标手牌范围")
        return_card = target_board.hand[return_index]
        if return_card.instance_id == target_board.protected_card_id:
            raise GameRuleError("受硬壳保护的牌不能作为回礼")
        outgoing = owner_by_id[outgoing_id]
        owner_board.hand.remove(outgoing)
        target_board.hand.remove(return_card)
        state.pending_choice = self._insert_pending(
            queue_id=item.queue_id,
            effect_id=item.effect_id,
            transfer_type="sweet_share",
            required_player_ids=[owner_id, target_id],
            received={owner_id: [return_card], target_id: [outgoing]},
        )
        self._emit(
            state,
            "sweet_lock",
            f"{self._player_name(room, owner_id)} 与{self._player_name(room, target_id)}同时交换了 1 张暗牌",
            effectId=item.effect_id,
            playerIds=[owner_id, target_id],
        )

    def _use_shell_guard(
        self,
        room: ArcadeRoom,
        state: SpoiledFruitState,
        item: EffectItem,
        payload: dict[str, Any],
    ) -> None:
        board = state.boards[item.owner_player_id]
        card_id = payload.get("cardId")
        if not isinstance(card_id, str) or card_id not in {
            card.instance_id for card in board.hand
        }:
            raise GameRuleError("请选择自己一张现有手牌进行保护")
        if len(board.hand) <= 1:
            self._emit(
                state,
                "protect",
                f"{self._player_name(room, item.owner_player_id)}只剩一张牌，硬壳保护自动失效",
                effectId=item.effect_id,
                playerId=item.owner_player_id,
                active=False,
            )
        else:
            board.protected_card_id = card_id
            board.shield_pair_id = item.pair_catalog_id
            self._emit(
                state,
                "protect",
                f"{self._player_name(room, item.owner_player_id)}给固定牌序中的一张牌加上硬壳",
                effectId=item.effect_id,
                playerId=item.owner_player_id,
                protectedSlotIndex=self._protected_index(board),
                active=True,
            )
        self._complete_head(state, item)
        self._resolve_until_blocked(room, state)

    def _use_careful_stocking(
        self,
        room: ArcadeRoom,
        state: SpoiledFruitState,
        item: EffectItem,
        payload: dict[str, Any],
    ) -> None:
        board = state.boards[item.owner_player_id]
        card_id = payload.get("cardId")
        by_id = {card.instance_id: card for card in board.hand}
        if card_id not in by_id:
            raise GameRuleError("只能移动自己的一张现有手牌")
        to_index = self._read_index(payload, "toIndex")
        if not 0 <= to_index < len(board.hand):
            raise GameRuleError("理货位置超出手牌范围")
        old_index = next(index for index, card in enumerate(board.hand) if card.instance_id == card_id)
        card = board.hand.pop(old_index)
        board.hand.insert(to_index, card)
        self._emit(
            state,
            "move",
            f"{self._player_name(room, item.owner_player_id)}用精心理货移动了一张牌",
            effectId=item.effect_id,
            playerId=item.owner_player_id,
            fromIndex=old_index,
            toIndex=to_index,
        )
        self._complete_head(state, item)
        self._resolve_until_blocked(room, state)

    def _resolve_until_blocked(self, room: ArcadeRoom, state: SpoiledFruitState) -> None:
        state.pending_choice = None
        while state.effect_queue:
            item = state.effect_queue[0]
            if item.effect_id in OPTIONAL_EFFECTS:
                state.pending_choice = {
                    "type": "optional",
                    "queueId": item.queue_id,
                    "effectId": item.effect_id,
                    "requiredPlayerIds": [item.owner_player_id],
                }
                return
            if item.effect_id == "half_exchange":
                owner = state.boards[item.owner_player_id]
                hand_count = len(owner.hand)
                targets = [
                    player_id for player_id in state.turn_order
                    if player_id != item.owner_player_id
                    and not state.boards[player_id].safe
                    and len(state.boards[player_id].hand) == hand_count
                ]
                if hand_count == 0 or not targets:
                    self._emit(
                        state,
                        "effect_noop",
                        f"{EFFECT_LABELS[item.effect_id]}没有同手牌数目标，本次作废",
                        effectId=item.effect_id,
                        playerId=item.owner_player_id,
                    )
                    self._complete_head(state, item)
                    continue
                target_id = self.rng.choice(targets)
                count = math.ceil(hand_count / 2)
                state.pending_choice = {
                    "type": "half_select",
                    "queueId": item.queue_id,
                    "effectId": item.effect_id,
                    "requiredPlayerIds": [item.owner_player_id, target_id],
                    "selectionCount": count,
                    "handCount": hand_count,
                    "selections": {},
                }
                self._emit(
                    state,
                    "half_target",
                    f"对半交换随机选中{self._player_name(room, target_id)}；双方各锁定 {count} 张",
                    effectId=item.effect_id,
                    playerIds=[item.owner_player_id, target_id],
                    selectionCount=count,
                )
                return
            if item.effect_id == "extra_pick":
                source_id = self._draw_source(state, item.owner_player_id)
                if source_id is None:
                    self._emit(
                        state,
                        "effect_noop",
                        "顺手再摘没有合法来源，本次作废",
                        effectId=item.effect_id,
                        playerId=item.owner_player_id,
                    )
                    self._complete_head(state, item)
                    continue
                state.pending_choice = {
                    "type": "extra_draw",
                    "queueId": item.queue_id,
                    "effectId": item.effect_id,
                    "requiredPlayerIds": [item.owner_player_id],
                    "sourcePlayerId": source_id,
                }
                return
            if item.effect_id == "market_conveyor":
                if self._begin_conveyor(room, state, item):
                    return
                continue
            if item.effect_id not in AUTOMATIC_EFFECTS:
                raise RuntimeError(f"unhandled fruit effect: {item.effect_id}")
            self._complete_head(state, item)
            if item.effect_id == "harvest":
                self._emit(
                    state,
                    "harvest",
                    f"{self._player_name(room, item.owner_player_id)}收下了一篮好水果",
                    effectId=item.effect_id,
                    playerId=item.owner_player_id,
                    pairCatalogId=item.pair_catalog_id,
                )
            elif item.effect_id == "shake_basket":
                hand = state.boards[item.owner_player_id].hand
                before = [card.instance_id for card in hand]
                self.rng.shuffle(hand)
                self._emit(
                    state,
                    "shuffle",
                    f"{self._player_name(room, item.owner_player_id)}的整篮手牌已由服务端随机洗序",
                    effectId=item.effect_id,
                    playerId=item.owner_player_id,
                    changed=before != [card.instance_id for card in hand],
                )
            elif item.effect_id == "sour_skip":
                state.skip_count += 1
                self._emit(
                    state,
                    "skip",
                    f"酸味累积：本回合交接时将额外跳过 {state.skip_count} 人",
                    effectId=item.effect_id,
                    playerId=item.owner_player_id,
                    skipCount=state.skip_count,
                )
        self._finish_or_advance(room, state)

    def _begin_conveyor(
        self,
        room: ArcadeRoom,
        state: SpoiledFruitState,
        item: EffectItem,
    ) -> bool:
        participants = [
            player_id for player_id in state.turn_order
            if not state.boards[player_id].safe and state.boards[player_id].hand
        ]
        if len(participants) < 2:
            self._emit(
                state,
                "effect_noop",
                "流水果摊不足两名有牌玩家，本次作废",
                effectId=item.effect_id,
            )
            self._complete_head(state, item)
            return False
        outgoing: dict[str, Card] = {}
        for player_id in participants:
            board = state.boards[player_id]
            card = board.hand.pop(0)
            outgoing[player_id] = card
            if card.instance_id == board.protected_card_id:
                self._clear_shield(board)
        received: dict[str, list[Card]] = {}
        for index, source_id in enumerate(participants):
            target_id = participants[(index + 1) % len(participants)]
            received[target_id] = [outgoing[source_id]]
        state.pending_choice = self._insert_pending(
            queue_id=item.queue_id,
            effect_id=item.effect_id,
            transfer_type="market_conveyor",
            required_player_ids=participants,
            received=received,
        )
        self._emit(
            state,
            "conveyor_start",
            f"流水果摊启动：{len(participants)} 名玩家同时传出最左牌",
            effectId=item.effect_id,
            playerIds=participants,
            count=len(participants),
        )
        return True

    def _finish_or_advance(self, room: ArcadeRoom, state: SpoiledFruitState) -> None:
        self._normalize_shields(state, state.turn_order)
        self._mark_empty_players_safe(room, state, reason="效果队列清空后空篮")
        if state.removed_pair_count == len(NORMAL_DEFINITIONS):
            self._finish(room, state)
            return
        if state.current_player_id is None:
            raise RuntimeError("进行中的牌局缺少当前玩家")
        next_id = state.current_player_id
        steps = 1 + state.skip_count
        state.skip_count = 0
        for _ in range(steps):
            candidate = self._next_active(state, next_id)
            if candidate is None:
                raise RuntimeError("正常水果尚未全部离场，但没有可行动玩家")
            next_id = candidate
        state.current_player_id = next_id
        self._emit_turn(room, state)

    def _finish(self, room: ArcadeRoom, state: SpoiledFruitState) -> None:
        if state.effect_queue or state.pending_choice is not None:
            raise RuntimeError("最后一对的果效尚未结算，不能结束牌局")
        remaining = [
            (player_id, card)
            for player_id in state.turn_order
            for card in state.boards[player_id].hand
        ]
        if len(remaining) != state.old_maid_count or any(
            CARD_DEFINITIONS[card.catalog_id].kind != "old_maid"
            for _, card in remaining
        ):
            raise RuntimeError("结算时的剩余手牌不是恰好全部坏果老鳖")
        holders: list[dict[str, Any]] = []
        loser_ids: list[str] = []
        for player_id in state.turn_order:
            cards = state.boards[player_id].hand
            if cards:
                loser_ids.append(player_id)
                holders.append({
                    "playerId": player_id,
                    "cards": [self._card_view(card) for card in cards],
                })
        winner_ids = [player_id for player_id in state.turn_order if player_id not in loser_ids]
        for player_id in winner_ids:
            board = state.boards[player_id]
            board.safe = True
            board.pending_empty = False
            if player_id not in state.safe_order:
                state.safe_order.append(player_id)
        state.current_player_id = None
        state.finished = {
            "winnerIds": winner_ids,
            "loserIds": loser_ids,
            "oldMaidHolders": holders,
        }
        loser_names = [self._player_name(room, player_id) for player_id in loser_ids]
        self._emit(
            state,
            "finish",
            f"坏果揭晓：{', '.join(loser_names)}仍持有老鳖",
            winnerIds=winner_ids,
            loserIds=loser_ids,
            holderCount=len(loser_ids),
        )
        room.finish(
            "fruit_market",
            winner_ids,
            f"全部 30 对水果离场；{', '.join(loser_names)}持有坏果老鳖",
        )

    def _sweep_pairs(
        self,
        state: SpoiledFruitState,
        owner_ids: Iterable[str],
        *,
        setup: bool = False,
    ) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        for owner_id in self._ordered_subset(state, owner_ids):
            board = state.boards[owner_id]
            counts = Counter(card.catalog_id for card in board.hand)
            catalog_ids = sorted(
                (
                    catalog_id for catalog_id, count in counts.items()
                    if count >= 2 and CARD_DEFINITIONS[catalog_id].kind == "normal"
                ),
                key=lambda catalog_id: CARD_DEFINITIONS[catalog_id].sort_index,
            )
            for catalog_id in catalog_ids:
                matching = [card for card in board.hand if card.catalog_id == catalog_id][:2]
                remove_ids = {card.instance_id for card in matching}
                board.hand = [card for card in board.hand if card.instance_id not in remove_ids]
                if board.protected_card_id in remove_ids:
                    self._clear_shield(board)
                board.harvest_pair_ids.append(catalog_id)
                state.removed_pair_count += 1
                pairs.append((owner_id, catalog_id))
        self._normalize_shields(state, owner_ids)
        if setup or not pairs:
            return pairs
        state.batch_sequence += 1
        batch_id = f"batch-{state.batch_sequence:03d}"
        for owner_id, catalog_id in pairs:
            definition = CARD_DEFINITIONS[catalog_id]
            state.queue_sequence += 1
            item = EffectItem(
                queue_id=f"effect-{state.queue_sequence:03d}",
                batch_id=batch_id,
                pair_catalog_id=catalog_id,
                effect_id=definition.effect_id,
                owner_player_id=owner_id,
            )
            state.effect_queue.append(item)
            self._emit(
                state,
                "pair",
                f"{CARD_DEFINITIONS[catalog_id].name_zh}成对离场，{EFFECT_LABELS[definition.effect_id]}进入队尾",
                playerId=owner_id,
                pairCatalogId=catalog_id,
                effectId=definition.effect_id,
                queueId=item.queue_id,
                batchId=batch_id,
            )
        return pairs

    def _draw_one(
        self,
        state: SpoiledFruitState,
        *,
        owner_id: str,
        source_id: str,
        slot_index: int,
        event_type: str,
        message_prefix: str,
    ) -> None:
        source = state.boards[source_id]
        if not 0 <= slot_index < len(source.hand):
            raise GameRuleError("暗抽位置超出来源玩家的固定牌序")
        card = source.hand[slot_index]
        if card.instance_id == source.protected_card_id:
            raise GameRuleError("这个位置正受硬壳保护，不能正常暗抽")
        source.hand.pop(slot_index)
        state.boards[owner_id].hand.append(card)
        state.normal_draw_count += 1
        # Any completed normal draw from a protected owner ends that owner's shield,
        # even when a different unprotected slot was selected.
        self._clear_shield(source)
        self._normalize_shields(state, [source_id, owner_id])
        self._emit(
            state,
            event_type,
            f"{message_prefix}完成；新牌固定追加到最右侧",
            playerId=owner_id,
            sourcePlayerId=source_id,
            sourceSlotIndex=slot_index,
            destinationIndex=len(state.boards[owner_id].hand) - 1,
        )

    def _mark_empty_players_safe(
        self,
        room: ArcadeRoom,
        state: SpoiledFruitState,
        *,
        reason: str,
    ) -> None:
        for player_id in state.turn_order:
            board = state.boards[player_id]
            board.pending_empty = not board.hand and not board.safe
        for player_id in state.turn_order:
            board = state.boards[player_id]
            if board.pending_empty:
                board.pending_empty = False
                board.safe = True
                if player_id not in state.safe_order:
                    state.safe_order.append(player_id)
                self._emit(
                    state,
                    "safe",
                    f"{self._player_name(room, player_id)}{reason}，安全离场",
                    playerId=player_id,
                )

    def _draw_source(self, state: SpoiledFruitState, owner_id: str | None) -> str | None:
        if owner_id is None or owner_id not in state.turn_order:
            return None
        start = state.turn_order.index(owner_id)
        for offset in range(1, len(state.turn_order)):
            candidate = state.turn_order[(start + offset) % len(state.turn_order)]
            board = state.boards[candidate]
            if board.safe or not board.hand:
                continue
            self._normalize_shields(state, [candidate])
            if self._available_cards(board):
                return candidate
        return None

    def _next_active(self, state: SpoiledFruitState, after_player_id: str) -> str | None:
        start = state.turn_order.index(after_player_id)
        for offset in range(1, len(state.turn_order) + 1):
            candidate = state.turn_order[(start + offset) % len(state.turn_order)]
            board = state.boards[candidate]
            if not board.safe and board.hand:
                return candidate
        return None

    def _first_active_from(self, state: SpoiledFruitState, player_id: str) -> str | None:
        start = state.turn_order.index(player_id)
        for offset in range(len(state.turn_order)):
            candidate = state.turn_order[(start + offset) % len(state.turn_order)]
            board = state.boards[candidate]
            if not board.safe and board.hand:
                return candidate
        return None

    def _available_cards(self, board: PlayerBoard) -> list[Card]:
        return [card for card in board.hand if card.instance_id != board.protected_card_id]

    def _peek_targets(self, state: SpoiledFruitState, owner_id: str) -> list[str]:
        return [
            player_id for player_id in state.turn_order
            if player_id != owner_id
            and not state.boards[player_id].safe
            and bool(state.boards[player_id].hand)
        ]

    def _sweet_targets(self, state: SpoiledFruitState, owner_id: str) -> list[str]:
        if not self._available_cards(state.boards[owner_id]):
            return []
        return [
            player_id for player_id in state.turn_order
            if player_id != owner_id
            and not state.boards[player_id].safe
            and bool(self._available_cards(state.boards[player_id]))
        ]

    def _insert_pending(
        self,
        *,
        queue_id: str,
        effect_id: str,
        transfer_type: str,
        required_player_ids: list[str],
        received: dict[str, list[Card]],
    ) -> dict[str, Any]:
        return {
            "type": "insert",
            "queueId": queue_id,
            "effectId": effect_id,
            "transferType": transfer_type,
            "requiredPlayerIds": list(required_player_ids),
            "received": received,
            "placements": {},
        }

    def _require_pending(
        self,
        state: SpoiledFruitState,
        pending_type: str,
        player_id: str,
    ) -> dict[str, Any]:
        pending = state.pending_choice
        if pending is None or pending.get("type") != pending_type:
            raise GameRuleError("当前没有这项待处理选择")
        if player_id not in pending.get("requiredPlayerIds", []):
            raise GameRuleError("这项私密选择不属于你")
        if player_id in pending.get("placements", {}):
            raise GameRuleError("你已经提交了本次插入位置")
        if player_id in pending.get("selections", {}):
            raise GameRuleError("你已经锁定了本次交换牌")
        return pending

    def _queue_head(self, state: SpoiledFruitState, queue_id: str) -> EffectItem:
        if not state.effect_queue or state.effect_queue[0].queue_id != queue_id:
            raise GameRuleError("果效队列已经变化，请刷新后重试")
        return state.effect_queue[0]

    def _complete_head(self, state: SpoiledFruitState, item: EffectItem) -> None:
        if not state.effect_queue or state.effect_queue[0].queue_id != item.queue_id:
            raise RuntimeError("attempted to complete a non-head effect")
        state.effect_queue.pop(0)
        state.pending_choice = None

    def _normalize_shields(
        self,
        state: SpoiledFruitState,
        player_ids: Iterable[str],
    ) -> None:
        for player_id in set(player_ids):
            board = state.boards[player_id]
            ids = {card.instance_id for card in board.hand}
            if board.protected_card_id not in ids or len(board.hand) <= 1:
                self._clear_shield(board)

    @staticmethod
    def _clear_shield(board: PlayerBoard) -> None:
        board.protected_card_id = None
        board.shield_pair_id = None

    def _ordered_subset(
        self,
        state: SpoiledFruitState,
        player_ids: Iterable[str],
    ) -> list[str]:
        wanted = set(player_ids)
        if not wanted:
            return []
        anchor = state.current_player_id or state.first_player_id or state.turn_order[0]
        start = state.turn_order.index(anchor)
        rotated = state.turn_order[start:] + state.turn_order[:start]
        return [player_id for player_id in rotated if player_id in wanted]

    def _slot_is_selectable(
        self,
        state: SpoiledFruitState,
        viewer_id: str,
        player_id: str,
        index: int,
    ) -> bool:
        board = state.boards[player_id]
        if board.hand[index].instance_id == board.protected_card_id:
            return False
        pending = state.pending_choice
        if pending is not None:
            if pending.get("type") == "extra_draw":
                return viewer_id in pending["requiredPlayerIds"] and player_id == pending["sourcePlayerId"]
            if pending.get("type") == "optional" and pending.get("effectId") == "sweet_share":
                return viewer_id in pending["requiredPlayerIds"] and viewer_id != player_id
            return False
        return (
            viewer_id == state.current_player_id
            and player_id == self._draw_source(state, viewer_id)
        )

    def _private_choice(self, state: SpoiledFruitState, viewer_id: str) -> dict[str, Any] | None:
        pending = state.pending_choice
        if pending is None or viewer_id not in pending.get("requiredPlayerIds", []):
            return None
        if (
            viewer_id in pending.get("placements", {})
            or viewer_id in pending.get("selections", {})
        ):
            return None
        result: dict[str, Any] = {
            "type": pending["type"],
            "queueId": pending["queueId"],
            "effectId": pending["effectId"],
            "effectLabelZh": EFFECT_LABELS[pending["effectId"]],
        }
        if pending["type"] == "optional":
            effect_id = pending["effectId"]
            if effect_id == "peek_hand":
                result["targetPlayerIds"] = self._peek_targets(state, viewer_id)
            elif effect_id == "sweet_share":
                result["targetPlayerIds"] = self._sweet_targets(state, viewer_id)
                result["availableCardIds"] = [
                    card.instance_id for card in self._available_cards(state.boards[viewer_id])
                ]
            elif effect_id == "shell_guard":
                result["availableCardIds"] = [card.instance_id for card in state.boards[viewer_id].hand]
            elif effect_id == "careful_stocking":
                result["availableCardIds"] = [card.instance_id for card in state.boards[viewer_id].hand]
        elif pending["type"] == "extra_draw":
            result["sourcePlayerId"] = pending["sourcePlayerId"]
        elif pending["type"] == "half_select":
            result.update({
                "selectionCount": pending["selectionCount"],
                "handCount": pending["handCount"],
                "otherPlayerId": next(
                    player_id for player_id in pending["requiredPlayerIds"]
                    if player_id != viewer_id
                ),
                "availableCardIds": [
                    card.instance_id for card in self._available_cards(state.boards[viewer_id])
                ],
            })
        elif pending["type"] == "insert":
            result.update({
                "transferType": pending["transferType"],
                "incomingCards": [
                    self._card_view(card) for card in pending["received"][viewer_id]
                ],
                "baseHandCount": len(state.boards[viewer_id].hand),
            })
        return result

    @staticmethod
    def _public_pending(pending: dict[str, Any] | None) -> dict[str, Any] | None:
        if pending is None:
            return None
        return {
            "type": pending["type"],
            "queueId": pending["queueId"],
            "effectId": pending["effectId"],
            "requiredPlayerIds": list(pending.get("requiredPlayerIds", [])),
            "completedPlayerIds": list(
                pending.get("placements", {}).keys()
                or pending.get("selections", {}).keys()
            ),
        }

    def _legal_actions(
        self,
        room: ArcadeRoom,
        state: SpoiledFruitState,
        viewer_id: str,
    ) -> list[str]:
        if room.phase != "playing":
            return []
        pending = state.pending_choice
        if pending is not None:
            if viewer_id not in pending.get("requiredPlayerIds", []):
                return []
            if viewer_id in pending.get("placements", {}) or viewer_id in pending.get("selections", {}):
                return []
            return {
                "optional": ["resolve_optional"],
                "extra_draw": ["draw_extra"],
                "half_select": ["select_exchange_cards"],
                "insert": ["place_received"],
            }[pending["type"]]
        if not state.effect_queue and state.current_player_id == viewer_id:
            return ["draw_card"]
        return []

    def _phase(self, room: ArcadeRoom, state: SpoiledFruitState) -> str:
        if room.phase == "finished":
            return "finished"
        if state.pending_choice:
            return "effect_insert" if state.pending_choice["type"] == "insert" else "effect_choice"
        if state.effect_queue:
            return "effect_queue"
        return "turn_draw"

    def _scene_id(self, room: ArcadeRoom, state: SpoiledFruitState) -> str:
        if room.phase == "finished":
            return "game.finished"
        if state.pending_choice:
            return "effect.private-exchange"
        if state.effect_queue:
            return "pair.effect-queue"
        return "turn.normal-draw"

    def _effect_view(self, item: EffectItem) -> dict[str, Any]:
        return {
            "queueId": item.queue_id,
            "batchId": item.batch_id,
            "pairCatalogId": item.pair_catalog_id,
            "effectId": item.effect_id,
            "effectLabelZh": EFFECT_LABELS[item.effect_id],
            "ownerPlayerId": item.owner_player_id,
        }

    def _card_view(self, card: Card) -> dict[str, Any]:
        return {"instanceId": card.instance_id, **definition_view(card.catalog_id)}

    def _emit_turn(self, room: ArcadeRoom, state: SpoiledFruitState) -> None:
        if state.current_player_id is None:
            return
        source_id = self._draw_source(state, state.current_player_id)
        self._emit(
            state,
            "turn",
            f"轮到{self._player_name(room, state.current_player_id)}，从{self._player_name(room, source_id) if source_id else '空果篮'}按序暗抽",
            playerId=state.current_player_id,
            sourcePlayerId=source_id,
        )

    @staticmethod
    def _player_name(room: ArcadeRoom, player_id: str | None) -> str:
        if player_id is None:
            return "无人"
        try:
            return room.player(player_id).name
        except (KeyError, StopIteration):
            return player_id

    @staticmethod
    def _read_index(payload: dict[str, Any], key: str) -> int:
        value = payload.get(key)
        if type(value) is not int:
            raise GameRuleError("位置必须是整数")
        return value

    @staticmethod
    def _protected_index(board: PlayerBoard) -> int | None:
        if board.protected_card_id is None:
            return None
        return next(
            (
                index for index, card in enumerate(board.hand)
                if card.instance_id == board.protected_card_id
            ),
            None,
        )

    def _emit(
        self,
        state: SpoiledFruitState,
        event_type: str,
        message: str,
        **details: Any,
    ) -> None:
        state.event_sequence += 1
        state.events.append({
            "sequence": state.event_sequence,
            "type": event_type,
            "message": message,
            **details,
        })
        if len(state.events) > MAX_PUBLIC_EVENTS:
            state.events = state.events[-MAX_PUBLIC_EVENTS:]

    def _new_deck(self, old_maid_count: int) -> list[Card]:
        if not 2 <= old_maid_count <= len(OLD_MAID_DEFINITIONS):
            raise RuntimeError("unsupported Old Maid count")
        deck = [
            Card("unassigned", definition.id)
            for definition in NORMAL_DEFINITIONS
            for _ in range(2)
        ]
        deck.extend(
            Card("unassigned", definition.id)
            for definition in OLD_MAID_DEFINITIONS[:old_maid_count]
        )
        return deck

    @staticmethod
    def _empty_view(room: ArcadeRoom, viewer: ArcadePlayer) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "gameKey": "spoiled-fruit",
            "mode": "standard",
            "phase": room.phase,
            "sceneId": "setup.deal",
            "firstPlayerId": None,
            "currentPlayerId": None,
            "playerCount": len(room.players),
            "oldMaidCount": len(room.players) // 2,
            "totalCardCount": 60 + len(room.players) // 2,
            "removedPairCount": 0,
            "initialRemovedPairCount": 0,
            "normalDrawCount": 0,
            "effectTransferCount": 0,
            "players": [],
            "drawSourcePlayerId": None,
            "effectQueue": [],
            "activeEffect": None,
            "skipCount": 0,
            "pendingChoice": None,
            "privateChoice": None,
            "privatePeek": None,
            "legalActions": [],
            "events": [],
            "eventSequence": 0,
            "safeOrder": [],
            "finished": None,
            "won": False,
            "result": None,
        }
