from __future__ import annotations

from copy import deepcopy

import pytest

from backend.app.games.plugin_api import GameRuleError

from halli_galli_test_helpers import configure_state, dispatch, make_room


@pytest.mark.parametrize(
    ("tops", "expected"),
    [
        ([('banana', 5)], ["banana"]),
        ([('banana', 2), ('banana', 3)], ["banana"]),
        ([('strawberry', 1), ('strawberry', 1), ('strawberry', 3)], ["strawberry"]),
        ([('banana', 2), ('banana', 3), ('plum', 1), ('plum', 4)], ["banana", "plum"]),
        ([('banana', 4)], []),
        ([('banana', 2), ('banana', 4)], []),
        ([('banana', 4), ('banana', 3), ('banana', 2), ('banana', 1)], []),
        ([('banana', 2), ('plum', 3)], []),
    ],
)
def test_exactly_five_predicate_covers_positive_and_negative_cases(tops, expected) -> None:
    player_count = max(2, len(tops))
    game, room, players, _ = make_room(player_count)
    configure_state(
        game,
        room,
        discards={players[i].id: [spec] for i, spec in enumerate(tops)},
        remainder_to=players[-1].id,
        final_duel_armed=player_count == 2,
    )
    assert room.state.valid_fruit_ids == expected


def test_flip_covers_old_top_recomputes_totals_and_advances_turn() -> None:
    game, room, players, clock = make_room(3)
    configure_state(
        game,
        room,
        discards={
            "p1": [("banana", 3)],
            "p2": [("banana", 1)],
            "p3": [("banana", 4)],
        },
        draw_tops={"p1": ("strawberry", 2)},
        fixed_draw_counts={"p1": 1},
        remainder_to="p2",
        current_player_id="p1",
        final_duel_armed=False,
    )
    assert room.state.fruit_totals["banana"] == 8
    clock.advance(400)
    dispatch(game, room, players[0], "flip_card")

    assert room.state.players["p1"].discard_pile[-1].fruit_id == "strawberry"
    assert len(room.state.players["p1"].discard_pile) == 2
    assert room.state.fruit_totals["banana"] == 5
    assert room.state.valid_fruit_ids == ["banana"]
    assert room.state.current_player_id == "p2"
    assert room.state.board_epoch == 21
    assert room.state.events[-1]["cue"] == "card_flip"


def test_flip_rejects_wrong_turn_stale_versions_and_minimum_delay() -> None:
    game, room, players, clock = make_room(3)
    with pytest.raises(GameRuleError, match="NOT_YOUR_TURN"):
        dispatch(game, room, players[1], "flip_card")
    with pytest.raises(GameRuleError, match="STALE_REVISION"):
        dispatch(game, room, players[0], "flip_card", {"revision": 999})
    with pytest.raises(GameRuleError, match="STALE_BOARD"):
        dispatch(game, room, players[0], "flip_card", {"expectedBoardEpoch": 999})

    dispatch(game, room, players[0], "flip_card")
    with pytest.raises(GameRuleError, match="FLIP_TOO_EARLY"):
        dispatch(game, room, players[1], "flip_card")
    clock.advance(350)
    dispatch(game, room, players[1], "flip_card")


def test_correct_bell_collects_every_complete_discard_in_deterministic_order() -> None:
    game, room, players, _ = make_room(4)
    configure_state(
        game,
        room,
        discards={
            "p1": [("lime", 1), ("banana", 2)],
            "p2": [("plum", 2), ("banana", 3)],
            "p3": [("strawberry", 4)],
            "p4": [("lime", 2), ("plum", 1)],
        },
        fixed_draw_counts={"p3": 6},
        remainder_to="p1",
        final_duel_armed=False,
    )
    expected_order = [
        card.id
        for player_id in ["p3", "p4", "p1", "p2"]
        for card in room.state.players[player_id].discard_pile
    ]
    before_draw = [card.id for card in room.state.players["p3"].draw_pile]
    dispatch(game, room, players[2], "ring_bell")

    assert room.phase == "playing"
    assert all(not room.state.players[player.id].discard_pile for player in players)
    assert [card.id for card in room.state.players["p3"].draw_pile] == before_draw + expected_order
    assert room.state.current_player_id == "p3"
    assert room.state.board_epoch == 21
    assert room.state.fruit_totals == {"banana": 0, "strawberry": 0, "lime": 0, "plum": 0}
    resolution = room.state.bell_resolution
    assert resolution["kind"] == "correct"
    assert resolution["capturedCount"] == 7
    assert resolution["validFruitIds"] == ["banana"]


