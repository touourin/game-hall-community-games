from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError


DIRECTIONS = ("up", "left", "down", "right")
DIRECTION_LABELS = {
    "up": "上",
    "left": "左",
    "down": "下",
    "right": "右",
}
MAX_EQUATION_LENGTH = 32
PROGRESSION_PATH = Path(__file__).resolve().parents[1] / "model" / "progression.json"


@dataclass(frozen=True)
class LevelProfile:
    level: int
    time_limit_ms: int
    max_target: int
    choice_min: int
    choice_max: int
    max_factor: int
    templates: tuple[str, ...]
    track_period_ms: int
    run_cycle_ms: int
    speed_lines: int


@dataclass(frozen=True)
class Expression:
    text: str
    value: int
    operation_count: int
    template: str


@dataclass(frozen=True)
class EquationOption:
    direction: str
    equation: str
    left_value: int
    right_value: int
    is_correct: bool
    left_template: str
    right_template: str


@dataclass(frozen=True)
class MathQuestion:
    id: int
    level: int
    time_limit_ms: int
    created_monotonic: float
    deadline_monotonic: float
    correct_direction: str
    options: tuple[EquationOption, ...]


@dataclass
class MathRunnerState:
    level: int = 1
    correct_answers: int = 0
    score: int = 0
    started_monotonic: float = 0.0
    elapsed_ms: int = 0
    question: MathQuestion | None = None
    response_times_ms: list[int] = field(default_factory=list)
    last_direction: str | None = None
    last_points: int = 0
    level_up: bool = False
    end_reason: str | None = None
    final_correct_direction: str | None = None


def _load_progression() -> tuple[int, int, tuple[LevelProfile, ...]]:
    raw = json.loads(PROGRESSION_PATH.read_text(encoding="utf-8"))
    if raw.get("schemaVersion") != 1:
        raise RuntimeError("算途疾行等级配置版本不受支持")

    questions_per_level = raw.get("questionsPerLevel")
    distance_per_question = raw.get("distancePerQuestionMeters")
    levels = raw.get("levels")
    if questions_per_level != 10 or not isinstance(distance_per_question, int):
        raise RuntimeError("算途疾行等级配置缺少固定进度参数")
    if not isinstance(levels, list) or len(levels) != 10:
        raise RuntimeError("算途疾行必须配置连续的 10 个等级")

    profiles: list[LevelProfile] = []
    previous_time_limit: int | None = None
    previous_target = 0
    for expected_level, item in enumerate(levels, start=1):
        if not isinstance(item, dict) or item.get("level") != expected_level:
            raise RuntimeError("算途疾行等级编号必须从 1 连续到 10")
        profile = LevelProfile(
            level=expected_level,
            time_limit_ms=int(item["timeLimitMs"]),
            max_target=int(item["maxTarget"]),
            choice_min=int(item["choiceMin"]),
            choice_max=int(item["choiceMax"]),
            max_factor=int(item["maxFactor"]),
            templates=tuple(item["templates"]),
            track_period_ms=int(item["trackPeriodMs"]),
            run_cycle_ms=int(item["runCycleMs"]),
            speed_lines=int(item["speedLines"]),
        )
        if not 2 <= profile.choice_min <= profile.choice_max <= 4:
            raise RuntimeError("算途疾行每级必须开放 2–4 个方向")
        if previous_time_limit is not None and profile.time_limit_ms >= previous_time_limit:
            raise RuntimeError("算途疾行答题时限必须逐级缩短")
        if profile.max_target < previous_target:
            raise RuntimeError("算途疾行心算范围不能随等级下降")
        if not profile.templates:
            raise RuntimeError("算途疾行每级至少需要一个算式模板")
        profiles.append(profile)
        previous_time_limit = profile.time_limit_ms
        previous_target = profile.max_target
    return questions_per_level, distance_per_question, tuple(profiles)


