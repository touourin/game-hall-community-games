from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .catalog import PIECE_COLORS, STANDARD_COLORS


def empty_piece_vector() -> dict[str, int]:
    return {color: 0 for color in PIECE_COLORS}


def empty_bonus_vector() -> dict[str, int]:
    return {color: 0 for color in STANDARD_COLORS}


@dataclass
class Reservation:
    reservation_id: str
    card_id: str
    level: int
    source: str
    known_to_all: bool


@dataclass
class PlayerBoard:
    display_name: str = ""
    pieces: dict[str, int] = field(default_factory=empty_piece_vector)
    purchased_card_ids: list[str] = field(default_factory=list)
    reservations: list[Reservation] = field(default_factory=list)
    noble_ids: list[str] = field(default_factory=list)
    forfeited: bool = False


@dataclass
class TierState:
    level: int
    deck: list[str] = field(default_factory=list)
    market: list[str | None] = field(default_factory=lambda: [None, None, None, None])


@dataclass
class PublicEvent:
    seq: int
    type: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class TurnState:
    first_player_id: str | None = None
    active_player_id: str | None = None
    round_number: int = 1
    action_number: int = 0
    pending_return_count: int = 0
    eligible_noble_ids: list[str] = field(default_factory=list)
    end_triggered_by: str | None = None
    final_turn_player_id: str | None = None
    last_action: str | None = None


@dataclass
class ScoreRow:
    player_id: str
    prestige: int
    card_prestige: int
    noble_prestige: int
    purchased_card_count: int
    rank: int
    winner: bool
    forfeited: bool = False


@dataclass
class GameResult:
    winner_ids: list[str]
    outcome: str
    reason: str
    rows: list[ScoreRow]
    summary_zh: str


@dataclass
class SplendorState:
    schema_version: int = 1
    model_version: str = "1.0.0"
    rules_profile: str = "base-2024-refresh"
    phase: str = "waiting"
    revision: int = 0
    market_revision: int = 0
    turn_order: list[str] = field(default_factory=list)
    current_player_index: int = 0
    turn: TurnState = field(default_factory=TurnState)
    supply: dict[str, int] = field(default_factory=empty_piece_vector)
    initial_supply: dict[str, int] = field(default_factory=empty_piece_vector)
    tiers: dict[int, TierState] = field(default_factory=dict)
    available_noble_ids: list[str] = field(default_factory=list)
    unused_noble_ids: list[str] = field(default_factory=list)
    players: dict[str, PlayerBoard] = field(default_factory=dict)
    reservation_counter: int = 0
    event_counter: int = 0
    events: list[PublicEvent] = field(default_factory=list)
    result: GameResult | None = None
