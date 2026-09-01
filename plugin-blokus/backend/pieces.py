from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


DUO_BOARD_SIZE = 14
FOUR_BOARD_SIZE = 20
DUO_START_POINTS = ((4, 4), (9, 9))
FOUR_START_POINTS = ((0, 0), (19, 0), (19, 19), (0, 19))
BOARD_SIZES = {2: DUO_BOARD_SIZE, 4: FOUR_BOARD_SIZE}
START_POINTS = {2: DUO_START_POINTS, 4: FOUR_START_POINTS}
COLORS = ("blue", "yellow", "red", "green")
COLOR_NAMES = ("蓝", "黄", "红", "绿")
RANK_POINTS = (2, 1, 0, -1)
EDGES = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIAGONALS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
Cells = tuple[tuple[int, int], ...]

_catalog = json.loads(
    (Path(__file__).resolve().parents[1] / "pieces.json").read_text(encoding="utf-8")
)
PIECES: dict[str, Cells] = {
    item["id"]: tuple(
        (x, y)
        for y, row in enumerate(item["rows"])
        for x, cell in enumerate(row)
        if cell == "#"
    )
    for item in _catalog
}


def normalize(cells: Cells) -> Cells:
    left = min(x for x, _ in cells)
    top = min(y for _, y in cells)
    return tuple(sorted(((x - left, y - top) for x, y in cells), key=lambda p: (p[1], p[0])))


@lru_cache(maxsize=168)
def transform(piece_id: str, rotation: int = 0, flipped: bool = False) -> Cells:
    cells = PIECES[piece_id]
    if flipped:
        cells = tuple((-x, y) for x, y in cells)
    for _ in range(rotation):
        cells = tuple((-y, x) for x, y in cells)
    return normalize(cells)


@lru_cache(maxsize=21)
def orientations(piece_id: str) -> tuple[tuple[int, bool, Cells], ...]:
    seen: set[Cells] = set()
    result = []
    for flipped in (False, True):
        for rotation in range(4):
            cells = transform(piece_id, rotation, flipped)
            if cells not in seen:
                seen.add(cells)
                result.append((rotation, flipped, cells))
    return tuple(result)
