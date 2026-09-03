from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query


PROJECT_ROOT = Path(__file__).resolve().parents[4]
PLUGIN_DIR = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom  # noqa: E402
from backend.app.games.plugins import _load_engine_factory  # noqa: E402


ENGINE_FACTORY = _load_engine_factory(PLUGIN_DIR, "plugin-dead-mans-draw")
app = FastAPI(title="Dead Man's Draw live browser harness")


def players(count: int) -> list[ArcadePlayer]:
    return [
        ArcadePlayer(
            id=f"p{index + 1}", account_id=f"browser-{index + 1}",
            name=f"玩家{index + 1}", token_hash=f"token-{index + 1}", seat=index,
        )
        for index in range(count)
    ]


def room_and_engine(count: int, seed: int, *, traits: bool):
    game = ENGINE_FACTORY()
    game.rng = random.Random(seed)
    members = players(count)
    room = ArcadeRoom(
        code=f"DMD{count}", game_key=game.key, host_id=members[0].id,
        players=members, state=game.initial_state(),
        options={
            "firstPlayer": "host", "rulesProfile": "tabletop_base_2015",
            "traitsEnabled": traits,
        },
    )
    game.start(room)
    return game, room, members


def remove_setup_card(room: ArcadeRoom, identifier: str) -> None:
    if identifier in room.state.draw_pile:
        room.state.draw_pile.remove(identifier)
        return
    if identifier in room.state.discard_pile:
        room.state.discard_pile.remove(identifier)
        return
    raise AssertionError(f"准备区中找不到 {identifier}")


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
            {"id": player.id, "name": player.name, "seat": player.seat, "connected": True}
            for player in members
        ],
        "requiredPlayers": len(members), "minimumPlayers": 2,
        "roundNumber": room.state.turn_number,
        "winner": room.winner if finished else None,
        "winnerPlayerIds": list(room.winner_player_ids),
        "winReason": room.win_reason if finished else None,
        "actions": {
            "canStart": False, "canRestart": finished, "canAct": not finished,
            "canKickPlayers": False, "canDissolve": False, "canEditRules": False,
            "canRequestUndo": False, "canRequestDraw": False, "canResolveRequest": False,
        },
        "rematchReadyPlayerIds": [], "request": None,
        "chat": {"maxLength": 200, "messages": []},
        "game": game.view(room, viewer),
    }


def choose_action(game: Any, room: ArcadeRoom, member: ArcadePlayer, rng: random.Random) -> bool:
    view = game.view(room, member)
    legal = view["actions"]
    if legal["canChooseTrait"]:
        game.act(room, member, "choose_trait", {"traitId": view["self"]["traitOffer"][0]["id"]})
        return True
    if legal["canChooseLockerTarget"]:
        target = next(player["id"] for player in view["players"] if player["id"] != member.id and not player["forfeited"])
        game.act(room, member, "choose_locker_target", {"playerId": target})
        return True
    if legal["canResolveEffect"]:
        choice = view["turn"]["pendingChoice"]
        safe = [option for option in choice["options"] if not option["causesImmediateBust"]]
        option = rng.choice(safe or choice["options"])
        game.act(room, member, "resolve_effect", {"choiceId": choice["choiceId"], "optionId": option["optionId"]})
        return True
    if legal["canDraw"] and (
        not legal["canCollect"] or len(view["playArea"]) < 5 and rng.random() < .57
    ):
        game.act(room, member, "draw", {})
        return True
    if legal["canCollect"]:
        game.act(room, member, "collect", {})
        return True
    return False


@app.get("/api/preview")
def preview(count: int = Query(ge=2, le=4)) -> dict[str, Any]:
    game, room, members = room_and_engine(count, 52_000 + count, traits=False)
    desired = ["loot-mermaid-5", "loot-anchor-3", "loot-oracle-3", "loot-key-4"]
    for identifier in desired:
        if identifier in room.state.draw_pile:
            room.state.draw_pile.remove(identifier)
        elif identifier in room.state.discard_pile:
            room.state.discard_pile.remove(identifier)
    room.state.draw_pile[:0] = desired
    for _ in range(3):
        game.act(room, members[0], "draw", {})
    return {"snapshot": snapshot(game, room, members)}


@app.get("/api/scenario")
def scenario(name: str = Query(pattern="^(trait|effect|shared)$")) -> dict[str, Any]:
    if name == "trait":
        game, room, members = room_and_engine(4, 81_001, traits=True)
    elif name == "effect":
        game, room, members = room_and_engine(4, 81_002, traits=False)
        for identifier in ("loot-mermaid-5", "loot-hook-4", "loot-mermaid-9"):
            remove_setup_card(room, identifier)
        room.state.players[members[0].id].bank["mermaid"].append("loot-mermaid-9")
        room.state.draw_pile[:0] = ["loot-mermaid-5", "loot-hook-4"]
        game.act(room, members[0], "draw", {})
        game.act(room, members[0], "draw", {})
        assert room.state.turn.pending_choice is not None
        assert room.state.turn.pending_choice.options[0].causes_immediate_bust is True
    else:
        game, room, members = room_and_engine(4, 81_003, traits=False)
        bank_plan = {
            members[0].id: ("loot-anchor-7", "loot-hook-2"),
            members[1].id: ("loot-cannon-7", "loot-key-2"),
            members[2].id: ("loot-mermaid-5",),
        }
        for player_id, identifiers in bank_plan.items():
            for identifier in identifiers:
                remove_setup_card(room, identifier)
                suit = identifier.split("-")[1]
                room.state.players[player_id].bank[suit].append(identifier)
        room.state.discard_pile.extend(room.state.draw_pile)
        room.state.draw_pile = []
        game._finish_game(room, room.state, "draw-pile-exhausted")
        assert room.state.result.outcome == "shared-win"
    game.assert_invariants(room.state)
    return {"snapshot": snapshot(game, room, members)}


@app.post("/api/autoplay")
def autoplay(count: int = Query(ge=2, le=4)) -> dict[str, Any]:
    seed = 76_000 + count
    game, room, members = room_and_engine(count, seed, traits=True)
    rng = random.Random(seed ^ 0x5A17)
    trace: list[str] = []
    for _ in range(1_200):
        if room.phase == "finished":
            break
        acted = False
        for member in members:
            before = room.state.revision
            if choose_action(game, room, member, rng):
                trace.append(f"{member.id}:{before}->{room.state.revision}:{room.state.phase}")
                acted = True
                break
        if not acted:
            raise HTTPException(500, f"牌局卡死在 {room.state.phase}")
    else:
        raise HTTPException(500, "牌局超过 1200 个动作仍未结束")
    return {
        "snapshot": snapshot(game, room, members),
        "report": {
            "playerCount": count,
            "actionCount": len(trace),
            "turnCount": room.state.turn_number,
            "winnerPlayerIds": list(room.winner_player_ids),
            "result": game.record_state(room)["result"],
            "settlement": [
                {
                    "playerId": member.id,
                    "role": game.player_result(room, member)[0],
                    "won": game.player_result(room, member)[2],
                }
                for member in members
            ],
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8020)
