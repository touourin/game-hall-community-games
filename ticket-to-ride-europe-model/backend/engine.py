from __future__ import annotations

import json
import random
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Iterable

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def _catalog(name: str) -> dict[str, Any]:
    return json.loads((PLUGIN_ROOT / "model" / name).read_text(encoding="utf-8"))


BOARD = _catalog("board-map.json")
CARD_CATALOG = _catalog("card-catalog.json")
ROUTES: dict[str, dict[str, Any]] = {item["id"]: item for item in BOARD["routes"]}
CITIES: dict[str, dict[str, Any]] = {item["id"]: item for item in BOARD["cities"]}
TRAIN_TYPES: dict[str, dict[str, Any]] = {
    item["id"]: item for item in CARD_CATALOG["trainCardTypes"]
}
TICKETS: dict[str, dict[str, Any]] = {
    item["id"]: item for item in CARD_CATALOG["destinationTickets"]
}

BASE_COLORS = ("purple", "blue", "orange", "white", "green", "yellow", "black", "red")
PLAYER_COLORS = ("ruby", "sapphire", "jade", "amber", "violet")
LOCOMOTIVE_TYPE = "train-locomotive"
MAX_TRAINS = 45
MAX_STATIONS = 3
EUROPEAN_EXPRESS_POINTS = 10
UNUSED_STATION_POINTS = 4


@dataclass(frozen=True, slots=True)
class TrainCard:
    id: str
    type_id: str

    @property
    def color(self) -> str:
        return TRAIN_TYPES[self.type_id]["color"]

    @property
    def is_locomotive(self) -> bool:
        return self.type_id == LOCOMOTIVE_TYPE


@dataclass(slots=True)
class EuropePlayerState:
    player_id: str
    display_name: str
    seat: int
    color: str
    status: str = "active"
    trains_remaining: int = MAX_TRAINS
    stations_remaining: int = MAX_STATIONS
    route_score: int = 0
    train_hand: list[TrainCard] = field(default_factory=list)
    destination_ticket_ids: list[str] = field(default_factory=list)
    initial_ticket_options: list[str] = field(default_factory=list)
    initial_ticket_choice_submitted: bool = False
    final_station_assignment_submitted: bool = False


@dataclass(slots=True)
class StationPlacement:
    city_id: str
    owner_player_id: str
    borrowed_route_id: str | None = None


@dataclass(slots=True)
class PendingTicketChoice:
    player_id: str
    offered_ticket_ids: list[str]
    min_keep: int
    kind: str = "turn"


@dataclass(slots=True)
class PendingTunnel:
    actor_player_id: str
    route_id: str
    declared_color: str
    initial_cards: list[TrainCard]
    revealed_cards: list[TrainCard]
    extra_cost: int
    payment_mode: str


@dataclass(slots=True)
class FinalRound:
    trigger_player_id: str
    remaining_player_ids: list[str]


@dataclass(slots=True)
class EuropeState:
    phase: str = "lobby"
    turn_order: list[str] = field(default_factory=list)
    current_player_id: str | None = None
    players: dict[str, EuropePlayerState] = field(default_factory=dict)
    train_deck: list[TrainCard] = field(default_factory=list)
    train_discard: list[TrainCard] = field(default_factory=list)
    face_up_market: list[TrainCard] = field(default_factory=list)
    destination_deck: list[str] = field(default_factory=list)
    removed_destination_ticket_ids: list[str] = field(default_factory=list)
    claimed_routes: dict[str, str] = field(default_factory=dict)
    station_placements: list[StationPlacement] = field(default_factory=list)
    pending_ticket_choice: PendingTicketChoice | None = None
    pending_tunnel: PendingTunnel | None = None
    final_round: FinalRound | None = None
    turn_number: int = 0
    event_sequence: int = 0
    latest_event: dict[str, Any] | None = None
    public_history: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    result_reason: str | None = None


