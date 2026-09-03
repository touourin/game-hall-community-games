from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .catalog import SUIT_ORDER


def empty_bank() -> dict[str, list[str]]:
    return {suit: [] for suit in SUIT_ORDER}


@dataclass
class PublicEvent:
    seq: int
    type: str
    text_zh: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlayerBoard:
    bank: dict[str, list[str]] = field(default_factory=empty_bank)
    trait_offer: list[str] = field(default_factory=list)
    trait_id: str | None = None
    locker_target_id: str | None = None
    forfeited: bool = False


@dataclass
class PlayEntry:
    entry_id: str
    card_id: str
    source_zone: str
    source_owner_id: str | None = None
    parent_entry_id: str | None = None
    protection_reasons: set[str] = field(default_factory=set)


@dataclass
class ChoiceOption:
    option_id: str
    label_zh: str
    card_id: str | None = None
    player_id: str | None = None
    suit: str | None = None
    entry_id: str | None = None
    causes_immediate_bust: bool = False


@dataclass
class PendingChoice:
    choice_id: str
    kind: str
    actor_id: str
    prompt_zh: str
    options: list[ChoiceOption]
    source_entry_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class TurnState:
    number: int
    actor_id: str
    play_area: list[PlayEntry] = field(default_factory=list)
    kraken_debt: int = 0
    safe_harbor_slots: int = 0
    oracle_peek_card_ids: list[str] = field(default_factory=list)
    map_reveal_card_ids: list[str] = field(default_factory=list)
    busting_card_id: str | None = None
    deck_exhausted_during_turn: bool = False
    pending_choice: PendingChoice | None = None
    effect_stack: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ScoreRow:
    player_id: str
    suit_subtotals: dict[str, int]
    card_adjustments: int
    total: int
    bank_card_count: int
    eligible: bool = True
    rank: int | None = None
    winner: bool = False


@dataclass
class GameResult:
    winner_ids: list[str]
    outcome: str
    reason: str
    scores: list[ScoreRow]
    summary_zh: str


@dataclass
class DeadMansDrawState:
    schema_version: int = 1
    model_version: str = "1.0.0"
    phase: str = "waiting"
    rules_profile_id: str = "tabletop_base_2015"
    traits_enabled: bool = True
    traits_revealed: bool = False
    turn_order: list[str] = field(default_factory=list)
    current_player_index: int = 0
    players: dict[str, PlayerBoard] = field(default_factory=dict)
    draw_pile: list[str] = field(default_factory=list)
    discard_pile: list[str] = field(default_factory=list)
    trait_deck: list[str] = field(default_factory=list)
    unused_traits: list[str] = field(default_factory=list)
    removed_from_game: list[str] = field(default_factory=list)
    turn: TurnState | None = None
    turn_number: int = 0
    entry_counter: int = 0
    choice_counter: int = 0
    option_counter: int = 0
    event_counter: int = 0
    revision: int = 0
    events: list[PublicEvent] = field(default_factory=list)
    result: GameResult | None = None

