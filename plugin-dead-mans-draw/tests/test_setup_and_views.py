from __future__ import annotations

import json

import pytest

from backend.app.games.plugin_api import ArcadeRoom, GameRuleError

from dead_mans_draw_test_helpers import make_engine, make_players, started_room


@pytest.mark.parametrize("count", (2, 3, 4))
def test_regular_setup_has_exact_card_zones_for_every_table_size(count: int) -> None:
    game, room, players = started_room(count)

    assert room.phase == "playing"
    assert room.state.phase == "turn"
    assert room.state.turn.actor_id == players[0].id
    assert len(room.state.draw_pile) == 50
    assert len(room.state.discard_pile) == 10
    assert len(set(room.state.draw_pile + room.state.discard_pile)) == 60
    assert {
        card_id.rsplit("-", 1)[0]
        for card_id in room.state.discard_pile
    } == {
        "loot-anchor", "loot-hook", "loot-cannon", "loot-key", "loot-chest",
        "loot-map", "loot-oracle", "loot-sword", "loot-kraken", "loot-mermaid",
    }
    game.assert_invariants(room.state)


@pytest.mark.parametrize("count", (1, 5))
def test_rejects_unsupported_player_counts(count: int) -> None:
    game = make_engine()
    players = make_players(count)
    room = ArcadeRoom("NOPE", game.key, players[0].id, players, game.initial_state())
    with pytest.raises(GameRuleError, match="2–4"):
        game.start(room)


def test_regular_build_rejects_nonstandard_profiles_and_variants() -> None:
    game = make_engine()
    players = make_players(2)
    room = ArcadeRoom(
        "NOPE", game.key, players[0].id, players, game.initial_state(),
        options={"rulesProfile": "digital_safe_2014"},
    )
    with pytest.raises(GameRuleError, match="常规规则"):
        game.start(room)

    room.options = {"globalVariant": "variant-strange-lands"}
    with pytest.raises(GameRuleError, match="不启用"):
        game.start(room)


def test_trait_offers_are_unique_private_and_revealed_together() -> None:
    game, room, players = started_room(4, traits_enabled=True)
    offers = {
        player.id: [item["id"] for item in game.view(room, player)["self"]["traitOffer"]]
        for player in players
    }
    assert all(len(items) == 2 for items in offers.values())
    assert len({item for items in offers.values() for item in items}) == 8
    p1_serialized = json.dumps(game.view(room, players[0]), ensure_ascii=False)
    assert offers[players[1].id][0] not in p1_serialized

    for player in players:
        view = game.view(room, player)
        game.act(room, player, "choose_trait", {"traitId": view["self"]["traitOffer"][0]["id"]})
        if game.view(room, player)["actions"]["canChooseLockerTarget"]:
            target = next(candidate.id for candidate in players if candidate.id != player.id)
            game.act(room, player, "choose_locker_target", {"playerId": target})

    assert room.state.phase == "turn"
    assert room.state.traits_revealed is True
    assert all(item["traitId"] for item in game.view(room, players[0])["players"])


def test_davy_jones_owner_must_select_a_different_live_target() -> None:
    game, room, players = started_room(2, traits_enabled=True)
    board = room.state.players[players[0].id]
    board.trait_offer = ["trait-davy-jones-locker", board.trait_offer[0]]
    game.act(room, players[0], "choose_trait", {"traitId": "trait-davy-jones-locker"})
    other = game.view(room, players[1])["self"]["traitOffer"][0]["id"]
    game.act(room, players[1], "choose_trait", {"traitId": other})
    assert room.state.phase == "trait_selection"

    with pytest.raises(GameRuleError, match="另一名"):
        game.act(room, players[0], "choose_locker_target", {"playerId": players[0].id})
    game.act(room, players[0], "choose_locker_target", {"playerId": players[1].id})
    assert room.state.phase == "turn"


def test_view_hides_draw_order_and_rejects_stale_or_out_of_turn_actions() -> None:
    game, room, players = started_room(3)
    serialized = json.dumps(game.view(room, players[0]), ensure_ascii=False)
    assert room.state.draw_pile[0] not in serialized
    assert "draw_pile" not in serialized

    with pytest.raises(GameRuleError, match="还没有轮到"):
        game.act(room, players[1], "draw", {})
    with pytest.raises(GameRuleError, match="旧状态"):
        game.act(room, players[0], "draw", {"revision": room.state.revision - 1})
    assert len(room.state.draw_pile) == 50


def test_manifest_disables_spectators_while_private_trait_offers_exist() -> None:
    manifest = json.loads(
        (room_path := __import__("pathlib").Path(__file__).resolve().parents[1] / "manifest.json").read_text(encoding="utf-8")
    )
    assert room_path.is_file()
    assert manifest["capabilities"]["spectators"] is False
    assert manifest["defaultOptions"]["allowSpectators"] is False
