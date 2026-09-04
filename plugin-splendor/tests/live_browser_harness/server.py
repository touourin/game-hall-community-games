from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query


PROJECT_ROOT = Path(__file__).resolve().parents[4]
PLUGIN_DIR = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom  # noqa: E402


def _helpers():
    module_name = "splendor_live_test_helpers"
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = PLUGIN_DIR / "tests" / "helpers.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Splendor helpers from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


HELPERS = _helpers()
app = FastAPI(title="Splendor live browser harness")


def snapshot(game: Any, room: ArcadeRoom, members: list[ArcadePlayer]) -> dict[str, Any]:
    viewer = members[0]
    finished = room.phase == "finished"
    return {
        "revision": room.state.revision,
        "roomCode": room.code,
        "gameKey": game.key,
        "gameName": game.name,
        "phase": room.phase,
        "statsEligible": True,
        "options": room.options,
        "hostId": viewer.id,
        "self": {"id": viewer.id, "name": viewer.name, "seat": viewer.seat},
        "viewer": {"mode": "player", "id": viewer.id, "targetPlayerId": viewer.id},
        "players": [
            {"id": player.id, "name": player.name, "seat": player.seat, "connected": player.connected}
            for player in members
        ],
        "requiredPlayers": len(members),
        "minimumPlayers": 2,
        "roundNumber": room.state.turn.round_number,
        "winner": room.winner if finished else None,
        "winnerPlayerIds": list(room.winner_player_ids),
        "winReason": room.win_reason if finished else None,
        "actions": {
            "canStart": False,
            "canRestart": finished,
            "canAct": not finished,
            "canKickPlayers": False,
            "canDissolve": False,
            "canEditRules": False,
            "canRequestUndo": False,
            "canRequestDraw": False,
            "canResolveRequest": False,
        },
        "rematchReadyPlayerIds": [],
        "request": None,
        "chat": {"maxLength": 200, "messages": []},
        "game": game.view(room, viewer),
    }


def preview(count: int = Query(default=4, ge=2, le=4)) -> dict[str, Any]:
    game, room, members = HELPERS.started_room(count, 61_000 + count)
    for _ in range(22):
        if room.phase == "finished":
            break
        active = room.player(room.state.turn.active_player_id)
        HELPERS.autoplay_step(game, room, active)
    return {"snapshot": snapshot(game, room, members)}


def scenario(name: str = Query(pattern="^(payment|return|noble|final-round|shared)$")) -> dict[str, Any]:
    game, room, members = HELPERS.started_room(4, 72_000)
    if name == "payment":
        card_id = "dev-white-1-04"
        HELPERS.put_market_card(room.state, card_id)
        HELPERS.set_player_pieces(room.state, members[0].id, {
            "blue": 2, "black": 2, "gold": 2,
        })
    elif name == "return":
        HELPERS.set_player_pieces(room.state, members[0].id, {
            "white": 1, "blue": 2, "green": 2, "red": 2, "black": 1, "gold": 1,
        })
        HELPERS.act(game, room, members[0], "take_different", colors=["white", "blue", "green"])
    elif name == "noble":
        pair = list(HELPERS.NOBLES)[:2]
        HELPERS.set_available_nobles(room.state, pair)
        requirements = {
            color: max(HELPERS.NOBLES[pair[0]]["requirement"][color], HELPERS.NOBLES[pair[1]]["requirement"][color])
            for color in HELPERS.STANDARD_COLORS
        }
        for color, amount in requirements.items():
            HELPERS.grant_bonus(room.state, members[0].id, color, amount)
        HELPERS.act(game, room, members[0], "take_same", color="black")
    elif name == "final-round":
        room.state.turn.end_triggered_by = members[0].id
        room.state.turn.final_turn_player_id = members[-1].id
        HELPERS.force_turn(room.state, members[1].id)
    else:
        first, second = HELPERS.disjoint_card_sets_with_score(15, 4, 2)
        HELPERS.grant_cards(room.state, members[0].id, first)
        HELPERS.grant_cards(room.state, members[1].id, second)
        game._finish_game(room, room.state, "final-round-complete")
    game.assert_invariants(room.state)
    return {"snapshot": snapshot(game, room, members)}


@app.get("/api/preview")
def preview_api(count: int = Query(default=4, ge=2, le=4)) -> dict[str, Any]:
    return preview(count)


@app.get("/api/scenario")
def scenario_api(name: str = Query(pattern="^(payment|return|noble|final-round|shared)$")) -> dict[str, Any]:
    return scenario(name)


@app.post("/api/autoplay")
def autoplay(count: int = Query(ge=2, le=4)) -> dict[str, Any]:
    game, room, members, trace = HELPERS.autoplay_game(count, 83_000 + count)
    return {
        "snapshot": snapshot(game, room, members),
        "report": {
            "playerCount": count,
            "actionCount": len(trace),
            "turnCount": room.state.turn.action_number,
            "winnerPlayerIds": list(room.winner_player_ids),
            "summaryZh": room.state.result.summary_zh,
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8022)
