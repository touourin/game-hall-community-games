from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError
from backend.app.games.plugins import discover_game_plugins


PLUGIN_ROOT = Path(__file__).resolve().parents[2]


def engine(seed: int = 20260903):
    game = next(
        plugin.engine
        for plugin in discover_game_plugins(PLUGIN_ROOT)
        if plugin.engine.key == "plugin-ticket-to-ride-europe"
    )
    game.rng = random.Random(seed)
    return game


def room_players(count: int) -> list[ArcadePlayer]:
    return [
        ArcadePlayer(
            id=f"p{index + 1}",
            account_id=f"a{index + 1}",
            name=f"玩家{index + 1}",
            token_hash=f"token-{index + 1}",
            seat=index,
        )
        for index in range(count)
    ]


def started_room(count: int = 3, seed: int = 20260903):
    game = engine(seed)
    players = room_players(count)
    room = ArcadeRoom(
        code=f"EUR{count}",
        game_key=game.key,
        host_id=players[0].id,
        players=players,
        state=game.initial_state(),
        options={"firstPlayer": "host"},
    )
    game.start(room)
    return game, room, players


def finish_setup(game, room: ArcadeRoom, players: list[ArcadePlayer], keep: int = 2) -> None:
    for player in players:
        options = list(room.state.players[player.id].initial_ticket_options)
        game.act(room, player, "keep_initial_tickets", {"ticketIds": options[:keep]})


def set_hand(game, room: ArcadeRoom, player_id: str, colors: list[str]) -> list[str]:
    from importlib import import_module

    module = import_module(game.__class__.__module__)
    hand = [
        module.TrainCard(f"test-{player_id}-{color}-{index}", f"train-{color}")
        for index, color in enumerate(colors, start=1)
    ]
    room.state.players[player_id].train_hand = hand
    return [card.id for card in hand]


def route_between(game, a: str, b: str, *, color: str | None = None, index: int = 0):
    module = __import__(game.__class__.__module__, fromlist=["ROUTES"])
    matches = [
        route
        for route in module.ROUTES.values()
        if {route["fromCityId"], route["toCityId"]} == {a, b}
        and (color is None or route["color"] == color)
    ]
    return matches[index]


def ticket_between(game, a: str, b: str) -> str:
    module = __import__(game.__class__.__module__, fromlist=["TICKETS"])
    return next(
        ticket_id
        for ticket_id, ticket in module.TICKETS.items()
        if {ticket["fromCityId"], ticket["toCityId"]} == {a, b}
    )


def payment_for_route(game, room: ArcadeRoom, player_id: str, route: dict) -> tuple[list[str], str]:
    hand = room.state.players[player_id].train_hand
    locos = [card for card in hand if card.color == "locomotive"]
    colors = [route["color"]] if route["color"] != "gray" else list(game_module(game).BASE_COLORS)
    for color in colors:
        base = [card for card in hand if card.color == color]
        if len(base) + len(locos) < route["length"]:
            continue
        required_locomotives = route["locomotivesRequired"] if route["kind"] == "ferry" else 0
        selected_locomotives = locos[:required_locomotives]
        selected = selected_locomotives + base[: route["length"] - len(selected_locomotives)]
        if len(selected) < route["length"]:
            selected += locos[len(selected_locomotives) : len(selected_locomotives) + route["length"] - len(selected)]
        if len(selected) == route["length"]:
            return [card.id for card in selected], color
    if len(locos) >= route["length"]:
        return [card.id for card in locos[: route["length"]]], "locomotive"
    raise AssertionError(f"no payment for {route['id']}")


def game_module(game):
    return __import__(game.__class__.__module__, fromlist=["TrainCard", "ROUTES", "TICKETS"])


@pytest.mark.parametrize("count", (2, 3, 4, 5))
def test_start_deals_complete_unique_components(count: int) -> None:
    game, room, players = started_room(count)
    state = room.state

    assert room.phase == "playing"
    assert state.phase == "setup_ticket_selection"
    assert len(state.players) == count
    assert len(state.face_up_market) == 5
    assert sum(card.is_locomotive for card in state.face_up_market) <= 2
    assert len(state.train_deck) == 110 - count * 4 - 5
    assert len(state.destination_deck) == 40 - count * 3
    assert len(state.removed_destination_ticket_ids) == 6 - count
    all_ids = [card.id for item in state.players.values() for card in item.train_hand]
    all_ids += [card.id for card in state.train_deck + state.face_up_market]
    assert len(all_ids) == len(set(all_ids)) == 110
    for player in players:
        player_state = state.players[player.id]
        assert len(player_state.train_hand) == 4
        assert len(player_state.initial_ticket_options) == 4
        categories = [game_module(game).TICKETS[ticket_id]["category"] for ticket_id in player_state.initial_ticket_options]
        assert categories.count("long") == 1
        assert categories.count("regular") == 3


