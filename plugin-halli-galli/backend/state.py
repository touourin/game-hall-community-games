from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .catalog import FRUIT_ORDER, FruitCard


def empty_totals() -> dict[str, int]:
    return {fruit_id: 0 for fruit_id in FRUIT_ORDER}


@dataclass
class HalliGalliPlayerState:
    id: str
    seat: int
    display_name: str
    draw_pile: list[FruitCard] = field(default_factory=list)
    discard_pile: list[FruitCard] = field(default_factory=list)
    status: str = "eligible"
    elimination_reason: str | None = None
    last_action_seq: int = 0


@dataclass
class HalliGalliState:
    schema_version: int = 1
    model_version: str = "1.0.0"
    profile_id: str = "official_last_bell"
    stage: str = "setup"
    player_ids: list[str] = field(default_factory=list)
    players: dict[str, HalliGalliPlayerState] = field(default_factory=dict)
    starting_player_id: str | None = None
    current_player_id: str | None = None
    deal_offset: int = 0
    turn_number: int = 0
    board_epoch: int = 0
    earliest_next_flip_at_ms: int = 0
    fruit_totals: dict[str, int] = field(default_factory=empty_totals)
    valid_fruit_ids: list[str] = field(default_factory=list)
    final_duel_armed: bool = False
    bell_resolution: dict[str, Any] | None = None
    no_progress_deadline_ms: int | None = None
    event_seq: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    processed_actions: dict[str, str] = field(default_factory=dict)
    processed_action_order: list[str] = field(default_factory=list)
