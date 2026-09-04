from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from backend.app.games.plugin_api import ArcadeRoom, GameRuleError

from splendor_test_helpers import (
    CARDS,
    NOBLES,
    act,
    all_located_card_ids,
    make_players,
    started_room,
)


@pytest.mark.parametrize(
    ("count", "colored", "nobles"),
    [(2, 4, 3), (3, 5, 4), (4, 7, 5)],
)
def test_regular_setup_for_every_supported_player_count(count: int, colored: int, nobles: int) -> None:
    game, room, players = started_room(count)
    state = room.state

    assert room.phase == "playing"
    assert state.phase == "turn_action"
    assert state.turn.first_player_id == players[0].id
    assert state.turn.active_player_id == players[0].id
    assert state.supply == {
        "white": colored, "blue": colored, "green": colored,
        "red": colored, "black": colored, "gold": 5,
    }
    assert [len(state.tiers[level].deck) for level in (1, 2, 3)] == [36, 26, 16]
    assert all(len(state.tiers[level].market) == 4 for level in (1, 2, 3))
    assert len(state.available_noble_ids) == nobles
    assert len(all_located_card_ids(state)) == len(set(all_located_card_ids(state))) == 90
    game.assert_invariants(state)


@pytest.mark.parametrize("count", [1, 5])
def test_setup_rejects_unsupported_player_counts(count: int) -> None:
    game, _, _ = started_room(2)
    players = make_players(count)
    room = ArcadeRoom("BAD", game.key, players[0].id, players, game.initial_state())
    with pytest.raises(GameRuleError, match="2–4"):
        game.start(room)


def test_setup_rejects_nonstandard_rule_profile() -> None:
    game, _, players = started_room(2)
    room = ArcadeRoom(
        "BAD", game.key, players[0].id, players, game.initial_state(),
        options={"rulesProfile": "house-rule"},
    )
    with pytest.raises(GameRuleError, match="常规规则"):
        game.start(room)


def test_catalog_matches_reviewed_model_distribution() -> None:
    assert len(CARDS) == 90
    assert len(NOBLES) == 10
    assert Counter(item["level"] for item in CARDS.values()) == {1: 40, 2: 30, 3: 20}
    assert Counter(item["bonusColor"] for item in CARDS.values()) == {
        "white": 18, "blue": 18, "green": 18, "red": 18, "black": 18,
    }
    assert Counter(item["prestige"] for item in NOBLES.values()) == {3: 10}
    assert Counter(item["requirementTotal"] for item in NOBLES.values()) == {8: 5, 9: 5}


def test_blind_reservation_is_owner_only_but_market_reservation_stays_public() -> None:
    game, room, players = started_room(3)
    blind_id = room.state.tiers[2].deck[0]
    act(game, room, players[0], "reserve_blind", level=2)

    owner_json = json.dumps(game.view(room, players[0]), ensure_ascii=False)
    opponent_json = json.dumps(game.view(room, players[1]), ensure_ascii=False)
    assert blind_id in owner_json
    assert blind_id not in opponent_json
    assert '"deck":' not in opponent_json
    assert "unused_noble" not in opponent_json

    room.state.current_player_index = 1
    room.state.turn.active_player_id = players[1].id
    face_up_id = next(card_id for card_id in room.state.tiers[1].market if card_id)
    act(game, room, players[1], "reserve_face_up", cardId=face_up_id)
    assert face_up_id in json.dumps(game.view(room, players[0]), ensure_ascii=False)
    assert face_up_id in json.dumps(game.view(room, players[2]), ensure_ascii=False)


def test_manifest_disables_spectating_until_api_can_distinguish_private_owner_view() -> None:
    manifest = json.loads((Path(__file__).resolve().parents[1] / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["capabilities"]["spectators"] is False
    assert manifest["defaultOptions"]["allowSpectators"] is False


def test_view_exposes_all_modeled_stable_zones_and_no_hidden_order() -> None:
    game, room, players = started_room(4)
    view = game.view(room, players[0])
    assert view["sceneId"] == "turn_idle"
    assert len(view["tiers"]) == 3
    assert sum(len(tier["slots"]) for tier in view["tiers"]) == 12
    assert len(view["availableNobles"]) == 5
    assert len(view["players"]) == 4
    serialized = json.dumps(view)
    assert room.state.tiers[1].deck[0] not in serialized
    assert "initial_supply" not in serialized
    assert "unused_noble_ids" not in serialized
