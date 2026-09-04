#!/usr/bin/env python3
"""Run a reproducible 2–4 player full-game stress matrix."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any


PLUGIN_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_helpers() -> Any:
    module_name = "splendor_stress_test_helpers"
    path = PLUGIN_DIR / "tests" / "helpers.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Splendor test helpers from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_matrix(games_per_count: int) -> dict[str, Any]:
    helpers = load_helpers()
    report: dict[str, Any] = {
        "rulesProfile": "base-2024-refresh",
        "gamesPerPlayerCount": games_per_count,
        "totalGames": games_per_count * 3,
        "playerCounts": {},
    }
    for player_count in (2, 3, 4):
        action_lengths: list[int] = []
        round_lengths: list[int] = []
        top_scores: list[int] = []
        action_mix: Counter[str] = Counter()
        single_wins = 0
        shared_wins = 0
        seed_start = 90_000 + player_count * 1_000

        for offset in range(games_per_count):
            seed = seed_start + offset
            game, room, _, trace = helpers.autoplay_game(player_count, seed)
            game.assert_invariants(room.state)
            if room.phase != "finished" or room.state.result is None:
                raise AssertionError(f"seed {seed} did not finish")

            eligible_rows = [row for row in room.state.result.rows if not row.forfeited]
            top_score = max(row.prestige for row in eligible_rows)
            fewest_cards = min(
                row.purchased_card_count
                for row in eligible_rows
                if row.prestige == top_score
            )
            expected_winners = {
                row.player_id
                for row in eligible_rows
                if row.prestige == top_score
                and row.purchased_card_count == fewest_cards
            }
            if set(room.winner_player_ids) != expected_winners:
                raise AssertionError(f"seed {seed} winner comparator mismatch")
            if top_score < 15:
                raise AssertionError(f"seed {seed} settled below 15 prestige")

            action_lengths.append(len(trace))
            round_lengths.append(room.state.turn.round_number)
            top_scores.append(top_score)
            action_mix.update(item.rsplit(":", 1)[1] for item in trace)
            if len(room.winner_player_ids) == 1:
                single_wins += 1
            else:
                shared_wins += 1

        report["playerCounts"][str(player_count)] = {
            "seedRange": [seed_start, seed_start + games_per_count - 1],
            "completedGames": games_per_count,
            "singleWins": single_wins,
            "sharedWins": shared_wins,
            "actions": {
                "min": min(action_lengths),
                "max": max(action_lengths),
                "mean": round(mean(action_lengths), 2),
                "total": sum(action_lengths),
            },
            "rounds": {
                "min": min(round_lengths),
                "max": max(round_lengths),
                "mean": round(mean(round_lengths), 2),
            },
            "winningPrestige": {
                "min": min(top_scores),
                "max": max(top_scores),
            },
            "actionMix": dict(sorted(action_mix.items())),
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--games-per-count", type=int, default=32)
    arguments = parser.parse_args()
    if arguments.games_per_count < 1:
        parser.error("--games-per-count must be at least 1")
    print(json.dumps(run_matrix(arguments.games_per_count), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
