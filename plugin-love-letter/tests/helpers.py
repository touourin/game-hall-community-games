from __future__ import annotations

import importlib
import random
from pathlib import Path
from typing import Any

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom
from backend.app.games.plugins import _load_engine_factory


PLUGIN_DIR = Path(__file__).resolve().parents[1]


def make_engine(seed: int = 20260903):
    game = _load_engine_factory(PLUGIN_DIR, "plugin-love-letter")()
    game.rng = random.Random(seed)
    return game


def symbols(game: Any):
    module = importlib.import_module(type(game).__module__)
    return module.Card, module.CARD_COUNTS, module.CARD_SPECS


def card(game: Any, type_id: str, suffix: str | int = 1):
    Card, _, _ = symbols(game)
    return Card(f"fixture-{type_id}-{suffix}", type_id)


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


def started_room(count: int = 3, *, seed: int = 20260903):
    game = make_engine(seed)
    players = make_players(count)
    room = ArcadeRoom(
        code=f"LOVE{count}",
        game_key=game.key,
        host_id=players[0].id,
        players=players,
        state=game.initial_state(),
        options={"firstPlayer": "host"},
    )
    game.start(room)
    return game, room, players


def configure_play(
    game: Any,
    room: ArcadeRoom,
    hands: dict[str, list[str]],
    *,
    actor_id: str = "p1",
    deck: list[str] | None = None,
    reserve: str | None = "spy",
    protected: list[str] | None = None,
    out: list[str] | None = None,
) -> None:
    state = room.state
    state.hands = {
        player_id: [card(game, type_id, f"{player_id}-{index}") for index, type_id in enumerate(hands.get(player_id, []), 1)]
        for player_id in state.player_ids
    }
    deck_types = deck if deck is not None else ["guard", "priest", "baron", "handmaid", "prince"]
    state.deck = [card(game, type_id, f"deck-{index}") for index, type_id in enumerate(deck_types, 1)]
    state.reserve = card(game, reserve, "reserve") if reserve else None
    state.face_up_set_aside = []
    state.played = {player_id: [] for player_id in state.player_ids}
    state.out_player_ids = list(out or [])
    state.protected_player_ids = list(protected or [])
    state.spy_player_ids = []
    state.knowledge = []
    state.current_player_id = actor_id
    state.start_player_id = actor_id
    state.stage = "play"
    state.turn_number = 7
    state.pending_choice = None
    state.round_summary = None
    state.game_winner_ids = []
    room.phase = "playing"
    room.winner_player_ids = []
    room.win_reason = None


def play_type(game: Any, room: ArcadeRoom, players: list[ArcadePlayer], type_id: str):
    state = room.state
    player = next(item for item in players if item.id == state.current_player_id)
    played = next(card for card in state.hands[player.id] if card.type_id == type_id)
    game.act(room, player, "play_card", {"cardId": played.id, "turnNumber": state.turn_number})
    return played


def resolve_choice(game: Any, room: ArcadeRoom, players: list[ArcadePlayer], **payload: Any) -> None:
    pending = room.state.pending_choice
    assert pending is not None
    player = next(item for item in players if item.id == pending.actor_id)
    game.act(
        room,
        player,
        "resolve_choice",
        {"choiceId": pending.id, "turnNumber": room.state.turn_number, **payload},
    )


def all_physical_cards(room: ArcadeRoom) -> list[Any]:
    state = room.state
    cards = list(state.deck)
    if state.reserve is not None:
        cards.append(state.reserve)
    cards.extend(state.face_up_set_aside)
    for player_id in state.player_ids:
        cards.extend(state.hands[player_id])
        cards.extend(entry.card for entry in state.played[player_id])
    return cards
