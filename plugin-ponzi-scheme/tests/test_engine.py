from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any

import pytest

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError
from backend.app.games.plugins import discover_game_plugins


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = Path(__file__).resolve().parents[1]


def engine():
    game = next(
        plugin.engine
        for plugin in discover_game_plugins(PLUGIN_ROOT)
        if plugin.engine.key == "plugin-ponzi-scheme"
    )
    game.rng = random.Random(20260902)
    return game


def started_room(
    player_count: int = 3,
    *,
    luxuries: bool = True,
    skip_first_trade: bool = True,
):
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
        "PONZ",
        game.key,
        players[0].id,
        players,
        game.initial_state(),
        options={
            "firstPlayer": "host",
            "luxuries": luxuries,
            "skipFirstTrade": skip_first_trade,
        },
    )
    game.start(room)
    return game, room, players


def test_catalog_contains_all_unique_fund_cards_and_components() -> None:
    catalog = json.loads((PLUGIN_DIR / "data" / "components.json").read_text(encoding="utf-8"))
    cards = catalog["fundCards"]

    assert len(cards) == 72
    assert [card["id"] for card in cards] == [f"F{amount:03d}" for amount in range(9, 81)]
    assert [card["amount"] for card in cards] == list(range(9, 81))
    assert {kind: sum(card["kind"] == kind for card in cards) for kind in ("starting", "regular", "bear")} == {
        "starting": 9,
        "regular": 45,
        "bear": 18,
    }
    assert sum(item["supply"] for item in catalog["industries"]) == 60
    assert [item["value"] for item in catalog["money"]["denominations"]] == [1, 5, 10, 20]


@pytest.mark.parametrize("player_count", (2, 6))
def test_rejects_unsupported_player_counts(player_count: int) -> None:
    with pytest.raises(GameRuleError, match="3–5"):
        started_room(player_count)


def test_setup_and_funding_rows_are_authoritative() -> None:
    game, room, players = started_room()
    state = room.state

    assert state.market == [f"F{amount:03d}" for amount in range(9, 18)]
    assert len(state.fund_deck) == 63
    assert state.current_player_id == players[0].id

    game.act(room, players[0], "fund", {"industryId": "transportation", "cardId": "F009"})
    assert state.ledgers[players[0].id].cash == 9
    assert state.ledgers[players[0].id].industries["transportation"] == 1
    assert state.ledgers[players[0].id].funds[0].due_in == 5
    assert len(state.market) == 9
    assert state.current_player_id == players[1].id

    second_row_card = game._market_rows(state)[1][0]
    with pytest.raises(GameRuleError, match="第 1 排"):
        game.act(
            room,
            players[1],
            "fund",
            {"industryId": "grain", "cardId": second_row_card},
        )

    state.ledgers[players[1].id].industries["grain"] = 3
    with pytest.raises(GameRuleError, match="第 4 枚"):
        game.act(
            room,
            players[1],
            "fund",
            {"industryId": "grain", "cardId": state.market[0]},
        )


def test_cash_is_private_but_funds_and_industries_are_public() -> None:
    game, room, players = started_room()
    game.act(room, players[0], "fund", {"industryId": "media", "cardId": "F009"})

    owner_view = game.view(room, players[0])
    other_view = game.view(room, players[1])
    owner = next(item for item in owner_view["ledgers"] if item["playerId"] == players[0].id)
    hidden = next(item for item in other_view["ledgers"] if item["playerId"] == players[0].id)

    assert owner["cash"] == 9
    assert owner["cashHidden"] is False
    assert hidden["cash"] is None
    assert hidden["cashHidden"] is True
    assert hidden["industries"]["media"] == 1
    assert hidden["funds"][0]["id"] == "F009"


def test_first_round_skips_trade_then_new_starter_prunes_market() -> None:
    game, room, players = started_room(skip_first_trade=True)

    for player in players:
        game.act(room, player, "pass_funding", {})

    assert room.state.stage == "market_prune"
    assert room.state.current_player_id == players[1].id
    game.act(room, players[1], "discard_market_card", {"cardId": "F009"})

    assert room.state.round_number == 2
    assert room.state.stage == "funding"
    assert room.state.current_player_id == players[1].id
    assert "F009" in room.state.removed_starting_cards


def test_luxury_purchase_replaces_trade_action() -> None:
    game, room, players = started_room(skip_first_trade=False)
    room.state.stage = "trade"
    room.state.current_player_id = players[0].id
    room.state.phase_cursor = 0
    room.state.ledgers[players[0].id].cash = 30

    game.act(room, players[0], "buy_luxury", {"luxuryId": "watch"})

    assert room.state.ledgers[players[0].id].cash == 0
    assert room.state.ledgers[players[0].id].luxuries == ["watch"]
    assert "watch" not in room.state.luxury_market
    assert room.state.current_player_id == players[1].id


