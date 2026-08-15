from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom


def engine():
    entry = Path(__file__).resolve().parents[1] / "backend" / "plugin.py"
    spec = importlib.util.spec_from_file_location("star_stones_example", entry)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.create_engine()


def test_players_take_turns_and_last_stone_wins() -> None:
    game = engine()
    first = ArcadePlayer("p1", "a1", "玩家一", "token-1", 0)
    second = ArcadePlayer("p2", "a2", "玩家二", "token-2", 1)
    room = ArcadeRoom(
        "DUEL",
        game.key,
        first.id,
        [first, second],
        game.initial_state(),
        options={"firstPlayer": "host"},
    )

    game.start(room)
    assert room.state.current_player_id == first.id

    game.act(room, first, "take", {"count": 3})
    assert room.state.remaining == 12
    assert room.state.current_player_id == second.id

    room.state.remaining = 1
    room.state.current_player_id = second.id
    game.act(room, second, "take", {"count": 1})

    assert room.phase == "finished"
    assert room.winner_player_ids == [second.id]