@pytest.mark.parametrize("count", (1, 6))
def test_rejects_unsupported_player_counts(count: int) -> None:
    game = engine()
    players = room_players(count)
    room = ArcadeRoom("NOPE", game.key, players[0].id, players, game.initial_state())
    with pytest.raises(GameRuleError, match="2–5"):
        game.start(room)


def test_initial_ticket_choice_is_private_and_requires_two() -> None:
    game, room, players = started_room(3)
    p1_options = list(room.state.players[players[0].id].initial_ticket_options)
    p2_options = list(room.state.players[players[1].id].initial_ticket_options)
    p1_view = game.view(room, players[0])
    serialized = json.dumps(p1_view, ensure_ascii=False)

    assert {item["id"] for item in p1_view["initialTicketOptions"]} == set(p1_options)
    assert not set(p2_options) & set(serialized.split('"'))
    with pytest.raises(GameRuleError, match="至少保留 2"):
        game.act(room, players[0], "keep_initial_tickets", {"ticketIds": p1_options[:1]})

    finish_setup(game, room, players)
    assert room.state.phase == "turn_idle"
    assert room.state.current_player_id == players[0].id
    assert all(len(room.state.players[player.id].destination_ticket_ids) == 2 for player in players)


def test_public_locomotive_ends_turn_but_blind_locomotive_allows_second_draw() -> None:
    game, room, players = started_room(3)
    finish_setup(game, room, players)
    module = game_module(game)
    p1 = players[0]
    loco = module.TrainCard("market-loco", "train-locomotive")
    room.state.face_up_market[0] = loco

    game.act(room, p1, "draw_train_card", {"source": "market", "cardId": loco.id})
    assert room.state.current_player_id == players[1].id
    assert room.state.phase == "turn_idle"

    room.state.current_player_id = p1.id
    room.state.train_deck.append(module.TrainCard("blind-loco", "train-locomotive"))
    game.act(room, p1, "draw_train_card", {"source": "deck"})
    assert room.state.current_player_id == p1.id
    assert room.state.phase == "train_draw_second"
    assert room.state.players[p1.id].train_hand[-1].id == "blind-loco"

    visible_loco = next((card for card in room.state.face_up_market if card.is_locomotive), None)
    if visible_loco is None:
        visible_loco = module.TrainCard("second-market-loco", "train-locomotive")
        room.state.face_up_market[0] = visible_loco
    with pytest.raises(GameRuleError, match="第二次抽牌"):
        game.act(room, p1, "draw_train_card", {"source": "market", "cardId": visible_loco.id})

    room.state.train_deck.append(module.TrainCard("blind-blue", "train-blue"))
    game.act(room, p1, "draw_train_card", {"source": "deck"})
    assert room.state.current_player_id == players[1].id
    assert room.state.phase == "turn_idle"


def test_market_with_three_locomotives_is_replaced() -> None:
    game, room, _ = started_room(3)
    module = game_module(game)
    room.state.face_up_market = [
        module.TrainCard(f"refresh-loco-{index}", "train-locomotive") for index in range(3)
    ] + [
        module.TrainCard("refresh-red", "train-red"),
        module.TrainCard("refresh-blue", "train-blue"),
    ]
    room.state.train_deck = [
        module.TrainCard(f"refresh-green-{index}", "train-green") for index in range(8)
    ]
    room.state.train_discard = []

    assert game._refill_market(room.state) is True
    assert len(room.state.face_up_market) == 5
    assert sum(card.is_locomotive for card in room.state.face_up_market) <= 2


