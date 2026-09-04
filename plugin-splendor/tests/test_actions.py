from __future__ import annotations

import copy

import pytest

from backend.app.games.plugin_api import GameRuleError

from splendor_test_helpers import (
    PIECE_COLORS,
    STANDARD_COLORS,
    act,
    force_turn,
    relocate_deck_to_player,
    set_player_pieces,
    started_room,
)


def drain_colors(state, colors: list[str]) -> None:
    recipients = list(state.players)
    cursor = 0
    for color in colors:
        while state.supply[color] > 0:
            player_id = recipients[cursor % len(recipients)]
            state.players[player_id].pieces[color] += 1
            state.supply[color] -= 1
            cursor += 1


@pytest.mark.parametrize("remaining", [5, 4, 3, 2, 1])
def test_take_different_uses_three_or_all_remaining_nonempty_colors(remaining: int) -> None:
    game, room, players = started_room(4, seed=100 + remaining)
    empty = list(STANDARD_COLORS)[remaining:]
    drain_colors(room.state, empty)
    available = [color for color in STANDARD_COLORS if room.state.supply[color] > 0]
    required = min(3, remaining)
    chosen = available[:required]
    before = copy.deepcopy(room.state.supply)

    act(game, room, players[0], "take_different", colors=chosen)

    for color in STANDARD_COLORS:
        assert room.state.supply[color] == before[color] - (1 if color in chosen else 0)
    game.assert_invariants(room.state)


def test_take_different_rejects_wrong_count_duplicates_gold_and_empty_supply() -> None:
    game, room, players = started_room(2)
    with pytest.raises(GameRuleError, match="必须选择 3"):
        act(game, room, players[0], "take_different", colors=["white", "blue"])
    with pytest.raises(GameRuleError, match="互不相同"):
        act(game, room, players[0], "take_different", colors=["white", "white", "blue"])
    with pytest.raises(GameRuleError, match="五种宝石色"):
        act(game, room, players[0], "take_different", colors=["white", "blue", "gold"])
    drain_colors(room.state, list(STANDARD_COLORS))
    with pytest.raises(GameRuleError, match="没有可拿取"):
        act(game, room, players[0], "take_different", colors=[])


@pytest.mark.parametrize(("supply", "allowed"), [(5, True), (4, True), (3, False)])
def test_take_same_checks_supply_before_action(supply: int, allowed: bool) -> None:
    game, room, players = started_room(3)
    take = room.state.supply["red"] - supply
    room.state.supply["red"] -= take
    room.state.players[players[1].id].pieces["red"] += take
    if allowed:
        act(game, room, players[0], "take_same", color="red")
        assert room.state.players[players[0].id].pieces["red"] == 2
        assert room.state.supply["red"] == supply - 2
    else:
        with pytest.raises(GameRuleError, match="至少有 4"):
            act(game, room, players[0], "take_same", color="red")


def test_take_same_rejects_gold() -> None:
    game, room, players = started_room(2)
    with pytest.raises(GameRuleError, match="彩色宝石"):
        act(game, room, players[0], "take_same", color="gold")


def test_over_limit_enters_mandatory_return_and_only_exact_return_advances() -> None:
    game, room, players = started_room(4)
    set_player_pieces(room.state, players[0].id, {
        "white": 1, "blue": 2, "green": 2, "red": 2, "black": 1, "gold": 1,
    })
    act(game, room, players[0], "take_different", colors=["white", "blue", "green"])
    assert room.state.phase == "return_tokens"
    assert room.state.turn.active_player_id == players[0].id
    assert room.state.turn.pending_return_count == 2

    invalid = {color: 0 for color in PIECE_COLORS}
    invalid["white"] = 1
    with pytest.raises(GameRuleError, match="恰好归还 2"):
        act(game, room, players[0], "return_tokens", pieces=invalid)
    valid = {color: 0 for color in PIECE_COLORS}
    valid["gold"] = 1
    valid["blue"] = 1
    act(game, room, players[0], "return_tokens", pieces=valid)
    assert sum(room.state.players[players[0].id].pieces.values()) == 10
    assert room.state.phase == "turn_action"
    assert room.state.turn.active_player_id == players[1].id


def test_face_up_and_blind_reservations_move_exact_cards_and_award_gold() -> None:
    game, room, players = started_room(3)
    face_up = room.state.tiers[1].market[0]
    replacement = room.state.tiers[1].deck[0]
    act(game, room, players[0], "reserve_face_up", cardId=face_up)
    reservation = room.state.players[players[0].id].reservations[0]
    assert reservation.card_id == face_up
    assert reservation.known_to_all is True
    assert room.state.tiers[1].market[0] == replacement
    assert room.state.players[players[0].id].pieces["gold"] == 1

    force_turn(room.state, players[1].id)
    blind = room.state.tiers[2].deck[0]
    market_before = list(room.state.tiers[2].market)
    act(game, room, players[1], "reserve_blind", level=2)
    blind_reservation = room.state.players[players[1].id].reservations[0]
    assert blind_reservation.card_id == blind
    assert blind_reservation.known_to_all is False
    assert room.state.tiers[2].market == market_before
    assert room.state.players[players[1].id].pieces["gold"] == 1


def test_reserve_limit_gold_shortage_empty_deck_and_empty_market_refill() -> None:
    game, room, players = started_room(4)
    for _ in range(3):
        card_id = next(card_id for card_id in room.state.tiers[1].market if card_id)
        act(game, room, players[0], "reserve_face_up", cardId=card_id)
        force_turn(room.state, players[0].id)
    with pytest.raises(GameRuleError, match="最多保留 3"):
        act(game, room, players[0], "reserve_face_up", cardId=room.state.tiers[1].market[0])

    game, room, players = started_room(2)
    set_player_pieces(room.state, players[1].id, {"gold": 5})
    card_id = room.state.tiers[1].market[0]
    act(game, room, players[0], "reserve_face_up", cardId=card_id)
    assert room.state.players[players[0].id].pieces["gold"] == 0

    game, room, players = started_room(2)
    relocate_deck_to_player(room.state, 1, players[1].id)
    with pytest.raises(GameRuleError, match="已经抽空"):
        act(game, room, players[0], "reserve_blind", level=1)
    market_card = room.state.tiers[1].market[0]
    act(game, room, players[0], "reserve_face_up", cardId=market_card)
    assert room.state.tiers[1].market[0] is None
    game.assert_invariants(room.state)


def test_rejects_out_of_turn_stale_state_and_stale_market_without_mutation() -> None:
    game, room, players = started_room(3)
    before = copy.deepcopy(room.state)
    with pytest.raises(GameRuleError, match="还没有轮到"):
        act(game, room, players[1], "take_same", color="white")
    assert room.state.supply == before.supply

    with pytest.raises(GameRuleError, match="旧状态"):
        game.act(room, players[0], "take_same", {"revision": room.state.revision - 1, "color": "white"})
    with pytest.raises(GameRuleError, match="市场已经变化"):
        game.act(room, players[0], "reserve_face_up", {
            "revision": room.state.revision,
            "marketRevision": room.state.market_revision - 1,
            "cardId": room.state.tiers[1].market[0],
        })
    assert room.state.supply == before.supply
