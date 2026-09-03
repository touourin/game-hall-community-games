from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom
from backend.app.games.plugins import _load_engine_factory


PLUGIN_DIR = Path(__file__).resolve().parents[1]


def make_engine(seed: int = 20260903):
    game = _load_engine_factory(PLUGIN_DIR, "plugin-dead-mans-draw")()
    game.rng = random.Random(seed)
    return game


def make_players(count: int) -> list[ArcadePlayer]:
    return [
        ArcadePlayer(
            id=f"p{index + 1}",
            account_id=f"a{index + 1}",
            name=f"玩家{index + 1}",
            token_hash=f"token-{index + 1}",
            seat=index,
        )
        for index in range(count)
    ]


def started_room(
    count: int = 3,
    *,
    seed: int = 20260903,
    traits_enabled: bool = False,
):
    game = make_engine(seed)
    players = make_players(count)
    room = ArcadeRoom(
        code=f"DMD{count}",
        game_key=game.key,
        host_id=players[0].id,
        players=players,
        state=game.initial_state(),
        options={
            "firstPlayer": "host",
            "rulesProfile": "tabletop_base_2015",
            "traitsEnabled": traits_enabled,
        },
    )
    game.start(room)
    return game, room, players


def actor(room: ArcadeRoom, players: list[ArcadePlayer]) -> ArcadePlayer:
    return next(player for player in players if player.id == room.state.turn.actor_id)


def remove_card(state: Any, card_id: str) -> None:
    if card_id in state.draw_pile:
        state.draw_pile.remove(card_id)
        return
    if card_id in state.discard_pile:
        state.discard_pile.remove(card_id)
        return
    if card_id in state.removed_from_game:
        state.removed_from_game.remove(card_id)
        return
    for board in state.players.values():
        for pile in board.bank.values():
            if card_id in pile:
                pile.remove(card_id)
                return
    if state.turn is not None:
        for entry in list(state.turn.play_area):
            if entry.card_id == card_id:
                state.turn.play_area.remove(entry)
                return
        if card_id in state.turn.map_reveal_card_ids:
            state.turn.map_reveal_card_ids.remove(card_id)
            return
        if state.turn.busting_card_id == card_id:
            state.turn.busting_card_id = None
            return
    raise AssertionError(f"找不到卡牌 {card_id}")


def put_draw_top(game: Any, room: ArcadeRoom, card_id: str) -> None:
    state = room.state
    remove_card(state, card_id)
    state.draw_pile.insert(0, card_id)
    game.assert_invariants(state)


def put_discard(game: Any, room: ArcadeRoom, card_id: str) -> None:
    state = room.state
    remove_card(state, card_id)
    state.discard_pile.append(card_id)
    game.assert_invariants(state)


def put_bank(game: Any, room: ArcadeRoom, player_id: str, *card_ids: str) -> None:
    state = room.state
    for card_id in card_ids:
        remove_card(state, card_id)
        state.players[player_id].bank[game_card_suit(card_id)].append(card_id)
    for pile in state.players[player_id].bank.values():
        pile.sort(key=game_card_value, reverse=True)
    game.assert_invariants(state)


def game_card_suit(card_id: str) -> str:
    return card_id.split("-")[1]


def game_card_value(card_id: str) -> int:
    return int(card_id.rsplit("-", 1)[1])


def draw_exact(game: Any, room: ArcadeRoom, player: ArcadePlayer, card_id: str) -> None:
    put_draw_top(game, room, card_id)
    game.act(room, player, "draw", {})


def pending_choice(room: ArcadeRoom):
    choice = room.state.turn.pending_choice
    assert choice is not None
    return choice


def choose_option(
    game: Any,
    room: ArcadeRoom,
    player: ArcadePlayer,
    *,
    card_id: str | None = None,
    player_id: str | None = None,
    suit: str | None = None,
    causes_bust: bool | None = None,
) -> None:
    choice = pending_choice(room)
    option = next(
        item
        for item in choice.options
        if (card_id is None or item.card_id == card_id)
        and (player_id is None or item.player_id == player_id)
        and (suit is None or item.suit == suit)
        and (causes_bust is None or item.causes_immediate_bust is causes_bust)
    )
    game.act(
        room,
        player,
        "resolve_effect",
        {"choiceId": choice.choice_id, "optionId": option.option_id},
    )


def set_trait(room: ArcadeRoom, player_id: str, trait_id: str | None) -> None:
    room.state.players[player_id].trait_id = trait_id
    room.state.traits_revealed = True


def rebuild_remaining_as_discard(game: Any, room: ArcadeRoom, draw_ids: list[str]) -> None:
    state = room.state
    occupied = set(draw_ids)
    for board in state.players.values():
        for pile in board.bank.values():
            occupied.update(pile)
    if state.turn is not None:
        occupied.update(entry.card_id for entry in state.turn.play_area)
        occupied.update(state.turn.map_reveal_card_ids)
        if state.turn.busting_card_id:
            occupied.add(state.turn.busting_card_id)
    all_ids = {
        f"loot-{suit}-{value}"
        for suit, values in {
            "anchor": range(2, 8), "hook": range(2, 8), "cannon": range(2, 8),
            "key": range(2, 8), "chest": range(2, 8), "map": range(2, 8),
            "oracle": range(2, 8), "sword": range(2, 8), "kraken": range(2, 8),
            "mermaid": range(4, 10),
        }.items()
        for value in values
    }
    state.draw_pile = list(draw_ids)
    state.discard_pile = sorted(all_ids - occupied)
    state.removed_from_game = []
    game.assert_invariants(state)
