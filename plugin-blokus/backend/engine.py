from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from random import SystemRandom
from typing import Any

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError

from .pieces import (
    BOARD_SIZES, COLORS, COLOR_NAMES, DIAGONALS, EDGES, FOUR_BOARD_SIZE,
    FOUR_START_POINTS, PIECES, RANK_POINTS, START_POINTS, Cells, orientations,
    transform,
)


@dataclass
class BlokusState:
    board: list[list[int]] = field(
        default_factory=lambda: [
            [-1] * FOUR_BOARD_SIZE for _ in range(FOUR_BOARD_SIZE)
        ]
    )
    board_size: int = FOUR_BOARD_SIZE
    start_points: list[tuple[int, int]] = field(
        default_factory=lambda: list(FOUR_START_POINTS)
    )
    player_ids: list[str] = field(default_factory=list)
    remaining: dict[str, list[str]] = field(default_factory=dict)
    current_player_id: str | None = None
    turn_number: int = 0
    blocked_ids: list[str] = field(default_factory=list)
    forfeited_ids: list[str] = field(default_factory=list)
    moves: list[dict[str, Any]] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    rankings: list[str] = field(default_factory=list)
    scores: dict[str, int] = field(default_factory=dict)


def inside(board: list[list[int]], x: int, y: int) -> bool:
    return 0 <= y < len(board) and 0 <= x < len(board[y])


def rank_label(rank: int, points: int) -> str:
    score = f"{points:+d}" if points else "0"
    return f"第 {rank} 名 · {score} 分"


def placement_error(
    board: list[list[int]], color: int, cells: Cells, first_move: bool,
    start_point: tuple[int, int],
) -> str | None:
    if any(not inside(board, x, y) for x, y in cells):
        return "棋块不能超出棋盘"
    if any(board[y][x] != -1 for x, y in cells):
        return "棋块不能重叠"
    if first_move:
        return None if start_point in cells else "首块必须覆盖自己的起始点"
    corner_contact = False
    for x, y in cells:
        for dx, dy in EDGES:
            if inside(board, x + dx, y + dy) and board[y + dy][x + dx] == color:
                return "同色棋块只能角接，不能边接"
        for dx, dy in DIAGONALS:
            if inside(board, x + dx, y + dy) and board[y + dy][x + dx] == color:
                corner_contact = True
    return None if corner_contact else "新棋块必须与已有同色棋块角接"


