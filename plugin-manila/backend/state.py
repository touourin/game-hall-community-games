from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .catalog import DESTINATION_COSTS, DESTINATION_PAYOUTS, PUNT_IDS


@dataclass
class WorkerPlacement:
    worker_id: str
    player_id: str
    role: str = "accomplice"
    slot_index: int | None = None


@dataclass
class ManilaPlayerState:
    player_id: str
    display_name: str
    seat: int
    color_index: int
    cash: int = 30
    share_ids: list[str] = field(default_factory=list)
    mortgaged_share_ids: list[str] = field(default_factory=list)
    worker_ids: list[str] = field(default_factory=list)
    available_worker_ids: list[str] = field(default_factory=list)
    passed_placement: bool = False
    forfeited: bool = False
    final_wealth: int | None = None


@dataclass
class PuntState:
    id: str
    cargo_id: str | None = None
    lane_id: str | None = None
    position: int = 0
    status: str = "waiting"
    occupants: list[WorkerPlacement] = field(default_factory=list)
    last_die: int | None = None
    destination_slot: str | None = None
    plundered: bool = False
    displaced_player_ids: list[str] = field(default_factory=list)


@dataclass
class DestinationSlotState:
    id: str
    cost: int
    payout: int
    bettor: WorkerPlacement | None = None
    punt_id: str | None = None


@dataclass
class AuctionState:
    opener_id: str
    current_player_id: str | None
    active_player_ids: list[str]
    passed_player_ids: list[str] = field(default_factory=list)
    leader_id: str | None = None
    current_bid: int = 0


@dataclass
class ManilaState:
    schema_version: int = 1
    model_version: str = "1.0.0"
    stage: str = "setup"
    voyage_number: int = 0
    turn_order: list[str] = field(default_factory=list)
    players: dict[str, ManilaPlayerState] = field(default_factory=dict)
    market_values: dict[str, int] = field(default_factory=dict)
    share_commodities: dict[str, str] = field(default_factory=dict)
    share_supply: dict[str, list[str]] = field(default_factory=dict)
    harbor_master_id: str | None = None
    auction: AuctionState | None = None
    punts: dict[str, PuntState] = field(
        default_factory=lambda: {punt_id: PuntState(punt_id) for punt_id in PUNT_IDS}
    )
    port_slots: list[DestinationSlotState] = field(
        default_factory=lambda: [
            DestinationSlotState(slot, DESTINATION_COSTS[slot], DESTINATION_PAYOUTS[slot])
            for slot in ("A", "B", "C")
        ]
    )
    shipyard_slots: list[DestinationSlotState] = field(
        default_factory=lambda: [
            DestinationSlotState(slot, DESTINATION_COSTS[slot], DESTINATION_PAYOUTS[slot])
            for slot in ("A", "B", "C")
        ]
    )
    special_workers: dict[str, WorkerPlacement | None] = field(
        default_factory=lambda: {
            "pirate-captain": None,
            "pirate-crew": None,
            "pilot-small": None,
            "pilot-large": None,
            "insurance": None,
        }
    )
    schedule: list[str] = field(default_factory=list)
    schedule_index: int = -1
    placement_round: int = 0
    placement_cursor: int = 0
    current_player_id: str | None = None
    movement_round: int = 0
    die_results: dict[str, int] = field(default_factory=dict)
    last_move_order: list[str] = field(default_factory=list)
    pirate_board_queue: list[str] = field(default_factory=list)
    pirate_route_queue: list[str] = field(default_factory=list)
    event_seq: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)
    animation: dict[str, Any] | None = None
    last_settlement: dict[str, Any] | None = None
    rankings: list[str] = field(default_factory=list)
    result_reason: str | None = None


def fresh_destination_slots() -> tuple[list[DestinationSlotState], list[DestinationSlotState]]:
    def slots() -> list[DestinationSlotState]:
        return [
            DestinationSlotState(slot, DESTINATION_COSTS[slot], DESTINATION_PAYOUTS[slot])
            for slot in ("A", "B", "C")
        ]

    return slots(), slots()
