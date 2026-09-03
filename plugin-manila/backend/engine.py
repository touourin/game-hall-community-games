from __future__ import annotations

from dataclasses import asdict
from random import SystemRandom
from typing import Any

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError

from .catalog import (
    COMMODITIES,
    LANE_IDS,
    MODEL_VERSION,
    PLAYER_COLORS,
    PUNT_IDS,
    RULESET_ID,
    SPECIAL_POSITIONS,
    placement_schedule,
    share_commodity,
    share_id,
)
from .rules import (
    final_wealth,
    is_int,
    next_market_value,
    split_evenly,
    validate_cargo_assignments,
    validate_pilot_moves,
    validate_start_assignments,
)
from .state import (
    AuctionState,
    ManilaPlayerState,
    ManilaState,
    PuntState,
    WorkerPlacement,
    fresh_destination_slots,
)


EVENT_LIMIT = 80


class ManilaEngine:
    """Server-authoritative implementation of the 2005 Manila base rules."""

    key = "plugin-manila"
    name = "马尼拉"
    min_players = 3
    max_players = 5
    action_phases = {"playing"}

    def __init__(self, rng: Any | None = None) -> None:
        self.rng = rng or SystemRandom()

    def initial_state(self) -> ManilaState:
        return ManilaState()

    @staticmethod
    def can_start(room: ArcadeRoom, viewer: ArcadePlayer) -> bool:
        del viewer
        active = [player for player in room.players if not player.left_room]
        return 3 <= len(active) <= 5 and len(active) == len(room.players)

    def start(self, room: ArcadeRoom) -> None:
        seated = sorted(
            (player for player in room.players if not player.left_room),
            key=lambda player: player.seat,
        )
        if not self.min_players <= len(seated) <= self.max_players:
            raise GameRuleError("马尼拉需要 3–5 位玩家")
        if len(seated) != len(room.players):
            raise GameRuleError("请先移除已经离开房间的玩家")

        if room.options.get("firstPlayer") == "host":
            starter = next(
                (player for player in seated if player.id == room.host_id),
                seated[0],
            )
        else:
            starter = self.rng.choice(seated)
        starter_index = seated.index(starter)
        ordered = seated[starter_index:] + seated[:starter_index]

        initial_pool = [
            share_id(commodity_id, copy_index)
            for commodity_id in COMMODITIES
            for copy_index in range(1, 4)
        ]
        self.rng.shuffle(initial_pool)
        dealt: set[str] = set()
        players: dict[str, ManilaPlayerState] = {}
        worker_count = 4 if len(ordered) == 3 else 3
        for color_index, member in enumerate(ordered):
            cards = [initial_pool.pop(), initial_pool.pop()]
            dealt.update(cards)
            workers = [
                f"worker-{color_index + 1}-{index + 1}"
                for index in range(worker_count)
            ]
            players[member.id] = ManilaPlayerState(
                player_id=member.id,
                display_name=member.name,
                seat=member.seat,
                color_index=color_index,
                share_ids=cards,
                worker_ids=workers,
                available_worker_ids=list(workers),
            )

        all_shares = {
            share_id(commodity_id, copy_index)
            for commodity_id in COMMODITIES
            for copy_index in range(1, 6)
        }
        supply = {
            commodity_id: sorted(
                card_id
                for card_id in all_shares - dealt
                if share_commodity(card_id) == commodity_id
            )
            for commodity_id in COMMODITIES
        }
        state = ManilaState(
            model_version=MODEL_VERSION,
            stage="auction",
            voyage_number=1,
            turn_order=[member.id for member in ordered],
            players=players,
            market_values={commodity_id: 0 for commodity_id in COMMODITIES},
            share_commodities={card_id: share_commodity(card_id) for card_id in all_shares},
            share_supply=supply,
            auction=AuctionState(
                opener_id=starter.id,
                current_player_id=starter.id,
                active_player_ids=[member.id for member in ordered],
            ),
            current_player_id=starter.id,
        )
        room.state = state
        room.phase = "playing"
        room.round_number = 1
        self._emit(
            state,
            "game_start",
            f"{len(ordered)} 位玩家进入马尼拉港，{starter.name} 发起首航拍卖",
            {"starterId": starter.id, "playerCount": len(ordered)},
            animation={"kind": "deal", "cardCount": len(ordered) * 2},
        )

    def act(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        action: str,
        payload: dict[str, Any],
    ) -> None:
        self._member(room, player)
        if room.phase != "playing":
            raise GameRuleError("当前对局尚未开始或已经结束")
        state: ManilaState = room.state
        ledger = state.players.get(player.id)
        if ledger is None:
            raise GameRuleError("只有本局玩家可以操作")
        if action == "resign":
            self.manual_forfeit(room, player)
            return
        if ledger.forfeited:
            raise GameRuleError("退出后不能继续操作")
        if not isinstance(payload, dict):
            raise GameRuleError("操作参数必须是对象")
        self._require_voyage(state, payload)

        handlers = {
            "bid": self._bid,
            "pass_auction": self._pass_auction,
            "buy_share": self._buy_share,
            "skip_share": self._skip_share,
            "select_cargo": self._select_cargo,
            "set_start_positions": self._set_start_positions,
            "place_accomplice": self._place_accomplice,
            "pass_placement": self._pass_placement,
            "take_loan": self._take_loan,
            "repay_loan": self._repay_loan,
            "roll_dice": self._roll_dice,
            "choose_move_order": self._choose_move_order,
            "pirate_board": self._pirate_board,
            "pirate_stay": self._pirate_stay,
            "pilot_move": self._pilot_move,
            "pilot_pass": self._pilot_pass,
            "route_plundered_punt": self._route_plundered_punt,
            "next_voyage": self._next_voyage,
        }
        handler = handlers.get(action)
        if handler is None:
            raise GameRuleError("不支持这个马尼拉操作")
        handler(room, state, player, payload)

    # ------------------------------------------------------------------
    # Auction and harbor-master setup

    def _bid(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_stage(state, "auction")
        auction = self._require_auction_turn(state, player.id)
        amount = payload.get("amount")
        if not is_int(amount) or amount <= auction.current_bid:
            raise GameRuleError("报价必须是严格高于当前价的整数")
        if amount > self._payment_capacity(state.players[player.id]):
            raise GameRuleError("报价超过现金与可抵押份额的总支付能力")
        auction.current_bid = amount
        auction.leader_id = player.id
        self._emit(
            state,
            "auction_bid",
            f"{player.name} 报价 {amount} 比索",
            {"playerId": player.id, "amount": amount},
            animation={"kind": "auction_bid", "playerId": player.id, "amount": amount},
        )
        self._advance_auction(room, state, player.id)

    def _pass_auction(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        del payload
        self._require_stage(state, "auction")
        auction = self._require_auction_turn(state, player.id)
        if player.id not in auction.passed_player_ids:
            auction.passed_player_ids.append(player.id)
        self._emit(
            state,
            "auction_pass",
            f"{player.name} 退出本航行拍卖",
            {"playerId": player.id},
        )
        self._advance_auction(room, state, player.id)

    def _advance_auction(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        actor_id: str,
    ) -> None:
        auction = state.auction
        if auction is None:
            raise RuntimeError("auction state is missing")
        remaining = [
            player_id
            for player_id in auction.active_player_ids
            if player_id not in auction.passed_player_ids
            and not state.players[player_id].forfeited
        ]
        if auction.leader_id is not None:
            challengers = [
                player_id for player_id in remaining
                if player_id != auction.leader_id
            ]
            if not challengers:
                self._resolve_auction(room, state, auction.leader_id, auction.current_bid)
                return
            next_id = self._next_in_order(state.turn_order, actor_id, challengers)
        else:
            if not remaining:
                fallback = state.harbor_master_id or auction.opener_id
                if state.players[fallback].forfeited:
                    fallback = self._active_ids(state)[0]
                self._resolve_auction(room, state, fallback, 0)
                return
            next_id = self._next_in_order(state.turn_order, actor_id, remaining)
        auction.current_player_id = next_id
        state.current_player_id = next_id

    def _resolve_auction(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        winner_id: str,
        amount: int,
    ) -> None:
        winner = state.players[winner_id]
        if amount:
            self._pay_with_forced_loans(state, winner, amount, "港务长拍卖")
        state.harbor_master_id = winner_id
        state.current_player_id = winner_id
        state.stage = "harbor_share"
        state.auction = None
        wording = (
            f"{winner.display_name} 以 {amount} 比索成为港务长"
            if amount
            else f"无人报价，{winner.display_name} 以 0 比索担任港务长"
        )
        self._emit(
            state,
            "auction_won",
            wording,
            {"playerId": winner_id, "amount": amount},
            animation={"kind": "harbor_master", "playerId": winner_id},
        )

    def _buy_share(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        del room
        self._require_harbor_master(state, player.id, "harbor_share")
        commodity_id = payload.get("commodityId")
        if commodity_id not in COMMODITIES:
            raise GameRuleError("请选择有效的份额种类")
        supply = state.share_supply[commodity_id]
        if not supply:
            raise GameRuleError("这种货物的份额已经售罄")
        price = max(5, state.market_values[commodity_id])
        ledger = state.players[player.id]
        if self._payment_capacity(ledger) < price:
            raise GameRuleError("现金与可抵押份额不足以购买这张份额")
        self._pay_with_forced_loans(state, ledger, price, "购买份额")
        card_id = supply.pop(0)
        ledger.share_ids.append(card_id)
        state.stage = "harbor_load"
        self._emit(
            state,
            "share_bought",
            f"{player.name} 支付 {price} 比索购买一张份额",
            {"playerId": player.id, "price": price},
            animation={"kind": "share_deal", "playerId": player.id},
        )

    def _skip_share(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        del room, payload
        self._require_harbor_master(state, player.id, "harbor_share")
        state.stage = "harbor_load"
        self._emit(
            state,
            "share_skipped",
            f"{player.name} 跳过本航行的份额购买",
            {"playerId": player.id},
        )

    def _select_cargo(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        del room
        self._require_harbor_master(state, player.id, "harbor_load")
        try:
            assignments = validate_cargo_assignments(payload.get("assignments"))
        except ValueError as error:
            raise GameRuleError(str(error)) from error
        for punt_id, commodity_id in assignments.items():
            state.punts[punt_id].cargo_id = commodity_id
        state.stage = "harbor_launch"
        self._emit(
            state,
            "cargo_selected",
            f"{player.name} 完成三艘货船装载",
            {
                "playerId": player.id,
                "cargo": [
                    {"puntId": punt_id, "commodityId": assignments[punt_id]}
                    for punt_id in PUNT_IDS
                ],
            },
            animation={"kind": "cargo_load"},
        )

    def _set_start_positions(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_harbor_master(state, player.id, "harbor_launch")
        try:
            assignments = validate_start_assignments(payload.get("assignments"))
        except ValueError as error:
            raise GameRuleError(str(error)) from error
        if any(state.punts[punt_id].cargo_id is None for punt_id in PUNT_IDS):
            raise GameRuleError("必须先完成货物装船")
        for punt_id, (lane_id, position) in assignments.items():
            punt = state.punts[punt_id]
            punt.lane_id = lane_id
            punt.position = position
            punt.status = "sailing"
        state.schedule = list(placement_schedule(len(self._active_ids(state))))
        state.schedule_index = -1
        state.placement_round = 0
        state.movement_round = 0
        self._emit(
            state,
            "punts_launched",
            f"{player.name} 将三艘货船的起点总和设为 9",
            {
                "playerId": player.id,
                "starts": [
                    {
                        "puntId": punt_id,
                        "laneId": assignments[punt_id][0],
                        "position": assignments[punt_id][1],
                    }
                    for punt_id in PUNT_IDS
                ],
            },
            animation={"kind": "launch"},
        )
        self._advance_schedule(room, state)

    # ------------------------------------------------------------------
    # Worker placement and finance

    def _place_accomplice(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_stage(state, "placement")
        self._require_current(state, player.id)
        ledger = state.players[player.id]
        if ledger.passed_placement:
            raise GameRuleError("本航行 Pass 后不能重新加入部署")
        if not ledger.available_worker_ids:
            raise GameRuleError("没有可部署的助手")
        target_id = payload.get("targetId")
        if not isinstance(target_id, str):
            raise GameRuleError("请选择一个部署位置")
        options = {
            option["targetId"]: option
            for option in self._placement_options(state, player.id)
        }
        option = options.get(target_id)
        if option is None:
            raise GameRuleError("这个位置当前不可用")
        cost = option["cost"]
        capacity = self._payment_capacity(ledger)
        blind = capacity < cost
        if blind and not option.get("blindAllowed", False):
            raise GameRuleError("无法支付这个位置，且不满足免票部署条件")

        worker_id = ledger.available_worker_ids.pop(0)
        paid = min(ledger.cash, cost) if blind else cost
        if blind:
            ledger.cash -= paid
        elif paid:
            self._pay_with_forced_loans(state, ledger, paid, "部署助手")
        placement = WorkerPlacement(
            worker_id=worker_id,
            player_id=player.id,
            role="blind-passenger" if blind else "accomplice",
            slot_index=option.get("slotIndex"),
        )
        self._occupy_target(state, option, placement)
        if target_id == "insurance":
            ledger.cash += 10

        label = option["label"]
        payment_note = f"支付 {paid}" if paid else "免费"
        if blind:
            payment_note = f"免票并交出全部 {paid} 比索"
        self._emit(
            state,
            "worker_placed",
            f"{player.name} 在{label}部署助手（{payment_note}）",
            {
                "playerId": player.id,
                "workerId": worker_id,
                "targetId": target_id,
                "paid": paid,
                "blindPassenger": blind,
            },
            animation={
                "kind": "worker_move",
                "playerId": player.id,
                "workerId": worker_id,
                "targetId": target_id,
            },
        )
        self._advance_placement_turn(room, state)

    def _pass_placement(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        del payload
        self._require_stage(state, "placement")
        self._require_current(state, player.id)
        state.players[player.id].passed_placement = True
        self._emit(
            state,
            "placement_pass",
            f"{player.name} 退出本航行余下的部署",
            {"playerId": player.id},
        )
        self._advance_placement_turn(room, state)

    def _take_loan(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        del room
        card_id = payload.get("shareId")
        ledger = state.players[player.id]
        if card_id not in ledger.share_ids or card_id in ledger.mortgaged_share_ids:
            raise GameRuleError("只能抵押自己持有且尚未抵押的份额")
        ledger.mortgaged_share_ids.append(card_id)
        ledger.cash += 12
        self._emit(
            state,
            "loan_taken",
            f"{player.name} 抵押一张份额并取得 12 比索",
            {"playerId": player.id, "amount": 12},
            animation={"kind": "mortgage", "playerId": player.id},
        )

    def _repay_loan(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        del room
        card_id = payload.get("shareId")
        ledger = state.players[player.id]
        if card_id not in ledger.mortgaged_share_ids:
            raise GameRuleError("这张份额没有抵押")
        if ledger.cash < 15:
            raise GameRuleError("赎回份额需要 15 比索")
        ledger.cash -= 15
        ledger.mortgaged_share_ids.remove(card_id)
        self._emit(
            state,
            "loan_repaid",
            f"{player.name} 支付 15 比索赎回一张份额",
            {"playerId": player.id, "amount": 15},
            animation={"kind": "redeem", "playerId": player.id},
        )

    # ------------------------------------------------------------------
    # Sailing, pirates, pilots

    def _roll_dice(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        del room, payload
        self._require_harbor_master(state, player.id, "roll")
        sailing = [punt_id for punt_id in PUNT_IDS if state.punts[punt_id].status == "sailing"]
        if not sailing:
            raise GameRuleError("没有仍在航行的货船")
        state.die_results = {punt_id: self.rng.randint(1, 6) for punt_id in sailing}
        for punt_id, result in state.die_results.items():
            state.punts[punt_id].last_die = result
        state.stage = "move_order"
        state.current_player_id = player.id
        self._emit(
            state,
            "dice_rolled",
            f"{player.name} 掷出第 {state.movement_round} 轮航行骰",
            {
                "playerId": player.id,
                "round": state.movement_round,
                "dice": dict(state.die_results),
            },
            animation={
                "kind": "dice_roll",
                "round": state.movement_round,
                "dice": dict(state.die_results),
            },
        )

    def _choose_move_order(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_harbor_master(state, player.id, "move_order")
        punt_ids = payload.get("puntIds")
        expected = [punt_id for punt_id in PUNT_IDS if state.punts[punt_id].status == "sailing"]
        if (
            not isinstance(punt_ids, list)
            or len(punt_ids) != len(expected)
            or any(not isinstance(punt_id, str) for punt_id in punt_ids)
            or set(punt_ids) != set(expected)
        ):
            raise GameRuleError("移动顺序必须完整包含所有仍在航行的货船且不能重复")

        moves: list[dict[str, Any]] = []
        for punt_id in punt_ids:
            punt = state.punts[punt_id]
            before = punt.position
            result = state.die_results[punt_id]
            after = before + result
            if after > 13:
                self._dock_punt(state, punt, "port")
            else:
                punt.position = after
            moves.append(
                {
                    "puntId": punt_id,
                    "from": before,
                    "die": result,
                    "to": min(after, 14),
                    "destination": punt.destination_slot,
                }
            )
        state.last_move_order = list(punt_ids)
        state.die_results = {}
        self._emit(
            state,
            "punts_moved",
            f"港务长完成第 {state.movement_round} 轮货船移动",
            {"round": state.movement_round, "moves": moves},
            animation={"kind": "punt_move", "round": state.movement_round, "moves": moves},
        )

        if state.movement_round == 2:
            self._begin_pirate_boarding(room, state)
        elif state.movement_round == 3:
            self._finish_third_movement(room, state)
        else:
            self._advance_schedule(room, state)

    def _pirate_board(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_stage(state, "pirate_board")
        self._require_current(state, player.id)
        if not state.pirate_board_queue:
            raise GameRuleError("当前没有等待行动的海盗")
        worker_id = state.pirate_board_queue[0]
        placement = self._find_pirate_worker(state, worker_id)
        if placement is None or placement.player_id != player.id:
            raise GameRuleError("只有当前海盗可以决定是否登船")
        punt_id = payload.get("puntId")
        if punt_id not in self._pirate_board_targets(state):
            raise GameRuleError("基础规则只能登上恰停 13 且仍有空位的货船")
        punt = state.punts[punt_id]
        self._remove_pirate_worker(state, worker_id)
        placement.role = "pirate-boarded"
        placement.slot_index = len(punt.occupants)
        punt.occupants.append(placement)
        state.pirate_board_queue.pop(0)
        self._emit(
            state,
            "pirate_boarded",
            f"{player.name} 的海盗登上 {self._punt_label(punt)}",
            {"playerId": player.id, "workerId": worker_id, "puntId": punt_id},
            animation={"kind": "pirate_board", "workerId": worker_id, "puntId": punt_id},
        )
        self._prepare_next_pirate(room, state)

    def _pirate_stay(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        del payload
        self._require_stage(state, "pirate_board")
        self._require_current(state, player.id)
        if not state.pirate_board_queue:
            raise GameRuleError("当前没有等待行动的海盗")
        worker_id = state.pirate_board_queue[0]
        placement = self._find_pirate_worker(state, worker_id)
        if placement is None or placement.player_id != player.id:
            raise GameRuleError("只有当前海盗可以决定留守")
        state.pirate_board_queue.pop(0)
        self._emit(
            state,
            "pirate_stayed",
            f"{player.name} 的海盗留在海盗船",
            {"playerId": player.id, "workerId": worker_id},
        )
        self._prepare_next_pirate(room, state)

    def _pilot_move(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        if state.stage not in {"pilot_small", "pilot_large"}:
            raise GameRuleError("当前不是引航阶段")
        self._require_current(state, player.id)
        large = state.stage == "pilot_large"
        special_id = "pilot-large" if large else "pilot-small"
        occupant = state.special_workers[special_id]
        if occupant is None or occupant.player_id != player.id:
            raise GameRuleError("只有对应引航员可以移动货船")
        try:
            moves = validate_pilot_moves(payload.get("moves"), large=large)
        except ValueError as error:
            raise GameRuleError(str(error)) from error
        for punt_id, delta in moves:
            punt = state.punts[punt_id]
            if punt.status != "sailing":
                raise GameRuleError("引航员只能影响尚未抵港的货船")
            if punt.position + delta < 0:
                raise GameRuleError("引航不能把货船移到航线起点之前")

        animation_moves: list[dict[str, Any]] = []
        for punt_id, delta in moves:
            punt = state.punts[punt_id]
            before = punt.position
            after = before + delta
            if after > 13:
                self._dock_punt(state, punt, "port")
            else:
                punt.position = after
            animation_moves.append(
                {
                    "puntId": punt_id,
                    "from": before,
                    "delta": delta,
                    "to": min(after, 14),
                    "destination": punt.destination_slot,
                }
            )
        self._emit(
            state,
            "pilot_moved",
            f"{player.name} 使用{'大' if large else '小'}引航员调整货船",
            {"playerId": player.id, "large": large, "moves": animation_moves},
            animation={"kind": "pilot_move", "large": large, "moves": animation_moves},
        )
        self._advance_pilots(room, state, large)

    def _pilot_pass(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        del payload
        if state.stage not in {"pilot_small", "pilot_large"}:
            raise GameRuleError("当前不是引航阶段")
        self._require_current(state, player.id)
        large = state.stage == "pilot_large"
        special_id = "pilot-large" if large else "pilot-small"
        occupant = state.special_workers[special_id]
        if occupant is None or occupant.player_id != player.id:
            raise GameRuleError("只有对应引航员可以放弃能力")
        self._emit(
            state,
            "pilot_passed",
            f"{player.name} 放弃{'大' if large else '小'}引航能力",
            {"playerId": player.id, "large": large},
        )
        self._advance_pilots(room, state, large)

    def _route_plundered_punt(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_stage(state, "pirate_route")
        self._require_current(state, player.id)
        captain = state.special_workers["pirate-captain"]
        if captain is None or captain.player_id != player.id:
            raise GameRuleError("只有当前海盗船长可以决定被劫货船去向")
        if not state.pirate_route_queue:
            raise GameRuleError("没有等待分配去向的被劫货船")
        punt_id = payload.get("puntId")
        if punt_id != state.pirate_route_queue[0]:
            raise GameRuleError("必须按港务长本轮移动顺序处理被劫货船")
        destination = payload.get("destination")
        if destination not in {"port", "shipyard"}:
            raise GameRuleError("被劫货船只能送往港口或船坞")
        punt = state.punts[punt_id]
        self._dock_punt(state, punt, destination)
        state.pirate_route_queue.pop(0)
        self._emit(
            state,
            "pirate_routed",
            f"{player.name} 将被劫的{self._punt_label(punt)}送往"
            f"{'港口' if destination == 'port' else '船坞'}",
            {"playerId": player.id, "puntId": punt_id, "destination": destination},
            animation={"kind": "pirate_route", "puntId": punt_id, "destination": destination},
        )
        if state.pirate_route_queue:
            state.current_player_id = captain.player_id
        else:
            self._settle_voyage(room, state)

    # ------------------------------------------------------------------
    # Schedule progression

    def _advance_schedule(self, room: ArcadeRoom, state: ManilaState) -> None:
        while True:
            state.schedule_index += 1
            if state.schedule_index >= len(state.schedule):
                self._settle_voyage(room, state)
                return
            token = state.schedule[state.schedule_index]
            if token == "placement":
                state.placement_round += 1
                state.placement_cursor = 0
                if self._start_placement_round(state):
                    return
                continue
            if token == "movement":
                state.movement_round += 1
                if not any(
                    punt.status == "sailing" for punt in state.punts.values()
                ):
                    if state.movement_round == 3:
                        self._finish_third_movement(room, state)
                        return
                    continue
                state.stage = "roll"
                state.current_player_id = state.harbor_master_id
                return
            if token == "pilots":
                if self._start_pilot_sequence(state):
                    return
                continue
            raise RuntimeError(f"unknown Manila schedule token: {token}")

    def _start_placement_round(self, state: ManilaState) -> bool:
        order = self._harbor_order(state)
        for index, player_id in enumerate(order):
            if self._eligible_to_place(state, player_id):
                state.stage = "placement"
                state.placement_cursor = index
                state.current_player_id = player_id
                return True
        return False

    def _advance_placement_turn(self, room: ArcadeRoom, state: ManilaState) -> None:
        order = self._harbor_order(state)
        for index in range(state.placement_cursor + 1, len(order)):
            player_id = order[index]
            if self._eligible_to_place(state, player_id):
                state.placement_cursor = index
                state.current_player_id = player_id
                return
        self._advance_schedule(room, state)

    def _start_pilot_sequence(self, state: ManilaState) -> bool:
        small = state.special_workers["pilot-small"]
        if small is not None and not state.players[small.player_id].forfeited:
            state.stage = "pilot_small"
            state.current_player_id = small.player_id
            return True
        large = state.special_workers["pilot-large"]
        if large is not None and not state.players[large.player_id].forfeited:
            state.stage = "pilot_large"
            state.current_player_id = large.player_id
            return True
        return False

    def _advance_pilots(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        just_used_large: bool,
    ) -> None:
        if not just_used_large:
            large = state.special_workers["pilot-large"]
            if large is not None and not state.players[large.player_id].forfeited:
                state.stage = "pilot_large"
                state.current_player_id = large.player_id
                return
        self._advance_schedule(room, state)

    def _begin_pirate_boarding(self, room: ArcadeRoom, state: ManilaState) -> None:
        if not self._pirate_board_targets(state):
            self._advance_schedule(room, state)
            return
        queue = [
            placement.worker_id
            for placement in (
                state.special_workers["pirate-captain"],
                state.special_workers["pirate-crew"],
            )
            if placement is not None
            and not state.players[placement.player_id].forfeited
        ]
        state.pirate_board_queue = queue
        if not queue:
            self._advance_schedule(room, state)
            return
        state.stage = "pirate_board"
        self._prepare_next_pirate(room, state)

    def _prepare_next_pirate(self, room: ArcadeRoom, state: ManilaState) -> None:
        while state.pirate_board_queue:
            worker_id = state.pirate_board_queue[0]
            placement = self._find_pirate_worker(state, worker_id)
            if placement is None or state.players[placement.player_id].forfeited:
                state.pirate_board_queue.pop(0)
                continue
            if not self._pirate_board_targets(state):
                state.pirate_board_queue.clear()
                break
            state.stage = "pirate_board"
            state.current_player_id = placement.player_id
            return
        self._advance_schedule(room, state)

    def _finish_third_movement(self, room: ArcadeRoom, state: ManilaState) -> None:
        pirates = [
            placement
            for placement in (
                state.special_workers["pirate-captain"],
                state.special_workers["pirate-crew"],
            )
            if placement is not None
        ]
        order = state.last_move_order or list(PUNT_IDS)
        route_queue: list[str] = []
        for punt_id in order:
            punt = state.punts[punt_id]
            if punt.status != "sailing":
                continue
            if punt.position == 13 and pirates:
                punt.plundered = True
                punt.status = "plundered_waiting"
                punt.displaced_player_ids = [occupant.player_id for occupant in punt.occupants]
                punt.occupants.clear()
                route_queue.append(punt_id)
            elif punt.position == 13:
                self._dock_punt(state, punt, "port")
            else:
                self._dock_punt(state, punt, "shipyard")
        state.pirate_route_queue = route_queue
        if route_queue:
            captain = state.special_workers["pirate-captain"]
            if captain is None:
                # Defensive fallback: a remaining crew is always promoted to captain.
                for punt_id in list(route_queue):
                    self._dock_punt(state, state.punts[punt_id], "port")
                state.pirate_route_queue.clear()
                self._settle_voyage(room, state)
                return
            state.stage = "pirate_route"
            state.current_player_id = captain.player_id
            self._emit(
                state,
                "pirate_plunder",
                f"海盗劫掠 {len(route_queue)} 艘恰停 13 的货船",
                {"puntIds": list(route_queue)},
                animation={"kind": "pirate_plunder", "puntIds": list(route_queue)},
            )
            return
        self._settle_voyage(room, state)

    # ------------------------------------------------------------------
    # Atomic settlement and next voyage

    def _settle_voyage(self, room: ArcadeRoom, state: ManilaState) -> None:
        if state.last_settlement and state.last_settlement.get("voyageNumber") == state.voyage_number:
            raise RuntimeError("voyage settlement attempted twice")
        before_cash = {player_id: ledger.cash for player_id, ledger in state.players.items()}
        cash = dict(before_cash)
        mortgages = {
            player_id: list(ledger.mortgaged_share_ids)
            for player_id, ledger in state.players.items()
        }
        entries: list[dict[str, Any]] = []

        def entry(
            from_id: str,
            to_id: str,
            amount: int,
            reason: str,
            *,
            punt_id: str | None = None,
            slot_id: str | None = None,
            bank_coverage: int = 0,
            payer_amount: int | None = None,
            self_insurance: bool = False,
        ) -> None:
            entries.append(
                {
                    "entryId": f"V{state.voyage_number}-E{len(entries) + 1:02d}",
                    "fromId": from_id,
                    "toId": to_id,
                    "amount": amount,
                    "reason": reason,
                    "puntId": punt_id,
                    "slotId": slot_id,
                    "bankCoverage": bank_coverage,
                    "payerAmount": amount if payer_amount is None else payer_amount,
                    "selfInsurance": self_insurance,
                }
            )

        def bank_pay(player_id: str, amount: int, reason: str, **metadata: Any) -> None:
            if amount <= 0:
                return
            cash[player_id] += amount
            entry("bank", player_id, amount, reason, **metadata)

        pirate_workers = [
            placement
            for placement in (
                state.special_workers["pirate-captain"],
                state.special_workers["pirate-crew"],
            )
            if placement is not None
            and not state.players[placement.player_id].forfeited
        ]

        for punt_id in PUNT_IDS:
            punt = state.punts[punt_id]
            if punt.cargo_id is None:
                continue
            profit = COMMODITIES[punt.cargo_id]["profit"]
            if punt.plundered:
                if pirate_workers:
                    share = split_evenly(profit, len(pirate_workers))
                    for pirate in pirate_workers:
                        bank_pay(
                            pirate.player_id,
                            share,
                            "pirate_profit",
                            punt_id=punt_id,
                        )
                continue
            if punt.status == "port" and punt.occupants:
                eligible = [
                    occupant for occupant in punt.occupants
                    if not state.players[occupant.player_id].forfeited
                ]
                if eligible:
                    share = split_evenly(profit, len(eligible))
                    for occupant in eligible:
                        bank_pay(
                            occupant.player_id,
                            share,
                            "cargo_profit",
                            punt_id=punt_id,
                        )

        for slot in state.port_slots:
            if slot.punt_id and slot.bettor and not state.players[slot.bettor.player_id].forfeited:
                bank_pay(
                    slot.bettor.player_id,
                    slot.payout,
                    "port_bet",
                    punt_id=slot.punt_id,
                    slot_id=f"port-{slot.id}",
                )

        insurer = state.special_workers["insurance"]
        insurer_id = (
            insurer.player_id
            if insurer is not None and not state.players[insurer.player_id].forfeited
            else None
        )

        def force_settlement_funds(player_id: str, required: int) -> None:
            ledger = state.players[player_id]
            available = sorted(
                card_id
                for card_id in ledger.share_ids
                if card_id not in mortgages[player_id]
            )
            while cash[player_id] < required and available:
                card_id = available.pop(0)
                mortgages[player_id].append(card_id)
                cash[player_id] += 12
                entry("bank", player_id, 12, "forced_mortgage")

        for slot in state.shipyard_slots:
            if not slot.punt_id:
                continue
            recipient_id = (
                slot.bettor.player_id
                if slot.bettor is not None
                and not state.players[slot.bettor.player_id].forfeited
                else "bank"
            )
            slot_id = f"shipyard-{slot.id}"
            if insurer_id is None:
                if recipient_id != "bank":
                    bank_pay(
                        recipient_id,
                        slot.payout,
                        "shipyard_bet",
                        punt_id=slot.punt_id,
                        slot_id=slot_id,
                    )
                else:
                    entry(
                        "bank",
                        "bank",
                        slot.payout,
                        "shipyard_unclaimed",
                        punt_id=slot.punt_id,
                        slot_id=slot_id,
                    )
                continue

            if recipient_id == insurer_id:
                entry(
                    insurer_id,
                    insurer_id,
                    slot.payout,
                    "self_insurance",
                    punt_id=slot.punt_id,
                    slot_id=slot_id,
                    payer_amount=0,
                    self_insurance=True,
                )
                continue

            force_settlement_funds(insurer_id, slot.payout)
            paid = min(cash[insurer_id], slot.payout)
            coverage = slot.payout - paid
            cash[insurer_id] -= paid
            if recipient_id != "bank":
                cash[recipient_id] += slot.payout
            entry(
                insurer_id,
                recipient_id,
                slot.payout,
                "insured_repair",
                punt_id=slot.punt_id,
                slot_id=slot_id,
                bank_coverage=coverage,
                payer_amount=paid,
            )

        delivered = sorted(
            {
                punt.cargo_id
                for punt in state.punts.values()
                if punt.status == "port" and punt.cargo_id is not None
            }
        )
        before_market = dict(state.market_values)
        after_market = dict(before_market)
        for commodity_id in delivered:
            after_market[commodity_id] = next_market_value(after_market[commodity_id])

        # No balance can become negative, and mortgage identities remain private.
        if any(amount < 0 for amount in cash.values()):
            raise RuntimeError("settlement would create a negative player balance")
        for player_id, ledger in state.players.items():
            if not set(mortgages[player_id]).issubset(ledger.share_ids):
                raise RuntimeError("settlement mortgage is not owned by player")

        for player_id, ledger in state.players.items():
            ledger.cash = cash[player_id]
            ledger.mortgaged_share_ids = mortgages[player_id]
        state.market_values = after_market
        settlement = {
            "voyageNumber": state.voyage_number,
            "entries": entries,
            "cashBefore": before_cash,
            "cashAfter": cash,
            "marketBefore": before_market,
            "marketAfter": after_market,
            "deliveredCommodityIds": delivered,
            "damagedPuntIds": [
                punt.id for punt in state.punts.values() if punt.status == "shipyard"
            ],
            "plunderedPuntIds": [
                punt.id for punt in state.punts.values() if punt.plundered
            ],
        }
        state.last_settlement = settlement
        self._emit(
            state,
            "voyage_settled",
            f"第 {state.voyage_number} 次航行完成：{len(delivered)} 种货物抵港",
            {
                "voyageNumber": state.voyage_number,
                "deliveredCommodityIds": delivered,
                "entryCount": len(entries),
            },
            animation={"kind": "settlement", "entryCount": len(entries)},
        )

        if any(value == 30 for value in after_market.values()):
            self._finish_game(room, state)
            return
        state.stage = "voyage_summary"
        state.current_player_id = state.harbor_master_id

    def _next_voyage(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        del payload
        self._require_harbor_master(state, player.id, "voyage_summary")
        previous_harbor_master = state.harbor_master_id
        if previous_harbor_master is None:
            raise RuntimeError("harbor master missing between voyages")
        for ledger in state.players.values():
            ledger.available_worker_ids = (
                [] if ledger.forfeited else list(ledger.worker_ids)
            )
            ledger.passed_placement = False
        state.voyage_number += 1
        room.round_number = state.voyage_number
        state.punts = {punt_id: PuntState(punt_id) for punt_id in PUNT_IDS}
        state.port_slots, state.shipyard_slots = fresh_destination_slots()
        state.special_workers = {
            "pirate-captain": None,
            "pirate-crew": None,
            "pilot-small": None,
            "pilot-large": None,
            "insurance": None,
        }
        state.schedule = []
        state.schedule_index = -1
        state.placement_round = 0
        state.placement_cursor = 0
        state.movement_round = 0
        state.die_results = {}
        state.last_move_order = []
        state.pirate_board_queue = []
        state.pirate_route_queue = []
        state.last_settlement = None
        state.stage = "auction"
        active = self._active_ids(state)
        opener = previous_harbor_master if previous_harbor_master in active else active[0]
        state.auction = AuctionState(
            opener_id=opener,
            current_player_id=opener,
            active_player_ids=list(active),
        )
        state.current_player_id = opener
        self._emit(
            state,
            "voyage_started",
            f"第 {state.voyage_number} 次航行开始，上一任港务长发起拍卖",
            {"voyageNumber": state.voyage_number, "openerId": opener},
            animation={"kind": "new_voyage", "voyageNumber": state.voyage_number},
        )

    def _finish_game(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        reason_prefix: str = "货物价值达到 30",
    ) -> None:
        active = self._active_ids(state)
        for player_id in active:
            ledger = state.players[player_id]
            ledger.final_wealth = final_wealth(
                ledger.cash,
                ledger.share_ids,
                ledger.mortgaged_share_ids,
                state.market_values,
            )
        active.sort(
            key=lambda player_id: (
                -(state.players[player_id].final_wealth or 0),
                state.players[player_id].seat,
            )
        )
        forfeited = [
            player_id for player_id in state.turn_order
            if state.players[player_id].forfeited
        ]
        state.rankings = active + forfeited
        best = state.players[active[0]].final_wealth if active else 0
        winners = [
            player_id for player_id in active
            if state.players[player_id].final_wealth == best
        ]
        winner_names = "、".join(state.players[player_id].display_name for player_id in winners)
        state.stage = "finished"
        state.current_player_id = None
        state.result_reason = f"{reason_prefix}；{winner_names} 以 {best} 比索财富获胜"
        room.finish("最高财富", winners, state.result_reason)

    # ------------------------------------------------------------------
    # Public interface and forfeit recovery

    def view(self, room: ArcadeRoom, viewer: ArcadePlayer) -> dict[str, Any]:
        from .projection import build_view

        state: ManilaState = room.state
        legal = self._legal_actions(room, state, viewer.id)
        return build_view(state, room, viewer.id, legal)

    def player_result(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
    ) -> tuple[str, str, bool]:
        state: ManilaState = room.state
        ledger = state.players.get(player.id)
        if ledger is None:
            return "旁观者", "observer", False
        if ledger.forfeited:
            return "已退出", "forfeited", False
        wealth = ledger.final_wealth
        label = f"最终财富 {wealth}" if wealth is not None else f"现金 {ledger.cash}"
        return label, "merchant", player.id in room.winner_player_ids

    def record_state(self, room: ArcadeRoom) -> dict[str, Any]:
        return asdict(room.state)

    def manual_forfeit(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        self._member(room, player)
        if room.phase != "playing":
            return False
        state: ManilaState = room.state
        ledger = state.players.get(player.id)
        if ledger is None or ledger.forfeited:
            return False
        ledger.forfeited = True
        ledger.available_worker_ids.clear()
        self._remove_player_workers(state, player.id)
        self._emit(
            state,
            "player_forfeited",
            f"{player.name} 已退出本局",
            {"playerId": player.id},
        )
        active = self._active_ids(state)
        if len(active) <= 1:
            # Early termination uses the same wealth formula and current market.
            self._finish_game(room, state, "仅剩一位仍在牌局中的玩家")
            return True
        if state.harbor_master_id == player.id:
            state.harbor_master_id = self._next_in_order(state.turn_order, player.id, active)
        if state.stage == "auction" and state.auction is not None:
            auction = state.auction
            was_current = auction.current_player_id == player.id
            if player.id not in auction.passed_player_ids:
                auction.passed_player_ids.append(player.id)
            if auction.leader_id == player.id:
                auction.leader_id = None
                auction.current_bid = 0
                was_current = True
            remaining = [
                candidate
                for candidate in auction.active_player_ids
                if candidate not in auction.passed_player_ids
                and not state.players[candidate].forfeited
            ]
            only_leader_remains = (
                auction.leader_id is not None
                and remaining == [auction.leader_id]
            )
            if was_current or not remaining or only_leader_remains:
                self._advance_auction(room, state, player.id)
        elif state.current_player_id == player.id:
            if state.stage == "placement":
                self._advance_placement_turn(room, state)
            elif state.stage == "pirate_board":
                state.pirate_board_queue = [
                    worker_id for worker_id in state.pirate_board_queue
                    if self._find_pirate_worker(state, worker_id) is not None
                ]
                self._prepare_next_pirate(room, state)
            elif state.stage in {"pilot_small", "pilot_large"}:
                self._advance_pilots(room, state, state.stage == "pilot_large")
            elif state.stage == "pirate_route":
                captain = state.special_workers["pirate-captain"]
                if captain:
                    state.current_player_id = captain.player_id
                else:
                    for punt_id in list(state.pirate_route_queue):
                        self._dock_punt(state, state.punts[punt_id], "port")
                    state.pirate_route_queue.clear()
                    self._settle_voyage(room, state)
            else:
                state.current_player_id = state.harbor_master_id
        return True

    def disconnect_timeout(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        return self.manual_forfeit(room, player)

    # ------------------------------------------------------------------
    # Legal actions and state helpers

    def _legal_actions(
        self,
        room: ArcadeRoom,
        state: ManilaState,
        player_id: str,
    ) -> dict[str, Any]:
        ledger = state.players.get(player_id)
        if ledger is None or ledger.forfeited or room.phase != "playing":
            return {}
        legal: dict[str, Any] = {
            "canResign": True,
            "loanableShareIds": [
                card_id for card_id in ledger.share_ids
                if card_id not in ledger.mortgaged_share_ids
            ],
            "repayableShareIds": (
                list(ledger.mortgaged_share_ids) if ledger.cash >= 15 else []
            ),
        }
        if state.stage == "auction" and state.current_player_id == player_id:
            auction = state.auction
            if auction:
                legal.update(
                    {
                        "canBid": self._payment_capacity(ledger) > auction.current_bid,
                        "minimumBid": auction.current_bid + 1,
                        "maximumBid": self._payment_capacity(ledger),
                        "canPassAuction": True,
                    }
                )
        elif state.current_player_id != player_id:
            return legal
        elif state.stage == "harbor_share":
            legal["shareOptions"] = [
                {
                    "commodityId": commodity_id,
                    "price": max(5, state.market_values[commodity_id]),
                    "remaining": len(state.share_supply[commodity_id]),
                    "affordable": (
                        self._payment_capacity(ledger)
                        >= max(5, state.market_values[commodity_id])
                    ),
                }
                for commodity_id in COMMODITIES
                if state.share_supply[commodity_id]
            ]
            legal["canSkipShare"] = True
        elif state.stage == "harbor_load":
            legal["canSelectCargo"] = True
        elif state.stage == "harbor_launch":
            legal["canSetStartPositions"] = True
        elif state.stage == "placement":
            legal["placementTargets"] = self._placement_options(state, player_id)
            legal["canPassPlacement"] = True
        elif state.stage == "roll":
            legal["canRollDice"] = True
        elif state.stage == "move_order":
            legal["moveOrderPuntIds"] = [
                punt_id for punt_id in PUNT_IDS
                if state.punts[punt_id].status == "sailing"
            ]
        elif state.stage == "pirate_board":
            legal["pirateBoardPuntIds"] = self._pirate_board_targets(state)
            legal["canPirateStay"] = True
        elif state.stage in {"pilot_small", "pilot_large"}:
            legal["pilot"] = {
                "large": state.stage == "pilot_large",
                "puntIds": [
                    punt_id for punt_id in PUNT_IDS
                    if state.punts[punt_id].status == "sailing"
                ],
                "canPass": True,
            }
        elif state.stage == "pirate_route" and state.pirate_route_queue:
            legal["pirateRoute"] = {
                "puntId": state.pirate_route_queue[0],
                "destinations": ["port", "shipyard"],
            }
        elif state.stage == "voyage_summary":
            legal["canStartNextVoyage"] = True
        return legal

    def _placement_options(
        self,
        state: ManilaState,
        player_id: str,
    ) -> list[dict[str, Any]]:
        raw: list[dict[str, Any]] = []
        for punt_id in PUNT_IDS:
            punt = state.punts[punt_id]
            if punt.status != "sailing" or punt.cargo_id is None:
                continue
            costs = COMMODITIES[punt.cargo_id]["costs"]
            slot_index = len(punt.occupants)
            if slot_index < len(costs):
                raw.append(
                    {
                        "targetId": punt_id,
                        "kind": "punt",
                        "label": f"{COMMODITIES[punt.cargo_id]['label']}货船",
                        "cost": costs[slot_index],
                        "slotIndex": slot_index,
                    }
                )
        for prefix, slots, label in (
            ("port", state.port_slots, "港口"),
            ("shipyard", state.shipyard_slots, "船坞"),
        ):
            for slot in slots:
                if slot.bettor is None and slot.punt_id is None:
                    raw.append(
                        {
                            "targetId": f"{prefix}-{slot.id}",
                            "kind": prefix,
                            "label": f"{label} {slot.id}",
                            "cost": slot.cost,
                            "slotIndex": ord(slot.id) - ord("A"),
                            "payout": slot.payout,
                        }
                    )
        for special_id, definition in SPECIAL_POSITIONS.items():
            if special_id == "pirate-crew" and state.special_workers["pirate-captain"] is None:
                continue
            if state.special_workers[special_id] is None:
                raw.append(
                    {
                        "targetId": special_id,
                        "kind": definition["kind"],
                        "label": definition["label"],
                        "cost": definition["cost"],
                    }
                )
        noninsurance = [option["cost"] for option in raw if option["targetId"] != "insurance"]
        ledger = state.players[player_id]
        capacity = self._payment_capacity(ledger)
        blind_eligible = bool(noninsurance) and capacity < min(noninsurance)
        options: list[dict[str, Any]] = []
        for option in raw:
            affordable = option["cost"] <= capacity
            if affordable or (blind_eligible and option["targetId"] != "insurance"):
                options.append(
                    {
                        **option,
                        "affordable": affordable,
                        "blindAllowed": blind_eligible and not affordable,
                        "payable": option["cost"] if affordable else ledger.cash,
                    }
                )
        return options

    def _occupy_target(
        self,
        state: ManilaState,
        option: dict[str, Any],
        placement: WorkerPlacement,
    ) -> None:
        target_id = option["targetId"]
        kind = option["kind"]
        if kind == "punt":
            state.punts[target_id].occupants.append(placement)
            return
        if kind in {"port", "shipyard"}:
            prefix, slot_id = target_id.split("-", 1)
            slots = state.port_slots if prefix == "port" else state.shipyard_slots
            slot = next(slot for slot in slots if slot.id == slot_id)
            slot.bettor = placement
            return
        if kind == "pirate":
            state.special_workers[target_id] = placement
            placement.role = target_id
            return
        state.special_workers[target_id] = placement
        placement.role = target_id

    def _payment_capacity(self, ledger: ManilaPlayerState) -> int:
        available = len(
            set(ledger.share_ids) - set(ledger.mortgaged_share_ids)
        )
        return ledger.cash + 12 * available

    def _pay_with_forced_loans(
        self,
        state: ManilaState,
        ledger: ManilaPlayerState,
        amount: int,
        reason: str,
    ) -> None:
        while ledger.cash < amount:
            card_id = next(
                (
                    candidate
                    for candidate in sorted(ledger.share_ids)
                    if candidate not in ledger.mortgaged_share_ids
                ),
                None,
            )
            if card_id is None:
                raise GameRuleError(f"现金不足以支付{reason}")
            ledger.mortgaged_share_ids.append(card_id)
            ledger.cash += 12
            self._emit(
                state,
                "forced_mortgage",
                f"{ledger.display_name} 为支付{reason}强制抵押一张份额",
                {"playerId": ledger.player_id, "amount": 12, "reason": reason},
                animation={"kind": "mortgage", "playerId": ledger.player_id},
            )
        ledger.cash -= amount

    def _dock_punt(self, state: ManilaState, punt: PuntState, destination: str) -> None:
        slots = state.port_slots if destination == "port" else state.shipyard_slots
        slot = next((candidate for candidate in slots if candidate.punt_id is None), None)
        if slot is None:
            raise RuntimeError(f"no open {destination} slot for {punt.id}")
        slot.punt_id = punt.id
        punt.status = destination
        punt.position = 14 if destination == "port" else punt.position
        punt.destination_slot = f"{destination}-{slot.id}"

    def _pirate_board_targets(self, state: ManilaState) -> list[str]:
        targets: list[str] = []
        for punt_id in PUNT_IDS:
            punt = state.punts[punt_id]
            if (
                punt.status == "sailing"
                and punt.position == 13
                and punt.cargo_id is not None
                and len(punt.occupants) < len(COMMODITIES[punt.cargo_id]["costs"])
            ):
                targets.append(punt_id)
        return targets

    @staticmethod
    def _find_pirate_worker(
        state: ManilaState,
        worker_id: str,
    ) -> WorkerPlacement | None:
        for special_id in ("pirate-captain", "pirate-crew"):
            placement = state.special_workers[special_id]
            if placement is not None and placement.worker_id == worker_id:
                return placement
        return None

    @staticmethod
    def _remove_pirate_worker(state: ManilaState, worker_id: str) -> None:
        captain = state.special_workers["pirate-captain"]
        crew = state.special_workers["pirate-crew"]
        if captain is not None and captain.worker_id == worker_id:
            state.special_workers["pirate-captain"] = crew
            if crew is not None:
                crew.role = "pirate-captain"
            state.special_workers["pirate-crew"] = None
        elif crew is not None and crew.worker_id == worker_id:
            state.special_workers["pirate-crew"] = None

    def _remove_player_workers(self, state: ManilaState, player_id: str) -> None:
        for punt in state.punts.values():
            punt.occupants = [
                placement for placement in punt.occupants
                if placement.player_id != player_id
            ]
            for index, placement in enumerate(punt.occupants):
                placement.slot_index = index
        for slot in state.port_slots + state.shipyard_slots:
            if slot.bettor and slot.bettor.player_id == player_id:
                slot.bettor = None
        for special_id, placement in list(state.special_workers.items()):
            if placement and placement.player_id == player_id:
                if special_id == "pirate-captain":
                    crew = state.special_workers["pirate-crew"]
                    state.special_workers["pirate-captain"] = crew
                    if crew:
                        crew.role = "pirate-captain"
                    state.special_workers["pirate-crew"] = None
                else:
                    state.special_workers[special_id] = None

    def _eligible_to_place(self, state: ManilaState, player_id: str) -> bool:
        ledger = state.players[player_id]
        return (
            not ledger.forfeited
            and not ledger.passed_placement
            and bool(ledger.available_worker_ids)
            and bool(self._placement_options(state, player_id))
        )

    def _harbor_order(self, state: ManilaState) -> list[str]:
        active = self._active_ids(state)
        harbor_master = state.harbor_master_id
        if harbor_master not in active:
            return active
        index = active.index(harbor_master)
        return active[index:] + active[:index]

    @staticmethod
    def _active_ids(state: ManilaState) -> list[str]:
        return [
            player_id for player_id in state.turn_order
            if not state.players[player_id].forfeited
        ]

    @staticmethod
    def _next_in_order(
        turn_order: list[str],
        actor_id: str,
        candidates: list[str],
    ) -> str:
        if not candidates:
            raise RuntimeError("cannot select next player from empty candidates")
        start = turn_order.index(actor_id) if actor_id in turn_order else -1
        for offset in range(1, len(turn_order) + 1):
            candidate = turn_order[(start + offset) % len(turn_order)]
            if candidate in candidates:
                return candidate
        return candidates[0]

    @staticmethod
    def _require_voyage(state: ManilaState, payload: dict[str, Any]) -> None:
        voyage = payload.get("voyageNumber")
        if not is_int(voyage) or voyage != state.voyage_number:
            raise GameRuleError("航行编号已经更新，请根据最新桌面重新操作")

    @staticmethod
    def _require_stage(state: ManilaState, expected: str) -> None:
        if state.stage != expected:
            raise GameRuleError("当前阶段不能执行这个操作")

    @staticmethod
    def _require_current(state: ManilaState, player_id: str) -> None:
        if state.current_player_id != player_id:
            raise GameRuleError("还没有轮到你行动")

    def _require_harbor_master(
        self,
        state: ManilaState,
        player_id: str,
        stage: str,
    ) -> None:
        self._require_stage(state, stage)
        if state.harbor_master_id != player_id or state.current_player_id != player_id:
            raise GameRuleError("只有当前港务长可以执行这个操作")

    def _require_auction_turn(
        self,
        state: ManilaState,
        player_id: str,
    ) -> AuctionState:
        auction = state.auction
        if auction is None or auction.current_player_id != player_id:
            raise GameRuleError("还没有轮到你竞价")
        if player_id in auction.passed_player_ids:
            raise GameRuleError("本次拍卖 Pass 后不能重新加入")
        return auction

    @staticmethod
    def _member(room: ArcadeRoom, player: ArcadePlayer) -> None:
        if not any(member.id == player.id for member in room.players):
            raise GameRuleError("只有本局玩家可以操作")

    @staticmethod
    def _punt_label(punt: PuntState) -> str:
        if punt.cargo_id in COMMODITIES:
            return f"{COMMODITIES[punt.cargo_id]['label']}货船"
        return "货船"

    def _emit(
        self,
        state: ManilaState,
        event_type: str,
        message: str,
        details: dict[str, Any] | None = None,
        *,
        animation: dict[str, Any] | None = None,
    ) -> None:
        state.event_seq += 1
        event = {
            "id": state.event_seq,
            "type": event_type,
            "message": message,
            "details": details or {},
        }
        state.events.append(event)
        if len(state.events) > EVENT_LIMIT:
            state.events = state.events[-EVENT_LIMIT:]
        if animation is not None:
            state.animation = {"id": state.event_seq, **animation}