class BlokusEngine:
    key = "plugin-blokus"
    name = "方格游戏"
    min_players = 2
    max_players = 4
    manages_seating = True

    def __init__(self, rng: Any | None = None) -> None:
        self.rng = rng or SystemRandom()

    def initial_state(self) -> BlokusState:
        return BlokusState()

    @staticmethod
    def can_start(room: ArcadeRoom, viewer: ArcadePlayer) -> bool:
        return len(room.players) in (2, 4) and not any(
            player.left_room for player in room.players
        )

    def start(self, room: ArcadeRoom) -> None:
        player_count = len(room.players)
        if player_count not in (2, 4) or any(
            player.left_room for player in room.players
        ):
            raise GameRuleError("方格游戏仅支持 2 位或 4 位玩家")
        players = sorted(room.players, key=lambda player: player.seat)
        order = [player.id for player in players]
        self.rng.shuffle(order)
        board_size = BOARD_SIZES[player_count]
        start_points = list(START_POINTS[player_count])
        room.state = BlokusState(
            board=[[-1] * board_size for _ in range(board_size)],
            board_size=board_size,
            start_points=start_points,
            player_ids=order,
            remaining={player_id: list(PIECES) for player_id in order},
            current_player_id=order[0],
            turn_number=1,
        )
        room.phase = "playing"

    @staticmethod
    def _member(room: ArcadeRoom, player: ArcadePlayer) -> None:
        if not any(member.id == player.id for member in room.players):
            raise GameRuleError("只有本局玩家可以操作")

    def act(
        self, room: ArcadeRoom, player: ArcadePlayer, action: str, payload: dict[str, Any],
    ) -> None:
        self._member(room, player)
        if room.phase != "playing":
            raise GameRuleError("当前对局尚未开始或已经结束")
        state: BlokusState = room.state
        if player.id in state.forfeited_ids:
            raise GameRuleError("弃权后不能继续落子")
        if action == "resign":
            self.manual_forfeit(room, player)
            return
        if action != "place":
            raise GameRuleError("请选择一块棋块落子；无合法落点时会自动跳过")
        if state.current_player_id != player.id:
            raise GameRuleError("还没有轮到你")
        if not isinstance(payload, dict):
            raise GameRuleError("落子参数无效")
        for key in ("x", "y", "rotation", "turnNumber"):
            if type(payload.get(key)) is not int:
                raise GameRuleError("落点、旋转和回合编号必须是整数")
        if payload["turnNumber"] != state.turn_number:
            raise GameRuleError("棋盘已更新，请重新选择落点")
        if not (
            inside(state.board, payload["x"], payload["y"])
            and 0 <= payload["rotation"] < 4
        ):
            raise GameRuleError("落点或旋转参数超出范围")
        if type(payload.get("flipped")) is not bool:
            raise GameRuleError("翻转参数必须是布尔值")
        piece_id = payload.get("pieceId")
        if not isinstance(piece_id, str) or piece_id not in state.remaining[player.id]:
            raise GameRuleError("这块棋块不存在或已经使用")
        cells = tuple(
            (x + payload["x"], y + payload["y"])
            for x, y in transform(piece_id, payload["rotation"], payload["flipped"])
        )
        color = state.player_ids.index(player.id)
        error = placement_error(
            state.board, color, cells,
            len(state.remaining[player.id]) == 21,
            state.start_points[color],
        )
        if error:
            raise GameRuleError(error)
        for x, y in cells:
            state.board[y][x] = color
        state.remaining[player.id].remove(piece_id)
        state.moves.append({
            "playerId": player.id, "pieceId": piece_id, "cells": [list(cell) for cell in cells],
            "x": payload["x"], "y": payload["y"], "rotation": payload["rotation"],
            "flipped": payload["flipped"], "turnNumber": state.turn_number,
        })
        self._advance(room)

    def find_move(self, room: ArcadeRoom, player_id: str) -> dict[str, Any] | None:
        """Search every distinct orientation around legal corner anchors."""
        state: BlokusState = room.state
        if player_id in state.forfeited_ids or not state.remaining[player_id]:
            return None
        color = state.player_ids.index(player_id)
        first_move = len(state.remaining[player_id]) == 21
        if first_move:
            anchors = {state.start_points[color]}
        else:
            anchors = {
                (x + dx, y + dy)
                for y, row in enumerate(state.board)
                for x, value in enumerate(row)
                if value == color
                for dx, dy in DIAGONALS
                if inside(state.board, x + dx, y + dy)
                and state.board[y + dy][x + dx] == -1
                and not any(
                    inside(state.board, x + dx + ex, y + dy + ey)
                    and state.board[y + dy + ey][x + dx + ex] == color
                    for ex, ey in EDGES
                )
            }
        for piece_id in sorted(state.remaining[player_id], key=lambda key: -len(PIECES[key])):
            for rotation, flipped, shape in orientations(piece_id):
                checked: set[tuple[int, int]] = set()
                for ax, ay in sorted(anchors, key=lambda p: (p[1], p[0])):
                    for sx, sy in shape:
                        origin = (ax - sx, ay - sy)
                        if origin in checked:
                            continue
                        checked.add(origin)
                        cells = tuple((origin[0] + x, origin[1] + y) for x, y in shape)
                        if placement_error(
                            state.board, color, cells, first_move,
                            state.start_points[color],
                        ) is None:
                            return {
                                "pieceId": piece_id, "x": origin[0], "y": origin[1],
                                "rotation": rotation, "flipped": flipped,
                                "turnNumber": state.turn_number,
                            }
        return None

    def _advance(self, room: ArcadeRoom) -> None:
        state: BlokusState = room.state
        current = state.player_ids.index(state.current_player_id)
        player_count = len(state.player_ids)
        for step in range(1, player_count + 1):
            player_id = state.player_ids[(current + step) % player_count]
            if player_id in state.forfeited_ids or player_id in state.blocked_ids:
                continue
            if self.find_move(room, player_id) is None:
                state.blocked_ids.append(player_id)
                reason = "已放完全部棋块" if not state.remaining[player_id] else "已无合法落点，自动跳过"
                state.events.append(f"{room.player(player_id).name} {reason}")
                continue
            state.current_player_id = player_id
            state.turn_number += 1
            return
        self._finish(room)

    def _finish(self, room: ArcadeRoom) -> None:
        if room.phase == "finished":
            return
        state: BlokusState = room.state
        active = [player_id for player_id in state.player_ids if player_id not in state.forfeited_ids]
        active.sort(key=lambda player_id: (
            sum(len(PIECES[key]) for key in state.remaining[player_id]),
            len(state.remaining[player_id]),
            -state.player_ids.index(player_id),
        ))
        # Forfeits rank below all players who finish; an earlier forfeit ranks last.
        state.rankings = active + list(reversed(state.forfeited_ids))
        rank_points = RANK_POINTS[:len(state.rankings)]
        state.scores = dict(zip(state.rankings, rank_points, strict=True))
        state.current_player_id = None
        winner = room.player(state.rankings[0])
        results = "；".join(
            f"{room.player(player_id).name}：{rank_label(rank, state.scores[player_id])}"
            for rank, player_id in enumerate(state.rankings, 1)
        )
        room.finish("第一名", [winner.id], f"名次结算：{results}")

    def manual_forfeit(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        self._member(room, player)
        state: BlokusState = room.state
        if room.phase != "playing" or player.id in state.forfeited_ids:
            return False
        state.forfeited_ids.append(player.id)
        state.events.append(f"{player.name} 弃权，已落棋块保留")
        if len(state.forfeited_ids) >= len(state.player_ids) - 1:
            self._finish(room)
        elif state.current_player_id == player.id:
            self._advance(room)
        return True

    def disconnect_timeout(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        return self.manual_forfeit(room, player)

    def view(self, room: ArcadeRoom, viewer: ArcadePlayer) -> dict[str, Any]:
        state: BlokusState = room.state
        players = []
        for color, player_id in enumerate(state.player_ids):
            remaining = state.remaining[player_id]
            status = (
                "forfeited" if player_id in state.forfeited_ids else
                "finished" if not remaining else
                "blocked" if player_id in state.blocked_ids else "active"
            )
            players.append({
                "id": player_id, "color": COLORS[color], "colorName": COLOR_NAMES[color],
                "start": list(state.start_points[color]), "remainingPieces": list(remaining),
                "remainingSquares": sum(len(PIECES[key]) for key in remaining),
                "placedSquares": 89 - sum(len(PIECES[key]) for key in remaining),
                "status": status,
                "rank": state.rankings.index(player_id) + 1 if player_id in state.rankings else None,
                "points": state.scores.get(player_id),
            })
        return {
            "mode": "duo" if len(state.player_ids) == 2 else "classic",
            "boardSize": state.board_size,
            "board": [list(row) for row in state.board],
            "players": players,
            "currentPlayerId": state.current_player_id,
            "turnNumber": state.turn_number,
            "isMyTurn": room.phase == "playing" and state.current_player_id == viewer.id,
            "moveCount": len(state.moves),
            "lastMove": deepcopy(state.moves[-1]) if state.moves else None,
            "events": state.events[-8:],
            "rankings": list(state.rankings),
            "rankPoints": list(RANK_POINTS[:len(state.player_ids)]),
        }

    def player_result(self, room: ArcadeRoom, player: ArcadePlayer) -> tuple[str, str, bool]:
        state: BlokusState = room.state
        rank = state.rankings.index(player.id) + 1 if player.id in state.rankings else None
        label = rank_label(rank, state.scores[player.id]) if rank else "未结算"
        return label, "player", player.id in room.winner_player_ids

    def player_score(self, room: ArcadeRoom, player: ArcadePlayer) -> int | None:
        return room.state.scores.get(player.id) if room.phase == "finished" else None

    def record_state(self, room: ArcadeRoom) -> dict[str, Any]:
        return asdict(room.state)