@pytest.mark.parametrize("count,second_allowed", ((3, False), (4, True), (5, True)))
def test_double_route_player_count_rule(count: int, second_allowed: bool) -> None:
    game, room, players = started_room(count)
    finish_setup(game, room, players)
    yellow = route_between(game, "bruxelles", "paris", color="yellow")
    red = route_between(game, "bruxelles", "paris", color="red")
    set_hand(game, room, players[0].id, ["yellow", "yellow"])
    game.act(room, players[0], "claim_route", {
        "routeId": yellow["id"],
        "cardIds": [card.id for card in room.state.players[players[0].id].train_hand],
        "declaredColor": "yellow",
    })
    room.state.current_player_id = players[1].id
    set_hand(game, room, players[1].id, ["red", "red"])
    payload = {
        "routeId": red["id"],
        "cardIds": [card.id for card in room.state.players[players[1].id].train_hand],
        "declaredColor": "red",
    }
    if second_allowed:
        game.act(room, players[1], "claim_route", payload)
        assert room.state.claimed_routes[red["id"]] == players[1].id
    else:
        with pytest.raises(GameRuleError, match="关闭"):
            game.act(room, players[1], "claim_route", payload)


def test_same_player_can_never_claim_both_tracks_of_double_route() -> None:
    game, room, players = started_room(4)
    finish_setup(game, room, players)
    yellow = route_between(game, "bruxelles", "paris", color="yellow")
    red = route_between(game, "bruxelles", "paris", color="red")
    p1 = players[0]
    set_hand(game, room, p1.id, ["yellow", "yellow"])
    game.act(room, p1, "claim_route", {
        "routeId": yellow["id"],
        "cardIds": [card.id for card in room.state.players[p1.id].train_hand],
        "declaredColor": "yellow",
    })
    room.state.current_player_id = p1.id
    set_hand(game, room, p1.id, ["red", "red"])
    with pytest.raises(GameRuleError, match="不可由你"):
        game.act(room, p1, "claim_route", {
            "routeId": red["id"],
            "cardIds": [card.id for card in room.state.players[p1.id].train_hand],
            "declaredColor": "red",
        })


def test_route_scores_and_ferry_requires_minimum_locomotives() -> None:
    game, room, players = started_room(3)
    finish_setup(game, room, players)
    p1 = players[0]
    ferry = route_between(game, "amsterdam", "london")
    set_hand(game, room, p1.id, ["locomotive", "blue"])
    with pytest.raises(GameRuleError, match="至少需要 2"):
        game.act(room, p1, "claim_route", {
            "routeId": ferry["id"],
            "cardIds": [card.id for card in room.state.players[p1.id].train_hand],
            "declaredColor": "blue",
        })
    ids = set_hand(game, room, p1.id, ["locomotive", "locomotive"])
    game.act(room, p1, "claim_route", {
        "routeId": ferry["id"],
        "cardIds": ids,
        "declaredColor": "locomotive",
    })
    assert room.state.players[p1.id].trains_remaining == 43
    assert room.state.players[p1.id].route_score == 2
    assert room.state.claimed_routes[ferry["id"]] == p1.id


def prepare_tunnel(game, room: ArcadeRoom, player_id: str, initial: list[str], revealed: list[str]):
    module = game_module(game)
    route = route_between(game, "paris", "zurich")
    card_ids = set_hand(game, room, player_id, initial)
    room.state.train_deck = [
        module.TrainCard(f"risk-{color}-{index}", f"train-{color}")
        for index, color in enumerate(reversed(revealed), start=1)
    ]
    room.state.train_discard = []
    game.act(room, room.player(player_id), "claim_route", {
        "routeId": route["id"],
        "cardIds": card_ids,
        "declaredColor": "locomotive" if set(initial) == {"locomotive"} else initial[0],
    })
    return route


def test_tunnel_zero_extra_claims_immediately() -> None:
    game, room, players = started_room(3)
    finish_setup(game, room, players)
    route = prepare_tunnel(game, room, players[0].id, ["green"] * 3, ["red", "blue", "yellow"])
    assert room.state.pending_tunnel is None
    assert room.state.claimed_routes[route["id"]] == players[0].id
    assert room.state.players[players[0].id].route_score == 4


