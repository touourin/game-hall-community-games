from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import pytest

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError

from halli_galli_test_helpers import load_engine, make_room


MODEL_CATALOG = (
    Path(__file__).resolve().parents[2]
    / "halli-galli-game-model"
    / "model"
    / "card-catalog.json"
)


def engine_module(game):
    return __import__(type(game).__module__, fromlist=["ALL_CARDS"])


def test_runtime_catalog_matches_the_frozen_model() -> None:
    game, _ = load_engine()
    module = engine_module(game)
    model = json.loads(MODEL_CATALOG.read_text(encoding="utf-8"))

    assert module.MODEL_VERSION == model["modelVersion"]
    assert list(module.FRUIT_ORDER) == [fruit["id"] for fruit in model["fruits"]]
    assert module.COPY_DISTRIBUTION == {
        row["fruitCount"]: row["copies"]
        for row in model["copyDistribution"]
    }
    for fruit in model["fruits"]:
        assert module.FRUIT_SPECS[fruit["id"]]["nameZh"] == fruit["nameZh"]
        assert module.FRUIT_SPECS[fruit["id"]]["shape"] == fruit["shape"]
        assert module.FRUIT_SPECS[fruit["id"]]["palette"] == fruit["palette"]


def test_complete_deck_has_20_faces_56_unique_instances_and_exact_distribution() -> None:
    game, _ = load_engine()
    module = engine_module(game)
    cards = module.ALL_CARDS

    assert len(cards) == 56
    assert len({card.id for card in cards}) == 56
    assert len({card.face_id for card in cards}) == 20
    assert Counter(card.fruit_id for card in cards) == Counter(
        {fruit_id: 14 for fruit_id in module.FRUIT_ORDER},
    )
    for fruit_id in module.FRUIT_ORDER:
        assert Counter(
            card.fruit_count for card in cards if card.fruit_id == fruit_id
        ) == Counter({1: 5, 2: 3, 3: 3, 4: 2, 5: 1})


@pytest.mark.parametrize("player_count", [2, 3, 4, 5, 6])
def test_start_deals_every_card_as_evenly_as_possible(player_count: int) -> None:
    game, room, players, _ = make_room(player_count, seed=100 + player_count)
    state = room.state
    sizes = [len(state.players[player.id].draw_pile) for player in players]
    card_ids = [
        card.id
        for player in players
        for card in state.players[player.id].draw_pile
    ]

    assert room.phase == "playing"
    assert state.profile_id == "official_last_bell"
    assert state.current_player_id == players[0].id
    assert state.starting_player_id == players[0].id
    assert sum(sizes) == 56
    assert max(sizes) - min(sizes) <= 1
    assert len(set(card_ids)) == 56
    assert state.final_duel_armed is (player_count == 2)
    assert all(not state.players[player.id].discard_pile for player in players)
    game.assert_invariants(room)


@pytest.mark.parametrize("player_count", [1, 7])
def test_start_rejects_unsupported_player_counts(player_count: int) -> None:
    game, _ = load_engine()
    players = [
        ArcadePlayer(f"p{i}", f"a{i}", f"玩家{i}", "token", i)
        for i in range(player_count)
    ]
    room = ArcadeRoom("BAD", game.key, players[0].id, players, game.initial_state())
    with pytest.raises(GameRuleError, match="2–6"):
        game.start(room)


def test_regular_rules_are_locked_and_variant_cannot_be_selected() -> None:
    game, _ = load_engine()
    players = [
        ArcadePlayer(f"p{i}", f"a{i}", f"玩家{i}", "token", i)
        for i in range(2)
    ]
    room = ArcadeRoom(
        "VARIANT",
        game.key,
        players[0].id,
        players,
        game.initial_state(),
        options={"rulesProfile": "complete_collection"},
    )
    with pytest.raises(GameRuleError, match="固定使用常规"):
        game.start(room)


def test_live_view_exposes_counts_and_only_each_discard_top() -> None:
    game, room, players, clock = make_room(4)
    for _ in range(5):
        clock.advance(400)
        actor = room.player(room.state.current_player_id)
        payload = {
            "actionId": f"security-flip-{room.revision:02d}",
            "revision": room.revision,
            "expectedBoardEpoch": room.state.board_epoch,
        }
        game.act(room, actor, "flip_card", payload)
        room.revision += 1

    view = game.view(room, players[0])
    encoded = json.dumps(view, ensure_ascii=False)
    forbidden = {
        "drawPile", "discardPile", "validFruitIds", "fruitTotals",
        "processedActions", "copyIndex", "receivedAtNs", "seedSecret",
    }

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                assert key not in forbidden
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(view)
    assert "banana-1-01" not in encoded
    assert len(view["players"]) == 4
    assert all("drawCount" in player for player in view["players"])
    assert all("discardCount" in player for player in view["players"])
    assert all(
        player["topCard"] is None or "faceId" in player["topCard"]
        for player in view["players"]
    )
    assert "fruitTotals" not in view
    assert "validFruitIds" not in view


def test_record_state_is_public_and_does_not_persist_future_card_order() -> None:
    game, room, _, _ = make_room(3)
    record = game.record_state(room)
    encoded = json.dumps(record, ensure_ascii=False)
    assert "draw_pile" not in encoded
    assert "discard_pile" not in encoded
    assert "banana-1-01" not in encoded
    assert record["profileId"] == "official_last_bell"
    assert sum(player["ownedCount"] for player in record["players"]) == 56
