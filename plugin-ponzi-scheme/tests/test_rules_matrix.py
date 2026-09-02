from __future__ import annotations

import random
import sys
from typing import Any

import pytest

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError
from backend.app.games.plugins import discover_game_plugins


def started_room(
    player_count: int = 3,
    *,
    luxuries: bool = True,
    skip_first_trade: bool = True,
) -> tuple[Any, ArcadeRoom, list[ArcadePlayer]]:
    plugin_root = __import__("pathlib").Path(__file__).resolve().parents[2]
    game = next(
        plugin.engine
        for plugin in discover_game_plugins(plugin_root)
        if plugin.engine.key == "plugin-ponzi-scheme"
    )
    game.rng = random.Random(41739 + player_count)
    players = [
        ArcadePlayer(
            f"p{index + 1}",
            f"account-{index + 1}",
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


def holding(state: Any, card_id: str, due_in: int) -> Any:
    state_module = sys.modules[state.__class__.__module__]
    return state_module.FundHolding(card_id, due_in)


def stage_trade(room: ArcadeRoom, players: list[ArcadePlayer]) -> None:
    state = room.state
    state.stage = "trade"
    state.phase_cursor = 0
    state.current_player_id = players[0].id
    state.ledgers[players[0].id].cash = 20
    state.ledgers[players[1].id].cash = 20
    state.ledgers[players[0].id].industries["grain"] = 1
    state.ledgers[players[1].id].industries["grain"] = 1


def assert_component_conservation(state: Any) -> None:
    fund_ids = (
        list(state.market)
        + list(state.fund_deck)
        + list(state.fund_discard)
        + list(state.removed_starting_cards)
        + [holding.card_id for ledger in state.ledgers.values() for holding in ledger.funds]
    )
    assert len(fund_ids) == 72
    assert len(set(fund_ids)) == 72
    assert set(fund_ids) == {f"F{amount:03d}" for amount in range(9, 81)}
    for industry_id, remaining in state.industry_supply.items():
        owned = sum(ledger.industries[industry_id] for ledger in state.ledgers.values())
        assert remaining + owned == 15
    assert len(state.luxury_market) + sum(
        len(ledger.luxuries) for ledger in state.ledgers.values()
    ) == 4
    assert all(ledger.cash >= 0 for ledger in state.ledgers.values())


@pytest.mark.parametrize("player_count", (3, 4, 5))
def test_three_to_five_player_games_complete_with_all_components_conserved(
    player_count: int,
) -> None:
    game, room, players = started_room(player_count)
    by_id = {player.id: player for player in players}

    for _ in range(800):
        assert_component_conservation(room.state)
        if room.phase == "finished":
            break
        state = room.state
        player = by_id[state.current_player_id]
        legal = game.view(room, player)["legalActions"]
        if state.stage == "funding":
            option = next(
                (item for item in legal["fundingOptions"] if item["cardIds"]),
                None,
            )
            if option:
                game.act(
                    room,
                    player,
                    "fund",
                    {
                        "industryId": option["industryId"],
                        "cardId": option["cardIds"][0],
                    },
                )
            else:
                game.act(room, player, "pass_funding", {})
        elif state.stage == "trade":
            game.act(room, player, "pass_trade", {})
        elif state.stage == "market_prune":
            game.act(
                room,
                player,
                "discard_market_card",
                {"cardId": legal["discardMarketCardIds"][0]},
            )
        elif state.stage == "crash_discard":
            game.act(
                room,
                player,
                "discard_industry",
                {"industryId": legal["discardIndustryIds"][0]},
            )
        else:
            raise AssertionError(f"unexpected blocking stage: {state.stage}")
    else:
        pytest.fail(f"{player_count}-player game did not reach bankruptcy")

    assert room.phase == "finished"
    assert room.state.bankrupt_ids
    assert_component_conservation(room.state)
    assert set(room.winner_player_ids).isdisjoint(room.state.bankrupt_ids)
    assert any(event.type == "wheel" for event in room.state.events)


def test_exact_cash_payment_survives_at_zero_and_resets_due_marker() -> None:
    game, room, players = started_room()
    state = room.state
    state.ledgers[players[0].id].cash = 8
    state.ledgers[players[0].id].funds = [holding(state, "F009", 1)]

    game._settle_interest(room, state, 1)

    ledger = state.ledgers[players[0].id]
    assert room.phase == "playing"
    assert ledger.cash == 0
    assert ledger.bankrupt is False
    assert ledger.funds[0].due_in == 5
    assert state.round_number == 2


def test_all_due_cards_are_summed_before_exact_cash_is_checked() -> None:
    game, room, players = started_room()
    state = room.state
    ledger = state.ledgers[players[0].id]
    ledger.cash = 17
    ledger.funds = [holding(state, "F009", 1), holding(state, "F010", 1)]

    game._settle_interest(room, state, 1)

    assert room.phase == "playing"
    assert ledger.cash == 0
    assert [item.due_in for item in ledger.funds] == [5, 5]


def test_crash_double_step_pays_crossed_card_once_and_leaves_later_card_due_next() -> None:
    game, room, players = started_room()
    state = room.state
    ledger = state.ledgers[players[0].id]
    ledger.cash = 30
    ledger.funds = [holding(state, "F009", 1), holding(state, "F017", 3)]

    game._settle_interest(room, state, 2)

    assert room.phase == "playing"
    assert ledger.cash == 22
    assert [item.due_in for item in ledger.funds] == [5, 1]
    assert state.wheel_position == 2


def test_multiple_players_can_fail_the_same_settlement() -> None:
    game, room, players = started_room()
    state = room.state
    state.ledgers[players[0].id].cash = 7
    state.ledgers[players[0].id].funds = [holding(state, "F009", 1)]
    state.ledgers[players[1].id].cash = 8
    state.ledgers[players[1].id].funds = [holding(state, "F010", 1)]
    state.ledgers[players[2].id].cash = 0
    state.ledgers[players[2].id].industries["media"] = 1

    game._settle_interest(room, state, 1)

    assert room.phase == "finished"
    assert state.bankrupt_ids == [players[0].id, players[1].id]
    assert room.winner_player_ids == [players[2].id]
    assert state.ledgers[players[2].id].final_score == 1


def test_all_players_bankrupt_simultaneously_has_no_winner() -> None:
    game, room, players = started_room(5)
    state = room.state
    for player in players:
        state.ledgers[player.id].cash = 0
        state.ledgers[player.id].funds = [holding(state, "F009", 1)]

    game._settle_interest(room, state, 1)

    assert room.phase == "finished"
    assert state.bankrupt_ids == [player.id for player in players]
    assert room.winner_player_ids == []
    assert room.win_reason == "所有玩家同时破产，本局无人获胜"


def test_luxury_scoring_breakdown_and_cash_reveal_are_auditable() -> None:
    game, room, players = started_room(luxuries=True)
    state = room.state
    first = state.ledgers[players[0].id]
    first.cash = 99
    first.industries.update(transportation=3, grain=2, media=1)
    first.luxuries = ["watch", "yacht"]
    second = state.ledgers[players[1].id]
    second.industries.update(transportation=3, grain=2, media=1)

    game._finish(room, state)
    view = game.view(room, players[2])
    first_row = next(
        row for row in view["settlement"]["rows"] if row["playerId"] == players[0].id
    )

    assert room.winner_player_ids == [players[0].id]
    assert first_row == {
        "playerId": players[0].id,
        "rank": 1,
        "winner": True,
        "bankrupt": False,
        "industryScore": 10,
        "luxuryScore": 4,
        "wealthScore": None,
        "highestFund": 0,
        "total": 14,
    }
    assert view["ruleset"] == "bright-eye-standard"
    assert view["settlement"]["mode"] == "industry_and_luxury"
    assert all(not ledger["cashHidden"] for ledger in view["ledgers"])


def test_equal_score_uses_highest_fund_card_as_tiebreaker() -> None:
    game, room, players = started_room()
    state = room.state
    for player in players[:2]:
        state.ledgers[player.id].industries["grain"] = 2
    state.ledgers[players[0].id].funds = [holding(state, "F009", 5)]
    state.ledgers[players[1].id].funds = [holding(state, "F017", 3)]

    game._finish(room, state)

    assert room.winner_player_ids == [players[1].id]
    assert "最高资金牌 17 决胜" in room.win_reason


def test_equal_score_and_highest_fund_produces_co_winners_and_shared_rank() -> None:
    game, room, players = started_room()
    state = room.state
    state.ledgers[players[0].id].industries["grain"] = 1
    state.ledgers[players[1].id].industries["media"] = 1

    game._finish(room, state)
    rows = {
        row["playerId"]: row for row in game.view(room, players[0])["settlement"]["rows"]
    }

    assert room.winner_player_ids == [players[0].id, players[1].id]
    assert rows[players[0].id]["rank"] == 1
    assert rows[players[1].id]["rank"] == 1
    assert rows[players[2].id]["rank"] == 3


@pytest.mark.parametrize(
    ("cash", "points"),
    ((0, 0), (29, 0), (30, 1), (55, 1), (56, 2), (77, 2), (78, 3), (95, 3), (96, 4)),
)
def test_compatibility_wealth_threshold_boundaries(cash: int, points: int) -> None:
    game, _, _ = started_room(luxuries=False)
    assert game._wealth_points(cash) == points


def test_compatibility_mode_scores_cash_instead_of_owned_luxury() -> None:
    game, room, players = started_room(luxuries=False)
    ledger = room.state.ledgers[players[0].id]
    ledger.cash = 56
    ledger.industries["grain"] = 1
    ledger.luxuries = ["club"]

    game._finish(room, room.state)
    row = game.view(room, players[0])["settlement"]["rows"][0]

    assert row["industryScore"] == 1
    assert row["luxuryScore"] is None
    assert row["wealthScore"] == 2
    assert row["total"] == 3


@pytest.mark.parametrize("response", ("accept_offer", "counter_offer"))
def test_zero_value_offer_moves_exactly_one_industry_without_moving_cash(
    response: str,
) -> None:
    game, room, players = started_room(skip_first_trade=False)
    stage_trade(room, players)
    before = {
        player.id: room.state.ledgers[player.id].cash for player in players[:2]
    }

    game.act(
        room,
        players[0],
        "make_offer",
        {"targetId": players[1].id, "industryId": "grain", "offer": 0},
    )
    game.act(room, players[1], response, {})

    assert room.state.ledgers[players[0].id].cash == before[players[0].id]
    assert room.state.ledgers[players[1].id].cash == before[players[1].id]
    if response == "accept_offer":
        assert room.state.ledgers[players[0].id].industries["grain"] == 2
        assert room.state.ledgers[players[1].id].industries["grain"] == 0
    else:
        assert room.state.ledgers[players[0].id].industries["grain"] == 0
        assert room.state.ledgers[players[1].id].industries["grain"] == 2


@pytest.mark.parametrize("bad_offer", (-1, True, 1.5, "5", None))
def test_invalid_offer_types_and_negative_values_are_rejected(bad_offer: Any) -> None:
    game, room, players = started_room(skip_first_trade=False)
    stage_trade(room, players)

    with pytest.raises(GameRuleError, match="非负整数"):
        game.act(
            room,
            players[0],
            "make_offer",
            {"targetId": players[1].id, "industryId": "grain", "offer": bad_offer},
        )


def test_crash_skips_empty_ledger_and_allows_choice_between_tied_largest_industries() -> None:
    game, room, players = started_room()
    state = room.state
    state.market = ["F063", "F064", "F065", "F009", "F010", "F011", "F012", "F013", "F014"]
    state.fund_deck = [f"F{amount:03d}" for amount in range(18, 63)] + [f"F{amount:03d}" for amount in range(66, 81)]
    state.ledgers[players[1].id].industries.update(grain=2, media=2)
    state.industry_supply["grain"] -= 2
    state.industry_supply["media"] -= 2
    state.ledgers[players[2].id].industries["real_estate"] = 1
    state.industry_supply["real_estate"] -= 1

    game._begin_crash(room, state)

    assert state.current_player_id == players[1].id
    assert game.view(room, players[1])["legalActions"]["discardIndustryIds"] == ["grain", "media"]
    assert any(event.type == "crash_skip" and event.data["playerId"] == players[0].id for event in state.events)
    game.act(room, players[1], "discard_industry", {"industryId": "media"})
    game.act(room, players[2], "discard_industry", {"industryId": "real_estate"})
    assert state.round_number == 2
    assert state.wheel_position == 2


@pytest.mark.parametrize("player_count", (3, 4, 5))
def test_crash_threshold_matches_player_count(player_count: int) -> None:
    game, room, _ = started_room(player_count)
    state = room.state
    state.market = [f"F{amount:03d}" for amount in range(63, 63 + player_count)]

    assert game._bear_count(state) == player_count
    game._begin_crash(room, state)
    assert any(event.type == "market_crash" for event in state.events)
    assert state.wheel_position == 2


def test_restock_recycles_discard_pile_without_duplication() -> None:
    game, room, _ = started_room()
    state = room.state
    state.market = [f"F{amount:03d}" for amount in range(9, 17)]
    state.fund_deck = []
    state.fund_discard = ["F018", "F019"]

    game._restock_market(state)

    assert len(state.market) == 9
    assert len(state.fund_deck) == 1
    assert state.fund_discard == []
    assert set(state.market[-2:] + state.fund_deck).issuperset({"F018", "F019"})


def test_event_history_is_bounded_without_reusing_sequence_numbers() -> None:
    game, room, _ = started_room()
    state = room.state

    for index in range(100):
        game._emit(state, "audit", f"event {index}")

    assert len(state.events) == 80
    assert state.events[0].seq == 22
    assert state.events[-1].seq == 101
    assert state.event_sequence == 101


def test_wrong_player_and_wrong_stage_cannot_mutate_state() -> None:
    game, room, players = started_room()
    original_market = list(room.state.market)

    with pytest.raises(GameRuleError, match="还没有轮到你"):
        game.act(room, players[1], "fund", {"industryId": "grain", "cardId": "F009"})
    with pytest.raises(GameRuleError, match="还没有轮到你"):
        game.act(room, players[0], "pass_trade", {})

    assert room.state.market == original_market
    assert all(ledger.cash == 0 for ledger in room.state.ledgers.values())


def test_resign_or_disconnect_timeout_immediately_loses_and_scores_survivors() -> None:
    game, room, players = started_room()
    room.state.ledgers[players[1].id].industries["grain"] = 2

    assert game.disconnect_timeout(room, players[0]) is True

    assert room.phase == "finished"
    assert room.state.ledgers[players[0].id].forfeited is True
    assert room.state.bankrupt_ids == [players[0].id]
    assert room.winner_player_ids == [players[1].id]
    assert game.disconnect_timeout(room, players[0]) is False
