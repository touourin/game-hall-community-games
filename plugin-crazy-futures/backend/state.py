from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

from .catalog import COMMODITIES


@dataclass
class MarketState:
    commodity: str
    spot_index: int = 25
    open_index: int = 25
    current_index: int = 25
    close_index: int = 25
    low_limit_index: int = 22
    high_limit_index: int = 28
    valid_trade_indices: list[int] = field(default_factory=list)
    seal: str | None = None


@dataclass
class PositionState:
    quantity: int = 0
    basis: Fraction = field(default_factory=lambda: Fraction(0))
    margin: Fraction = field(default_factory=lambda: Fraction(0))


@dataclass
class LoanRecord:
    principal: int
    borrowed_round: int
    rate_percent: int = 10


@dataclass
class PlayerLedger:
    cash: Fraction = field(default_factory=lambda: Fraction(100))
    positions: dict[str, PositionState] = field(
        default_factory=lambda: {
            commodity: PositionState() for commodity in COMMODITIES
        }
    )
    loans: list[LoanRecord] = field(default_factory=list)
    hand: list[str] = field(default_factory=list)
    bankrupt: bool = False
    forfeited: bool = False
    exchange_debt: Fraction = field(default_factory=lambda: Fraction(0))
    forced_liquidations: int = 0
    margin_buffer: int = 0
    peek_cards: list[str] = field(default_factory=list)
    final_score: Fraction | None = None


@dataclass
class ActiveEffect:
    id: str
    instance_id: str
    card_id: str
    card_name: str
    scope: str
    owner_id: str | None
    moves: list[dict[str, Any]]
    remaining_triggers: int
    sequence: int
    direction: str


@dataclass
class AuctionState:
    initiator_id: str
    commodity: str
    side: str
    quote_index: int
    leader_id: str
    participants: list[str]
    passed_ids: list[str] = field(default_factory=list)
    cursor_player_id: str | None = None


@dataclass
class PendingChoice:
    kind: str
    player_id: str
    count: int = 0
    reason: str | None = None
    resolving_card_id: str | None = None


@dataclass
class GameEvent:
    seq: int
    type: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    visible_to: str | None = None


@dataclass
class CrazyFuturesState:
    round_number: int = 1
    stage: str = "loan"
    turn_order: list[str] = field(default_factory=list)
    starter_index: int = 0
    current_player_id: str | None = None
    phase_order: list[str] = field(default_factory=list)
    phase_cursor: int = 0
    initiation_order: list[str] = field(default_factory=list)
    initiation_cursor: int = 0
    auction: AuctionState | None = None
    card_pass_count: int = 0
    settlement_queue: list[str] = field(default_factory=list)
    discard_queue: list[str] = field(default_factory=list)
    pending_choice: PendingChoice | None = None
    markets: dict[str, MarketState] = field(
        default_factory=lambda: {
            commodity: MarketState(commodity) for commodity in COMMODITIES
        }
    )
    ledgers: dict[str, PlayerLedger] = field(default_factory=dict)
    personal_deck: list[str] = field(default_factory=list)
    personal_discard: list[str] = field(default_factory=list)
    public_deck: list[str] = field(default_factory=list)
    public_discard: list[str] = field(default_factory=list)
    revealed_public: list[str] = field(default_factory=list)
    active_effects: list[ActiveEffect] = field(default_factory=list)
    event_sequence: int = 0
    effect_sequence: int = 0
    events: list[GameEvent] = field(default_factory=list)
    rankings: list[str] = field(default_factory=list)
