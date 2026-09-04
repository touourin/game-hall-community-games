from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import random
import sys
import time
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Query


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError  # noqa: E402
from backend.app.games.plugins import _load_engine_factory  # noqa: E402


ENGINE_FACTORY = _load_engine_factory(PLUGIN_DIR, "plugin-halli-galli")
app = FastAPI(title="Halli Galli live browser harness")


@dataclass
class BrowserClock:
    value: int = field(default_factory=lambda: int(time.time() * 1000))

    def __call__(self) -> int:
        return self.value

    def advance(self, milliseconds: int = 400) -> None:
        self.value += milliseconds


@dataclass
class Session:
    game: Any
    room: ArcadeRoom
    members: list[ArcadePlayer]
    clock: BrowserClock


SESSION: Session | None = None
SESSION_LOCK = Lock()


def players(count: int) -> list[ArcadePlayer]:
    names = ["阿梨", "白川", "青禾", "赤岩", "云雀", "墨川"]
    return [
        ArcadePlayer(
            id=f"p{index + 1}",
            account_id=f"browser-{index + 1}",
            name=names[index],
            token_hash=f"token-{index + 1}",
            seat=index,
        )
        for index in range(count)
    ]


def room_and_engine(count: int, seed: int) -> Session:
    game = ENGINE_FACTORY()
    clock = BrowserClock()
    game.rng = random.Random(seed)
    game.clock_ms = clock
    members = players(count)
    room = ArcadeRoom(
        code=f"HALLI{count}",
        game_key=game.key,
        host_id=members[0].id,
        players=members,
        state=game.initial_state(),
        options={"firstPlayer": "host", "rulesProfile": "official_last_bell"},
    )
    game.start(room)
    return Session(game, room, members, clock)


def snapshot(session: Session) -> dict[str, Any]:
    game, room, members = session.game, session.room, session.members
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
            {
                "id": player.id,
                "name": player.name,
                "seat": player.seat,
                "connected": player.connected,
                "isHost": player.id == room.host_id,
            }
            for player in members
        ],
        "requiredPlayers": len(members),
        "minimumPlayers": 2,
        "roundNumber": room.round_number,
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


def dispatch(session: Session, player_id: str, action: str, payload: dict[str, Any] | None = None) -> None:
    body = dict(payload or {})
    state = session.room.state
    body.setdefault("actionId", f"browser-{action}-{session.room.revision}-{state.event_seq}")
    if action == "flip_card":
        body.setdefault("revision", session.room.revision)
        body.setdefault("expectedBoardEpoch", state.board_epoch)
    elif action in {"ring_bell", "settle_no_progress"}:
        body.setdefault("boardEpoch", state.board_epoch)
    if action == "ring_bell":
        body.setdefault("inputMethod", "test")
    session.game.act(session.room, session.room.player(player_id), action, body)
    session.room.revision += 1


def configure_scene(
    session: Session,
    discard_specs: dict[str, list[tuple[str, int]]],
    *,
    last_chance_ids: set[str] | None = None,
    final_duel: bool | None = None,
) -> None:
    module = sys.modules[type(session.game).__module__]
    pool = list(module.ALL_CARDS)

    def take(spec: tuple[str, int]):
        fruit_id, amount = spec
        card = next(card for card in pool if card.fruit_id == fruit_id and card.fruit_count == amount)
        pool.remove(card)
        return card

    for player_id in session.room.state.player_ids:
        player = session.room.state.players[player_id]
        player.draw_pile = []
        player.discard_pile = [take(spec) for spec in discard_specs.get(player_id, [])]
        player.status = "eligible"
        player.elimination_reason = None
    receivers = [
        player_id for player_id in session.room.state.player_ids
        if player_id not in (last_chance_ids or set())
    ]
    for index, card in enumerate(pool):
        session.room.state.players[receivers[index % len(receivers)]].draw_pile.append(card)
    state = session.room.state
    state.stage = "playing"
    state.current_player_id = next(
        player_id for player_id in state.player_ids
        if state.players[player_id].draw_pile
    )
    state.turn_number = 12
    state.board_epoch = 12
    state.earliest_next_flip_at_ms = session.clock()
    state.fruit_totals, state.valid_fruit_ids = module.recompute_fruit_totals(state)
    state.final_duel_armed = len(state.player_ids) == 2 if final_duel is None else final_duel
    state.bell_resolution = None
    state.no_progress_deadline_ms = None
    state.events = []
    state.event_seq = 0
    state.result = None
    state.processed_actions = {}
    state.processed_action_order = []
    session.room.phase = "playing"
    session.room.winner = None
    session.room.winner_player_ids = []
    session.room.win_reason = None
    session.game.assert_invariants(session.room)