def test_ordinary_wrong_bell_pays_each_other_eligible_player_and_keeps_table() -> None:
    game, room, players, _ = make_room(4)
    configure_state(
        game,
        room,
        discards={
            "p1": [("banana", 2)],
            "p2": [("strawberry", 2)],
            "p3": [("lime", 2)],
            "p4": [("plum", 2)],
        },
        fixed_draw_counts={"p2": 8, "p3": 5, "p4": 5},
        remainder_to="p1",
        final_duel_armed=False,
    )
    before_epoch = room.state.board_epoch
    before_tops = {
        player.id: room.state.players[player.id].discard_pile[-1].id
        for player in players
    }
    before = {player.id: len(room.state.players[player.id].draw_pile) for player in players}
    dispatch(game, room, players[0], "ring_bell")

    after = {player.id: len(room.state.players[player.id].draw_pile) for player in players}
    assert after["p1"] == before["p1"] - 3
    assert after["p2"] == before["p2"] + 1
    assert after["p3"] == before["p3"] + 1
    assert after["p4"] == before["p4"] + 1
    assert room.state.board_epoch == before_epoch
    assert {
        player.id: room.state.players[player.id].discard_pile[-1].id
        for player in players
    } == before_tops
    assert room.state.bell_resolution["kind"] == "wrong"


def test_short_wrong_bell_payment_is_clockwise_and_eliminates_the_ringer() -> None:
    game, room, players, _ = make_room(5)
    configure_state(
        game,
        room,
        discards={
            "p1": [("banana", 1)],
            "p2": [("strawberry", 1)],
            "p3": [("lime", 1)],
            "p4": [("plum", 1)],
            "p5": [("banana", 1)],
        },
        fixed_draw_counts={"p3": 2, "p4": 7, "p5": 7},
        remainder_to="p1",
        final_duel_armed=False,
    )
    # Move all remainder away from p3: it can pay only p4 and p5.
    assert len(room.state.players["p3"].draw_pile) == 2
    p4_before = len(room.state.players["p4"].draw_pile)
    p5_before = len(room.state.players["p5"].draw_pile)
    p1_before = len(room.state.players["p1"].draw_pile)
    dispatch(game, room, players[2], "ring_bell")

    assert len(room.state.players["p4"].draw_pile) == p4_before + 1
    assert len(room.state.players["p5"].draw_pile) == p5_before + 1
    assert len(room.state.players["p1"].draw_pile) == p1_before
    assert room.state.players["p3"].status == "eliminated"
    assert room.state.players["p3"].elimination_reason == "wrong-bell-empty"
    assert [item["toPlayerId"] for item in room.state.bell_resolution["penalties"]] == ["p4", "p5"]


def test_same_epoch_and_stale_bell_requests_never_create_a_second_penalty() -> None:
    game, room, players, _ = make_room(4)
    configure_state(
        game,
        room,
        discards={player.id: [("plum", 1)] for player in players},
        remainder_to="p1",
        final_duel_armed=False,
    )
    epoch = room.state.board_epoch
    dispatch(game, room, players[0], "ring_bell", action_id="first-wrong-bell")
    snapshot = deepcopy(room.state)
    with pytest.raises(GameRuleError, match="BELL_ALREADY_RESOLVED"):
        dispatch(
            game,
            room,
            players[1],
            "ring_bell",
            {"boardEpoch": epoch},
            action_id="second-wrong-bell",
        )
    assert room.state == snapshot

    room.state.bell_resolution = None
    room.state.board_epoch += 1
    with pytest.raises(GameRuleError, match="STALE_BOARD"):
        dispatch(
            game,
            room,
            players[1],
            "ring_bell",
            {"boardEpoch": epoch},
            action_id="stale-wrong-bell",
        )
    assert room.state.players["p2"].status == "eligible"


def test_retrying_the_same_action_id_is_idempotent() -> None:
    game, room, players, _ = make_room(4)
    configure_state(
        game,
        room,
        discards={player.id: [("strawberry", 1)] for player in players},
        remainder_to="p1",
        final_duel_armed=False,
    )
    action_id = "idempotent-ring-001"
    dispatch(game, room, players[0], "ring_bell", action_id=action_id)
    after_first = deepcopy(room.state)
    game.act(
        room,
        players[0],
        "ring_bell",
        {"actionId": action_id, "boardEpoch": room.state.board_epoch, "inputMethod": "test"},
    )
    assert room.state == after_first


def test_invalid_input_method_is_rejected_without_mutation() -> None:
    game, room, players, _ = make_room(3)
    before = deepcopy(room.state)
    with pytest.raises(GameRuleError, match="inputMethod"):
        dispatch(
            game,
            room,
            players[0],
            "ring_bell",
            {"inputMethod": "client-fastest"},
        )
    assert room.state == before
