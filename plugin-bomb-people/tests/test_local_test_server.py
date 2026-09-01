from __future__ import annotations

import importlib.util
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = PLUGIN_ROOT / "tools" / "local_test_server.py"
SPEC = importlib.util.spec_from_file_location("bomb_people_local_test_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
SERVER_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SERVER_MODULE)
LocalArena = SERVER_MODULE.LocalArena


def test_local_arena_runs_real_lobby_voting_and_match_flow():
    arena = LocalArena(player_count=3, seed=101)
    lobby = arena.snapshot("local-p1")
    assert lobby["phase"] == "lobby"
    assert len(lobby["players"]) == 3
    assert lobby["game"]["boardSize"] == 20

    arena.action("local-p1", "propose_map", {"mapKey": "sky_citadel"})
    arena.action("local-p2", "vote_map", {"accept": True})
    approved = arena.action("local-p3", "vote_map", {"accept": True})
    assert approved["game"]["selectedMap"] == "sky_citadel"
    assert approved["game"]["mapProposal"] is None

    started = arena.start("local-p1")
    assert started["phase"] == "playing"
    assert started["game"]["stage"] == "countdown"
    assert len(started["game"]["players"]) == 3

    collapse = arena.jump_to_collapse("local-p1")
    assert collapse["game"]["stage"] == "collapse"
    finished = arena.finish_for_viewer("local-p1")
    assert finished["phase"] == "finished"
    assert finished["winnerPlayerIds"] == ["local-p1"]

    restarted = arena.restart("local-p1")
    assert restarted["phase"] == "playing"
    assert restarted["roundNumber"] == 2


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
