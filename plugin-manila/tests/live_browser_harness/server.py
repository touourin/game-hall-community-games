from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query


PROJECT_ROOT = Path(__file__).resolve().parents[4]
PLUGIN_DIR = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom  # noqa: E402
from backend.app.games.plugins import _load_engine_factory  # noqa: E402


ENGINE_FACTORY = _load_engine_factory(PLUGIN_DIR, "plugin-manila")
app = FastAPI(title="Manila live browser harness")


def players(count: int) -> list[ArcadePlayer]:
    return [
        ArcadePlayer(
            id=f"p{index + 1}",
            account_id=f"browser-{index + 1}",
            name=f"玩家{index + 1}",
            token_hash=f"token-{index + 1}",
            seat=index,
        )
        for index in range(count)
    ]


def room_and_engine(count: int, seed: int = 7103):
    engine = ENGINE_FACTORY()
    engine.rng = random.Random(seed)
    members = players(count)
    room = ArcadeRoom(
        code=f"MNL{count}",
        game_key=engine.key,
        host_id=members[0].id,
        players=members,
        state=engine.initial_state(),
        options={"firstPlayer": "host"},
    )
    engine.start(room)
    return engine, room, members


def act(engine: Any, room: ArcadeRoom, member: ArcadePlayer, action: str, **payload: Any) -> None:
    engine.act(
        room,
        member,
        action,
        {"voyageNumber": room.state.voyage_number, **payload},
    )


