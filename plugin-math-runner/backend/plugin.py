from __future__ import annotations

from .engine import MathRunnerEngine


def create_engine() -> MathRunnerEngine:
    return MathRunnerEngine()
