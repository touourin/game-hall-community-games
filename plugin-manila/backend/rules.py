from __future__ import annotations

from collections.abc import Iterable

from .catalog import COMMODITIES, LANE_IDS, MARKET_TRACK, PUNT_IDS, share_commodity


def is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_start_assignments(assignments: object) -> dict[str, tuple[str, int]]:
    if not isinstance(assignments, list) or len(assignments) != 3:
        raise ValueError("必须提交三艘船的起点")
    parsed: dict[str, tuple[str, int]] = {}
    for item in assignments:
        if not isinstance(item, dict):
            raise ValueError("起点配置必须是对象")
        punt_id = item.get("puntId")
        lane_id = item.get("laneId")
        position = item.get("position")
        if punt_id not in PUNT_IDS or punt_id in parsed:
            raise ValueError("三艘船必须各配置一次")
        if lane_id not in LANE_IDS:
            raise ValueError("请选择有效且唯一的航线")
        if not is_int(position) or not 0 <= position <= 5:
            raise ValueError("每艘船的起点必须在 0-5")
        parsed[punt_id] = (lane_id, position)
    if set(parsed) != set(PUNT_IDS):
        raise ValueError("三艘船必须各配置一次")
    if len({lane for lane, _ in parsed.values()}) != 3:
        raise ValueError("三艘船必须使用不同航线")
    if sum(position for _, position in parsed.values()) != 9:
        raise ValueError("三个起点之和必须等于 9")
    return parsed


def validate_cargo_assignments(assignments: object) -> dict[str, str]:
    if not isinstance(assignments, list) or len(assignments) != 3:
        raise ValueError("必须给三艘船各装一种货物")
    parsed: dict[str, str] = {}
    for item in assignments:
        if not isinstance(item, dict):
            raise ValueError("装船配置必须是对象")
        punt_id = item.get("puntId")
        commodity_id = item.get("commodityId")
        if punt_id not in PUNT_IDS or punt_id in parsed:
            raise ValueError("三艘船必须各配置一次")
        if commodity_id not in COMMODITIES:
            raise ValueError("请选择有效货物")
        parsed[punt_id] = commodity_id
    if len(set(parsed.values())) != 3:
        raise ValueError("本航行必须装载三种不同货物")
    return parsed


def validate_pilot_moves(moves: object, *, large: bool) -> list[tuple[str, int]]:
    if not isinstance(moves, list):
        raise ValueError("引航移动必须是数组")
    if not moves:
        raise ValueError("如不移动请使用放弃操作")
    parsed: list[tuple[str, int]] = []
    seen: set[str] = set()
    for move in moves:
        if not isinstance(move, dict):
            raise ValueError("引航移动必须是对象")
        punt_id = move.get("puntId")
        delta = move.get("delta")
        if punt_id not in PUNT_IDS or punt_id in seen:
            raise ValueError("引航目标必须有效且不能重复")
        if not is_int(delta) or delta == 0:
            raise ValueError("引航位移必须是非零整数")
        seen.add(punt_id)
        parsed.append((punt_id, delta))
    if not large:
        if len(parsed) != 1 or abs(parsed[0][1]) != 1:
            raise ValueError("小引航员只能把一艘船移动 1 格")
        return parsed
    if len(parsed) == 1 and abs(parsed[0][1]) in {1, 2}:
        return parsed
    if len(parsed) == 2 and all(abs(delta) == 1 for _, delta in parsed):
        return parsed
    raise ValueError("大引航员只能移动一艘船最多 2 格，或两艘船各 1 格")


def final_wealth(
    cash: int,
    share_ids: Iterable[str],
    mortgaged_share_ids: Iterable[str],
    market_values: dict[str, int],
) -> int:
    shares = list(share_ids)
    mortgages = list(mortgaged_share_ids)
    return (
        cash
        + sum(market_values[share_commodity(card_id)] for card_id in shares)
        - 15 * len(mortgages)
    )


def next_market_value(value: int) -> int:
    if value not in MARKET_TRACK:
        raise ValueError("货物价值不在市场轨上")
    return MARKET_TRACK[min(MARKET_TRACK.index(value) + 1, len(MARKET_TRACK) - 1)]


def split_evenly(total: int, count: int) -> int:
    if count <= 0 or total % count:
        raise ValueError("收益不能按当前人数整数平分")
    return total // count
