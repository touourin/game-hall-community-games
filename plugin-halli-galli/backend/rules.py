from __future__ import annotations

from typing import Iterable

from .catalog import FRUIT_ORDER
from .state import HalliGalliPlayerState, HalliGalliState


def recompute_fruit_totals(state: HalliGalliState) -> tuple[dict[str, int], list[str]]:
    totals = {fruit_id: 0 for fruit_id in FRUIT_ORDER}
    for player_id in state.player_ids:
        pile = state.players[player_id].discard_pile
        if pile:
            card = pile[-1]
            totals[card.fruit_id] += card.fruit_count
    valid = [fruit_id for fruit_id in FRUIT_ORDER if totals[fruit_id] == 5]
    return totals, valid


def eligible_player_ids(state: HalliGalliState) -> list[str]:
    return [
        player_id for player_id in state.player_ids
        if state.players[player_id].status == "eligible"
    ]


def flippable_player_ids(state: HalliGalliState) -> list[str]:
    return [
        player_id for player_id in state.player_ids
        if state.players[player_id].status == "eligible"
        and bool(state.players[player_id].draw_pile)
    ]


def clockwise_ids(state: HalliGalliState, start_player_id: str) -> list[str]:
    start = state.player_ids.index(start_player_id)
    return state.player_ids[start:] + state.player_ids[:start]


def next_flipper(state: HalliGalliState, after_player_id: str) -> str | None:
    order = clockwise_ids(state, after_player_id)
    for player_id in order[1:] + order[:1]:
        player = state.players[player_id]
        if player.status == "eligible" and player.draw_pile:
            return player_id
    return None


def owned_count(player: HalliGalliPlayerState) -> int:
    return len(player.draw_pile) + len(player.discard_pile)


def total_owned(players: Iterable[HalliGalliPlayerState]) -> int:
    return sum(owned_count(player) for player in players)
