from __future__ import annotations

from copy import deepcopy

import pytest

from backend.app.games.plugin_api import GameRuleError

from halli_galli_test_helpers import configure_state, dispatch, make_room


def test_last_draw_keeps_player_eligible_and_correct_bell_revives_them() -> None:
    game, room, players, clock = make_room(3)
    configure_state(
        game,
        room,
        discards={"p2": [("banana", 3)]},
        draw_tops={"p1": ("banana", 2)},
        fixed_draw_counts={"p1": 1, "p3": 8},
        remainder_to="p2",
        current_player_id="p1",
        final_duel_armed=False,
    )
    clock.advance(400)
    dispatch(game, room, players[0], "flip_card")
    assert room.state.players["p1"].draw_pile == []
    assert room.state.players["p1"].status == "eligible"
    assert room.state.current_player_id == "p2"
    assert game.view(room, players[0])["players"][0]["displayStatus"] == "last_chance"

    dispatch(game, room, players[0], "ring_bell")
    assert room.state.players["p1"].status == "eligible"
    assert room.state.players["p1"].draw_pile
    assert room.state.current_player_id == "p1"


def test_correct_bell_by_another_player_eliminates_empty_last_chance_player() -> None:
    game, room, players, _ = make_room(4)
    configure_state(
        game,
        room,
        discards={
            "p1": [("banana", 2)],
            "p2": [("banana", 3)],
            "p3": [("strawberry", 2)],
            "p4": [("plum", 1)],
        },
        fixed_draw_counts={"p1": 0, "p3": 7, "p4": 7},
        remainder_to="p2",
        final_duel_armed=False,
    )
    assert room.state.players["p1"].status == "eligible"
    dispatch(game, room, players[1], "ring_bell")
    assert room.state.players["p1"].status == "eliminated"
    assert room.state.players["p1"].elimination_reason == "discard-captured"


def test_three_to_two_transition_arms_duel_but_does_not_end_current_bell() -> None:
    game, room, players, _ = make_room(3)
    configure_state(
        game,
        room,
        discards={
            "p1": [("banana", 2)],
            "p2": [("banana", 3)],
            "p3": [("plum", 1)],
        },
        fixed_draw_counts={"p1": 8, "p2": 8, "p3": 0},
        remainder_to="p1",
        final_duel_armed=False,
    )
    dispatch(game, room, players[0], "ring_bell")
    assert room.phase == "playing"
    assert room.state.players["p3"].status == "eliminated"
    assert room.state.final_duel_armed is True
    assert room.state.events[-1]["type"] == "final_duel_armed"

    # Arrange the subsequent, genuinely final bell while preserving all cards.
    all_cards = (
        room.state.players["p1"].draw_pile
        + room.state.players["p2"].draw_pile
    )
    target = next(card for card in all_cards if card.fruit_count == 5)
    owner = "p1" if target in room.state.players["p1"].draw_pile else "p2"
    room.state.players[owner].draw_pile.remove(target)
    room.state.players[owner].discard_pile.append(target)
    room.state.fruit_totals, room.state.valid_fruit_ids = __import__(
        type(game).__module__, fromlist=["recompute_fruit_totals"]
    ).recompute_fruit_totals(room.state)
    room.state.board_epoch += 1
    dispatch(game, room, players[1], "ring_bell")
    assert room.phase == "finished"
    assert room.state.result["reasonCode"] == "final_correct_bell"


def test_two_player_first_correct_bell_ends_and_highest_card_count_wins() -> None:
    game, room, players, _ = make_room(2)
    configure_state(
        game,
        room,
        discards={"p1": [("lime", 2)], "p2": [("lime", 3)]},
        fixed_draw_counts={"p1": 10},
        remainder_to="p2",
        final_duel_armed=True,
    )
    dispatch(game, room, players[0], "ring_bell")

    assert room.phase == "finished"
    assert room.state.result["reasonCode"] == "final_correct_bell"
    assert sum(row["totalCount"] for row in room.state.result["rows"]) == 56
    highest = max(row["totalCount"] for row in room.state.result["rows"])
    assert room.winner_player_ids == [
        row["playerId"] for row in room.state.result["rows"]
        if row["totalCount"] == highest
    ]