def test_tunnel_extra_can_be_paid_or_declined_and_initial_cards_return() -> None:
    game, room, players = started_room(3)
    finish_setup(game, room, players)
    p1 = players[0]
    route = prepare_tunnel(game, room, p1.id, ["green"] * 3, ["green", "red", "locomotive"])
    assert room.state.phase == "tunnel_payment"
    assert room.state.pending_tunnel.extra_cost == 2
    extra_ids = set_hand(game, room, p1.id, ["green", "locomotive", "red"])
    with pytest.raises(GameRuleError, match="必须补付 2"):
        game.act(room, p1, "pay_tunnel_extra", {"cardIds": extra_ids[:1]})
    game.act(room, p1, "pay_tunnel_extra", {"cardIds": extra_ids[:2]})
    assert room.state.claimed_routes[route["id"]] == p1.id
    assert room.state.pending_tunnel is None

    game2, room2, players2 = started_room(3, seed=91)
    finish_setup(game2, room2, players2)
    p1b = players2[0]
    prepare_tunnel(game2, room2, p1b.id, ["blue"] * 3, ["blue", "locomotive", "red"])
    assert len(room2.state.players[p1b.id].train_hand) == 0
    game2.act(room2, p1b, "decline_tunnel", {})
    assert len(room2.state.players[p1b.id].train_hand) == 3
    assert not room2.state.claimed_routes


def test_all_locomotive_tunnel_counts_and_accepts_only_locomotive_extra() -> None:
    game, room, players = started_room(3)
    finish_setup(game, room, players)
    p1 = players[0]
    prepare_tunnel(game, room, p1.id, ["locomotive"] * 3, ["green", "locomotive", "red"])
    assert room.state.pending_tunnel.extra_cost == 1
    assert room.state.pending_tunnel.payment_mode == "locomotive-only"
    wrong = set_hand(game, room, p1.id, ["green", "locomotive"])
    with pytest.raises(GameRuleError, match="只能用彩虹"):
        game.act(room, p1, "pay_tunnel_extra", {"cardIds": wrong[:1]})
    game.act(room, p1, "pay_tunnel_extra", {"cardIds": wrong[1:]})
    assert room.state.pending_tunnel is None


def test_destination_unkept_cards_return_to_bottom_in_relative_order() -> None:
    game, room, players = started_room(3)
    finish_setup(game, room, players)
    p1 = players[0]
    ids = list(game_module(game).TICKETS)[:4]
    room.state.destination_deck = ids.copy()
    game.act(room, p1, "draw_destination_tickets", {})
    assert room.state.pending_ticket_choice.offered_ticket_ids == [ids[3], ids[2], ids[1]]
    game.act(room, p1, "keep_destination_tickets", {"ticketIds": [ids[2]]})
    assert room.state.destination_deck == [ids[1], ids[3], ids[0]]


def test_station_costs_one_two_three_and_city_is_unique() -> None:
    game, room, players = started_room(3)
    finish_setup(game, room, players)
    p1 = players[0]
    for index, city_id in enumerate(("paris", "wien", "kyiv"), start=1):
        room.state.current_player_id = p1.id
        ids = set_hand(game, room, p1.id, ["blue"] * index)
        game.act(room, p1, "build_station", {"cityId": city_id, "cardIds": ids})
        assert room.state.players[p1.id].stations_remaining == 3 - index
    room.state.current_player_id = players[1].id
    ids = set_hand(game, room, players[1].id, ["red"])
    with pytest.raises(GameRuleError, match="已经有火车站"):
        game.act(room, players[1], "build_station", {"cityId": "paris", "cardIds": ids})


def test_station_borrow_completes_ticket_but_not_longest_path() -> None:
    game, room, players = started_room(3)
    finish_setup(game, room, players)
    module = game_module(game)
    p1, p2 = players[:2]
    ams_bru = route_between(game, "amsterdam", "bruxelles")
    bru_par = route_between(game, "bruxelles", "paris", color="yellow")
    par_pam = route_between(game, "paris", "pamplona", color="blue")
    room.state.claimed_routes = {
        ams_bru["id"]: p1.id,
        bru_par["id"]: p2.id,
        par_pam["id"]: p1.id,
    }
    ticket_id = ticket_between(game, "amsterdam", "pamplona")
    room.state.players[p1.id].destination_ticket_ids = [ticket_id]
    station = module.StationPlacement("bruxelles", p1.id, bru_par["id"])
    room.state.station_placements = [station]
    room.state.players[p1.id].stations_remaining = 2

    assert game._ticket_completed(room.state, p1.id, ticket_id) is True
    assert game._longest_path_length(room.state, p1.id) == 4


