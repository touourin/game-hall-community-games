from __future__ import annotations

from .engine import DeadMansDrawEngine


def create_engine() -> DeadMansDrawEngine:
    return DeadMansDrawEngine()