def stage_trade(room: ArcadeRoom, players: list[ArcadePlayer]) -> None:
    state = room.state
    state.stage = "trade"
    state.phase_cursor = 0
    state.current_player_id = players[0].id
    state.ledgers[players[0].id].cash = 20
    state.ledgers[players[1].id].cash = 15
    state.ledgers[players[0].id].industries["grain"] = 1
    state.ledgers[players[1].id].industries["grain"] = 1


def holding(state: Any, card_id: str, due_in: int):
    state_module = sys.modules[state.__class__.__module__]
    return state_module.FundHolding(card_id, due_in)


def test_clandestine_offer_is_visible_only_to_participants_and_can_be_accepted() -> None:
    game, room, players = started_room(skip_first_trade=False)
    stage_trade(room, players)

    game.act(
        room,
        players[0],
        "make_offer",
        {"targetId": players[1].id, "industryId": "grain", "offer": 7},
    )

    assert game.view(room, players[0])["pendingTrade"]["offer"] == 7
    assert game.view(room, players[1])["pendingTrade"]["offer"] == 7
    assert game.view(room, players[2])["pendingTrade"]["offer"] is None
    assert game.record_state(room)["pendingTrade"]["offer"] is None
    assert "offer" not in room.state.events[-1].data

    game.act(room, players[1], "accept_offer", {})
    assert room.state.ledgers[players[0].id].cash == 13
    assert room.state.ledgers[players[1].id].cash == 22
    assert room.state.ledgers[players[0].id].industries["grain"] == 2
    assert room.state.ledgers[players[1].id].industries["grain"] == 0


def test_counter_offer_requires_equal_available_cash_and_reverses_industry() -> None:
    game, room, players = started_room(skip_first_trade=False)
    stage_trade(room, players)
    room.state.ledgers[players[1].id].cash = 6
    game.act(
        room,
        players[0],
        "make_offer",
        {"targetId": players[1].id, "industryId": "grain", "offer": 7},
    )
    assert game.view(room, players[1])["legalActions"]["canCounterOffer"] is False
    with pytest.raises(GameRuleError, match="现金不足"):
        game.act(room, players[1], "counter_offer", {})

    room.state.ledgers[players[1].id].cash = 9
    game.act(room, players[1], "counter_offer", {})
    assert room.state.ledgers[players[0].id].cash == 27
    assert room.state.ledgers[players[1].id].cash == 2
    assert room.state.ledgers[players[0].id].industries["grain"] == 0
    assert room.state.ledgers[players[1].id].industries["grain"] == 2


def test_market_crash_discards_largest_industry_and_advances_wheel_twice() -> None:
    game, room, players = started_room()
    state = room.state
    state.stage = "market_prune"
    state.current_player_id = players[0].id
    state.market = ["F009", "F018", "F019", "F020", "F021", "F022", "F063", "F064", "F065"]
    state.fund_deck = ["F023"]
    state.fund_discard = []
    for index, player in enumerate(players):
        state.ledgers[player.id].industries["transportation"] = index + 1
        state.ledgers[player.id].cash = 20
    state.ledgers[players[0].id].funds = [holding(state, "F009", 2)]

    game.act(room, players[0], "discard_market_card", {"cardId": "F009"})
    assert state.stage == "crash_discard"
    assert state.crash_occurred is True
    assert state.current_player_id == players[0].id

    for player in players:
        game.act(room, player, "discard_industry", {"industryId": "transportation"})

    assert state.round_number == 2
    assert state.stage == "funding"
    assert state.ledgers[players[0].id].cash == 12
    assert state.ledgers[players[0].id].funds[0].due_in == 5
    assert all(state.ledgers[player.id].industries["transportation"] == index for index, player in enumerate(players))
    assert len(state.market) == 9
    assert all(card_id not in state.fund_discard for card_id in ("F063", "F064", "F065"))


def test_bankruptcy_ends_immediately_and_scores_industries_plus_luxuries() -> None:
    game, room, players = started_room(luxuries=True)
    state = room.state
    state.ledgers[players[0].id].cash = 0
    state.ledgers[players[0].id].funds = [holding(state, "F009", 1)]
    state.ledgers[players[1].id].cash = 40
    state.ledgers[players[1].id].industries["grain"] = 2
    state.ledgers[players[1].id].luxuries = ["watch"]
    state.ledgers[players[2].id].cash = 40
    state.ledgers[players[2].id].industries["media"] = 1

    game._settle_interest(room, state, 1)

    assert room.phase == "finished"
    assert room.winner_player_ids == [players[1].id]
    assert state.ledgers[players[0].id].bankrupt is True
    assert state.ledgers[players[1].id].final_score == 4
    assert state.ledgers[players[2].id].final_score == 1
    finished_view = game.view(room, players[2])
    assert all(item["cashHidden"] is False for item in finished_view["ledgers"])
