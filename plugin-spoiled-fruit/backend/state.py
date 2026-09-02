from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Card:
    instance_id: str
    catalog_id: str


@dataclass
class PlayerBoard:
    player_id: str
    seat_index: int
    hand: list[Card] = field(default_factory=list)
    safe: bool = False
    pending_empty: bool = False
    protected_card_id: str | None = None
    shield_pair_id: str | None = None
    harvest_pair_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EffectItem:
    queue_id: str
    batch_id: str
    pair_catalog_id: str
    effect_id: str
    owner_player_id: str


@dataclass
class SpoiledFruitState:
    first_player_id: str | None = None
    turn_order: list[str] = field(default_factory=list)
    boards: dict[str, PlayerBoard] = field(default_factory=dict)
    current_player_id: str | None = None
    old_maid_count: int = 0
    total_card_count: int = 0
    removed_pair_count: int = 0
    initial_removed_pair_count: int = 0
    normal_draw_count: int = 0
    effect_transfer_count: int = 0
    skip_count: int = 0
    effect_queue: list[EffectItem] = field(default_factory=list)
    pending_choice: dict[str, Any] | None = None
    private_peeks: dict[str, dict[str, Any]] = field(default_factory=dict)
    safe_order: list[str] = field(default_factory=list)
    batch_sequence: int = 0
    queue_sequence: int = 0
    event_sequence: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)
    finished: dict[str, Any] | None = None
