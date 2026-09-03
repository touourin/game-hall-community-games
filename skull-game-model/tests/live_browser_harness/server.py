from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
THIRD_PARTY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom  # noqa: E402
from backend.app.games.plugins import discover_game_plugins  # noqa: E402


ENGINE_FACTORY = next(
    plugin.registration.create_engine
    for plugin in discover_game_plugins(THIRD_PARTY_ROOT)
    if plugin.registration.key == "plugin-skull"
)

app = FastAPI(title="Skull live browser harness")


def _players(count: int) -> list[ArcadePlayer]:
    return [
        ArcadePlayer(
            id=f"p{index + 1}",
            account_id=f"browser-account-{index + 1}",
            name=f"玩家{index + 1}",
            token_hash=f"browser-token-{index + 1}",
            seat=index,
        )
        for index in range(count)
    ]


def _choose_action(
    view: dict[str, Any],
    rng: random.Random,
) -> tuple[str, dict[str, Any]]:
    actions = set(view["actions"])
    if "commit_initial" in actions:
        return "commit_initial", {"discId": rng.choice(view["hand"])["id"]}
    if "choose_penalty" in actions:
        return "choose_penalty", {
            "slotId": rng.choice(view["round"]["penaltySlots"]),
        }
    if "choose_self_penalty" in actions:
        return "choose_self_penalty", {
            "discId": rng.choice(view["round"]["selfPenaltyCandidates"])["id"],
        }
    if "choose_next_first" in actions:
        return "choose_next_first", {
            "playerId": rng.choice(
                view["round"]["eligibleNextFirstPlayerIds"],
            ),
        }
    if "reveal_disc" in actions:
        return "reveal_disc", {
            "ownerId": rng.choice(view["legalRevealOwnerIds"]),
        }
    if "place_disc" in actions and (
        "open_bid" not in actions or rng.random() < 0.58
    ):
        return "place_disc", {"discId": rng.choice(view["hand"])["id"]}
    if "open_bid" in actions:
        return "open_bid", {
            "count": rng.randint(view["minimumBid"], view["maximumBid"]),
        }
    if "raise_bid" in actions and (
        "pass_bid" not in actions or rng.random() < 0.56
    ):
        return "raise_bid", {
            "count": rng.randint(view["minimumBid"], view["maximumBid"]),
        }
    if "pass_bid" in actions:
        return "pass_bid", {}
    raise RuntimeError(f"没有可执行动作：{view['phase']} / {sorted(actions)}")


def _snapshot(
    engine: Any,
    room: ArcadeRoom,
    players: list[ArcadePlayer],
    viewer: ArcadePlayer | None = None,
) -> dict[str, Any]:
    viewer = viewer or players[0]
    game_view = engine.view(room, viewer)
    finished = room.phase == "finished"
    return {
        "revision": len(room.state.public_history),
        "roomCode": room.code,
        "gameKey": "plugin-skull",
        "gameName": "骷髅牌",
        "phase": room.phase,
        "statsEligible": room.stats_eligible,
        "options": room.options,
        "hostId": room.host_id,
        "self": {"id": viewer.id, "name": viewer.name, "seat": viewer.seat},
        "viewer": {
            "mode": "player",
            "id": viewer.id,
            "name": viewer.name,
            "targetPlayerId": viewer.id,
        },
        "players": [
            {
                "id": player.id,
                "name": player.name,
                "seat": player.seat,
                "connected": True,
                "isHost": player.id == room.host_id,
            }
            for player in players
        ],
        "requiredPlayers": len(players),
        "minimumPlayers": 3,
        "roundNumber": room.state.round.number,
        "winner": "skull" if finished else None,
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
        "game": game_view,
    }


