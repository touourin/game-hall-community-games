from __future__ import annotations

import pytest

from manila_plugin_test_backend.rules import (
    final_wealth,
    next_market_value,
    split_evenly,
    validate_cargo_assignments,
    validate_pilot_moves,
    validate_start_assignments,
)


def test_start_positions_require_unique_lanes_range_and_sum_nine() -> None:
    parsed = validate_start_assignments(
        [
            {"puntId": "punt-1", "laneId": "lane-2", "position": 0},
            {"puntId": "punt-2", "laneId": "lane-3", "position": 4},
            {"puntId": "punt-3", "laneId": "lane-1", "position": 5},
        ]
    )
    assert parsed["punt-3"] == ("lane-1", 5)
    invalid = [
        [
            {"puntId": "punt-1", "laneId": "lane-1", "position": 2},
            {"puntId": "punt-2", "laneId": "lane-1", "position": 3},
            {"puntId": "punt-3", "laneId": "lane-3", "position": 4},
        ],
        [
            {"puntId": "punt-1", "laneId": "lane-1", "position": 1},
            {"puntId": "punt-2", "laneId": "lane-2", "position": 3},
            {"puntId": "punt-3", "laneId": "lane-3", "position": 4},
        ],
        [
            {"puntId": "punt-1", "laneId": "lane-1", "position": 6},
            {"puntId": "punt-2", "laneId": "lane-2", "position": 1},
            {"puntId": "punt-3", "laneId": "lane-3", "position": 2},
        ],
    ]
    for value in invalid:
        with pytest.raises(ValueError):
            validate_start_assignments(value)


def test_cargo_requires_three_different_commodities() -> None:
    parsed = validate_cargo_assignments(
        [
            {"puntId": "punt-1", "commodityId": "jade"},
            {"puntId": "punt-2", "commodityId": "silk"},
            {"puntId": "punt-3", "commodityId": "ginseng"},
        ]
    )
    assert set(parsed.values()) == {"jade", "silk", "ginseng"}
    with pytest.raises(ValueError):
        validate_cargo_assignments(
            [
                {"puntId": "punt-1", "commodityId": "jade"},
                {"puntId": "punt-2", "commodityId": "jade"},
                {"puntId": "punt-3", "commodityId": "ginseng"},
            ]
        )


@pytest.mark.parametrize(
    ("large", "moves"),
    [
        (False, [{"puntId": "punt-1", "delta": -1}]),
        (False, [{"puntId": "punt-1", "delta": 1}]),
        (True, [{"puntId": "punt-1", "delta": 2}]),
        (
            True,
            [
                {"puntId": "punt-1", "delta": -1},
                {"puntId": "punt-2", "delta": 1},
            ],
        ),
    ],
)
def test_valid_pilot_shapes(large: bool, moves: list[dict[str, object]]) -> None:
    assert validate_pilot_moves(moves, large=large)


@pytest.mark.parametrize(
    ("large", "moves"),
    [
        (False, [{"puntId": "punt-1", "delta": 2}]),
        (False, []),
        (True, [{"puntId": "punt-1", "delta": 3}]),
        (
            True,
            [
                {"puntId": "punt-1", "delta": 1},
                {"puntId": "punt-1", "delta": -1},
            ],
        ),
    ],
)
def test_invalid_pilot_shapes(large: bool, moves: list[dict[str, object]]) -> None:
    with pytest.raises(ValueError):
        validate_pilot_moves(moves, large=large)


def test_market_split_and_final_wealth_corner_cases() -> None:
    assert [next_market_value(value) for value in (0, 5, 10, 20, 30)] == [5, 10, 20, 30, 30]
    assert split_evenly(36, 4) == 9
    with pytest.raises(ValueError):
        split_evenly(18, 4)
    assert final_wealth(
        7,
        ["share-jade-01", "share-silk-01"],
        ["share-jade-01"],
        {"ginseng": 0, "nutmeg": 5, "silk": 20, "jade": 30},
    ) == 42

