from __future__ import annotations

import random
from pathlib import Path

import pytest

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError
from backend.app.games.plugins import discover_game_plugins


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
DIRECTIONS = {"up", "left", "down", "right"}


def load_engine(seed: int = 20260901):
    game = next(
        plugin.engine
        for plugin in discover_game_plugins(PLUGIN_ROOT)
        if plugin.engine.key == "plugin-math-runner"
    )
    game.rng = random.Random(seed)
    return game


def make_room(seed: int = 20260901):
    now = [100.0]
    game = load_engine(seed)
    game.clock = lambda: now[0]
    player = ArcadePlayer("p1", "a1", "逐光者", "token", 0)
    room = ArcadeRoom("SOLO", game.key, player.id, [player], game.initial_state())
    game.start(room)
    return game, room, player, now


def choose_correct(game, room, player, now, response_seconds: float = 0.5) -> int:
    question = room.state.question
    now[0] += response_seconds
    before = room.state.score
    game.act(
        room,
        player,
        "choose",
        {
            "questionId": question.id,
            "direction": question.correct_direction,
        },
    )
    return room.state.score - before


def test_initial_view_exposes_choices_but_hides_the_answer() -> None:
    game, room, player, _now = make_room()
    question = room.state.question
    view = game.view(room, player)

    assert room.phase == "playing"
    assert view["level"] == 1
    assert view["questionId"] == 1
    assert 2 <= len(view["options"]) <= 4
    assert set(view["blockedDirections"]) | {
        option["direction"] for option in view["options"]
    } == DIRECTIONS
    assert view["correctDirection"] is None
    assert "correct_direction" not in view
    assert all(set(option) == {"direction", "equation"} for option in view["options"])
    assert question.correct_direction in {option.direction for option in question.options}


def test_generated_junctions_have_two_to_four_unique_routes_and_one_truth() -> None:
    game = load_engine(7)
    now = 0.0
    seen_counts: set[int] = set()

    for level in range(1, 11):
        for question_id in range(1, 301):
            question = game._new_question(
                level=level,
                question_id=question_id,
                now=now,
            )
            seen_counts.add(len(question.options))
            directions = [option.direction for option in question.options]
            equations = [option.equation for option in question.options]
            assert 2 <= len(directions) <= 4
            assert len(directions) == len(set(directions))
            assert len(equations) == len(set(equations))
            assert sum(option.left_value == option.right_value for option in question.options) == 1
            assert sum(option.is_correct for option in question.options) == 1
            assert all(" = " in option.equation for option in question.options)
            assert all(len(option.equation) <= 32 for option in question.options)
            assert all(option.left_value > 0 and option.right_value > 0 for option in question.options)
            assert question.correct_direction == next(
                option.direction for option in question.options if option.is_correct
            )

    assert 2 in seen_counts
    assert 4 in seen_counts


def test_correct_choice_scores_from_level_and_remaining_time() -> None:
    game, room, player, now = make_room()
    question = room.state.question
    now[0] += 1.0

    game.act(
        room,
        player,
        "choose",
        {"questionId": question.id, "direction": question.correct_direction},
    )

    assert room.state.correct_answers == 1
    assert room.state.score == 100 + (question.time_limit_ms - 1_000) // 20
    assert room.state.last_points == room.state.score
    assert room.state.question.id == 2
    assert game.view(room, player)["distanceMeters"] == 24


def test_every_tenth_correct_answer_levels_up_the_next_question() -> None:
    game, room, player, now = make_room()

    for _ in range(9):
        choose_correct(game, room, player, now, 0.1)
        assert room.state.level == 1
        assert room.state.level_up is False

    choose_correct(game, room, player, now, 0.1)
    view = game.view(room, player)

    assert room.state.correct_answers == 10
    assert view["level"] == 2
    assert view["levelUp"] is True
    assert view["streakInLevel"] == 0
    assert view["questionsToNextLevel"] == 10
    assert view["timeLimitMs"] == 6100


def test_one_hundred_correct_answers_complete_all_ten_levels() -> None:
    game, room, player, now = make_room(18)

    for _ in range(100):
        choose_correct(game, room, player, now, 0.05)

    view = game.view(room, player)
    assert room.phase == "finished"
    assert room.winner == "completed"
    assert room.winner_player_ids == [player.id]
    assert view["won"] is True
    assert view["level"] == 10
    assert view["correctAnswers"] == 100
    assert view["distanceMeters"] == 2400
    assert view["endReason"] == "completed"
    assert game.player_score(room, player) == 2400