class TicketToRideEuropeEngine:
    key = "plugin-ticket-to-ride-europe"
    name = "欧洲车票之旅"
    min_players = 2
    max_players = 5

    def __init__(self, rng: random.Random | random.SystemRandom | None = None) -> None:
        self.rng = rng or random.SystemRandom()

    def initial_state(self) -> EuropeState:
        return EuropeState()

    def start(self, room: ArcadeRoom) -> None:
        players = sorted(
            (player for player in room.players if not player.left_room),
            key=lambda player: (player.seat, player.id),
        )
        if not self.min_players <= len(players) <= self.max_players:
            raise GameRuleError("欧洲车票之旅需要 2–5 位玩家")

        if room.options.get("firstPlayer") == "host":
            first = next((player for player in players if player.id == room.host_id), players[0])
        else:
            first = self.rng.choice(players)
        first_index = players.index(first)
        ordered = players[first_index:] + players[:first_index]

        state = EuropeState(
            phase="setup_ticket_selection",
            turn_order=[player.id for player in ordered],
            players={
                player.id: EuropePlayerState(
                    player_id=player.id,
                    display_name=player.name,
                    seat=player.seat,
                    color=PLAYER_COLORS[index],
                )
                for index, player in enumerate(players)
            },
        )
        state.train_deck = self._new_train_deck()
        self.rng.shuffle(state.train_deck)
        for _ in range(4):
            for player in players:
                state.players[player.id].train_hand.append(state.train_deck.pop())
        self._refill_market(state)

        long_tickets = [item["id"] for item in CARD_CATALOG["destinationTickets"] if item["category"] == "long"]
        regular_tickets = [item["id"] for item in CARD_CATALOG["destinationTickets"] if item["category"] == "regular"]
        self.rng.shuffle(long_tickets)
        self.rng.shuffle(regular_tickets)
        for player in players:
            state.players[player.id].initial_ticket_options = [
                long_tickets.pop(),
                regular_tickets.pop(),
                regular_tickets.pop(),
                regular_tickets.pop(),
            ]
        state.removed_destination_ticket_ids.extend(long_tickets)
        state.destination_deck = regular_tickets

        room.state = state
        room.phase = "playing"
        room.round_number = 0
        self._event(
            state,
            "game_started",
            None,
            f"{len(players)} 人牌局开始；所有玩家正在秘密选择初始任务牌",
            firstPlayerId=first.id,
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
        if not isinstance(payload, dict):
            raise GameRuleError("操作参数必须是对象")
        state: EuropeState = room.state
        if player.id not in state.players or state.players[player.id].status != "active":
            raise GameRuleError("该玩家已经不能继续行动")
        if action == "resign":
            self.manual_forfeit(room, player)
            return

        handlers: dict[str, Callable[[ArcadeRoom, EuropeState, ArcadePlayer, dict[str, Any]], None]] = {
            "keep_initial_tickets": self._keep_initial_tickets,
            "draw_train_card": self._draw_train_card_action,
            "claim_route": self._claim_route,
            "pay_tunnel_extra": self._pay_tunnel_extra,
            "decline_tunnel": self._decline_tunnel,
            "draw_destination_tickets": self._draw_destination_tickets,
            "keep_destination_tickets": self._keep_destination_tickets,
            "build_station": self._build_station,
            "assign_station_routes": self._assign_station_routes,
        }
        handler = handlers.get(action)
        if handler is None:
            raise GameRuleError("不支持这个欧洲车票之旅操作")
        handler(room, state, player, payload)

    def view(self, room: ArcadeRoom, viewer: ArcadePlayer) -> dict[str, Any]:
        state: EuropeState = room.state
        if state.phase == "lobby":
            return {
                "schemaVersion": 1,
                "gameKey": "ticket-to-ride-europe-base",
                "sceneId": "setup.table",
                "phase": "lobby",
                "players": [],
                "actions": [],
            }

        viewer_state = state.players.get(viewer.id)
        actions = self._legal_actions(state, viewer.id)
        own_hand = [self._card_view(card) for card in viewer_state.train_hand] if viewer_state else []
        own_tickets = [self._ticket_view(state, viewer.id, ticket_id) for ticket_id in viewer_state.destination_ticket_ids] if viewer_state else []
        initial_options = [self._ticket_view(state, viewer.id, ticket_id) for ticket_id in viewer_state.initial_ticket_options] if viewer_state else []
        pending_choice = None
        if state.pending_ticket_choice and state.pending_ticket_choice.player_id == viewer.id:
            pending_choice = {
                "kind": state.pending_ticket_choice.kind,
                "minKeep": state.pending_ticket_choice.min_keep,
                "offeredTickets": [
                    self._ticket_view(state, viewer.id, ticket_id)
                    for ticket_id in state.pending_ticket_choice.offered_ticket_ids
                ],
            }
        own_tunnel = None
        if state.pending_tunnel and state.pending_tunnel.actor_player_id == viewer.id:
            own_tunnel = {
                "routeId": state.pending_tunnel.route_id,
                "declaredColor": state.pending_tunnel.declared_color,
                "initialCards": [self._card_view(card) for card in state.pending_tunnel.initial_cards],
                "extraCost": state.pending_tunnel.extra_cost,
                "paymentMode": state.pending_tunnel.payment_mode,
            }

        finished = room.phase == "finished"
        stations = []
        for station in state.station_placements:
            show_assignment = finished or station.owner_player_id == viewer.id
            stations.append({
                "cityId": station.city_id,
                "ownerPlayerId": station.owner_player_id,
                "borrowedRouteId": station.borrowed_route_id if show_assignment else None,
            })

        pending_tunnel = None
        if state.pending_tunnel:
            pending_tunnel = {
                "actorPlayerId": state.pending_tunnel.actor_player_id,
                "routeId": state.pending_tunnel.route_id,
                "declaredColor": state.pending_tunnel.declared_color,
                "revealedCards": [self._card_view(card) for card in state.pending_tunnel.revealed_cards],
                "extraCost": state.pending_tunnel.extra_cost,
                "status": "awaiting_payment",
            }

        legal_routes = self._legal_route_ids(state, viewer.id) if viewer_state else []
        station_cities = self._station_city_ids(state, viewer.id) if viewer_state else []
        return {
            "schemaVersion": 1,
            "gameKey": "ticket-to-ride-europe-base",
            "sceneId": self._scene_id(state, room.phase),
            "phase": "finished" if finished else state.phase,
            "rules": {
                "playerCount": len(state.turn_order),
                "startingTrains": MAX_TRAINS,
                "startingStations": MAX_STATIONS,
                "europeanExpressPoints": EUROPEAN_EXPRESS_POINTS,
                "unusedStationPoints": UNUSED_STATION_POINTS,
                "doubleRoutesRestricted": len(state.turn_order) <= 3,
            },
            "turnOrder": list(state.turn_order),
            "currentPlayerId": state.current_player_id,
            "turnNumber": state.turn_number,
            "players": [self._public_player_view(state, player_id) for player_id in state.turn_order],
            "market": [self._card_view(card) for card in state.face_up_market],
            "trainDeckCount": len(state.train_deck),
            "trainDiscardCount": len(state.train_discard),
            "destinationDeckCount": len(state.destination_deck),
            "claimedRoutes": [
                {"routeId": route_id, "ownerPlayerId": owner_id}
                for route_id, owner_id in state.claimed_routes.items()
            ],
            "stationPlacements": stations,
            "hand": own_hand,
            "destinationTickets": own_tickets,
            "initialTicketOptions": initial_options,
            "pendingTicketChoice": pending_choice,
            "pendingTunnel": pending_tunnel,
            "ownTunnelPayment": own_tunnel,
            "legalClaimRouteIds": legal_routes,
            "stationEligibleCityIds": station_cities,
            "finalRound": (
                {
                    "triggerPlayerId": state.final_round.trigger_player_id,
                    "remainingPlayerIds": list(state.final_round.remaining_player_ids),
                }
                if state.final_round
                else None
            ),
            "actions": actions,
            "latestEvent": state.latest_event,
            "history": list(state.public_history[-30:]),
            "result": state.result,
        }

    def player_result(self, room: ArcadeRoom, player: ArcadePlayer) -> tuple[str, str, bool]:
        state: EuropeState = room.state
        won = player.id in room.winner_player_ids
        if not state.result:
            return ("进行中", "individual", False)
        record = next((item for item in state.result["players"] if item["playerId"] == player.id), None)
        if record is None:
            return ("未参赛", "individual", False)
        if state.players[player.id].status == "forfeited":
            return (f"退出 · {record['total']} 分", "individual", False)
        label = "胜者" if won else f"第 {record['rank']} 名"
        return (f"{label} · {record['total']} 分", "individual", won)

    def record_state(self, room: ArcadeRoom) -> dict[str, Any]:
        state: EuropeState = room.state
        return {
            "gameKey": self.key,
            "turnsPlayed": state.turn_number,
            "winnerPlayerIds": list(room.winner_player_ids),
            "resultReason": state.result_reason,
            "claimedRoutes": [
                {"routeId": route_id, "ownerPlayerId": owner_id}
                for route_id, owner_id in state.claimed_routes.items()
            ],
            "stationPlacements": [
                {
                    "cityId": station.city_id,
                    "ownerPlayerId": station.owner_player_id,
                    "borrowedRouteId": station.borrowed_route_id,
                }
                for station in state.station_placements
            ],
            "players": list(state.result["players"]) if state.result else [
                {
                    "playerId": item.player_id,
                    "status": item.status,
                    "routeScore": item.route_score,
                    "trainsRemaining": item.trains_remaining,
                    "stationsRemaining": item.stations_remaining,
                    "trainHandCount": len(item.train_hand),
                    "destinationTicketCount": len(item.destination_ticket_ids),
                }
                for item in state.players.values()
            ],
        }

    def manual_forfeit(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        if room.phase != "playing":
            return False
        state: EuropeState = room.state
        player_state = state.players.get(player.id)
        if not player_state or player_state.status != "active":
            return False
        player_state.status = "forfeited"
        self._event(state, "player_forfeited", player.id, f"{player.name} 已退出本局")

        if state.phase == "setup_ticket_selection" and not player_state.initial_ticket_choice_submitted:
            state.removed_destination_ticket_ids.extend(player_state.initial_ticket_options)
            player_state.initial_ticket_options = []
            player_state.initial_ticket_choice_submitted = True
        if state.pending_ticket_choice and state.pending_ticket_choice.player_id == player.id:
            self._put_tickets_on_bottom(state, state.pending_ticket_choice.offered_ticket_ids)
            state.pending_ticket_choice = None
            state.phase = "turn_idle"
        if state.pending_tunnel and state.pending_tunnel.actor_player_id == player.id:
            state.train_discard.extend(state.pending_tunnel.initial_cards)
            state.train_discard.extend(state.pending_tunnel.revealed_cards)
            state.pending_tunnel = None
            state.phase = "turn_idle"
        if state.final_round and player.id in state.final_round.remaining_player_ids:
            state.final_round.remaining_player_ids.remove(player.id)
        if state.phase == "final_station_assignment":
            player_state.final_station_assignment_submitted = True

        active_ids = self._active_ids(state)
        if len(active_ids) == 1:
            self._finish_by_forfeit(room, state, active_ids[0])
            return True
        if state.phase == "setup_ticket_selection":
            self._start_turns_if_ready(room, state)
            return True
        if state.phase == "final_station_assignment":
            if self._station_assignments_complete(state):
                self._settle(room, state)
            return True
        if state.current_player_id == player.id:
            self._advance_after_forfeit(room, state, player.id)
        return True

    def _new_train_deck(self) -> list[TrainCard]:
        cards: list[TrainCard] = []
        for card_type in CARD_CATALOG["trainCardTypes"]:
            for index in range(1, card_type["copies"] + 1):
                cards.append(TrainCard(f"{card_type['id']}-{index:02d}", card_type["id"]))
        return cards

    def _keep_initial_tickets(
        self,
        room: ArcadeRoom,
        state: EuropeState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        if state.phase != "setup_ticket_selection":
            raise GameRuleError("当前不在初始任务选择阶段")
        player_state = state.players[player.id]
        if player_state.initial_ticket_choice_submitted:
            raise GameRuleError("你已经提交过初始任务选择")
        ticket_ids = self._string_list(payload, "ticketIds")
        if len(ticket_ids) < 2:
            raise GameRuleError("初始任务至少保留 2 张")
        if not set(ticket_ids) <= set(player_state.initial_ticket_options):
            raise GameRuleError("只能选择本次发给你的初始任务牌")
        player_state.destination_ticket_ids.extend(ticket_ids)
        state.removed_destination_ticket_ids.extend(
            ticket_id for ticket_id in player_state.initial_ticket_options if ticket_id not in set(ticket_ids)
        )
        player_state.initial_ticket_options = []
        player_state.initial_ticket_choice_submitted = True
        self._event(state, "initial_tickets_kept", player.id, f"{player.name} 已完成初始任务选择")
        self._start_turns_if_ready(room, state)

    def _start_turns_if_ready(self, room: ArcadeRoom, state: EuropeState) -> None:
        if not all(
            item.initial_ticket_choice_submitted
            for item in state.players.values()
            if item.status == "active"
        ):
            return
        state.phase = "turn_idle"
        state.current_player_id = next(player_id for player_id in state.turn_order if state.players[player_id].status == "active")
        state.turn_number = 1
        room.round_number = 1
        self._event(
            state,
            "setup_complete",
            state.current_player_id,
            f"初始选择完成；轮到 {state.players[state.current_player_id].display_name}",
        )

    def _draw_train_card_action(
        self,
        room: ArcadeRoom,
        state: EuropeState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_turn(state, player.id, {"turn_idle", "train_draw_second"})
        source = self._string(payload, "source")
        second_draw = state.phase == "train_draw_second"
        market_refreshed = False
        public_type_id: str | None = None
        if source == "deck":
            card = self._draw_from_train_deck(state)
            if card is None:
                raise GameRuleError("车票牌库与弃牌堆都没有牌")
        elif source == "market":
            card_id = self._string(payload, "cardId")
            card = next((item for item in state.face_up_market if item.id == card_id), None)
            if card is None:
                raise GameRuleError("所选公共明牌已经不存在")
            if second_draw and card.is_locomotive:
                raise GameRuleError("第二次抽牌不能拿公共彩虹车票")
            state.face_up_market.remove(card)
            public_type_id = card.type_id
            market_refreshed = self._refill_market(state)
        else:
            raise GameRuleError("抽牌来源必须是 deck 或 market")

        state.players[player.id].train_hand.append(card)
        self._event(
            state,
            "train_card_drawn",
            player.id,
            f"{player.name} 从{'牌库' if source == 'deck' else '公共市场'}抽取了 1 张车票牌",
            source=source,
            cardTypeId=public_type_id,
            marketRefreshed=market_refreshed,
        )
        if second_draw or (source == "market" and card.is_locomotive) or not self._second_draw_available(state):
            self._end_turn(room, state, player.id)
        else:
            state.phase = "train_draw_second"

    def _claim_route(
        self,
        room: ArcadeRoom,
        state: EuropeState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_turn(state, player.id, {"turn_idle"})
        route_id = self._string(payload, "routeId")
        route = ROUTES.get(route_id)
        if route is None:
            raise GameRuleError("轨道不存在")
        player_state = state.players[player.id]
        if player_state.trains_remaining < route["length"]:
            raise GameRuleError("剩余车厢不足以占用这条轨道")
        if not self._route_is_open(state, player.id, route):
            raise GameRuleError("这条轨道已经关闭或不可由你占用")
        card_ids = self._string_list(payload, "cardIds")
        declared = payload.get("declaredColor")
        if declared is not None and (not isinstance(declared, str) or declared not in (*BASE_COLORS, "locomotive")):
            raise GameRuleError("支付颜色无效")
        cards, resolved_color, payment_mode = self._validate_route_payment(
            player_state,
            route,
            card_ids,
            declared,
        )
        self._remove_cards(player_state.train_hand, cards)

        if route["kind"] == "tunnel":
            revealed = [
                card
                for _ in range(3)
                if (card := self._draw_from_train_deck(state)) is not None
            ]
            if payment_mode == "locomotive-only":
                extra_cost = sum(card.is_locomotive for card in revealed)
            else:
                extra_cost = sum(card.is_locomotive or card.color == resolved_color for card in revealed)
            self._event(
                state,
                "tunnel_cards_revealed",
                player.id,
                f"{player.name} 发起隧道；额外费用为 {extra_cost} 张",
                routeId=route_id,
                declaredColor=resolved_color,
                revealedCards=[self._card_view(card) for card in revealed],
                extraCost=extra_cost,
            )
            if extra_cost:
                state.pending_tunnel = PendingTunnel(
                    actor_player_id=player.id,
                    route_id=route_id,
                    declared_color=resolved_color,
                    initial_cards=cards,
                    revealed_cards=revealed,
                    extra_cost=extra_cost,
                    payment_mode=payment_mode,
                )
                state.phase = "tunnel_payment"
                return
            state.train_discard.extend(cards)
            state.train_discard.extend(revealed)
            self._complete_route_claim(room, state, player.id, route, "tunnel")
            return

        state.train_discard.extend(cards)
        self._complete_route_claim(room, state, player.id, route, route["kind"])

    def _pay_tunnel_extra(
        self,
        room: ArcadeRoom,
        state: EuropeState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        if state.phase != "tunnel_payment" or not state.pending_tunnel:
            raise GameRuleError("当前没有待补付的隧道")
        pending = state.pending_tunnel
        if pending.actor_player_id != player.id:
            raise GameRuleError("只有隧道发起者可以补付")
        card_ids = self._string_list(payload, "cardIds")
        if len(card_ids) != pending.extra_cost:
            raise GameRuleError(f"必须补付 {pending.extra_cost} 张车票牌")
        player_state = state.players[player.id]
        cards = self._cards_from_hand(player_state, card_ids)
        if pending.payment_mode == "locomotive-only":
            if any(not card.is_locomotive for card in cards):
                raise GameRuleError("全彩虹发起的隧道只能用彩虹车票补付")
        elif any(not card.is_locomotive and card.color != pending.declared_color for card in cards):
            raise GameRuleError("隧道补付必须使用声明颜色或彩虹车票")
        self._remove_cards(player_state.train_hand, cards)
        state.train_discard.extend(pending.initial_cards)
        state.train_discard.extend(pending.revealed_cards)
        state.train_discard.extend(cards)
        route = ROUTES[pending.route_id]
        state.pending_tunnel = None
        self._event(
            state,
            "tunnel_extra_paid",
            player.id,
            f"{player.name} 补付 {len(cards)} 张并完成隧道",
            routeId=route["id"],
            extraCost=len(cards),
        )
        self._complete_route_claim(room, state, player.id, route, "tunnel")

    def _decline_tunnel(
        self,
        room: ArcadeRoom,
        state: EuropeState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        if payload:
            raise GameRuleError("放弃隧道不需要参数")
        if state.phase != "tunnel_payment" or not state.pending_tunnel:
            raise GameRuleError("当前没有待决定的隧道")
        pending = state.pending_tunnel
        if pending.actor_player_id != player.id:
            raise GameRuleError("只有隧道发起者可以放弃")
        state.players[player.id].train_hand.extend(pending.initial_cards)
        state.train_discard.extend(pending.revealed_cards)
        route_id = pending.route_id
        state.pending_tunnel = None
        self._event(
            state,
            "tunnel_declined",
            player.id,
            f"{player.name} 放弃补付；初始牌已收回，回合结束",
            routeId=route_id,
        )
        self._end_turn(room, state, player.id)

    def _draw_destination_tickets(
        self,
        room: ArcadeRoom,
        state: EuropeState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        if payload:
            raise GameRuleError("抽取任务牌不需要参数")
        self._require_turn(state, player.id, {"turn_idle"})
        if not state.destination_deck:
            raise GameRuleError("任务牌库已经用尽")
        offered = [state.destination_deck.pop() for _ in range(min(3, len(state.destination_deck)))]
        state.pending_ticket_choice = PendingTicketChoice(player.id, offered, 1)
        state.phase = "ticket_choice"
        self._event(
            state,
            "destination_tickets_drawn",
            player.id,
            f"{player.name} 抽取了 {len(offered)} 张任务牌并正在秘密选择",
            count=len(offered),
        )

    def _keep_destination_tickets(
        self,
        room: ArcadeRoom,
        state: EuropeState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        pending = state.pending_ticket_choice
        if state.phase != "ticket_choice" or not pending or pending.player_id != player.id:
            raise GameRuleError("当前没有由你决定的任务牌")
        ticket_ids = self._string_list(payload, "ticketIds")
        if len(ticket_ids) < pending.min_keep:
            raise GameRuleError("本次至少保留 1 张任务牌")
        if not set(ticket_ids) <= set(pending.offered_ticket_ids):
            raise GameRuleError("只能保留本次抽到的任务牌")
        state.players[player.id].destination_ticket_ids.extend(ticket_ids)
        unkept = [ticket_id for ticket_id in pending.offered_ticket_ids if ticket_id not in set(ticket_ids)]
        self._put_tickets_on_bottom(state, unkept)
        state.pending_ticket_choice = None
        self._event(
            state,
            "destination_tickets_kept",
            player.id,
            f"{player.name} 保留了 {len(ticket_ids)} 张任务牌",
            keptCount=len(ticket_ids),
            returnedCount=len(unkept),
        )
        self._end_turn(room, state, player.id)

    def _build_station(
        self,
        room: ArcadeRoom,
        state: EuropeState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_turn(state, player.id, {"turn_idle"})
        city_id = self._string(payload, "cityId")
        if city_id not in CITIES:
            raise GameRuleError("城市不存在")
        if any(station.city_id == city_id for station in state.station_placements):
            raise GameRuleError("这座城市已经有火车站")
        player_state = state.players[player.id]
        if player_state.stations_remaining <= 0:
            raise GameRuleError("你已经没有可建造的火车站")
        cost = 4 - player_state.stations_remaining
        card_ids = self._string_list(payload, "cardIds")
        if len(card_ids) != cost:
            raise GameRuleError(f"第 {cost} 座火车站必须支付 {cost} 张牌")
        cards = self._cards_from_hand(player_state, card_ids)
        base_colors = {card.color for card in cards if not card.is_locomotive}
        if len(base_colors) > 1:
            raise GameRuleError("建站支付牌必须为同一种基础颜色，彩虹可以替代")
        self._remove_cards(player_state.train_hand, cards)
        state.train_discard.extend(cards)
        player_state.stations_remaining -= 1
        state.station_placements.append(StationPlacement(city_id, player.id))
        self._event(
            state,
            "station_built",
            player.id,
            f"{player.name} 在 {CITIES[city_id]['labelZhCN']} 建造了第 {cost} 座火车站",
            cityId=city_id,
            cost=cost,
        )
        self._end_turn(room, state, player.id)

    def _assign_station_routes(
        self,
        room: ArcadeRoom,
        state: EuropeState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        if state.phase != "final_station_assignment":
            raise GameRuleError("当前不在火车站借线阶段")
        player_state = state.players[player.id]
        if player_state.final_station_assignment_submitted:
            raise GameRuleError("你已经提交过火车站借线选择")
        assignments = payload.get("assignments")
        if not isinstance(assignments, dict) or not all(isinstance(key, str) for key in assignments):
            raise GameRuleError("assignments 必须是以城市 ID 为键的对象")
        owned = [station for station in state.station_placements if station.owner_player_id == player.id]
        if set(assignments) != {station.city_id for station in owned}:
            raise GameRuleError("必须为自己的每座已建火车站提交一项选择")
        for station in owned:
            route_id = assignments[station.city_id]
            if route_id is None:
                station.borrowed_route_id = None
                continue
            if not isinstance(route_id, str) or route_id not in ROUTES:
                raise GameRuleError("借用轨道不存在")
            route = ROUTES[route_id]
            owner_id = state.claimed_routes.get(route_id)
            if owner_id is None or owner_id == player.id:
                raise GameRuleError("火车站只能借用一条相邻的对手轨道")
            if station.city_id not in {route["fromCityId"], route["toCityId"]}:
                raise GameRuleError("借用轨道必须与火车站所在城市相邻")
            station.borrowed_route_id = route_id
        player_state.final_station_assignment_submitted = True
        self._event(
            state,
            "station_routes_assigned",
            player.id,
            f"{player.name} 已确认火车站借线方案",
        )
        if self._station_assignments_complete(state):
            self._settle(room, state)

    def _validate_route_payment(
        self,
        player: EuropePlayerState,
        route: dict[str, Any],
        card_ids: list[str],
        declared_color: str | None,
    ) -> tuple[list[TrainCard], str, str]:
        if len(card_ids) != route["length"]:
            raise GameRuleError(f"这条轨道必须支付 {route['length']} 张车票牌")
        cards = self._cards_from_hand(player, card_ids)
        base_colors = {card.color for card in cards if not card.is_locomotive}
        if len(base_colors) > 1:
            raise GameRuleError("占轨支付不能混合多种基础颜色")
        all_locomotive = not base_colors

        if route["color"] != "gray":
            resolved_color = route["color"]
            if base_colors and base_colors != {resolved_color}:
                raise GameRuleError("支付颜色与固定颜色轨道不符")
            if declared_color not in {None, resolved_color, "locomotive" if all_locomotive else resolved_color}:
                raise GameRuleError("声明颜色与轨道不符")
        else:
            if all_locomotive:
                if declared_color not in {None, "locomotive"}:
                    raise GameRuleError("全彩虹支付时声明颜色应为 locomotive")
                resolved_color = "locomotive"
            else:
                resolved_color = next(iter(base_colors))
                if declared_color not in {None, resolved_color}:
                    raise GameRuleError("灰色轨道的声明颜色与支付牌不符")

        if route["kind"] == "ferry":
            locomotive_count = sum(card.is_locomotive for card in cards)
            if locomotive_count < route["locomotivesRequired"]:
                raise GameRuleError(f"这条渡轮至少需要 {route['locomotivesRequired']} 张彩虹车票")

        payment_mode = "locomotive-only" if all_locomotive else "declared-color"
        return cards, resolved_color, payment_mode

    def _complete_route_claim(
        self,
        room: ArcadeRoom,
        state: EuropeState,
        player_id: str,
        route: dict[str, Any],
        route_kind: str,
    ) -> None:
        player = state.players[player_id]
        state.claimed_routes[route["id"]] = player_id
        player.trains_remaining -= route["length"]
        player.route_score += route["points"]
        state.phase = "turn_idle"
        self._event(
            state,
            "route_claimed",
            player_id,
            f"{player.display_name} 占用了 {CITIES[route['fromCityId']]['labelZhCN']}—{CITIES[route['toCityId']]['labelZhCN']}，获得 {route['points']} 分",
            routeId=route["id"],
            routeKind=route_kind,
            length=route["length"],
            points=route["points"],
        )
        self._end_turn(room, state, player_id)

    def _end_turn(self, room: ArcadeRoom, state: EuropeState, player_id: str) -> None:
        if state.current_player_id != player_id:
            raise RuntimeError("turn completion does not match current player")
        state.phase = "turn_idle"
        if state.final_round:
            if player_id in state.final_round.remaining_player_ids:
                state.final_round.remaining_player_ids.remove(player_id)
            state.final_round.remaining_player_ids = [
                item for item in state.final_round.remaining_player_ids if state.players[item].status == "active"
            ]
            if not state.final_round.remaining_player_ids:
                self._begin_final_station_assignment(room, state)
                return
            state.current_player_id = state.final_round.remaining_player_ids[0]
        else:
            player = state.players[player_id]
            if player.trains_remaining <= 2:
                rotation = self._rotation_after(state, player_id)
                remaining = [item for item in rotation if state.players[item].status == "active"] + [player_id]
                state.final_round = FinalRound(player_id, remaining)
                state.current_player_id = remaining[0]
                self._event(
                    state,
                    "final_round_triggered",
                    player_id,
                    f"{player.display_name} 只剩 {player.trains_remaining} 个车厢；最后一轮开始",
                    triggerPlayerId=player_id,
                    remainingPlayerIds=list(remaining),
                )
            else:
                state.current_player_id = self._next_active_after(state, player_id)
        state.turn_number += 1
        room.round_number = state.turn_number

    def _begin_final_station_assignment(self, room: ArcadeRoom, state: EuropeState) -> None:
        state.phase = "final_station_assignment"
        state.current_player_id = None
        for player_id, player in state.players.items():
            player.final_station_assignment_submitted = (
                player.status != "active"
                or not any(station.owner_player_id == player_id for station in state.station_placements)
            )
        self._event(state, "final_turns_complete", None, "所有最终回合完成；正在确认火车站借线")
        if self._station_assignments_complete(state):
            self._settle(room, state)

    def _station_assignments_complete(self, state: EuropeState) -> bool:
        return all(
            player.final_station_assignment_submitted
            for player in state.players.values()
            if player.status == "active"
        )

    def _settle(self, room: ArcadeRoom, state: EuropeState) -> None:
        state.phase = "scoring"
        active_ids = self._active_ids(state)
        longest = {player_id: self._longest_path_length(state, player_id) for player_id in active_ids}
        longest_value = max(longest.values(), default=0)
        express_ids = {player_id for player_id, length in longest.items() if length == longest_value}
        breakdowns = [
            self._score_player(state, player_id, player_id in express_ids, longest.get(player_id, 0))
            for player_id in state.turn_order
        ]
        by_id = {item["playerId"]: item for item in breakdowns}

        def tie_key(player_id: str) -> tuple[int, int, int, int]:
            item = by_id[player_id]
            return (
                item["total"],
                item["completedTicketCount"],
                -item["stationsUsed"],
                1 if item["europeanExpress"] else 0,
            )

        best_key = max(tie_key(player_id) for player_id in active_ids)
        winner_ids = [player_id for player_id in active_ids if tie_key(player_id) == best_key]
        ordered = sorted(
            state.turn_order,
            key=lambda player_id: (
                state.players[player_id].status == "active",
                *tie_key(player_id),
                -state.players[player_id].seat,
            ),
            reverse=True,
        )
        rank = 0
        previous: tuple[int, int, int, int] | None = None
        for position, player_id in enumerate(ordered, start=1):
            current = tie_key(player_id)
            if previous != current or state.players[player_id].status != "active":
                rank = position
            by_id[player_id]["rank"] = rank
            previous = current

        state.result_reason = "score"
        state.result = {
            "reason": "score",
            "winnerPlayerIds": winner_ids,
            "ranking": ordered,
            "europeanExpressPlayerIds": [player_id for player_id in active_ids if player_id in express_ids],
            "longestPathLength": longest_value,
            "players": [by_id[player_id] for player_id in ordered],
        }
        state.phase = "finished"
        winners = "、".join(state.players[player_id].display_name for player_id in winner_ids)
        top_score = by_id[winner_ids[0]]["total"]
        self._event(state, "game_scored", None, f"终局计分完成；{winners} 以 {top_score} 分获胜")
        room.finish("score", winner_ids, f"{winners} 以 {top_score} 分获胜")

    def _score_player(
        self,
        state: EuropeState,
        player_id: str,
        receives_express: bool,
        longest_path: int,
    ) -> dict[str, Any]:
        player = state.players[player_id]
        completed: list[str] = []
        failed: list[str] = []
        destination_points = 0
        for ticket_id in player.destination_ticket_ids:
            ticket = TICKETS[ticket_id]
            if self._ticket_completed(state, player_id, ticket_id):
                completed.append(ticket_id)
                destination_points += ticket["points"]
            else:
                failed.append(ticket_id)
                destination_points -= ticket["points"]
        station_points = player.stations_remaining * UNUSED_STATION_POINTS
        express_points = EUROPEAN_EXPRESS_POINTS if receives_express and player.status == "active" else 0
        total = player.route_score + destination_points + station_points + express_points
        return {
            "playerId": player_id,
            "status": player.status,
            "routePoints": player.route_score,
            "destinationPoints": destination_points,
            "stationPoints": station_points,
            "longestPathPoints": express_points,
            "total": total,
            "completedTicketCount": len(completed),
            "completedTicketIds": completed,
            "failedTicketIds": failed,
            "stationsUsed": MAX_STATIONS - player.stations_remaining,
            "longestPathLength": longest_path,
            "europeanExpress": bool(express_points),
            "rank": 0,
        }

    def _ticket_completed(self, state: EuropeState, player_id: str, ticket_id: str) -> bool:
        ticket = TICKETS[ticket_id]
        adjacency: defaultdict[str, set[str]] = defaultdict(set)
        route_ids = {
            route_id for route_id, owner_id in state.claimed_routes.items() if owner_id == player_id
        }
        route_ids.update(
            station.borrowed_route_id
            for station in state.station_placements
            if station.owner_player_id == player_id and station.borrowed_route_id
        )
        for route_id in route_ids:
            route = ROUTES[route_id]
            adjacency[route["fromCityId"]].add(route["toCityId"])
            adjacency[route["toCityId"]].add(route["fromCityId"])
        start, target = ticket["fromCityId"], ticket["toCityId"]
        queue: deque[str] = deque([start])
        visited: set[str] = set()
        while queue:
            city = queue.popleft()
            if city == target:
                return True
            if city in visited:
                continue
            visited.add(city)
            queue.extend(adjacency[city] - visited)
        return False

    def _longest_path_length(self, state: EuropeState, player_id: str) -> int:
        owned = [ROUTES[route_id] for route_id, owner_id in state.claimed_routes.items() if owner_id == player_id]
        if not owned:
            return 0
        incident: defaultdict[str, list[int]] = defaultdict(list)
        for index, route in enumerate(owned):
            incident[route["fromCityId"]].append(index)
            incident[route["toCityId"]].append(index)

        @lru_cache(maxsize=None)
        def search(city_id: str, used_mask: int) -> int:
            best = 0
            for edge_index in incident[city_id]:
                bit = 1 << edge_index
                if used_mask & bit:
                    continue
                route = owned[edge_index]
                next_city = route["toCityId"] if route["fromCityId"] == city_id else route["fromCityId"]
                best = max(best, route["length"] + search(next_city, used_mask | bit))
            return best

        return max(search(city_id, 0) for city_id in incident)

    def _finish_by_forfeit(self, room: ArcadeRoom, state: EuropeState, winner_id: str) -> None:
        breakdowns = [self._score_player(state, player_id, False, self._longest_path_length(state, player_id)) for player_id in state.turn_order]
        for index, item in enumerate(breakdowns, start=1):
            item["rank"] = 1 if item["playerId"] == winner_id else index + 1
        breakdowns.sort(key=lambda item: item["playerId"] != winner_id)
        state.result_reason = "last_player_remaining"
        state.result = {
            "reason": "last_player_remaining",
            "winnerPlayerIds": [winner_id],
            "ranking": [item["playerId"] for item in breakdowns],
            "europeanExpressPlayerIds": [],
            "longestPathLength": 0,
            "players": breakdowns,
        }
        state.phase = "finished"
        state.current_player_id = None
        winner = state.players[winner_id]
        room.finish("forfeit", [winner_id], f"{winner.display_name} 成为最后留在牌桌的玩家")

    def _advance_after_forfeit(self, room: ArcadeRoom, state: EuropeState, player_id: str) -> None:
        if state.final_round:
            state.final_round.remaining_player_ids = [
                item for item in state.final_round.remaining_player_ids if state.players[item].status == "active"
            ]
            if not state.final_round.remaining_player_ids:
                self._begin_final_station_assignment(room, state)
                return
            state.current_player_id = state.final_round.remaining_player_ids[0]
        else:
            state.current_player_id = self._next_active_after(state, player_id)
        state.turn_number += 1
        room.round_number = state.turn_number

    def _legal_actions(self, state: EuropeState, viewer_id: str) -> list[str]:
        player = state.players.get(viewer_id)
        if not player or player.status != "active":
            return []
        if state.phase == "setup_ticket_selection":
            return [] if player.initial_ticket_choice_submitted else ["keep_initial_tickets"]
        if state.phase == "tunnel_payment":
            return ["pay_tunnel_extra", "decline_tunnel"] if state.pending_tunnel and state.pending_tunnel.actor_player_id == viewer_id else []
        if state.phase == "ticket_choice":
            return ["keep_destination_tickets"] if state.pending_ticket_choice and state.pending_ticket_choice.player_id == viewer_id else []
        if state.phase == "final_station_assignment":
            return [] if player.final_station_assignment_submitted else ["assign_station_routes"]
        if state.phase not in {"turn_idle", "train_draw_second"} or state.current_player_id != viewer_id:
            return []
        if state.phase == "train_draw_second":
            return ["draw_train_card"] if self._second_draw_available(state) else []
        actions: list[str] = []
        if state.face_up_market or state.train_deck or state.train_discard:
            actions.append("draw_train_card")
        if self._legal_route_ids(state, viewer_id):
            actions.append("claim_route")
        if state.destination_deck:
            actions.append("draw_destination_tickets")
        if self._station_city_ids(state, viewer_id):
            actions.append("build_station")
        return actions

    def _legal_route_ids(self, state: EuropeState, player_id: str) -> list[str]:
        player = state.players[player_id]
        return [
            route_id
            for route_id, route in ROUTES.items()
            if route["length"] <= player.trains_remaining
            and self._route_is_open(state, player_id, route)
            and self._has_route_payment(player, route)
        ]

    def _has_route_payment(self, player: EuropePlayerState, route: dict[str, Any]) -> bool:
        counts = Counter(card.color for card in player.train_hand)
        locomotives = counts["locomotive"]
        if route["kind"] == "ferry" and locomotives < route["locomotivesRequired"]:
            return False
        if route["color"] == "gray":
            return locomotives >= route["length"] or any(counts[color] + locomotives >= route["length"] for color in BASE_COLORS)
        return counts[route["color"]] + locomotives >= route["length"]

    def _station_city_ids(self, state: EuropeState, player_id: str) -> list[str]:
        player = state.players[player_id]
        if player.stations_remaining <= 0:
            return []
        cost = 4 - player.stations_remaining
        counts = Counter(card.color for card in player.train_hand)
        if not (counts["locomotive"] >= cost or any(counts[color] + counts["locomotive"] >= cost for color in BASE_COLORS)):
            return []
        occupied = {station.city_id for station in state.station_placements}
        return [city_id for city_id in CITIES if city_id not in occupied]

    def _route_is_open(self, state: EuropeState, player_id: str, route: dict[str, Any]) -> bool:
        if route["id"] in state.claimed_routes:
            return False
        group_id = route["parallelGroupId"]
        if not group_id:
            return True
        siblings = [item for item in ROUTES.values() if item["parallelGroupId"] == group_id and item["id"] != route["id"]]
        sibling_owners = [state.claimed_routes[item["id"]] for item in siblings if item["id"] in state.claimed_routes]
        if player_id in sibling_owners:
            return False
        return not sibling_owners or len(state.turn_order) >= 4

    def _second_draw_available(self, state: EuropeState) -> bool:
        if state.train_deck or state.train_discard:
            return True
        return any(not card.is_locomotive for card in state.face_up_market)

    def _draw_from_train_deck(self, state: EuropeState) -> TrainCard | None:
        if not state.train_deck and state.train_discard:
            state.train_deck = state.train_discard
            state.train_discard = []
            self.rng.shuffle(state.train_deck)
        return state.train_deck.pop() if state.train_deck else None

    def _refill_market(self, state: EuropeState) -> bool:
        refreshed = False
        while len(state.face_up_market) < 5:
            card = self._draw_from_train_deck(state)
            if card is None:
                break
            state.face_up_market.append(card)
        attempts = 0
        while len(state.face_up_market) == 5 and sum(card.is_locomotive for card in state.face_up_market) >= 3:
            pool = [*state.train_deck, *state.train_discard, *state.face_up_market]
            if len(pool) < 5 or sum(not card.is_locomotive for card in pool) < 3:
                break
            state.train_discard.extend(state.face_up_market)
            state.face_up_market = []
            refreshed = True
            attempts += 1
            while len(state.face_up_market) < 5:
                card = self._draw_from_train_deck(state)
                if card is None:
                    break
                state.face_up_market.append(card)
            if attempts >= 64:
                # A deterministic escape hatch for adversarial test RNGs.
                pool = [*state.train_deck, *state.train_discard, *state.face_up_market]
                non_locomotives = [card for card in pool if not card.is_locomotive]
                locomotives = [card for card in pool if card.is_locomotive]
                state.face_up_market = non_locomotives[:3] + (non_locomotives[3:] + locomotives)[:2]
                chosen = {card.id for card in state.face_up_market}
                state.train_deck = [card for card in pool if card.id not in chosen]
                state.train_discard = []
                self.rng.shuffle(state.train_deck)
                break
        return refreshed

    def _cards_from_hand(self, player: EuropePlayerState, card_ids: list[str]) -> list[TrainCard]:
        by_id = {card.id: card for card in player.train_hand}
        try:
            return [by_id[card_id] for card_id in card_ids]
        except KeyError as exc:
            raise GameRuleError("支付牌不在你的手牌中") from exc

    @staticmethod
    def _remove_cards(hand: list[TrainCard], cards: Iterable[TrainCard]) -> None:
        remove_ids = {card.id for card in cards}
        hand[:] = [card for card in hand if card.id not in remove_ids]

    @staticmethod
    def _put_tickets_on_bottom(state: EuropeState, ticket_ids: list[str]) -> None:
        state.destination_deck[0:0] = list(reversed(ticket_ids))

    def _public_player_view(self, state: EuropeState, player_id: str) -> dict[str, Any]:
        player = state.players[player_id]
        return {
            "id": player.player_id,
            "name": player.display_name,
            "seat": player.seat,
            "color": player.color,
            "status": player.status,
            "score": player.route_score,
            "trainsRemaining": player.trains_remaining,
            "stationsRemaining": player.stations_remaining,
            "trainHandCount": len(player.train_hand),
            "destinationTicketCount": len(player.destination_ticket_ids),
            "initialTicketChoiceSubmitted": player.initial_ticket_choice_submitted,
            "finalStationAssignmentSubmitted": player.final_station_assignment_submitted,
        }

    def _card_view(self, card: TrainCard) -> dict[str, Any]:
        model = TRAIN_TYPES[card.type_id]
        return {
            "id": card.id,
            "typeId": card.type_id,
            "color": model["color"],
            "label": model["labelZhCN"],
            "visual": model["visual"],
        }

    def _ticket_view(self, state: EuropeState, player_id: str, ticket_id: str) -> dict[str, Any]:
        ticket = TICKETS[ticket_id]
        return {
            "id": ticket_id,
            "category": ticket["category"],
            "fromCityId": ticket["fromCityId"],
            "toCityId": ticket["toCityId"],
            "fromLabel": CITIES[ticket["fromCityId"]]["labelZhCN"],
            "toLabel": CITIES[ticket["toCityId"]]["labelZhCN"],
            "points": ticket["points"],
            "completed": self._ticket_completed(state, player_id, ticket_id),
        }

    def _event(
        self,
        state: EuropeState,
        event_type: str,
        player_id: str | None,
        message: str,
        **details: Any,
    ) -> None:
        state.event_sequence += 1
        event = {
            "sequence": state.event_sequence,
            "type": event_type,
            "playerId": player_id,
            "message": message,
            **details,
        }
        state.latest_event = event
        state.public_history.append(event)
        if len(state.public_history) > 120:
            state.public_history = state.public_history[-120:]

    @staticmethod
    def _scene_id(state: EuropeState, room_phase: str) -> str:
        if room_phase == "finished" or state.phase == "finished":
            return "game.finished"
        return {
            "setup_ticket_selection": "setup.ticket-selection",
            "train_draw_second": "draw.train-second",
            "tunnel_payment": "claim.tunnel-payment",
            "ticket_choice": "draw.ticket-choice",
            "final_station_assignment": "scoring.station-allocation",
            "scoring": "scoring.breakdown",
        }.get(state.phase, "round.final-turns" if state.final_round else "turn.choose-action")

    @staticmethod
    def _string(payload: dict[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise GameRuleError(f"{key} 必须是非空字符串")
        return value

    @staticmethod
    def _string_list(payload: dict[str, Any], key: str) -> list[str]:
        value = payload.get(key)
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            raise GameRuleError(f"{key} 必须是字符串数组")
        if len(value) != len(set(value)):
            raise GameRuleError(f"{key} 不能包含重复项")
        return value

    @staticmethod
    def _require_turn(state: EuropeState, player_id: str, phases: set[str]) -> None:
        if state.phase not in phases:
            raise GameRuleError("当前阶段不能执行这个回合行动")
        if state.current_player_id != player_id:
            raise GameRuleError("还没有轮到你")

    @staticmethod
    def _active_ids(state: EuropeState) -> list[str]:
        return [player_id for player_id in state.turn_order if state.players[player_id].status == "active"]

    @staticmethod
    def _rotation_after(state: EuropeState, player_id: str) -> list[str]:
        index = state.turn_order.index(player_id)
        return state.turn_order[index + 1 :] + state.turn_order[:index]

    def _next_active_after(self, state: EuropeState, player_id: str) -> str:
        for candidate in self._rotation_after(state, player_id):
            if state.players[candidate].status == "active":
                return candidate
        raise RuntimeError("no next active player")

