from __future__ import annotations

import argparse
import json
import random
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
HALL_ROOT = PLUGIN_ROOT.parents[1]
if str(HALL_ROOT) not in sys.path:
    sys.path.insert(0, str(HALL_ROOT))

from backend.app.games.plugin_api import (  # noqa: E402
    ArcadePlayer,
    ArcadeRoom,
    GameRuleError,
    utc_now_iso,
)
from backend.app.games.plugins import _load_engine_factory  # noqa: E402


PLAYER_NAMES = (
    "红队玩家",
    "蓝队玩家",
    "黄队玩家",
    "绿队玩家",
    "橙队玩家",
    "青队玩家",
    "紫队玩家",
    "黑金玩家",
)


class LocalArena:
    """Small local host that exercises the real plugin engine."""

    def __init__(self, player_count: int = 2, seed: int = 20260831) -> None:
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.paused = False
        self._seed = seed
        self._round_seed = 0
        self._factory = _load_engine_factory(PLUGIN_ROOT, "plugin-bomb-people")
        self.engine: Any = None
        self.room: ArcadeRoom
        self.map_keys: set[str] = set()
        self.reset(player_count=player_count)

    def _new_engine(self) -> Any:
        engine = self._factory()
        engine.rng = random.Random(self._seed + self._round_seed)
        self._round_seed += 1
        return engine

    @staticmethod
    def _players(player_count: int) -> list[ArcadePlayer]:
        if not 2 <= player_count <= 8:
            raise ValueError("本地测试人数必须为 2–8 人")
        return [
            ArcadePlayer(
                id=f"local-p{seat + 1}",
                account_id=f"local-a{seat + 1}",
                name=PLAYER_NAMES[seat],
                token_hash="local-test-only",
                seat=seat,
            )
            for seat in range(player_count)
        ]

    def reset(self, player_count: int = 2, map_key: str | None = None) -> dict[str, Any]:
        with self.lock:
            self.engine = self._new_engine()
            players = self._players(int(player_count))
            state = self.engine.initial_state()
            room = ArcadeRoom(
                code="LOCAL",
                game_key=self.engine.key,
                host_id=players[0].id,
                players=players,
                state=state,
                name="炸弹超人本地测试房",
                options={"listed": False, "allowGuests": True, "allowSpectators": True},
                listed=False,
            )
            catalog = self.engine.view(room, players[0])["mapCatalog"]
            self.map_keys = {entry["key"] for entry in catalog}
            if map_key:
                if map_key not in self.map_keys:
                    raise ValueError("请选择有效地图")
                state.selected_map = map_key
            self.room = room
            self.paused = False
            return self.snapshot(players[0].id)

    def _player(self, player_id: str | None) -> ArcadePlayer:
        target = player_id or self.room.players[0].id
        try:
            return self.room.player(target)
        except KeyError as error:
            raise ValueError("本地测试玩家不存在") from error

    def _prepare_round(self) -> None:
        self.room.winner = None
        self.room.winner_player_ids = []
        self.room.win_reason = None
        self.room.ended_at = None
        self.room.started_at = utc_now_iso()
        self.room.rematch_ready_ids.clear()
        self.room.round_number += 1

    def start(self, viewer_id: str | None = None) -> dict[str, Any]:
        with self.lock:
            if self.room.phase != "lobby":
                raise ValueError("只有等待房可以开始游戏")
            self._prepare_round()
            self.engine.start(self.room)
            self.room.revision += 1
            return self.snapshot(viewer_id)

    def restart(self, viewer_id: str | None = None) -> dict[str, Any]:
        with self.lock:
            if self.room.phase != "finished":
                raise ValueError("本局结束后才能重新开始")
            self._prepare_round()
            self.engine.start(self.room)
            self.room.revision += 1
            return self.snapshot(viewer_id)

    def action(
        self,
        viewer_id: str,
        action_name: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self.lock:
            player = self._player(viewer_id)
            if not isinstance(action_name, str) or not action_name:
                raise ValueError("缺少动作名称")
            self.engine.act(self.room, player, action_name, payload or {})
            self.room.revision += 1
            return self.snapshot(viewer_id)

    def set_paused(self, paused: bool, viewer_id: str | None = None) -> dict[str, Any]:
        with self.lock:
            self.paused = bool(paused)
            return self.snapshot(viewer_id)

    def jump_to_collapse(self, viewer_id: str | None = None) -> dict[str, Any]:
        with self.lock:
            if self.room.phase != "playing":
                raise ValueError("请先开始游戏")
            state = self.room.state
            if state.stage == "countdown":
                state.stage_ticks_remaining = 1
                self.engine.tick(self.room)
            if self.room.phase != "playing":
                return self.snapshot(viewer_id)
            state.round_ticks_remaining = 1
            state.stage_ticks_remaining = 1
            self.engine.tick(self.room)
            self.room.revision += 1
            return self.snapshot(viewer_id)

    def finish_for_viewer(self, viewer_id: str) -> dict[str, Any]:
        with self.lock:
            if self.room.phase != "playing":
                raise ValueError("请先开始游戏")
            self._player(viewer_id)
            winner = self.room.state.players.get(viewer_id)
            if winner is None:
                raise ValueError("当前玩家尚未进入本局")
            if not winner.alive:
                winner.alive = True
                winner.eliminated_tick = None
                winner.eliminated_by = None
                winner.elimination_reason = None
                winner.input_mask = 0
            for player in list(self.room.players):
                if player.id != viewer_id and self.room.phase == "playing":
                    self.engine.manual_forfeit(self.room, player)
            self.room.revision += 1
            return self.snapshot(viewer_id)

    def _item_kinds(self, viewer: ArcadePlayer) -> set[str]:
        return set(self.engine.view(self.room, viewer)["itemLabels"])

    def grant_item(self, viewer_id: str, kind: str) -> dict[str, Any]:
        with self.lock:
            viewer = self._player(viewer_id)
            if self.room.phase != "playing" or viewer.id not in self.room.state.players:
                raise ValueError("请先开始游戏")
            if kind not in self._item_kinds(viewer):
                raise ValueError("请选择有效道具")
            actor = self.room.state.players[viewer.id]
            if not actor.alive:
                raise ValueError("阵亡玩家不能获得调试道具")
            self.engine._grant_item(
                self.room.state,
                actor,
                kind,
                room=self.room,
                announce=True,
            )
            self.room.revision += 1
            return self.snapshot(viewer_id)

    def spawn_item(self, viewer_id: str, kind: str) -> dict[str, Any]:
        with self.lock:
            viewer = self._player(viewer_id)
            if self.room.phase != "playing" or viewer.id not in self.room.state.players:
                raise ValueError("请先开始游戏")
            if kind not in self._item_kinds(viewer):
                raise ValueError("请选择有效道具")
            state = self.room.state
            actor = state.players[viewer.id]
            occupied = {
                (bomb.x, bomb.y) for bomb in state.bombs.values()
            } | {
                (item.x, item.y) for item in state.items.values()
            } | {
                (other.x, other.y) for other in state.players.values() if other.alive
            } | set(state.flames)
            candidates = sorted(
                (
                    (abs(x - actor.x) + abs(y - actor.y), y, x)
                    for y, row in enumerate(state.board)
                    for x, cell in enumerate(row)
                    if cell == 0 and (x, y) not in occupied
                ),
                key=lambda entry: entry,
            )
            if not candidates:
                raise ValueError("当前地图没有可投放道具的空格")
            _, y, x = candidates[0]
            self.engine._spawn_item(state, kind, x, y, "local-test")
            self.room.revision += 1
            result = self.snapshot(viewer_id)
            result["localTestSpawn"] = {"kind": kind, "x": x, "y": y}
            return result

    def snapshot(self, viewer_id: str | None = None) -> dict[str, Any]:
        with self.lock:
            viewer = self._player(viewer_id)
            game = self.engine.view(self.room, viewer)
            actor = self.room.state.players.get(viewer.id)
            can_act = (
                self.room.phase == "playing"
                and actor is not None
                and actor.alive
            )
            return {
                "revision": self.room.revision,
                "roomCode": self.room.code,
                "roomName": self.room.name,
                "gameKey": self.room.game_key,
                "gameName": self.engine.name,
                "phase": self.room.phase,
                "statsEligible": False,
                "options": dict(self.room.options),
                "hostId": self.room.host_id,
                "self": {
                    "id": viewer.id,
                    "accountId": viewer.account_id,
                    "name": viewer.name,
                    "seat": viewer.seat,
                    "isGuest": False,
                },
                "viewer": {
                    "mode": "player",
                    "id": viewer.id,
                    "accountId": viewer.account_id,
                    "name": viewer.name,
                    "targetPlayerId": viewer.id,
                },
                "players": [
                    {
                        "id": player.id,
                        "accountId": player.account_id,
                        "name": player.name,
                        "seat": player.seat,
                        "connected": player.connected,
                        "isHost": player.id == self.room.host_id,
                        "isGuest": False,
                    }
                    for player in self.room.players
                ],
                "requiredPlayers": 2,
                "minimumPlayers": 2,
                "roundNumber": self.room.round_number,
                "winner": self.room.winner,
                "winnerPlayerIds": list(self.room.winner_player_ids),
                "winReason": self.room.win_reason,
                "actions": {
                    "canStart": self.room.phase == "lobby" and viewer.id == self.room.host_id,
                    "canRestart": self.room.phase == "finished",
                    "canAct": can_act,
                    "canKickPlayers": False,
                    "canDissolve": False,
                    "canEditRules": False,
                    "canRequestUndo": False,
                    "canRequestDraw": False,
                    "canResolveRequest": False,
                },
                "rematchReadyPlayerIds": [],
                "request": None,
                "chat": {"maxLength": 0, "messages": []},
                "game": game,
            }

    def payload(self, viewer_id: str | None = None, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ok": True,
            "snapshot": snapshot or self.snapshot(viewer_id),
            "test": {"paused": self.paused},
        }

    def tick_once(self) -> bool:
        with self.lock:
            if self.paused or self.room.phase != "playing":
                return False
            changed = bool(self.engine.tick(self.room))
            if changed:
                self.room.revision += 1
            return changed

    def run_ticks(self) -> None:
        interval = 1 / max(1, int(self.engine.realtime_tick_rate))
        deadline = time.perf_counter()
        while not self.stop_event.is_set():
            deadline += interval
            self.tick_once()
            self.stop_event.wait(max(0.0, deadline - time.perf_counter()))
            if time.perf_counter() - deadline > interval * 4:
                deadline = time.perf_counter()

    def stop(self) -> None:
        self.stop_event.set()


class LocalRequestHandler(BaseHTTPRequestHandler):
    server_version = "BombPeopleLocalTest/1.0"

    @property
    def arena(self) -> LocalArena:
        return self.server.arena  # type: ignore[attr-defined]

    def _json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 128_000:
            raise ValueError("请求内容过大")
        raw = self.rfile.read(length) if length else b"{}"
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("请求必须是 JSON 对象")
        return payload

    def _send(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _viewer_from_query(self) -> str | None:
        query = parse_qs(urlparse(self.path).query)
        values = query.get("viewerId", [])
        return values[0] if values else None

    def do_GET(self) -> None:  # noqa: N802
        try:
            path = urlparse(self.path).path
            if path == "/api/health":
                self._send(HTTPStatus.OK, {"ok": True, "service": "bomb-people-local-test"})
                return
            if path == "/api/snapshot":
                viewer_id = self._viewer_from_query()
                self._send(HTTPStatus.OK, self.arena.payload(viewer_id))
                return
            self._send(HTTPStatus.NOT_FOUND, {"ok": False, "error": "接口不存在"})
        except (GameRuleError, ValueError, KeyError, json.JSONDecodeError) as error:
            self._send(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
        except Exception as error:  # pragma: no cover - diagnostic server boundary
            self.log_error("Unhandled GET error: %r", error)
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": "本地测试服务异常"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            path = urlparse(self.path).path
            body = self._json_body()
            viewer_id = body.get("viewerId")
            if viewer_id is not None and not isinstance(viewer_id, str):
                raise ValueError("viewerId 格式不正确")

            if path == "/api/reset":
                snapshot = self.arena.reset(
                    int(body.get("playerCount", 2)),
                    body.get("mapKey"),
                )
            elif path == "/api/start":
                snapshot = self.arena.start(viewer_id)
            elif path == "/api/restart":
                snapshot = self.arena.restart(viewer_id)
            elif path == "/api/action":
                if not isinstance(viewer_id, str):
                    raise ValueError("缺少当前测试玩家")
                action_name = body.get("action")
                payload = body.get("payload", {})
                if not isinstance(payload, dict):
                    raise ValueError("动作参数必须是对象")
                snapshot = self.arena.action(viewer_id, action_name, payload)
            elif path == "/api/debug/pause":
                snapshot = self.arena.set_paused(bool(body.get("paused")), viewer_id)
            elif path == "/api/debug/collapse":
                snapshot = self.arena.jump_to_collapse(viewer_id)
            elif path == "/api/debug/finish":
                if not isinstance(viewer_id, str):
                    raise ValueError("缺少当前测试玩家")
                snapshot = self.arena.finish_for_viewer(viewer_id)
            elif path == "/api/debug/grant-item":
                if not isinstance(viewer_id, str):
                    raise ValueError("缺少当前测试玩家")
                snapshot = self.arena.grant_item(viewer_id, body.get("kind"))
            elif path == "/api/debug/spawn-item":
                if not isinstance(viewer_id, str):
                    raise ValueError("缺少当前测试玩家")
                snapshot = self.arena.spawn_item(viewer_id, body.get("kind"))
            else:
                self._send(HTTPStatus.NOT_FOUND, {"ok": False, "error": "接口不存在"})
                return

            self._send(HTTPStatus.OK, self.arena.payload(viewer_id, snapshot))
        except (GameRuleError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            self._send(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
        except Exception as error:  # pragma: no cover - diagnostic server boundary
            self.log_error("Unhandled POST error: %r", error)
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": "本地测试服务异常"})


class LocalHttpServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: tuple[str, int], arena: LocalArena) -> None:
        self.arena = arena
        super().__init__(address, LocalRequestHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="炸弹超人插件本地规则测试服务")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=10619)
    parser.add_argument("--players", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260831)
    args = parser.parse_args()

    arena = LocalArena(args.players, args.seed)
    server = LocalHttpServer((args.host, args.port), arena)
    tick_thread = threading.Thread(target=arena.run_ticks, name="bomb-people-ticker", daemon=True)
    tick_thread.start()
    print(f"Bomb People local test API: http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        arena.stop()
        tick_thread.join(timeout=1)


if __name__ == "__main__":
    main()
