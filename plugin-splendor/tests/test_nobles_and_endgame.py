from __future__ import annotations

from itertools import chain

from splendor_test_helpers import (
    CARDS,
    NOBLES,
    act,
    card_set_with_score,
    disjoint_card_sets_with_score,
    force_turn,
    grant_bonus,
    grant_cards,
    set_available_nobles,
    set_player_pieces,
    started_room,
)


def grant_noble_requirements(state, player_id: str, noble_id: str, exclude: set[str] | None = None) -> None:
    excluded = exclude or set()
    for color, amount in NOBLES[noble_id]["requirement"].items():
        grant_bonus(state, player_id, color, amount, exclude=excluded)


def high_score_single_color_cards(color: str) -> list[str]:
    candidates = sorted(
        (item for item in CARDS.values() if item["bonusColor"] == color and item["prestige"] > 0),
        key=lambda item: item["prestige"],
        reverse=True,
    )
    chosen: list[str] = []
    score = 0
    for item in candidates:
        chosen.append(item["id"])
        score += item["prestige"]
        if score >= 15:
            return chosen
    raise AssertionError("single-color fixture cannot reach 15")


def test_single_eligible_noble_is_acquired_automatically_after_main_action() -> None:
    game, room, players = started_room(4)
    target = next(iter(NOBLES))
    set_available_nobles(room.state, [target])
    grant_noble_requirements(room.state, players[0].id, target)
    act(game, room, players[0], "take_same", color="white")

    assert target in room.state.players[players[0].id].noble_ids
    assert target not in room.state.available_noble_ids
    assert room.state.turn.active_player_id == players[1].id
    assert any(event.type == "noble_acquired" for event in room.state.events)


def test_multiple_eligible_nobles_require_exactly_one_choice() -> None:
    game, room, players = started_room(4)
    pair = list(NOBLES)[:2]
    set_available_nobles(room.state, pair)
    required = {
        color: max(NOBLES[pair[0]]["requirement"][color], NOBLES[pair[1]]["requirement"][color])
        for color in NOBLES[pair[0]]["requirement"]
    }
    for color, amount in required.items():
        grant_bonus(room.state, players[0].id, color, amount)
    act(game, room, players[0], "take_same", color="black")

    assert room.state.phase == "choose_noble"
    assert set(room.state.turn.eligible_noble_ids) == set(pair)
    assert room.state.turn.active_player_id == players[0].id
    act(game, room, players[0], "choose_noble", nobleId=pair[1])
    assert room.state.players[players[0].id].noble_ids == [pair[1]]
    assert pair[0] in room.state.available_noble_ids


def test_held_pieces_never_count_toward_noble_requirements() -> None:
    game, room, players = started_room(4)
    target = next(iter(NOBLES))
    set_available_nobles(room.state, [target])
    holdings = {**NOBLES[target]["requirement"], "gold": 0}
    set_player_pieces(room.state, players[0].id, holdings)
    act(game, room, players[0], "take_same", color="green")
    assert target not in room.state.players[players[0].id].noble_ids
    assert room.state.phase == "turn_action"


def test_first_player_trigger_gives_every_later_seat_one_final_action() -> None:
    game, room, players = started_room(4)
    grant_cards(room.state, players[0].id, high_score_single_color_cards("white"))
    act(game, room, players[0], "take_different", colors=["white", "blue", "green"])
    assert room.state.turn.end_triggered_by == players[0].id
    assert room.state.turn.final_turn_player_id == players[3].id
    assert room.state.turn.active_player_id == players[1].id

    for player in players[1:]:
        act(game, room, player, "take_different", colors=["white", "blue", "green"])
    assert room.phase == "finished"
    assert room.state.result.reason == "final-round-complete"
    assert players[0].id in room.winner_player_ids


def test_middle_seat_trigger_skips_first_player_in_final_round() -> None:
    game, room, players = started_room(4)
    grant_cards(room.state, players[1].id, high_score_single_color_cards("blue"))
    force_turn(room.state, players[1].id)
    act(game, room, players[1], "take_different", colors=["white", "blue", "green"])
    assert room.state.turn.active_player_id == players[2].id
    act(game, room, players[2], "take_different", colors=["white", "blue", "green"])
    act(game, room, players[3], "take_different", colors=["white", "blue", "green"])
    assert room.phase == "finished"
    assert room.state.turn.action_number == 3


def test_last_seat_trigger_finishes_immediately() -> None:
    game, room, players = started_room(4)
    grant_cards(room.state, players[3].id, high_score_single_color_cards("green"))
    force_turn(room.state, players[3].id)
    act(game, room, players[3], "take_different", colors=["white", "blue", "green"])
    assert room.phase == "finished"
    assert room.state.turn.end_triggered_by == players[3].id