@app.post("/api/temporary-pass")
def temporary_pass_scenario() -> dict[str, Any]:
    """Stop at the moment a previous passer is reactivated by a raise."""
    engine = ENGINE_FACTORY()
    engine.rng = random.Random(7_300_099)
    players = _players(3)
    room = ArcadeRoom(
        code="REJOIN",
        game_key=engine.key,
        host_id=players[0].id,
        players=players,
        state=engine.initial_state(),
        options={"firstPlayer": "host", "lastChanceEnabled": True},
    )
    engine.start(room)

    def flower_id(player_id: str) -> str:
        return next(
            disc.id for disc in room.state.players[player_id].hand
            if disc.kind == "flower"
        )

    # The first player commits last, then everyone places one extra flower so
    # the scenario can raise without reaching the table maximum.
    for player in (players[1], players[2], players[0]):
        engine.act(
            room,
            player,
            "commit_initial",
            {"discId": flower_id(player.id)},
        )
    for player in players:
        engine.act(
            room,
            player,
            "place_disc",
            {"discId": flower_id(player.id)},
        )

    engine.act(room, players[0], "open_bid", {"count": 1})
    engine.act(room, players[1], "pass_bid", {})
    declined_before_raise = list(room.state.round.passed_player_ids)
    engine.act(room, players[2], "raise_bid", {"count": 2})
    declined_after_raise = list(room.state.round.passed_player_ids)
    engine.act(room, players[0], "pass_bid", {})

    reactivated = engine.view(room, players[1])
    if (
        declined_before_raise != [players[1].id]
        or declined_after_raise
        or room.state.round.current_player_id != players[1].id
        or not {"raise_bid", "pass_bid"}.issubset(reactivated["actions"])
    ):
        raise HTTPException(500, "暂不跟价玩家未在加价后恢复行动资格")

    return {
        "snapshot": _snapshot(engine, room, players, players[1]),
        "report": {
            "playerCount": 3,
            "actionCount": 10,
            "phaseTrace": ["round_setup", "placement", "bidding"],
            "resultReason": "temporary_pass_reactivated",
            "winnerPlayerIds": [],
            "settlement": [],
            "summary": "规则通过 · 玩家2暂不跟价后，因玩家3加价而重新获得行动",
        },
    }


@app.post("/api/autoplay")
def autoplay(count: int = Query(ge=3, le=6)) -> dict[str, Any]:
    engine = ENGINE_FACTORY()
    seed = 7_300_000 + count
    engine.rng = random.Random(seed)
    action_rng = random.Random(seed ^ 0x5A17)
    players = _players(count)
    room = ArcadeRoom(
        code=f"E2E{count}",
        game_key=engine.key,
        host_id=players[0].id,
        players=players,
        state=engine.initial_state(),
        options={"firstPlayer": "random", "lastChanceEnabled": True},
    )
    engine.start(room)

    phase_trace = [room.state.phase]
    action_trace: list[str] = []
    for _ in range(1_500):
        if room.phase == "finished":
            break
        actors = [
            (player, engine.view(room, player))
            for player in players
            if engine.view(room, player)["actions"]
        ]
        if not actors:
            raise HTTPException(500, f"牌局卡死在 {room.state.phase}")
        actor, view = action_rng.choice(actors)
        action, payload = _choose_action(view, action_rng)
        engine.act(room, actor, action, payload)
        action_trace.append(f"{actor.id}:{action}")
        if phase_trace[-1] != room.state.phase:
            phase_trace.append(room.state.phase)
    else:
        raise HTTPException(500, "牌局超过 1500 个动作仍未结束")

    record = engine.record_state(room)
    settlement = []
    for player in players:
        role, score_kind, won = engine.player_result(room, player)
        settlement.append({
            "playerId": player.id,
            "role": role,
            "scoreKind": score_kind,
            "won": won,
        })

    return {
        "snapshot": _snapshot(engine, room, players),
        "report": {
            "playerCount": count,
            "actionCount": len(action_trace),
            "phaseTrace": phase_trace,
            "resultReason": room.state.result_reason,
            "winnerPlayerIds": list(room.winner_player_ids),
            "settlement": settlement,
            "record": record,
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8019)
