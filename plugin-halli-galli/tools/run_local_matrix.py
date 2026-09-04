#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
from statistics import mean
import sys
from typing import Any


PLUGIN_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PLUGIN_DIR.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_helpers() -> Any:
    path = PLUGIN_DIR / "tests" / "halli_galli_test_helpers.py"
    spec = importlib.util.spec_from_file_location("halli_galli_matrix_helpers", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load helpers from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_matrix(games_per_count: int) -> dict[str, Any]:
    helpers = load_helpers()
    report: dict[str, Any] = {
        "rulesProfile": "official_last_bell",
        "gamesPerPlayerCount": games_per_count,
        "totalGames": games_per_count * 5,
        "playerCounts": {},
    }
    all_endings: Counter[str] = Counter()
    for player_count in range(2, 7):
        action_lengths: list[int] = []
        winners: Counter[int] = Counter()
        action_mix: Counter[str] = Counter()
        endings: Counter[str] = Counter()
        seed_start = 90_000 + player_count * 1_000
        for offset in range(games_per_count):
            seed = seed_start + offset
            game, room, _, mix, steps = helpers.autoplay_game(player_count, seed)
            game.assert_invariants(room)
            if room.phase != "finished":
                raise AssertionError(f"seed {seed} did not finish")
            if sum(row["totalCount"] for row in room.state.result["rows"]) != 56:
                raise AssertionError(f"seed {seed} lost cards")
            action_lengths.append(steps)
            winners[len(room.winner_player_ids)] += 1
            action_mix.update(mix)
            ending = room.state.result["reasonCode"]
            endings[ending] += 1
            all_endings[ending] += 1
        report["playerCounts"][str(player_count)] = {
            "seedRange": [seed_start, seed_start + games_per_count - 1],
            "completedGames": games_per_count,
            "actions": {
                "min": min(action_lengths),
                "max": max(action_lengths),
                "mean": round(mean(action_lengths), 2),
                "total": sum(action_lengths),
            },
            "winnerCountDistribution": dict(sorted(winners.items())),
            "endings": dict(sorted(endings.items())),
            "actionMix": dict(sorted(action_mix.items())),
        }
    report["endingTotals"] = dict(sorted(all_endings.items()))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic 2–6 player Halli Galli games")
    parser.add_argument("--games-per-count", type=int, default=32)
    arguments = parser.parse_args()
    if arguments.games_per_count < 1:
        parser.error("--games-per-count must be at least 1")
    print(json.dumps(run_matrix(arguments.games_per_count), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
