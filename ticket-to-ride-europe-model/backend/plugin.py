from __future__ import annotations

from .engine import TicketToRideEuropeEngine


def create_engine() -> TicketToRideEuropeEngine:
    return TicketToRideEuropeEngine()