def test_equal_prestige_uses_fewer_purchased_cards_as_tiebreaker() -> None:
    game, room, players = started_room(3)
    first = card_set_with_score(15, 3)
    second = card_set_with_score(15, 4, set(first))
    grant_cards(room.state, players[0].id, first)
    grant_cards(room.state, players[1].id, second)
    game._finish_game(room, room.state, "final-round-complete")
    assert room.winner_player_ids == [players[0].id]
    assert room.state.result.rows[0].purchased_card_count == 3


def test_equal_prestige_and_equal_card_count_produce_shared_victory() -> None:
    game, room, players = started_room(4)
    first, second = disjoint_card_sets_with_score(15, 4, 2)
    grant_cards(room.state, players[0].id, first)
    grant_cards(room.state, players[1].id, second)
    game._finish_game(room, room.state, "final-round-complete")
    assert set(room.winner_player_ids) == {players[0].id, players[1].id}
    assert room.state.result.outcome == "shared-win"
    assert "共同获胜" in room.state.result.summary_zh


def test_higher_prestige_beats_lower_score_even_with_more_cards() -> None:
    game, room, players = started_room(3)
    low = card_set_with_score(15, 3)
    high = card_set_with_score(16, 4, set(low))
    grant_cards(room.state, players[0].id, high)
    grant_cards(room.state, players[1].id, low)
    game._finish_game(room, room.state, "final-round-complete")
    assert room.winner_player_ids == [players[0].id]


def test_last_remaining_player_wins_and_forfeited_resources_return_to_supply() -> None:
    game, room, players = started_room(2)
    set_player_pieces(room.state, players[1].id, {"white": 2, "gold": 1})
    assert game.manual_forfeit(room, players[1]) is True
    assert room.phase == "finished"
    assert room.winner_player_ids == [players[0].id]
    assert room.state.supply["white"] == room.state.initial_supply["white"]
    assert room.state.supply["gold"] == room.state.initial_supply["gold"]
    rows = {row.player_id: row for row in room.state.result.rows}
    assert rows[players[0].id].rank == 1
    assert rows[players[1].id].rank == 2
    assert rows[players[1].id].forfeited is True


def test_current_player_forfeit_during_token_return_clears_resolution() -> None:
    game, room, players = started_room(3)
    set_player_pieces(room.state, players[0].id, {
        "white": 1, "blue": 2, "green": 2, "red": 2, "black": 1, "gold": 1,
    })
    act(game, room, players[0], "take_same", color="black")
    assert room.state.phase == "return_tokens"

    assert game.manual_forfeit(room, players[0]) is True
    assert room.state.phase == "turn_action"
    assert room.state.turn.active_player_id == players[1].id
    assert room.state.turn.pending_return_count == 0
    assert all(value == 0 for value in room.state.players[players[0].id].pieces.values())


def test_current_player_forfeit_during_noble_choice_clears_candidates() -> None:
    game, room, players = started_room(3)
    pair = list(NOBLES)[:2]
    set_available_nobles(room.state, pair)
    required = {
        color: max(NOBLES[pair[0]]["requirement"][color], NOBLES[pair[1]]["requirement"][color])
        for color in NOBLES[pair[0]]["requirement"]
    }
    for color, amount in required.items():
        grant_bonus(room.state, players[0].id, color, amount)
    act(game, room, players[0], "take_same", color="black")
    assert room.state.phase == "choose_noble"

    assert game.manual_forfeit(room, players[0]) is True
    assert room.state.phase == "turn_action"
    assert room.state.turn.active_player_id == players[1].id
    assert room.state.turn.eligible_noble_ids == []
    assert room.state.players[players[0].id].noble_ids == []


def test_forfeit_of_future_final_seat_moves_final_round_boundary() -> None:
    game, room, players = started_room(4)
    grant_cards(room.state, players[0].id, high_score_single_color_cards("white"))
    act(game, room, players[0], "take_different", colors=["white", "blue", "green"])
    assert room.state.turn.active_player_id == players[1].id

    assert game.manual_forfeit(room, players[3]) is True
    assert room.state.turn.final_turn_player_id == players[2].id
    act(game, room, players[1], "take_different", colors=["white", "blue", "green"])
    act(game, room, players[2], "take_different", colors=["white", "blue", "green"])
    assert room.phase == "finished"


def test_forfeit_by_current_final_seat_finishes_without_extra_round() -> None:
    game, room, players = started_room(4)
    grant_cards(room.state, players[0].id, high_score_single_color_cards("white"))
    act(game, room, players[0], "take_different", colors=["white", "blue", "green"])
    act(game, room, players[1], "take_different", colors=["white", "blue", "green"])
    act(game, room, players[2], "take_different", colors=["white", "blue", "green"])
    assert room.state.turn.active_player_id == players[3].id

    assert game.manual_forfeit(room, players[3]) is True
    assert room.phase == "finished"
    assert room.state.result.reason == "final-round-complete"
    assert room.state.turn.action_number == 3
