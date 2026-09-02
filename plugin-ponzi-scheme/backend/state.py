from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


INDUSTRY_IDS = ("transportation", "grain", "media", "real_estate")


@dataclass
class FundHolding:
    card_id: str
    due_in: int


@dataclass
class PlayerLedger:
    cash: int = 0
    industries: dict[str, int] = field(
        default_factory=lambda: {industry_id: 0 for industry_id in INDUSTRY_IDS}
    )
    funds: list[FundHolding] = field(default_factory=list)
    luxuries: list[str] = field(default_factory=list)
    bankrupt: bool = False
    forfeited: bool = False
    final_score: int | None = None


@dataclass
class PendingTrade:
    proposer_id: str
    target_id: str
    industry_id: str
    offer: int


@dataclass
class GameEvent:
    seq: int
    type: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class PonziSchemeState:
    round_number: int = 1
    stage: str = "funding"
    turn_order: list[str] = field(default_factory=list)
    starter_index: int = 0
    current_player_id: str | None = None
    phase_cursor: int = 0
    market: list[str] = field(default_factory=list)
    fund_deck: list[str] = field(default_factory=list)
    fund_discard: list[str] = field(default_factory=list)
    removed_starting_cards: list[str] = field(default_factory=list)
    industry_supply: dict[str, int] = field(
        default_factory=lambda: {industry_id: 15 for industry_id in INDUSTRY_IDS}
    )
    luxury_market: list[str] = field(default_factory=list)
    ledgers: dict[str, PlayerLedger] = field(default_factory=dict)
    pending_trade: PendingTrade | None = None
    crash_queue: list[str] = field(default_factory=list)
    crash_occurred: bool = False
    wheel_position: int = 0
    bankrupt_ids: list[str] = field(default_factory=list)
    rankings: list[str] = field(default_factory=list)
    events: list[GameEvent] = field(default_factory=list)
    event_sequence: int = 0
