from __future__ import annotations

import random
from dataclasses import dataclass

from .state import BOARD_SIZE, CELL_FLOOR, CELL_HARD, CELL_SOFT


@dataclass(frozen=True)
class MapSpec:
    key: str
    name: str
    subtitle: str
    pace: str
    density: str
    layout: str
    hard_rate: float
    soft_rate: float
    seed: int
    spawn_points: tuple[tuple[int, int], ...]
    spawn_mode: str = "standard"
    starting_items: tuple[str, ...] = ()


# Spawn tuples follow player-seat order: the first two are opposed, the first
# four remain balanced, and every point is the nearest 20×20 cell centre to a
# portal painted into that map's artwork.
MAP_SPECS: tuple[MapSpec, ...] = (
    MapSpec(
        "magma_crucible", "熔岩熔炉", "均衡箱群与熔炉环道", "均衡", "中密度",
        "islands", 0.12, 0.45, 101,
        (
            (3, 2), (16, 16), (16, 2), (3, 16),
            (10, 2), (10, 16), (2, 9), (17, 9),
        ),
    ),
    MapSpec(
        "frost_fracture", "冰霜裂谷", "宽阔冰道，追击空间更大", "快速", "稀疏",
        "scatter", 0.08, 0.34, 211,
        (
            (3, 3), (16, 16), (16, 3), (3, 16),
            (9, 3), (9, 16), (3, 9), (16, 9),
        ),
        starting_items=("speed",),
    ),
    MapSpec(
        "neon_reactor", "霓虹反应堆", "十字反应堆切分四区", "战术", "中密度",
        "cross", 0.14, 0.44, 307,
        (
            (3, 2), (17, 17), (16, 2), (2, 17),
            (10, 2), (9, 17), (1, 9), (18, 9),
        ),
    ),
    MapSpec(
        "jungle_ziggurat", "丛林金字塔", "中央神坛八点集结，高密箱墙环绕", "保守", "高密度",
        "rooms", 0.19, 0.53, 401,
        (
            (8, 8), (11, 10), (11, 8), (8, 10),
            (9, 8), (10, 10), (10, 8), (9, 10),
        ),
        spawn_mode="fortress",
    ),
    MapSpec(
        "sky_citadel", "云顶激斗场", "上下空港分列，自带速度和脚踢", "激斗", "稀疏",
        "scatter", 0.07, 0.29, 503,
        (
            (6, 2), (13, 17), (13, 2), (6, 17),
            (8, 2), (11, 17), (11, 2), (8, 17),
        ),
        spawn_mode="close",
        starting_items=("speed", "speed", "bomb_up", "kick"),
    ),
    MapSpec(
        "clockwork_foundry", "发条铸造厂", "机械墙分隔独立发展区", "保守", "高密度",
        "rooms", 0.21, 0.49, 601,
        (
            (2, 4), (17, 15), (17, 4), (2, 15),
            (2, 7), (17, 12), (17, 7), (2, 12),
        ),
        spawn_mode="fortress",
    ),
    MapSpec(
        "haunted_catacombs", "幽灵墓穴", "错落墓柱和密集宝箱", "探索", "高密度",
        "islands", 0.16, 0.55, 701,
        (
            (2, 2), (17, 16), (17, 2), (2, 16),
            (2, 4), (17, 15), (17, 4), (2, 15),
        ),
        starting_items=("ghost",),
    ),
    MapSpec(
        "storm_dockyard", "风暴船坞", "四区双人接战，自带打雷与扔雷", "激斗", "中低密度",
        "islands", 0.10, 0.33, 809,
        (
            (4, 4), (15, 15), (15, 4), (4, 15),
            (6, 5), (13, 13), (13, 5), (6, 13),
        ),
        spawn_mode="close",
        starting_items=("speed", "bomb_up", "punch", "throw"),
    ),
    MapSpec(
        "crystal_rift", "水晶裂隙", "环形壁垒连接八处裂隙出生点", "保守", "中高密度",
        "rings", 0.18, 0.47, 907,
        (
            (4, 3), (15, 16), (15, 3), (4, 16),
            (9, 6), (9, 13), (7, 10), (12, 10),
        ),
        spawn_mode="fortress",
        starting_items=("shield",),
    ),
    MapSpec(
        "solar_collapse", "太阳崩塌", "能量环与日核出生，遥控雷埋伏压迫", "激斗", "中密度",
        "rings", 0.12, 0.41, 1009,
        (
            (4, 4), (15, 14), (12, 6), (5, 14),
            (7, 12), (12, 12), (9, 16), (9, 9),  # Seven rings + solar core.
        ),
        spawn_mode="close",
        starting_items=("flame_up", "timer"),
    ),
)

MAP_BY_KEY = {spec.key: spec for spec in MAP_SPECS}