def test_wrong_choice_ends_the_run_and_reveals_only_after_finish() -> None:
    game, room, player, now = make_room()
    question = room.state.question
    wrong = next(option.direction for option in question.options if not option.is_correct)
    assert game.view(room, player)["correctDirection"] is None
    now[0] += 0.5

    game.act(
        room,
        player,
        "choose",
        {"questionId": question.id, "direction": wrong},
    )
    view = game.view(room, player)

    assert room.phase == "finished"
    assert room.winner == "failed"
    assert room.winner_player_ids == []
    assert view["endReason"] == "wrong"
    assert view["correctDirection"] == question.correct_direction
    assert view["lastDirection"] == wrong


def test_late_correct_choice_is_still_a_timeout() -> None:
    game, room, player, now = make_room()
    question = room.state.question
    now[0] = question.deadline_monotonic

    game.act(
        room,
        player,
        "choose",
        {
            "questionId": question.id,
            "direction": question.correct_direction,
        },
    )

    assert room.phase == "finished"
    assert room.state.end_reason == "timeout"
    assert room.state.correct_answers == 0


def test_timeout_is_rejected_early_and_finishes_at_the_deadline() -> None:
    game, room, player, now = make_room()
    question = room.state.question

    with pytest.raises(GameRuleError, match="还可以选择"):
        game.act(room, player, "timeout", {"questionId": question.id})

    now[0] = question.deadline_monotonic + 0.001
    game.act(room, player, "timeout", {"questionId": question.id})

    assert room.phase == "finished"
    assert room.state.end_reason == "timeout"
    assert game.view(room, player)["correctDirection"] == question.correct_direction


def test_stale_timeout_cannot_end_a_new_question() -> None:
    game, room, player, now = make_room()
    old_question_id = room.state.question.id
    choose_correct(game, room, player, now, 0.2)

    game.act(room, player, "timeout", {"questionId": old_question_id})

    assert room.phase == "playing"
    assert room.state.question.id == old_question_id + 1


def test_blocked_direction_and_invalid_payload_are_rejected() -> None:
    game, room, player, _now = make_room()
    question = room.state.question
    open_directions = {option.direction for option in question.options}
    blocked = next(direction for direction in DIRECTIONS if direction not in open_directions)

    with pytest.raises(GameRuleError, match="障碍封闭"):
        game.act(
            room,
            player,
            "choose",
            {"questionId": question.id, "direction": blocked},
        )
    with pytest.raises(GameRuleError, match="题目编号"):
        game.act(room, player, "choose", {"questionId": True, "direction": "up"})
    with pytest.raises(GameRuleError, match="上、下、左、右"):
        game.act(
            room,
            player,
            "choose",
            {"questionId": question.id, "direction": "forward"},
        )


def test_only_the_host_can_act_and_scores_exist_only_after_finish() -> None:
    game, room, player, now = make_room()
    other = ArcadePlayer("p2", "a2", "旁观者", "token-2", 1)

    assert game.player_score(room, player) is None
    with pytest.raises(GameRuleError, match="挑战者"):
        game.act(
            room,
            other,
            "choose",
            {
                "questionId": room.state.question.id,
                "direction": room.state.question.correct_direction,
            },
        )

    question = room.state.question
    now[0] = question.deadline_monotonic
    game.act(room, player, "timeout", {"questionId": question.id})
    assert game.player_score(room, player) == 0


def test_record_state_contains_leaderboard_and_run_details() -> None:
    game, room, player, now = make_room()
    choose_correct(game, room, player, now, 0.8)
    question = room.state.question
    now[0] = question.deadline_monotonic
    game.act(room, player, "timeout", {"questionId": question.id})

    record = game.record_state(room)
    assert record["score"] == room.state.score
    assert record["leaderboard_distance_meters"] == 24
    assert record["correct_answers"] == 1
    assert record["highest_level"] == 1
    assert record["distance_meters"] == 24
    assert record["average_response_ms"] == 800
    assert record["end_reason"] == "timeout"
    assert record["correct_direction"] in DIRECTIONS


def test_leaderboard_score_is_maximum_distance_not_skill_points() -> None:
    game, room, player, now = make_room()

    for _ in range(6):
        choose_correct(game, room, player, now, 0.2)

    question = room.state.question
    wrong = next(option.direction for option in question.options if not option.is_correct)
    now[0] += 0.2
    game.act(
        room,
        player,
        "choose",
        {"questionId": question.id, "direction": wrong},
    )

    assert room.phase == "finished"
    assert room.state.score > 144
    assert game.player_score(room, player) == 144
    assert game.record_state(room)["leaderboard_distance_meters"] == 144
