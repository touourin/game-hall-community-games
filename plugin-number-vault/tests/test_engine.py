from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom


def engine():
    entry = Path(__file__).resolve().parents[1] / "backend" / "plugin.py"
    spec = importlib.util.spec_from_file_location("number_vault_example", entry)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.create_engine()


def test_secret_stays_hidden_until_the_challenge_finishes() -> None:
    game = engine()
    player = ArcadePlayer("p1", "a1", "玩家一", "token", 0)
    room = ArcadeRoom("SOLO", game.key, player.id, [player], game.initial_state())

    game.start(room)
    secret = room.state.secret

    assert game.view(room, player)["answer"] is None
    game.act(room, player, "guess", {"value": secret})
    view = game.view(room, player)

    assert room.phase == "finished"
    assert view["answer"] == secret
    assert view["won"] is True