def test_final_round_includes_trigger_player_one_more_time() -> None:
    game, room, players = started_room(3)
    finish_setup(game, room, players)
    state = room.state
    state.players[players[0].id].trains_remaining = 2
    game._end_turn(room, state, players[0].id)
    assert state.final_round.trigger_player_id == players[0].id
    assert state.final_round.remaining_player_ids == [players[1].id, players[2].id, players[0].id]
    assert state.current_player_id == players[1].id

    game._end_turn(room, state, players[1].id)
    game._end_turn(room, state, players[2].id)
    assert state.current_player_id == players[0].id
    game._end_turn(room, state, players[0].id)
    assert room.phase == "finished"
    assert state.phase == "finished"


@pytest.mark.parametrize("count", (3, 4, 5))
def test_settlement_for_three_to_five_players_covers_positive_negative_and_bonus(count: int) -> None:
    game, room, players = started_room(count)
    finish_setup(game, room, players)
    state = room.state
    route_ids = list(game_module(game).ROUTES)
    for index, player in enumerate(players):
        state.claimed_routes[route_ids[index]] = player.id
        state.players[player.id].route_score = game_module(game).ROUTES[route_ids[index]]["points"]
        state.players[player.id].destination_ticket_ids = [list(game_module(game).TICKETS)[index]]
        state.players[player.id].initial_ticket_choice_submitted = True
    game._begin_final_station_assignment(room, state)

    assert room.phase == "finished"
    assert len(state.result["players"]) == count
    assert state.result["winnerPlayerIds"]
    assert all("destinationPoints" in item and "longestPathPoints" in item for item in state.result["players"])
    assert sum(item["longestPathPoints"] == 10 for item in state.result["players"]) >= 1
    assert all(game.player_result(room, player)[1] == "individual" for player in players)


def test_tie_break_completed_tickets_then_fewer_stations_then_express(monkeypatch) -> None:
    game, room, players = started_room(2)
    finish_setup(game, room, players)
    p1, p2 = players
    module = game_module(game)
    five_point = [ticket_id for ticket_id, ticket in module.TICKETS.items() if ticket["points"] == 5]
    ten_point = next(ticket_id for ticket_id, ticket in module.TICKETS.items() if ticket["points"] == 10)
    room.state.players[p1.id].destination_ticket_ids = five_point[:2]
    room.state.players[p2.id].destination_ticket_ids = [ten_point]
    monkeypatch.setattr(game, "_ticket_completed", lambda state, player_id, ticket_id: True)
    game._settle(room, room.state)
    assert room.winner_player_ids == [p1.id]

    game2, room2, players2 = started_room(2, seed=44)
    finish_setup(game2, room2, players2)
    a, b = players2
    room2.state.players[a.id].destination_ticket_ids = []
    room2.state.players[b.id].destination_ticket_ids = []
    room2.state.players[b.id].stations_remaining = 2
    room2.state.players[b.id].route_score = 4
    game2._settle(room2, room2.state)
    assert room2.winner_player_ids == [a.id]

    game3, room3, players3 = started_room(2, seed=45)
    finish_setup(game3, room3, players3)
    a, b = players3
    room3.state.players[a.id].destination_ticket_ids = []
    room3.state.players[b.id].destination_ticket_ids = []
    short_routes = [route for route in module.ROUTES.values() if route["length"] == 1]
    room3.state.claimed_routes = {short_routes[0]["id"]: a.id}
    room3.state.players[b.id].route_score = 10
    game3._settle(room3, room3.state)
    assert room3.winner_player_ids == [a.id]


def test_exact_tie_preserves_co_winners_and_longest_tie_rewards_all() -> None:
    game, room, players = started_room(2)
    finish_setup(game, room, players)
    p1, p2 = players
    module = game_module(game)
    one_routes = [route for route in module.ROUTES.values() if route["length"] == 1]
    room.state.players[p1.id].destination_ticket_ids = []
    room.state.players[p2.id].destination_ticket_ids = []
    room.state.claimed_routes = {one_routes[0]["id"]: p1.id, one_routes[1]["id"]: p2.id}
    room.state.players[p1.id].route_score = 1
    room.state.players[p2.id].route_score = 1
    game._settle(room, room.state)

    assert set(room.winner_player_ids) == {p1.id, p2.id}
    assert set(room.state.result["europeanExpressPlayerIds"]) == {p1.id, p2.id}
    assert all(item["longestPathPoints"] == 10 for item in room.state.result["players"])


