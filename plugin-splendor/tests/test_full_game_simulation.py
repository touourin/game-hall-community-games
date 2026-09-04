from __future__ import annotations

from collections import Counter

import pytest

from splendor_test_helpers import autoplay_game


@pytest.mark.parametrize("count", [2, 3, 4])
@pytest.mark.parametrize("seed_offset", range(8))
def test_complete_regular_games_finish_for_every_player_count(count: int, seed_offset: int) -> None:
    game, room, players, trace = autoplay_game(count, 20_000 + count * 100 + seed_offset)
    state = room.state
    game.assert_invariants(state)

    assert room.phase == "finished"
    assert room.winner_player_ids
    assert state.result is not None
    assert state.turn.action_number > 0
    assert len(trace) >= state.turn.action_number
    assert max(row.prestige for row in state.result.rows if not row.forfeited) >= 15

    candidates = [row for row in state.result.rows if not row.forfeited]
    best_score = max(row.prestige for row in candidates)
    fewest = min(row.purchased_card_count for row in candidates if row.prestige == best_score)
    expected = {
        row.player_id
        for row in candidates
        if row.prestige == best_score and row.purchased_card_count == fewest
    }
    assert set(room.winner_player_ids) == expected

    action_counts = Counter(item.rsplit(":", 1)[1] for item in trace)
    assert action_counts["purchase_face_up"] + action_counts["purchase_reserved"] > 0
    assert action_counts["take_different"] + action_counts["take_same"] > 0


@pytest.mark.parametrize("count", [2, 3, 4])
def test_deterministic_seed_reproduces_setup_and_outcome(count: int) -> None:
    first = autoplay_game(count, 33_000 + count)
    second = autoplay_game(count, 33_000 + count)
    assert first[3] == second[3]
    assert first[1].winner_player_ids == second[1].winner_player_ids
    assert first[1].state.result.summary_zh == second[1].state.result.summary_zh
