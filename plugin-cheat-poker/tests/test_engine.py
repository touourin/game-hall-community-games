from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import pytest

from backend.app.arcade.models import ArcadePlayer, ArcadeRoom
from backend.app.games.plugins import discover_game_plugins


PLUGIN_ROOT = Path(__file__).resolve().parents[2]


def engine():
    game = next(
        plugin.engine
        for plugin in discover_game_plugins(PLUGIN_ROOT)
        if plugin.engine.key == "plugin-cheat-poker"
    )
    game.rng = random.Random(20260804)
    return game


def started_room(player_count: int = 2):
    game = engine()
    players = [
        ArcadePlayer(
            f"p{index + 1}",
            f"a{index + 1}",
            f"玩家{index + 1}",
            f"token-{index + 1}",
            index,
        )
        for index in range(player_count)
    ]
    room = ArcadeRoom(
        "BLUF",
        game.key,
        players[0].id,
        players,
        game.initial_state(),
        options={"firstPlayer": "host"},
    )
    game.start(room)
    return game, room, players


def first_plain_card(cards: list[Any]):
    return next(card for card in cards if not card.is_joker)


def different_rank(rank: str) -> str:
    return "A" if rank != "A" else "K"


@pytest.mark.parametrize(
    ("player_count", "cards_per_player"),
    ((2, 15), (3, 15), (4, 10), (5, 10), (6, 9)),
)
def test_deals_fixed_equal_hands_and_hides_other_players_cards(
    player_count: int,
    cards_per_player: int,
) -> None:
    game, room, players = started_room(player_count)
    state = room.state
    counts = [len(state.hands[player.id]) for player in players]
    all_card_ids = [
        card.id
        for player in players
        for card in state.hands[player.id]
    ]

    assert counts == [cards_per_player] * player_count
    assert len(set(all_card_ids)) == cards_per_player * player_count
    assert state.pile == []
    assert state.archived_count == 0
    assert state.dealer_player_id == players[0].id
    assert state.current_player_id == players[0].id
    assert state.winner_target == (player_count + 1) // 2

    view = game.view(room, players[0])
    assert len(view["hand"]) == cards_per_player
    assert view["cardCounts"][players[1].id] == cards_per_player
    assert "hands" not in view
def test_a_lie_on_the_last_card_is_challenged_before_ranking() -> None:
    game, room, players = started_room()
    state = room.state
    card = first_plain_card(state.hands[players[0].id])
    state.hands[players[0].id] = [card]

    game.act(
        room,
        players[0],
        "play",
        {"cardIds": [card.id], "claimedRank": different_rank(card.rank)},
    )

    assert room.phase == "playing"
    assert state.rankings == []
    assert state.hands[players[0].id] == []

    game.act(room, players[1], "challenge", {})

    assert room.phase == "playing"
    assert state.rankings == []
    assert [held.id for held in state.hands[players[0].id]] == [card.id]
    assert state.current_player_id == players[1].id
    assert state.history[-1]["truthful"] is False


def test_joker_is_truthful_for_any_claimed_rank() -> None:
    game, room, players = started_room(3)
    state = room.state
    claimant_id = next(
        player_id
        for player_id, hand in state.hands.items()
        if any(card.is_joker for card in hand)
    )
    claimant = room.player(claimant_id)
    joker = next(card for card in state.hands[claimant_id] if card.is_joker)
    spare = next(card for card in state.hands[claimant_id] if card.id != joker.id)
    state.hands[claimant_id] = [joker, spare]
    state.current_player_id = claimant_id
    challenger_id = game._next_active_id(state, claimant_id)
    challenger = room.player(challenger_id)

    game.act(
        room,
        claimant,
        "play",
        {"cardIds": [joker.id], "claimedRank": "A"},
    )
    game.act(room, challenger, "challenge", {})

    assert state.history[-1]["truthful"] is True
    assert joker.id in {card.id for card in state.hands[challenger.id]}
    assert state.current_player_id == claimant.id


def test_pile_at_15_is_sealed_and_previous_player_reopens() -> None:
    game, room, players = started_room()
    state = room.state
    staged_pile = list(state.hands[players[1].id][:14])
    staged_ids = {card.id for card in staged_pile}
    state.hands[players[1].id] = [
        card for card in state.hands[players[1].id]
        if card.id not in staged_ids
    ]
    state.pile = staged_pile
    first_hand = state.hands[players[0].id]
    played = first_plain_card(first_hand)
    spare = next(card for card in first_hand if card.id != played.id)
    state.hands[players[0].id] = [played, spare]

    game.act(
        room,
        players[0],
        "play",
        {"cardIds": [played.id], "claimedRank": played.rank},
    )
    assert len(state.pile) == 15
    assert game.view(room, players[1])["pileLocked"] is True

    game.act(room, players[1], "accept", {})

    assert state.pile == []
    assert state.archived_count == 15
    assert state.required_rank is None
    assert state.current_player_id == players[0].id
    assert state.stage == "play"


def test_ranked_winners_receive_descending_points_and_others_lose_one() -> None:
    game, room, players = started_room(4)
    state = room.state
    first_card = first_plain_card(state.hands[players[0].id])
    second_card = first_plain_card(state.hands[players[1].id])
    state.hands[players[0].id] = [first_card]
    state.hands[players[1].id] = [second_card]

    game.act(
        room,
        players[0],
        "play",
        {"cardIds": [first_card.id], "claimedRank": first_card.rank},
    )
    game.act(room, players[1], "accept", {})
    assert state.rankings == [players[0].id]

    game.act(
        room,
        players[1],
        "play",
        {"cardIds": [second_card.id], "claimedRank": state.required_rank},
    )
    game.act(room, players[2], "accept", {})

    assert room.phase == "finished"
    assert room.winner_player_ids == [players[0].id, players[1].id]
    assert state.scores == {
        players[0].id: 2,
        players[1].id: 1,
        players[2].id: -1,
        players[3].id: -1,
    }
    assert game.player_result(room, players[0]) == ("第 1 名", "ranking", True)
    assert "hands" not in game.record_state(room)


def test_five_player_game_has_three_ranked_winners() -> None:
    game, room, players = started_room(5)
    state = room.state
    for player in players[:3]:
        state.hands[player.id] = [first_plain_card(state.hands[player.id])]

    for index, player in enumerate(players[:3]):
        card = state.hands[player.id][0]
        claim = state.required_rank or card.rank
        game.act(
            room,
            player,
            "play",
            {"cardIds": [card.id], "claimedRank": claim},
        )
        game.act(room, players[index + 1], "accept", {})

    assert room.phase == "finished"
    assert room.winner_player_ids == [player.id for player in players[:3]]
    assert [state.scores[player.id] for player in players] == [3, 2, 1, -1, -1]
