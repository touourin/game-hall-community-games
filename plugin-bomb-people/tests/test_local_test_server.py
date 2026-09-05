from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = PLUGIN_ROOT / "tools" / "local_test_server.py"
SPEC = importlib.util.spec_from_file_location("bomb_people_local_test_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
SERVER_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SERVER_MODULE)
LocalArena = SERVER_MODULE.LocalArena


def test_local_arena_runs_negotiated_map_and_complete_match_flow():
    arena = LocalArena(player_count=3, seed=101)
    lobby = arena.snapshot("local-p1")
    assert lobby["phase"] == "lobby"
    assert len(lobby["players"]) == 3
    assert lobby["game"]["boardSize"] == 20
    assert lobby["game"]["mapRotation"] == "consensus_or_random_no_repeat"
    assert lobby["game"]["canProposeMap"] is True

    proposed = arena.action(
        "local-p1", "propose_map", {"mapKey": "sky_citadel"},
    )
    assert proposed["game"]["mapProposal"]["approvalCount"] == 1
    assert arena.snapshot("local-p2")["game"]["canVoteMap"] is True
    arena.action("local-p2", "vote_map", {"accept": True})
    approved = arena.action("local-p3", "vote_map", {"accept": True})
    assert approved["game"]["nextMap"] == "sky_citadel"

    started = arena.start("local-p1")
    assert started["phase"] == "playing"
    assert started["game"]["stage"] == "countdown"
    assert started["game"]["selectedMap"] == "sky_citadel"
    assert len(started["game"]["players"]) == 3

    collapse = arena.jump_to_collapse("local-p1")
    assert collapse["game"]["stage"] == "collapse"
    finished = arena.finish_for_viewer("local-p1")
    assert finished["phase"] == "finished"
    assert finished["winnerPlayerIds"] == ["local-p1"]

    restarted = arena.restart("local-p1")
    assert restarted["phase"] == "playing"
    assert restarted["roundNumber"] == 2
    assert restarted["game"]["selectedMap"] != started["game"]["selectedMap"]


def test_local_arena_can_spawn_and_grant_every_debug_item():
    arena = LocalArena(player_count=2, seed=202)
    arena.start("local-p1")
    kinds = set(arena.snapshot("local-p1")["game"]["itemLabels"])
    assert len(kinds) == 15

    for kind in kinds:
        granted = arena.grant_item("local-p1", kind)
        assert granted["phase"] == "playing"

    spawned = arena.spawn_item("local-p1", "speed")
    assert any(item["kind"] == "speed" for item in spawned["game"]["items"])
    assert spawned["localTestSpawn"]["kind"] == "speed"


def test_local_arena_pause_stops_ticks_but_resume_advances():
    arena = LocalArena(player_count=2, seed=303)
    arena.start("local-p1")
    arena.set_paused(True, "local-p1")
    before = arena.snapshot("local-p1")["game"]["tick"]
    assert arena.tick_once() is False
    assert arena.snapshot("local-p1")["game"]["tick"] == before

    arena.set_paused(False, "local-p1")
    assert arena.tick_once() is True
    assert arena.snapshot("local-p1")["game"]["tick"] == before + 1


def test_local_finish_debug_action_can_award_an_eliminated_viewer():
    arena = LocalArena(player_count=3, seed=404)
    arena.start("local-p1")
    arena.room.state.players["local-p2"].alive = False
    arena.room.state.players["local-p2"].elimination_reason = "blast"

    finished = arena.finish_for_viewer("local-p2")
    assert finished["phase"] == "finished"
    assert finished["winnerPlayerIds"] == ["local-p2"]
    assert finished["game"]["winnerId"] == "local-p2"


@pytest.mark.parametrize("player_count", range(2, 9))
def test_local_arena_finishes_and_restarts_complete_rounds_for_two_to_eight_players(player_count):
    arena = LocalArena(player_count=player_count, seed=5000 + player_count)
    started = arena.start("local-p1")
    assert started["roundNumber"] == 1
    assert len(started["players"]) == player_count

    finished = arena.finish_for_viewer(f"local-p{player_count}")
    assert finished["phase"] == "finished"
    assert finished["winnerPlayerIds"] == [f"local-p{player_count}"]
    for index in range(1, player_count + 1):
        snapshot = arena.snapshot(f"local-p{index}")
        assert snapshot["winnerPlayerIds"] == [f"local-p{player_count}"]
        assert snapshot["actions"]["canRestart"] is True
        own = next(
            player for player in snapshot["game"]["players"]
            if player["id"] == f"local-p{index}"
        )
        assert own["stats"]["matches"] == 1
        assert own["stats"]["championships"] == (1 if index == player_count else 0)

    restarted = arena.restart("local-p1")
    assert restarted["phase"] == "playing"
    assert restarted["roundNumber"] == 2
    assert restarted["winnerPlayerIds"] == []
    assert restarted["game"]["winnerId"] is None
    assert restarted["game"]["selectedMap"] != started["game"]["selectedMap"]
    assert all(player["alive"] for player in restarted["game"]["players"])
    assert all(player["stats"]["matches"] == 1 for player in restarted["game"]["players"])