def run_autoplay(session: Session) -> tuple[Counter[str], int]:
    members = {player.id: player for player in session.members}
    action_mix: Counter[str] = Counter()
    last_wrong_turn = -1
    for action_count in range(1, 30_001):
        if session.room.phase == "finished":
            return action_mix, action_count - 1
        state = session.room.state
        eligible = [player_id for player_id in state.player_ids if state.players[player_id].status == "eligible"]
        if state.valid_fruit_ids:
            dispatch(session, eligible[action_count % len(eligible)], "ring_bell")
            action_mix["correctBell"] += 1
        elif (
            not state.final_duel_armed
            and len(eligible) > 2
            and state.turn_number > 0
            and state.turn_number % 19 == 0
            and last_wrong_turn != state.turn_number
            and not (state.bell_resolution and state.bell_resolution.get("boardEpoch") == state.board_epoch)
        ):
            candidates = [player_id for player_id in eligible if state.players[player_id].draw_pile]
            if candidates:
                actor = min(candidates, key=lambda player_id: len(state.players[player_id].draw_pile))
                dispatch(session, actor, "ring_bell")
                action_mix["wrongBell"] += 1
            last_wrong_turn = state.turn_number
        elif state.current_player_id:
            session.clock.advance()
            dispatch(session, state.current_player_id, "flip_card")
            action_mix["flip"] += 1
        elif state.no_progress_deadline_ms:
            session.clock.value = state.no_progress_deadline_ms
            dispatch(session, session.members[0].id, "settle_no_progress")
            action_mix["noProgress"] += 1
        else:
            raise RuntimeError("牌局进入未建模的停滞状态")
    raise RuntimeError("牌局超过 30000 个动作仍未结束")


@app.get("/api/preview")
def preview(count: int = Query(ge=2, le=6)) -> dict[str, Any]:
    global SESSION
    with SESSION_LOCK:
        session = room_and_engine(count, 52_000 + count)
        for _ in range(count):
            session.clock.advance()
            dispatch(session, session.room.state.current_player_id, "flip_card")
        SESSION = session
        return {"snapshot": snapshot(session)}


