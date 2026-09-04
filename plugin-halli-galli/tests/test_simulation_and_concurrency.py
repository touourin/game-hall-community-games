from __future__ import annotations

import asyncio
from collections import Counter

import pytest

from backend.app.games.plugin_api import GameRuleError

from halli_galli_test_helpers import autoplay_game, configure_state, make_room


@pytest.mark.parametrize("player_count", [2, 3, 4, 5, 6])
@pytest.mark.parametrize("seed_offset", range(6))
def test_seeded_full_games_finish_for_every_supported_player_count(
    player_count: int,
    seed_offset: int,
) -> None:
    seed = 20_000 + player_count * 100 + seed_offset
    game, room, players, action_mix, steps = autoplay_game(player_count, seed)

    assert room.phase == "finished"
    assert room.state.result is not None
    assert room.winner_player_ids
    assert steps < 30_000
    assert action_mix["flip"] > 0
    assert sum(row["totalCount"] for row in room.state.result["rows"]) == 56
    winner_rows = [row for row in room.state.result["rows"] if row["won"]]
    assert {row["playerId"] for row in winner_rows} == set(room.winner_player_ids)
    assert all(game.player_result(room, player)[2] == (player.id in room.winner_player_ids) for player in players)


def test_full_game_matrix_exercises_every_settlement_family() -> None:
    observed = Counter()
    for player_count in [2, 3, 4, 5, 6]:
        for seed_offset in range(10):
            _, room, _, action_mix, _ = autoplay_game(
                player_count,
                40_000 + player_count * 100 + seed_offset,
            )
            observed.update(action_mix)
            observed[f"ending:{room.state.result['reasonCode']}"] += 1
    assert observed["flip"] > 0
    assert observed["correct_bell"] > 0
    assert observed["wrong_bell"] > 0
    assert observed["ending:final_correct_bell"] + observed["ending:no_progress"] > 0


@pytest.mark.asyncio
async def test_six_simultaneous_bell_requests_are_serialized_to_one_resolution() -> None:
    game, room, players, _ = make_room(6)
    configure_state(
        game,
        room,
        discards={
            "p1": [("banana", 2)],
            "p2": [("banana", 3)],
            "p3": [("strawberry", 1)],
            "p4": [("lime", 1)],
            "p5": [("plum", 1)],
            "p6": [("strawberry", 2)],
        },
        remainder_to="p6",
        final_duel_armed=False,
    )
    epoch = room.state.board_epoch
    outcomes: list[str] = []

    async def ring(player, index: int) -> None:
        await asyncio.sleep(index * 0.0001)
        async with room.lock:
            try:
                game.act(
                    room,
                    player,
                    "ring_bell",
                    {
                        "actionId": f"concurrent-ring-{index:02d}",
                        "boardEpoch": epoch,
                        "inputMethod": "test",
                    },
                )
                room.revision += 1
                outcomes.append("resolved")
            except GameRuleError as error:
                outcomes.append(str(error).split("：", 1)[0])

    await asyncio.gather(*(ring(player, index) for index, player in enumerate(players)))

    assert outcomes.count("resolved") == 1
    assert outcomes.count("BELL_ALREADY_RESOLVED") == 5
    assert sum(event["type"] == "bell_correct" for event in room.state.events) == 1
    assert room.state.bell_resolution["actorPlayerId"] == "p1"
    game.assert_invariants(room)


def test_corrupt_duplicate_card_is_detected_by_invariant_guard() -> None:
    game, room, _, _ = make_room(4)
    room.state.players["p1"].draw_pile[0] = room.state.players["p1"].draw_pile[1]
    with pytest.raises(AssertionError, match="conservation|uniqueness"):
        game.assert_invariants(room)