def snapshot(engine: Any, room: ArcadeRoom, members: list[ArcadePlayer]) -> dict[str, Any]:
    viewer = members[0]
    return {
        "revision": room.revision,
        "roomCode": room.code,
        "gameKey": engine.key,
        "gameName": engine.name,
        "phase": room.phase,
        "statsEligible": True,
        "options": room.options,
        "hostId": viewer.id,
        "self": {"id": viewer.id, "name": viewer.name, "seat": viewer.seat},
        "viewer": {"mode": "player", "id": viewer.id, "targetPlayerId": viewer.id},
        "players": [
            {
                "id": member.id,
                "name": member.name,
                "seat": member.seat,
                "connected": True,
            }
            for member in members
        ],
        "requiredPlayers": len(members),
        "minimumPlayers": 3,
        "roundNumber": room.round_number,
        "winner": room.winner,
        "winnerPlayerIds": list(room.winner_player_ids),
        "winReason": room.win_reason,
        "actions": {
            "canStart": False,
            "canRestart": room.phase == "finished",
            "canAct": room.phase == "playing",
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
        "game": engine.view(room, viewer),
    }


def launch(engine: Any, room: ArcadeRoom, members: list[ArcadePlayer]) -> None:
    while room.state.stage == "auction":
        act(engine, room, room.player(room.state.current_player_id), "pass_auction")
    master = room.player(room.state.harbor_master_id)
    act(engine, room, master, "skip_share")
    act(
        engine,
        room,
        master,
        "select_cargo",
        assignments=[
            {"puntId": "punt-1", "commodityId": "ginseng"},
            {"puntId": "punt-2", "commodityId": "silk"},
            {"puntId": "punt-3", "commodityId": "jade"},
        ],
    )
    act(
        engine,
        room,
        master,
        "set_start_positions",
        assignments=[
            {"puntId": "punt-1", "laneId": "lane-1", "position": 2},
            {"puntId": "punt-2", "laneId": "lane-2", "position": 3},
            {"puntId": "punt-3", "laneId": "lane-3", "position": 4},
        ],
    )


def take_worker(state: Any, player_id: str):
    from importlib import import_module

    worker_type = import_module(state.__class__.__module__).WorkerPlacement
    ledger = state.players[player_id]
    worker_id = ledger.available_worker_ids.pop(0)
    return worker_type(worker_id=worker_id, player_id=player_id)


def decorate_table(engine: Any, room: ArcadeRoom, members: list[ArcadePlayer]) -> None:
    state = room.state
    assignments = [
        (members[0].id, "punt-1"),
        (members[1].id, "punt-2"),
        (members[2].id, "port-A"),
        (members[0].id, "insurance"),
    ]
    if len(members) >= 4:
        assignments.append((members[3].id, "pirate-captain"))
    if len(members) >= 5:
        assignments.append((members[4].id, "pilot-large"))
    for player_id, target_id in assignments:
        option = next(
            option
            for option in engine._placement_options(state, player_id)
            if option["targetId"] == target_id
        )
        placement = take_worker(state, player_id)
        placement.slot_index = option.get("slotIndex")
        engine._occupy_target(state, option, placement)
    state.current_player_id = members[0].id
    state.stage = "placement"


@app.get("/api/preview")
def preview(count: int = Query(default=5, ge=3, le=5)) -> dict[str, Any]:
    engine, room, members = room_and_engine(count, 8100 + count)
    launch(engine, room, members)
    decorate_table(engine, room, members)
    return {"snapshot": snapshot(engine, room, members)}


@app.get("/api/scenario")
def scenario(name: str = Query(pattern="^(auction|placement|movement|pirate|pilot|settlement|finished)$")) -> dict[str, Any]:
    engine, room, members = room_and_engine(5, 9100)
    if name == "auction":
        return {"snapshot": snapshot(engine, room, members)}
    launch(engine, room, members)
    decorate_table(engine, room, members)
    state = room.state
    if name == "placement":
        return {"snapshot": snapshot(engine, room, members)}
    if name == "movement":
        state.stage = "move_order"
        state.current_player_id = state.harbor_master_id
        state.movement_round = 2
        state.die_results = {"punt-1": 3, "punt-2": 5, "punt-3": 2}
        state.punts["punt-1"].position = 8
        state.punts["punt-2"].position = 11
        state.punts["punt-3"].position = 12
        return {"snapshot": snapshot(engine, room, members)}
    if name == "pirate":
        state.punts["punt-2"].position = 13
        state.punts["punt-3"].position = 13
        captain = state.special_workers["pirate-captain"]
        state.stage = "pirate_board"
        state.current_player_id = captain.player_id
        state.pirate_board_queue = [captain.worker_id]
        return {"snapshot": snapshot(engine, room, members)}
    if name == "pilot":
        pilot = state.special_workers["pilot-large"]
        state.stage = "pilot_large"
        state.current_player_id = pilot.player_id
        state.punts["punt-1"].position = 10
        state.punts["punt-2"].position = 12
        state.punts["punt-3"].position = 7
        return {"snapshot": snapshot(engine, room, members)}
    if name == "settlement":
        for punt in state.punts.values():
            punt.occupants.clear()
        state.port_slots[0].punt_id = "punt-1"
        state.punts["punt-1"].status = "port"
        state.punts["punt-1"].destination_slot = "port-A"
        state.punts["punt-1"].occupants = [take_worker(state, "p1"), take_worker(state, "p2")]
        state.shipyard_slots[0].punt_id = "punt-2"
        state.punts["punt-2"].status = "shipyard"
        state.punts["punt-2"].destination_slot = "shipyard-A"
        state.shipyard_slots[0].bettor = take_worker(state, "p3")
        state.shipyard_slots[1].punt_id = "punt-3"
        state.punts["punt-3"].status = "shipyard"
        state.punts["punt-3"].destination_slot = "shipyard-B"
        engine._settle_voyage(room, state)
        return {"snapshot": snapshot(engine, room, members)}

    for ledger in state.players.values():
        ledger.share_ids = []
        ledger.mortgaged_share_ids = []
        ledger.cash = 30
    for slot in state.port_slots + state.shipyard_slots:
        slot.bettor = None
        slot.punt_id = None
    state.special_workers = {key: None for key in state.special_workers}
    state.market_values["ginseng"] = 20
    state.port_slots[0].punt_id = "punt-1"
    state.punts["punt-1"].status = "port"
    state.punts["punt-1"].occupants.clear()
    state.punts["punt-2"].status = "shipyard"
    state.punts["punt-3"].status = "shipyard"
    engine._settle_voyage(room, state)
    return {"snapshot": snapshot(engine, room, members)}


def autoplay_game(count: int) -> tuple[Any, ArcadeRoom, list[ArcadePlayer], int]:
    engine, room, members = room_and_engine(count, 12000 + count)
    action_count = 0
    while room.phase == "playing" and action_count < 900:
        state = room.state
        member = room.player(state.current_player_id)
        if state.stage == "auction":
            act(engine, room, member, "pass_auction")
        elif state.stage == "harbor_share":
            act(engine, room, member, "skip_share")
        elif state.stage == "harbor_load":
            act(
                engine,
                room,
                member,
                "select_cargo",
                assignments=[
                    {"puntId": "punt-1", "commodityId": "ginseng"},
                    {"puntId": "punt-2", "commodityId": "nutmeg"},
                    {"puntId": "punt-3", "commodityId": "silk"},
                ],
            )
        elif state.stage == "harbor_launch":
            act(
                engine,
                room,
                member,
                "set_start_positions",
                assignments=[
                    {"puntId": "punt-1", "laneId": "lane-1", "position": 2},
                    {"puntId": "punt-2", "laneId": "lane-2", "position": 3},
                    {"puntId": "punt-3", "laneId": "lane-3", "position": 4},
                ],
            )
        elif state.stage == "placement":
            act(engine, room, member, "pass_placement")
        elif state.stage == "roll":
            act(engine, room, member, "roll_dice")
        elif state.stage == "move_order":
            act(
                engine,
                room,
                member,
                "choose_move_order",
                puntIds=[
                    punt_id
                    for punt_id in ("punt-1", "punt-2", "punt-3")
                    if state.punts[punt_id].status == "sailing"
                ],
            )
        elif state.stage == "voyage_summary":
            act(engine, room, member, "next_voyage")
        else:
            raise RuntimeError(f"autoplay stopped at unexpected stage {state.stage}")
        action_count += 1
    if room.phase != "finished":
        raise RuntimeError("autoplay exceeded 900 actions")
    return engine, room, members, action_count


@app.post("/api/autoplay")
def autoplay(count: int = Query(ge=3, le=5)) -> dict[str, Any]:
    engine, room, members, action_count = autoplay_game(count)
    return {
        "snapshot": snapshot(engine, room, members),
        "report": {
            "playerCount": count,
            "actionCount": action_count,
            "voyageCount": room.state.voyage_number,
            "winnerPlayerIds": list(room.winner_player_ids),
            "market": dict(room.state.market_values),
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8031)