@app.get("/api/scenario")
def scenario(name: str = Query(pattern="^(exact-five|wrong-bell|last-chance|final-duel|final-wrong|last-player|resignation|shared-win|no-progress)$")) -> dict[str, Any]:
    global SESSION
    with SESSION_LOCK:
        if name == "final-duel":
            session = room_and_engine(2, 71_002)
            configure_scene(session, {"p1": [("banana", 2)], "p2": [("banana", 3)]}, final_duel=True)
        elif name == "final-wrong":
            session = room_and_engine(2, 71_005)
            configure_scene(session, {"p1": [("banana", 2)], "p2": [("strawberry", 3)]}, final_duel=True)
        elif name == "last-player":
            session = room_and_engine(3, 71_006)
            configure_scene(
                session,
                {"p1": [("banana", 2)], "p2": [("banana", 3)], "p3": [("lime", 2)]},
                last_chance_ids={"p2", "p3"},
                final_duel=False,
            )
            dispatch(session, "p1", "ring_bell")
        elif name == "resignation":
            session = room_and_engine(2, 71_007)
            configure_scene(session, {"p1": [("banana", 2)], "p2": [("strawberry", 3)]}, final_duel=True)
            dispatch(session, "p2", "resign")
        elif name == "shared-win":
            session = room_and_engine(2, 71_003)
            module = sys.modules[type(session.game).__module__]
            configure_scene(session, {"p1": [("banana", 1)]}, final_duel=True)
            all_cards = session.room.state.players["p1"].draw_pile + session.room.state.players["p2"].draw_pile
            session.room.state.players["p1"].draw_pile = all_cards[:28]
            session.room.state.players["p2"].draw_pile = all_cards[28:]
            session.room.state.fruit_totals, session.room.state.valid_fruit_ids = module.recompute_fruit_totals(session.room.state)
            dispatch(session, "p1", "ring_bell")
        elif name == "no-progress":
            session = room_and_engine(3, 71_004)
            module = sys.modules[type(session.game).__module__]
            configure_scene(session, {"p1": [("banana", 1)], "p2": [("strawberry", 1)], "p3": [("lime", 1)]}, final_duel=False)
            for player_id in session.room.state.player_ids:
                player = session.room.state.players[player_id]
                player.discard_pile = player.draw_pile + player.discard_pile
                player.draw_pile = []
            session.room.state.current_player_id = None
            session.room.state.fruit_totals, session.room.state.valid_fruit_ids = module.recompute_fruit_totals(session.room.state)
            session.game._update_no_progress(session.room.state, session.clock())
            session.clock.value = session.room.state.no_progress_deadline_ms
            dispatch(session, "p1", "settle_no_progress")
        else:
            session = room_and_engine(4, 71_000)
            if name == "exact-five":
                configure_scene(session, {
                    "p1": [("banana", 2)], "p2": [("banana", 3)],
                    "p3": [("strawberry", 4)], "p4": [("plum", 1)],
                }, final_duel=False)
            elif name == "last-chance":
                configure_scene(session, {
                    "p1": [("banana", 2)], "p2": [("banana", 3)],
                    "p3": [("lime", 2)], "p4": [("plum", 1)],
                }, last_chance_ids={"p1"}, final_duel=False)
            else:
                configure_scene(session, {
                    "p1": [("banana", 2)], "p2": [("strawberry", 3)],
                    "p3": [("lime", 2)], "p4": [("plum", 3)],
                }, final_duel=False)
                dispatch(session, "p1", "ring_bell")
        SESSION = session
        return {"snapshot": snapshot(session)}


@app.post("/api/autoplay")
def autoplay(count: int = Query(ge=2, le=6)) -> dict[str, Any]:
    global SESSION
    with SESSION_LOCK:
        session = room_and_engine(count, 76_000 + count)
        action_mix, action_count = run_autoplay(session)
        SESSION = session
        return {
            "snapshot": snapshot(session),
            "report": {
                "playerCount": count,
                "actionCount": action_count,
                "winnerPlayerIds": list(session.room.winner_player_ids),
                "ending": session.room.state.result["reasonCode"],
                "actionMix": dict(action_mix),
            },
        }


@app.post("/api/step")
def step() -> dict[str, Any]:
    with SESSION_LOCK:
        if SESSION is None:
            raise HTTPException(409, "请先载入桌面")
        try:
            state = SESSION.room.state
            if SESSION.room.phase == "finished":
                return {"snapshot": snapshot(SESSION)}
            if state.valid_fruit_ids:
                actor = next(player_id for player_id in state.player_ids if state.players[player_id].status == "eligible")
                dispatch(SESSION, actor, "ring_bell")
            elif state.current_player_id:
                SESSION.clock.advance()
                dispatch(SESSION, state.current_player_id, "flip_card")
            elif state.no_progress_deadline_ms:
                SESSION.clock.value = state.no_progress_deadline_ms
                dispatch(SESSION, SESSION.members[0].id, "settle_no_progress")
            return {"snapshot": snapshot(SESSION)}
        except (GameRuleError, RuntimeError) as error:
            raise HTTPException(409, str(error)) from error


@app.post("/api/action")
def action(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    with SESSION_LOCK:
        if SESSION is None:
            raise HTTPException(409, "请先载入桌面")
        action_name = body.get("action")
        payload = body.get("payload")
        if not isinstance(action_name, str) or not isinstance(payload, dict):
            raise HTTPException(422, "action 和 payload 格式无效")
        try:
            dispatch(SESSION, SESSION.members[0].id, action_name, payload)
        except GameRuleError as error:
            raise HTTPException(409, str(error)) from error
        return {"snapshot": snapshot(SESSION)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8036)