def test_two_player_first_wrong_bell_gives_all_discards_to_opponent_then_ends() -> None:
    game, room, players, _ = make_room(2)
    configure_state(
        game,
        room,
        discards={
            "p1": [("banana", 2), ("plum", 1)],
            "p2": [("strawberry", 2), ("lime", 1)],
        },
        fixed_draw_counts={"p1": 30},
        remainder_to="p2",
        final_duel_armed=True,
    )
    p2_before = len(room.state.players["p2"].draw_pile)
    dispatch(game, room, players[0], "ring_bell")

    assert room.phase == "finished"
    assert room.state.result["reasonCode"] == "final_wrong_bell"
    assert len(room.state.players["p2"].draw_pile) == p2_before + 4
    assert all(not room.state.players[player.id].discard_pile for player in players)
    assert room.state.bell_resolution["winnerPlayerId"] == "p2"


def test_final_card_count_tie_produces_shared_winners() -> None:
    game, room, players, _ = make_room(2)
    # Before the final wrong bell: p1 owns 29 (28 draw + 1 discard), p2 owns 27.
    # p2 receives the one discard, producing 28–28.
    configure_state(
        game,
        room,
        discards={"p1": [("banana", 1)]},
        fixed_draw_counts={"p1": 28},
        remainder_to="p2",
        final_duel_armed=True,
    )
    assert [
        len(room.state.players[player.id].draw_pile)
        + len(room.state.players[player.id].discard_pile)
        for player in players
    ] == [29, 27]
    dispatch(game, room, players[0], "ring_bell")

    assert room.phase == "finished"
    assert room.winner_player_ids == ["p1", "p2"]
    assert room.state.result["sharedWin"] is True
    assert {row["rank"] for row in room.state.result["rows"]} == {1}


def test_wrong_bell_can_reduce_three_players_to_two_without_ending_that_bell() -> None:
    game, room, players, _ = make_room(3)
    configure_state(
        game,
        room,
        discards={player.id: [("strawberry", 1)] for player in players},
        fixed_draw_counts={"p3": 1, "p2": 8},
        remainder_to="p1",
        final_duel_armed=False,
    )
    dispatch(game, room, players[2], "ring_bell")
    assert room.phase == "playing"
    assert room.state.players["p3"].status == "eliminated"
    assert room.state.final_duel_armed is True


def test_resigning_from_three_arms_final_duel_and_resigning_from_two_finishes() -> None:
    game, room, players, _ = make_room(3)
    game.act(room, players[2], "resign", {})
    room.revision += 1
    assert room.phase == "playing"
    assert room.state.final_duel_armed is True

    game.act(room, players[1], "resign", {})
    room.revision += 1
    assert room.phase == "finished"
    assert room.winner_player_ids == ["p1"]
    assert room.state.result["reasonCode"] == "resignation"


def test_no_progress_waits_ten_seconds_then_uses_owned_card_counts() -> None:
    game, room, players, clock = make_room(3)
    configure_state(
        game,
        room,
        discards={
            "p1": [("banana", 1)],
            "p2": [("strawberry", 1)],
            "p3": [("lime", 1)],
        },
        fixed_draw_counts={"p1": 0, "p2": 0},
        remainder_to="p3",
        final_duel_armed=False,
    )
    # Move every remaining card into covered discard piles so nobody can flip.
    remainder = list(room.state.players["p3"].draw_pile)
    room.state.players["p3"].draw_pile = []
    room.state.players["p3"].discard_pile = remainder + room.state.players["p3"].discard_pile
    room.state.fruit_totals, room.state.valid_fruit_ids = __import__(
        type(game).__module__, fromlist=["recompute_fruit_totals"]
    ).recompute_fruit_totals(room.state)
    room.state.current_player_id = None
    game._update_no_progress(room.state, clock())
    deadline = room.state.no_progress_deadline_ms
    assert deadline == clock() + 10_000

    before = deepcopy(room.state)
    with pytest.raises(GameRuleError, match="还需等待"):
        dispatch(game, room, players[0], "settle_no_progress")
    assert room.state == before

    clock.value = deadline
    dispatch(game, room, players[0], "settle_no_progress")
    assert room.phase == "finished"
    assert room.state.result["reasonCode"] == "no_progress"
    assert sum(row["totalCount"] for row in room.state.result["rows"]) == 56


def test_result_view_and_player_result_agree_for_every_player() -> None:
    game, room, players, _ = make_room(2)
    configure_state(
        game,
        room,
        discards={"p1": [("plum", 5)]},
        remainder_to="p2",
        final_duel_armed=True,
    )
    dispatch(game, room, players[1], "ring_bell")
    view = game.view(room, players[0])
    assert view["sceneId"] == "finished"
    assert view["result"] == room.state.result
    for player in players:
        label, side, won = game.player_result(room, player)
        row = next(item for item in room.state.result["rows"] if item["playerId"] == player.id)
        assert f"{row['totalCount']} 张牌" in label
        assert side == "player"
        assert won is (player.id in room.winner_player_ids)