def test_longest_path_is_weighted_trail_and_never_reuses_edge() -> None:
    game, room, players = started_room(3)
    finish_setup(game, room, players)
    p1 = players[0]
    routes = [
        route_between(game, "paris", "bruxelles", color="yellow"),
        route_between(game, "bruxelles", "frankfurt"),
        route_between(game, "frankfurt", "paris", color="white"),
        route_between(game, "paris", "dieppe"),
    ]
    room.state.claimed_routes = {route["id"]: p1.id for route in routes}
    assert game._longest_path_length(room.state, p1.id) == sum(route["length"] for route in routes)


def test_forfeit_last_active_player_wins_and_record_has_no_hands() -> None:
    game, room, players = started_room(3)
    finish_setup(game, room, players)
    assert game.manual_forfeit(room, players[1]) is True
    assert game.manual_forfeit(room, players[2]) is True
    assert room.phase == "finished"
    assert room.winner_player_ids == [players[0].id]
    record = game.record_state(room)
    serialized = json.dumps(record, ensure_ascii=False)
    assert "train_hand" not in serialized
    assert "initial_ticket_options" not in serialized


@pytest.mark.parametrize("count", (3, 4, 5))
def test_seeded_full_game_autoplay_reaches_auditable_settlement(count: int) -> None:
    game, room, players = started_room(count, seed=7000 + count)
    finish_setup(game, room, players)
    action_rng = random.Random(9000 + count)

    for _ in range(6000):
        if room.phase == "finished":
            break
        state = room.state
        if state.phase == "tunnel_payment":
            actor = room.player(state.pending_tunnel.actor_player_id)
            pending = state.pending_tunnel
            hand = state.players[actor.id].train_hand
            eligible = [
                card for card in hand
                if card.is_locomotive
                or (pending.payment_mode != "locomotive-only" and card.color == pending.declared_color)
            ]
            if len(eligible) >= pending.extra_cost:
                game.act(room, actor, "pay_tunnel_extra", {"cardIds": [card.id for card in eligible[: pending.extra_cost]]})
            else:
                game.act(room, actor, "decline_tunnel", {})
            continue
        if state.phase == "ticket_choice":
            pending = state.pending_ticket_choice
            game.act(room, room.player(pending.player_id), "keep_destination_tickets", {"ticketIds": pending.offered_ticket_ids[:1]})
            continue
        if state.phase == "final_station_assignment":
            for player in players:
                ps = state.players[player.id]
                if ps.status != "active" or ps.final_station_assignment_submitted:
                    continue
                owned = [station for station in state.station_placements if station.owner_player_id == player.id]
                game.act(room, player, "assign_station_routes", {"assignments": {station.city_id: None for station in owned}})
            continue

        actor = room.player(state.current_player_id)
        view = game.view(room, actor)
        if state.phase == "train_draw_second":
            if state.train_deck or state.train_discard:
                game.act(room, actor, "draw_train_card", {"source": "deck"})
            else:
                card = next(card for card in state.face_up_market if not card.is_locomotive)
                game.act(room, actor, "draw_train_card", {"source": "market", "cardId": card.id})
            continue

        legal = [game_module(game).ROUTES[route_id] for route_id in view["legalClaimRouteIds"]]
        if legal:
            route = max(legal, key=lambda item: (item["length"], action_rng.random()))
            card_ids, color = payment_for_route(game, room, actor.id, route)
            game.act(room, actor, "claim_route", {
                "routeId": route["id"],
                "cardIds": card_ids,
                "declaredColor": color,
            })
        elif "draw_train_card" in view["actions"]:
            if state.train_deck or state.train_discard:
                game.act(room, actor, "draw_train_card", {"source": "deck"})
            else:
                card = next(iter(state.face_up_market))
                game.act(room, actor, "draw_train_card", {"source": "market", "cardId": card.id})
        else:
            raise AssertionError(f"autoplay stalled in {state.phase}: {view['actions']}")
    else:
        raise AssertionError("autoplay exceeded 6000 actions")

    assert room.phase == "finished"
    assert room.state.result["winnerPlayerIds"] == room.winner_player_ids
    assert len(room.state.result["players"]) == count
    assert all(item["rank"] >= 1 for item in room.state.result["players"])
    assert sum(item["total"] for item in room.state.result["players"]) == sum(
        item["routePoints"] + item["destinationPoints"] + item["stationPoints"] + item["longestPathPoints"]
        for item in room.state.result["players"]
    )
