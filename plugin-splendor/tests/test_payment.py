from __future__ import annotations

import pytest

from backend.app.games.plugin_api import GameRuleError

from splendor_test_helpers import (
    CARDS,
    PIECE_COLORS,
    act,
    force_turn,
    grant_bonus,
    put_market_card,
    set_player_pieces,
    started_room,
    zero_payment,
)


def affordable_level_one_card() -> str:
    return next(identifier for identifier, item in CARDS.items() if item["level"] == 1 and item["totalCost"] <= 5)


def target_view(game, room, player, card_id):
    return next(
        slot["card"]
        for tier in game.view(room, player)["tiers"]
        for slot in tier["slots"]
        if slot["card"] and slot["card"]["id"] == card_id
    )


def test_market_purchase_returns_exact_payment_and_adds_permanent_bonus() -> None:
    game, room, players = started_room(2)
    target = affordable_level_one_card()
    put_market_card(room.state, target)
    costs = CARDS[target]["cost"]
    set_player_pieces(room.state, players[0].id, costs)
    preview = target_view(game, room, players[0], target)["payment"]
    supply_before = dict(room.state.supply)

    act(game, room, players[0], "purchase_face_up", cardId=target, payment=preview["recommendedPayment"])

    board = room.state.players[players[0].id]
    assert target in board.purchased_card_ids
    assert all(board.pieces[color] == 0 for color in PIECE_COLORS)
    for color in PIECE_COLORS:
        assert room.state.supply[color] == supply_before[color] + preview["recommendedPayment"][color]
    assert game.view(room, players[0])["players"][0]["bonuses"][CARDS[target]["bonusColor"]] == 1


def test_player_may_spend_gold_even_when_matching_gems_are_held() -> None:
    game, room, players = started_room(2)
    target = affordable_level_one_card()
    put_market_card(room.state, target)
    total = CARDS[target]["totalCost"]
    holdings = dict(CARDS[target]["cost"])
    holdings["gold"] = total
    set_player_pieces(room.state, players[0].id, holdings)
    payment = zero_payment()
    payment["gold"] = total

    act(game, room, players[0], "purchase_face_up", cardId=target, payment=payment)

    board = room.state.players[players[0].id]
    assert board.pieces["gold"] == 0
    assert all(board.pieces[color] == CARDS[target]["cost"][color] for color in CARDS[target]["cost"])


def test_rejects_underpayment_overpayment_incomplete_vectors_and_unowned_resources() -> None:
    game, room, players = started_room(2)
    target = affordable_level_one_card()
    put_market_card(room.state, target)
    set_player_pieces(room.state, players[0].id, {**CARDS[target]["cost"], "gold": 1})
    valid = target_view(game, room, players[0], target)["payment"]["recommendedPayment"]

    under = dict(valid)
    paid_color = next(color for color, amount in under.items() if color != "gold" and amount > 0)
    under[paid_color] -= 1
    with pytest.raises(GameRuleError, match="黄金数量"):
        act(game, room, players[0], "purchase_face_up", cardId=target, payment=under)

    over = dict(valid)
    over["gold"] += 1
    with pytest.raises(GameRuleError, match="黄金数量"):
        act(game, room, players[0], "purchase_face_up", cardId=target, payment=over)

    incomplete = {color: 0 for color in CARDS[target]["cost"]}
    with pytest.raises(GameRuleError, match="六个字段"):
        act(game, room, players[0], "purchase_face_up", cardId=target, payment=incomplete)

    unavailable = dict(valid)
    unavailable[paid_color] = room.state.players[players[0].id].pieces[paid_color] + 1
    with pytest.raises(GameRuleError, match="持有"):
        act(game, room, players[0], "purchase_face_up", cardId=target, payment=unavailable)


def test_permanent_rewards_can_make_a_card_completely_free() -> None:
    game, room, players = started_room(4)
    target = affordable_level_one_card()
    put_market_card(room.state, target)
    for color, amount in CARDS[target]["cost"].items():
        grant_bonus(room.state, players[0].id, color, amount, exclude={target})
    preview = target_view(game, room, players[0], target)["payment"]
    assert preview["effectiveCost"] == {color: 0 for color in CARDS[target]["cost"]}
    assert preview["recommendedPayment"] == zero_payment()
    assert preview["affordable"] is True

    act(game, room, players[0], "purchase_face_up", cardId=target, payment=zero_payment())
    assert target in room.state.players[players[0].id].purchased_card_ids


def test_reserved_card_purchase_removes_reservation_without_refilling_market() -> None:
    game, room, players = started_room(3)
    reserved_card = room.state.tiers[1].deck[0]
    act(game, room, players[0], "reserve_blind", level=1)
    force_turn(room.state, players[0].id)
    board = room.state.players[players[0].id]
    reservation = board.reservations[0]
    assert reservation.card_id == reserved_card
    set_player_pieces(room.state, players[0].id, {**CARDS[reserved_card]["cost"], "gold": 0})
    view = game.view(room, players[0])
    card_view = view["players"][0]["reservations"][0]["card"]
    market_before = [list(room.state.tiers[level].market) for level in (1, 2, 3)]

    act(
        game,
        room,
        players[0],
        "purchase_reserved",
        reservationId=reservation.reservation_id,
        payment=card_view["payment"]["recommendedPayment"],
    )

    assert not board.reservations
    assert reserved_card in board.purchased_card_ids
    assert [list(room.state.tiers[level].market) for level in (1, 2, 3)] == market_before
