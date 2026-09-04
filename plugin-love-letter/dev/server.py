from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom  # noqa: E402
from backend.app.games.plugins import _load_engine_factory  # noqa: E402


ENGINE_FACTORY = _load_engine_factory(PLUGIN_DIR, "plugin-love-letter")
app = FastAPI(title="Love Letter live browser harness")


def players(count: int) -> list[ArcadePlayer]:
    names = ["阿梨", "白川", "沉舟", "冬青"]
    return [
        ArcadePlayer(
            id=f"p{index + 1}", account_id=f"browser-{index + 1}",
            name=names[index], token_hash=f"token-{index + 1}", seat=index,
        )
        for index in range(count)
    ]


def room_and_engine(count: int, seed: int):
    game = ENGINE_FACTORY()
    game.rng = random.Random(seed)
    members = players(count)
    room = ArcadeRoom(
        code=f"LOVE{count}", game_key=game.key, host_id=members[0].id,
        players=members, state=game.initial_state(), options={"firstPlayer": "host"},
    )
    game.start(room)
    return game, room, members


def snapshot(game: Any, room: ArcadeRoom, members: list[ArcadePlayer]) -> dict[str, Any]:
    viewer = members[0]
    finished = room.phase == "finished"
    return {
        "revision": room.revision,
        "roomCode": room.code,
        "gameKey": game.key,
        "gameName": game.name,
        "phase": room.phase,
        "statsEligible": True,
        "options": room.options,
        "hostId": viewer.id,
        "self": {"id": viewer.id, "name": viewer.name, "seat": viewer.seat},
        "viewer": {"mode": "player", "id": viewer.id, "name": viewer.name, "targetPlayerId": viewer.id},
        "players": [
            {"id": player.id, "name": player.name, "seat": player.seat, "connected": True, "isHost": player.id == room.host_id}
            for player in members
        ],
        "requiredPlayers": len(members),
        "minimumPlayers": 2,
        "roundNumber": room.round_number,
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


def choose_action(game: Any, room: ArcadeRoom, members_by_id: dict[str, ArcadePlayer]) -> None:
    state = room.state
    if state.stage == "draw":
        actor = members_by_id[state.current_player_id]
        game.act(room, actor, "draw_card", {"turnNumber": state.turn_number})
    elif state.stage == "play":
        actor = members_by_id[state.current_player_id]
        legal = game._legal_card_ids(state.hands[actor.id])
        game.act(room, actor, "play_card", {"cardId": legal[0], "turnNumber": state.turn_number})
    elif state.stage == "choice":
        pending = state.pending_choice
        actor = members_by_id[pending.actor_id]
        payload: dict[str, Any] = {"choiceId": pending.id, "turnNumber": state.turn_number}
        if pending.kind == "guess":
            target_id = pending.candidate_player_ids[0]
            actual = state.hands[target_id][0].type_id
            payload.update({"targetPlayerId": target_id, "cardTypeId": actual if actual != "guard" else "priest"})
        elif pending.kind == "target":
            payload["targetPlayerId"] = pending.candidate_player_ids[0]
        else:
            payload["keepCardId"] = pending.private_card_ids[0]
            payload["bottomCardIds"] = pending.private_card_ids[1:]
        game.act(room, actor, "resolve_choice", payload)
    elif state.stage == "round_summary":
        member = members_by_id[game._match_player_ids(state)[0]]
        game.act(room, member, "next_round", {"roundNumber": state.round_number})
    else:
        raise HTTPException(500, f"牌局卡死在 {state.stage}")


def configure_play(game: Any, room: ArcadeRoom, hand_types: dict[str, list[str]], deck_types: list[str]) -> None:
    module = sys.modules[type(game).__module__]
    Card = module.Card
    state = room.state
    state.hands = {
        player_id: [Card(f"fixture-{player_id}-{index}", type_id) for index, type_id in enumerate(hand_types[player_id])]
        for player_id in state.player_ids
    }
    state.deck = [Card(f"fixture-deck-{index}", type_id) for index, type_id in enumerate(deck_types)]
    state.reserve = Card("fixture-reserve-1", "priest")
    state.face_up_set_aside = []
    state.played = {player_id: [] for player_id in state.player_ids}
    state.out_player_ids = []
    state.protected_player_ids = []
    state.spy_player_ids = []
    state.knowledge = []
    state.current_player_id = "p1"
    state.start_player_id = "p1"
    state.stage = "play"
    state.turn_number = 8
    state.pending_choice = None
    state.round_summary = None


def play_type(game: Any, room: ArcadeRoom, member: ArcadePlayer, type_id: str) -> None:
    selected = next(card for card in room.state.hands[member.id] if card.type_id == type_id)
    game.act(room, member, "play_card", {"cardId": selected.id, "turnNumber": room.state.turn_number})


@app.get("/api/preview")
def preview(count: int = Query(ge=2, le=4)) -> dict[str, Any]:
    game, room, members = room_and_engine(count, 52_000 + count)
    game.act(room, members[0], "draw_card", {"turnNumber": room.state.turn_number})
    return {"snapshot": snapshot(game, room, members)}


@app.get("/api/scenario")
def scenario(name: str = Query(pattern="^(guard|chancellor|sealed)$")) -> dict[str, Any]:
    game, room, members = room_and_engine(4, 81_000)
    if name == "guard":
        configure_play(game, room, {"p1": ["guard", "spy"], "p2": ["queen"], "p3": ["priest"], "p4": ["princess"]}, ["guard", "baron", "king"])
        play_type(game, room, members[0], "guard")
    elif name == "chancellor":
        configure_play(game, room, {"p1": ["chancellor", "king"], "p2": ["queen"], "p3": ["priest"], "p4": ["princess"]}, ["spy", "guard", "baron"])
        play_type(game, room, members[0], "chancellor")
    else:
        configure_play(game, room, {"p1": ["countess", "king"], "p2": ["prince"], "p3": ["priest"], "p4": ["guard"]}, ["spy"])
        play_type(game, room, members[0], "countess")
    return {"snapshot": snapshot(game, room, members)}


@app.post("/api/autoplay")
def autoplay(count: int = Query(ge=2, le=4)) -> dict[str, Any]:
    game, room, members = room_and_engine(count, 76_000 + count)
    members_by_id = {member.id: member for member in members}
    start_round = room.state.round_number
    for action_count in range(1, 2501):
        if room.phase == "finished":
            break
        choose_action(game, room, members_by_id)
    else:
        raise HTTPException(500, "牌局超过 2500 个动作仍未结束")
    return {
        "snapshot": snapshot(game, room, members),
        "report": {
            "playerCount": count,
            "actionCount": action_count,
            "roundCount": room.state.round_number - start_round + 1,
            "winnerPlayerIds": list(room.winner_player_ids),
            "sealedCardRevealed": game.record_state(room)["sealedCardRevealed"],
            "settlement": [
                {"playerId": member.id, "label": game.player_result(room, member)[0], "won": game.player_result(room, member)[2]}
                for member in members
            ],
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8030)