def spawn_positions(count: int, spec: MapSpec) -> list[tuple[int, int]]:
    """Return seat-ordered spawns aligned with the portals painted on a map."""
    if not 2 <= count <= len(spec.spawn_points):
        raise ValueError(f"spawn count must be between 2 and {len(spec.spawn_points)}")
    return list(spec.spawn_points[:count])


def _spawn_clearance(spawns: list[tuple[int, int]]) -> set[tuple[int, int]]:
    reserved: set[tuple[int, int]] = set()
    center = (BOARD_SIZE - 1) / 2
    for x, y in spawns:
        reserved.add((x, y))
        dx = 1 if x < center else -1
        dy = 1 if y < center else -1
        for cell in ((x + dx, y), (x, y + dy), (x + 2 * dx, y), (x, y + 2 * dy)):
            if 0 <= cell[0] < BOARD_SIZE and 0 <= cell[1] < BOARD_SIZE:
                reserved.add(cell)
    return reserved


def _pattern_cells(layout: str) -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    if layout == "cross":
        gaps = {2, 5, 9, 10, 14, 17}
        for value in range(1, BOARD_SIZE - 1):
            if value not in gaps:
                cells.update(((9, value), (10, value), (value, 9), (value, 10)))
    elif layout == "rooms":
        for x in (5, 14):
            for y in range(BOARD_SIZE):
                if y not in {2, 3, 8, 11, 16, 17}:
                    cells.add((x, y))
        for y in (5, 14):
            for x in range(BOARD_SIZE):
                if x not in {2, 3, 8, 11, 16, 17}:
                    cells.add((x, y))
        cells.update({(9, 9), (10, 9), (9, 10), (10, 10)})
    elif layout == "rings":
        for low, high in ((4, 15), (7, 12)):
            for value in range(low, high + 1):
                if value not in {6, 9, 10, 13}:
                    cells.update(((value, low), (value, high), (low, value), (high, value)))
    elif layout == "islands":
        anchors = ((4, 3), (10, 3), (15, 5), (3, 10), (9, 9), (15, 11), (5, 16), (12, 16))
        for index, (x, y) in enumerate(anchors):
            cells.add((x, y))
            cells.add((x + (1 if index % 2 == 0 else 0), y + (0 if index % 2 == 0 else 1)))
    return cells


def build_board(
    spec: MapSpec,
    spawns: list[tuple[int, int]],
    variant: int = 0,
) -> list[list[int]]:
    rng = random.Random(spec.seed + variant * 7_919)
    board = [[CELL_FLOOR for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    reserved = _spawn_clearance(spawns)

    hard_cells = {
        cell for cell in _pattern_cells(spec.layout)
        if cell not in reserved
    }
    hard_target = round(BOARD_SIZE * BOARD_SIZE * spec.hard_rate)
    candidates = [
        (x, y)
        for y in range(BOARD_SIZE)
        for x in range(BOARD_SIZE)
        if (x, y) not in reserved and (x, y) not in hard_cells
    ]
    rng.shuffle(candidates)
    for x, y in candidates:
        if len(hard_cells) >= hard_target:
            break
        neighbours = sum(
            (x + dx, y + dy) in hard_cells
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
        )
        if spec.layout == "scatter" and neighbours:
            continue
        if neighbours >= 2:
            continue
        hard_cells.add((x, y))

    for x, y in hard_cells:
        board[y][x] = CELL_HARD

    soft_target = round(BOARD_SIZE * BOARD_SIZE * spec.soft_rate)
    soft_candidates = [
        (x, y)
        for y in range(BOARD_SIZE)
        for x in range(BOARD_SIZE)
        if board[y][x] == CELL_FLOOR and (x, y) not in reserved
    ]
    rng.shuffle(soft_candidates)
    for x, y in soft_candidates[:soft_target]:
        board[y][x] = CELL_SOFT

    for x, y in reserved:
        board[y][x] = CELL_FLOOR
    return board


def spiral_collapse_order() -> list[tuple[int, int]]:
    order: list[tuple[int, int]] = []
    for layer in range((BOARD_SIZE + 1) // 2):
        low = layer
        high = BOARD_SIZE - 1 - layer
        if low > high:
            break
        for x in range(low, high + 1):
            order.append((x, low))
        for y in range(low + 1, high + 1):
            order.append((high, y))
        if high > low:
            for x in range(high - 1, low - 1, -1):
                order.append((x, high))
            for y in range(high - 1, low, -1):
                order.append((low, y))
    return order


def map_catalog() -> list[dict[str, object]]:
    return [
        {
            "key": spec.key,
            "name": spec.name,
            "subtitle": spec.subtitle,
            "pace": spec.pace,
            "density": spec.density,
            "spawnMode": spec.spawn_mode,
            "startingItems": list(spec.starting_items),
        }
        for spec in MAP_SPECS
    ]
