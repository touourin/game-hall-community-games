from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


BOARD_SIZE = 20

CELL_FLOOR = 0
CELL_HARD = 1
CELL_SOFT = 2
CELL_STONE = 3

Stage = Literal["lobby", "countdown", "active", "collapse", "finished"]


@dataclass
class PlayerState:
    player_id: str
    seat: int
    x: int
    y: int
    facing_x: int = 0
    facing_y: int = 1
    input_mask: int = 0
    last_input_sequence: int = -1
    queued_move_x: int = 0
    queued_move_y: int = 0
    # Authoritative sub-cell position, expressed in thousandths of a tile
    # relative to (x, y).  Keeping the rule cell separate preserves the
    # grid-based bomb/map rules while allowing a player to stop between cells.
    offset_x: int = 0
    offset_y: int = 0
    move_fraction: float = 0.0
    move_cooldown: float = 0.0
    last_move_tick: int = -10_000
    bomb_requested: bool = False
    punch_requested: bool = False
    throw_requested: bool = False
    timer_requested: bool = False
    alive: bool = True
    eliminated_tick: int | None = None
    eliminated_by: str | None = None
    elimination_reason: str | None = None
    bomb_capacity: int = 1
    blast_range: int = 2
    speed_level: int = 0
    can_kick: bool = False
    can_punch: bool = False
    can_throw: bool = False
    can_timer: bool = False
    can_chain: bool = False
    has_magnet: bool = False
    has_ice: bool = False
    shield_charges: int = 0
    has_ghost: bool = False
    invincible_ticks: int = 0
    cursed_ticks: int = 0
    kills: int = 0
    carried_bomb_id: int | None = None


@dataclass
class BombState:
    bomb_id: int
    owner_id: str
    credit_player_id: str
    x: int
    y: int
    placed_tick: int
    fuse_ticks: int
    blast_range: int
    chain: bool = False
    ice: bool = False
    motion_dx: int = 0
    motion_dy: int = 0
    motion_delay: int = 0
    travel_left: int = -1
    carrier_id: str | None = None
    remote: bool = False


@dataclass
class ItemState:
    item_id: int
    kind: str
    x: int
    y: int
    source: str = "crate"


@dataclass
class FlameState:
    x: int
    y: int
    credit_player_id: str
    expires_tick: int


@dataclass
class SessionRecord:
    kills: int = 0
    championships: int = 0
    matches: int = 0


@dataclass
class EventState:
    event_id: int
    tick: int
    kind: str
    actor_id: str | None = None
    target_id: str | None = None
    item: str | None = None
    message: str = ""


@dataclass
class EffectState:
    effect_id: int
    kind: str
    tick: int
    expires_tick: int
    actor_id: str | None = None
    bomb_id: int | None = None
    x: int = 0
    y: int = 0
    target_x: int | None = None
    target_y: int | None = None
    direction_x: int = 0
    direction_y: int = 0


@dataclass
class BombPeopleState:
    tick: int = 0
    stage: Stage = "lobby"
    stage_ticks_remaining: int = 0
    round_ticks_remaining: int = 0
    selected_map: str = "magma_crucible"
    proposed_map: str | None = None
    proposed_by: str | None = None
    map_approvals: set[str] = field(default_factory=set)
    board: list[list[int]] = field(
        default_factory=lambda: [
            [CELL_FLOOR for _ in range(BOARD_SIZE)]
            for _ in range(BOARD_SIZE)
        ]
    )
    players: dict[str, PlayerState] = field(default_factory=dict)
    bombs: dict[int, BombState] = field(default_factory=dict)
    items: dict[int, ItemState] = field(default_factory=dict)
    flames: dict[tuple[int, int], FlameState] = field(default_factory=dict)
    ice_tiles: dict[tuple[int, int], int] = field(default_factory=dict)
    collapse_order: list[tuple[int, int]] = field(default_factory=list)
    collapse_index: int = 0
    collapse_cooldown: int = 0
    next_item_refresh_tick: int = 0
    next_bomb_id: int = 1
    next_item_id: int = 1
    next_event_id: int = 1
    next_effect_id: int = 1
    events: list[EventState] = field(default_factory=list)
    effects: list[EffectState] = field(default_factory=list)
    session_records: dict[str, SessionRecord] = field(default_factory=dict)
    match_winner_id: str | None = None
    settled: bool = False
    frozen: bool = False
    map_variant: int = 0