QUESTIONS_PER_LEVEL, DISTANCE_PER_QUESTION_METERS, LEVEL_PROFILES = _load_progression()
MAX_LEVEL = len(LEVEL_PROFILES)
TOTAL_QUESTIONS = MAX_LEVEL * QUESTIONS_PER_LEVEL


class MathRunnerEngine:
    key = "plugin-math-runner"
    name = "算途疾行"
    min_players = 1
    max_players = 1
    public_rooms = False

    def __init__(
        self,
        rng: random.Random | random.SystemRandom | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.rng = rng or random.SystemRandom()
        self.clock = clock or time.monotonic

    def initial_state(self) -> MathRunnerState:
        return MathRunnerState()

    def start(self, room: ArcadeRoom) -> None:
        started = self.clock()
        state = MathRunnerState(started_monotonic=started)
        state.question = self._new_question(level=1, question_id=1, now=started)
        room.state = state
        room.phase = "playing"

    def act(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        action: str,
        payload: dict[str, Any],
    ) -> None:
        if player.id != room.host_id:
            raise GameRuleError("只有当前挑战者可以控制跑者")
        if room.phase != "playing":
            raise GameRuleError("本次跑酷已经结束")

        state: MathRunnerState = room.state
        question = state.question
        if question is None:
            raise GameRuleError("当前路口尚未准备完成")

        if action == "choose":
            self._choose(room, player, state, question, payload)
            return
        if action == "timeout":
            self._timeout(room, player, state, question, payload)
            return
        raise GameRuleError("不支持这个跑酷操作")

    def view(self, room: ArcadeRoom, viewer: ArcadePlayer) -> dict[str, Any]:
        state: MathRunnerState = room.state
        question = state.question
        now = self.clock()
        elapsed_ms = self._elapsed_ms(state, now) if room.phase == "playing" else state.elapsed_ms
        remaining_ms = (
            self._remaining_ms(question, now)
            if question is not None and room.phase == "playing"
            else 0
        )
        options = [] if question is None else [
            {"direction": option.direction, "equation": option.equation}
            for option in question.options
        ]
        open_directions = {option["direction"] for option in options}
        profile = LEVEL_PROFILES[state.level - 1]
        finished = room.phase == "finished"
        streak_in_level = state.correct_answers % QUESTIONS_PER_LEVEL
        average_response_ms = (
            round(sum(state.response_times_ms) / len(state.response_times_ms))
            if state.response_times_ms
            else None
        )
        return {
            "level": state.level,
            "maxLevel": MAX_LEVEL,
            "correctAnswers": state.correct_answers,
            "totalQuestions": TOTAL_QUESTIONS,
            "streakInLevel": streak_in_level,
            "questionsPerLevel": QUESTIONS_PER_LEVEL,
            "questionsToNextLevel": (
                0
                if finished and state.end_reason == "completed"
                else QUESTIONS_PER_LEVEL - streak_in_level
            ),
            "score": state.score,
            "distanceMeters": state.correct_answers * DISTANCE_PER_QUESTION_METERS,
            "questionId": question.id if question is not None else None,
            "timeLimitMs": question.time_limit_ms if question is not None else profile.time_limit_ms,
            "remainingMs": remaining_ms,
            "options": options,
            "blockedDirections": [
                direction for direction in DIRECTIONS if direction not in open_directions
            ],
            "lastDirection": state.last_direction,
            "lastPoints": state.last_points,
            "levelUp": state.level_up,
            "endReason": state.end_reason,
            "correctDirection": (
                state.final_correct_direction if finished else None
            ),
            "elapsedMs": elapsed_ms,
            "averageResponseMs": average_response_ms,
            "speed": {
                "trackPeriodMs": profile.track_period_ms,
                "runCycleMs": profile.run_cycle_ms,
                "speedLines": profile.speed_lines,
            },
            "won": viewer.id in room.winner_player_ids,
            "result": room.winner if finished else None,
        }

    def player_result(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
    ) -> tuple[str, str, bool]:
        return "runner", "solo", player.id in room.winner_player_ids

    def player_score(self, room: ArcadeRoom, player: ArcadePlayer) -> int | None:
        state: MathRunnerState = room.state
        if room.phase != "finished":
            return None
        # The shared high-score leaderboard stores one authoritative integer.
        # For this game that value is metres travelled, so the public ranking is
        # ordered by maximum route distance instead of the secondary skill score.
        return state.correct_answers * DISTANCE_PER_QUESTION_METERS

    def record_state(self, room: ArcadeRoom) -> dict[str, Any]:
        state: MathRunnerState = room.state
        average_response_ms = (
            round(sum(state.response_times_ms) / len(state.response_times_ms))
            if state.response_times_ms
            else None
        )
        question = state.question
        distance_meters = state.correct_answers * DISTANCE_PER_QUESTION_METERS
        return {
            "score": state.score,
            "leaderboard_distance_meters": distance_meters,
            "correct_answers": state.correct_answers,
            "highest_level": state.level,
            "distance_meters": distance_meters,
            "elapsed_ms": state.elapsed_ms,
            "average_response_ms": average_response_ms,
            "end_reason": state.end_reason,
            "last_question_id": question.id if question is not None else None,
            "correct_direction": state.final_correct_direction,
        }

    def _choose(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        state: MathRunnerState,
        question: MathQuestion,
        payload: dict[str, Any],
    ) -> None:
        question_id = self._require_question_id(payload)
        if question_id != question.id:
            raise GameRuleError("这个路口已经过去，请按当前题目选择方向")

        direction = payload.get("direction")
        if not isinstance(direction, str) or direction not in DIRECTIONS:
            raise GameRuleError("请选择上、下、左、右中的一个方向")

        now = self.clock()
        if now >= question.deadline_monotonic:
            self._finish_timeout(room, player, state, question, now)
            return

        option = next(
            (entry for entry in question.options if entry.direction == direction),
            None,
        )
        if option is None:
            raise GameRuleError(f"{DIRECTION_LABELS[direction]}方向已被障碍封闭")

        response_ms = min(
            question.time_limit_ms,
            max(0, round((now - question.created_monotonic) * 1_000)),
        )
        state.last_direction = direction
        state.level_up = False

        if not option.is_correct:
            state.last_points = 0
            state.end_reason = "wrong"
            state.final_correct_direction = question.correct_direction
            state.elapsed_ms = self._elapsed_ms(state, now)
            room.finish(
                "failed",
                [],
                (
                    f"第 {question.id} 个路口选择错误，"
                    f"正确方向是{DIRECTION_LABELS[question.correct_direction]}"
                ),
            )
            return

        remaining_ms = max(0, question.time_limit_ms - response_ms)
        points = state.level * 100 + remaining_ms // 20
        state.correct_answers += 1
        state.score += points
        state.last_points = points
        state.response_times_ms.append(response_ms)
        state.elapsed_ms = self._elapsed_ms(state, now)
        state.final_correct_direction = question.correct_direction

        if state.correct_answers >= TOTAL_QUESTIONS:
            state.end_reason = "completed"
            room.finish(
                "completed",
                [player.id],
                f"连续通过 {TOTAL_QUESTIONS} 个路口，以 {state.score} 分完成十级赛道",
            )
            return

        next_level = min(
            MAX_LEVEL,
            state.correct_answers // QUESTIONS_PER_LEVEL + 1,
        )
        state.level_up = next_level > state.level
        state.level = next_level
        state.final_correct_direction = None
        state.question = self._new_question(
            level=state.level,
            question_id=question.id + 1,
            now=now,
        )

    def _timeout(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        state: MathRunnerState,
        question: MathQuestion,
        payload: dict[str, Any],
    ) -> None:
        question_id = self._require_question_id(payload)
        if question_id < question.id:
            return
        if question_id > question.id:
            raise GameRuleError("超时请求对应的路口尚未出现")
        now = self.clock()
        if now < question.deadline_monotonic:
            raise GameRuleError("跑者尚未到达路口，现在还可以选择")
        self._finish_timeout(room, player, state, question, now)

    def _finish_timeout(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        state: MathRunnerState,
        question: MathQuestion,
        now: float,
    ) -> None:
        state.last_points = 0
        state.level_up = False
        state.end_reason = "timeout"
        state.final_correct_direction = question.correct_direction
        state.elapsed_ms = self._elapsed_ms(state, now)
        room.finish(
            "failed",
            [],
            (
                f"第 {question.id} 个路口未及时选择，"
                f"正确方向是{DIRECTION_LABELS[question.correct_direction]}"
            ),
        )

    def _new_question(
        self,
        *,
        level: int,
        question_id: int,
        now: float,
    ) -> MathQuestion:
        profile = LEVEL_PROFILES[level - 1]
        option_count = self.rng.randint(profile.choice_min, profile.choice_max)
        sampled = set(self.rng.sample(list(DIRECTIONS), option_count))
        available = [direction for direction in DIRECTIONS if direction in sampled]
        correct_direction = self.rng.choice(available)
        used_equations: set[str] = set()
        options: list[EquationOption] = []
        for direction in available:
            option = self._build_equation(
                profile,
                is_correct=direction == correct_direction,
                used_equations=used_equations,
                direction=direction,
            )
            used_equations.add(option.equation)
            options.append(option)

        if sum(option.is_correct for option in options) != 1:
            raise RuntimeError("算途疾行生成的路口没有唯一正确方向")
        deadline = now + profile.time_limit_ms / 1_000
        return MathQuestion(
            id=question_id,
            level=level,
            time_limit_ms=profile.time_limit_ms,
            created_monotonic=now,
            deadline_monotonic=deadline,
            correct_direction=correct_direction,
            options=tuple(options),
        )

    def _build_equation(
        self,
        profile: LevelProfile,
        *,
        is_correct: bool,
        used_equations: set[str],
        direction: str,
    ) -> EquationOption:
        for _attempt in range(300):
            left_target = self.rng.randint(4, profile.max_target)
            right_target = (
                left_target
                if is_correct
                else self._different_target(left_target, profile.max_target)
            )
            left = self._expression_for_value(left_target, profile)
            right = self._expression_for_value(right_target, profile)
            if left is None or right is None or left.text == right.text:
                continue
            equation = f"{left.text} = {right.text}"
            if len(equation) > MAX_EQUATION_LENGTH or equation in used_equations:
                continue
            if (left.value == right.value) != is_correct:
                continue
            return EquationOption(
                direction=direction,
                equation=equation,
                left_value=left.value,
                right_value=right.value,
                is_correct=is_correct,
                left_template=left.template,
                right_template=right.template,
            )
        raise RuntimeError(f"无法为等级 {profile.level} 生成唯一算式")

    def _different_target(self, target: int, maximum: int) -> int:
        delta = self.rng.randint(1, min(9, max(1, maximum - 1)))
        candidates = [target - delta, target + delta]
        valid = [value for value in candidates if 2 <= value <= maximum and value != target]
        if valid:
            return self.rng.choice(valid)
        return 2 if target != 2 else min(maximum, 3)

    def _expression_for_value(
        self,
        value: int,
        profile: LevelProfile,
    ) -> Expression | None:
        templates = list(profile.templates)
        self.rng.shuffle(templates)
        for template in templates:
            expression = self._make_expression(template, value, profile)
            if expression is not None:
                return expression
        return None

    def _make_expression(
        self,
        template: str,
        value: int,
        profile: LevelProfile,
    ) -> Expression | None:
        factor = profile.max_factor
        if template == "add" and value >= 2:
            left = self.rng.randint(1, value - 1)
            return Expression(f"{left} + {value - left}", value, 1, template)

        if template == "subtract":
            right = self.rng.randint(1, min(factor * 2, 18))
            return Expression(f"{value + right} - {right}", value, 1, template)

        if template == "multiply":
            divisors = [
                entry
                for entry in range(2, factor + 1)
                if value % entry == 0 and 2 <= value // entry <= factor
            ]
            if not divisors:
                return None
            left = self.rng.choice(divisors)
            return Expression(f"{left} × {value // left}", value, 1, template)

        if template == "add_subtract":
            addend = self.rng.randint(2, min(factor * 2, 18))
            subtract = self.rng.randint(1, min(factor, addend + value - 1))
            first = value - addend + subtract
            if first < 1:
                return None
            return Expression(
                f"{first} + {addend} - {subtract}",
                value,
                2,
                template,
            )

        if template == "multiply_add":
            candidates = [
                (left, right)
                for left in range(2, factor + 1)
                for right in range(2, factor + 1)
                if 1 <= value - left * right <= factor * 2
            ]
            if not candidates:
                return None
            left, right = self.rng.choice(candidates)
            addend = value - left * right
            return Expression(
                f"{left} × {right} + {addend}",
                value,
                2,
                template,
            )

        if template == "divide_add" and value >= 3:
            quotient = self.rng.randint(2, min(factor, value - 1))
            divisor = self.rng.randint(2, factor)
            numerator = quotient * divisor
            addend = value - quotient
            return Expression(
                f"{numerator} ÷ {divisor} + {addend}",
                value,
                2,
                template,
            )

        if template == "group_multiply":
            divisors = [
                entry
                for entry in range(2, factor + 1)
                if value % entry == 0 and 2 <= value // entry <= factor * 2
            ]
            if not divisors:
                return None
            multiplier = self.rng.choice(divisors)
            group_total = value // multiplier
            left = self.rng.randint(1, group_total - 1)
            return Expression(
                f"({left} + {group_total - left}) × {multiplier}",
                value,
                2,
                template,
            )

        if template == "multiply_subtract":
            candidates = [
                (left, right)
                for left in range(2, factor + 1)
                for right in range(2, factor + 1)
                if 1 <= left * right - value <= factor * 2
            ]
            if not candidates:
                return None
            left, right = self.rng.choice(candidates)
            subtract = left * right - value
            return Expression(
                f"{left} × {right} - {subtract}",
                value,
                2,
                template,
            )

        if template == "group_multiply_subtract":
            candidates: list[tuple[int, int, int]] = []
            for multiplier in range(2, factor + 1):
                minimum_group = max(2, math.ceil((value + 1) / multiplier))
                for group_total in range(minimum_group, factor * 2 + 1):
                    subtract = group_total * multiplier - value
                    if 1 <= subtract <= factor * 2:
                        candidates.append((group_total, multiplier, subtract))
            if not candidates:
                return None
            group_total, multiplier, subtract = self.rng.choice(candidates)
            left = self.rng.randint(1, group_total - 1)
            return Expression(
                f"({left} + {group_total - left}) × {multiplier} - {subtract}",
                value,
                3,
                template,
            )

        if template == "multiply_add_divide":
            candidates: list[tuple[int, int, int]] = []
            for quotient in range(1, min(factor, value - 3) + 1):
                product = value - quotient
                for left in range(2, factor + 1):
                    if product % left == 0 and 2 <= product // left <= factor:
                        candidates.append((left, product // left, quotient))
            if not candidates:
                return None
            left, right, quotient = self.rng.choice(candidates)
            divisor = self.rng.randint(2, factor)
            numerator = quotient * divisor
            return Expression(
                f"{left} × {right} + {numerator} ÷ {divisor}",
                value,
                3,
                template,
            )
        return None

    @staticmethod
    def _require_question_id(payload: dict[str, Any]) -> int:
        question_id = payload.get("questionId")
        if isinstance(question_id, bool) or not isinstance(question_id, int):
            raise GameRuleError("缺少有效的路口题目编号")
        return question_id

    @staticmethod
    def _remaining_ms(question: MathQuestion, now: float) -> int:
        return max(0, int((question.deadline_monotonic - now) * 1_000))

    @staticmethod
    def _elapsed_ms(state: MathRunnerState, now: float) -> int:
        return max(0, round((now - state.started_monotonic) * 1_000))
