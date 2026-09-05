from __future__ import annotations

import importlib
import json
from collections import Counter
from pathlib import Path

import pytest

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError
from backend.app.games.plugins import discover_game_plugins


PLUGIN_ROOT = Path(__file__).resolve().parents[2]


class IdentityRng:
    def shuffle(self, values):
        return None


def load_engine():
    game = next(
        plugin.engine
        for plugin in discover_game_plugins(PLUGIN_ROOT)
        if plugin.engine.key == "plugin-bullhead-king"
    )
    game.rng = IdentityRng()
    return game


def make_room(player_count: int = 3):
    game = load_engine()
    players = [
        ArcadePlayer(
            f"p{index + 1}", f"a{index + 1}", f"玩家{index + 1}",
            "test-token", index,
        )
        for index in range(player_count)
    ]
    room = ArcadeRoom("BULL", game.key, players[0].id, players, game.initial_state())
    game.start(room)
    return game, room, players


def engine_symbols(game):
    module = importlib.import_module(type(game).__module__)
    return module.NumberCard, module.bullhead_value


def configure_turn(game, room, hands, rows, *, turn_number=1, scores=None):
    Card, _ = engine_symbols(game)
    state = room.state
    state.hands = {
        player_id: [Card(number) for number in numbers]
        for player_id, numbers in hands.items()
    }
    state.rows = [[Card(number) for number in row] for row in rows]
    state.captured = {player_id: [] for player_id in state.player_ids}
    state.round_penalties = {player_id: 0 for player_id in state.player_ids}
    state.scores = scores or {player_id: 0 for player_id in state.player_ids}
    state.stage = "select"
    state.turn_number = turn_number
    state.selections = {}
    state.revealed = []
    state.resolution_queue = []
    state.round_summary = None


def select(game, room, player, number):
    game.act(room, player, "select_card", {
        "cardId": f"card-{number:03d}",
        "turnNumber": room.state.turn_number,
    })


def assert_table_invariants(room) -> None:
    state = room.state
    assert len(state.rows) == 4
    assert all(1 <= len(row) <= 5 for row in state.rows)
    assert all(
        [card.number for card in row] == sorted(card.number for card in row)
        for row in state.rows
    )
    assert [row[0].number for row in state.rows] == sorted(
        row[0].number for row in state.rows
    )
    assert all(
        state.round_penalties[player_id]
        == sum(card.bullheads for card in state.captured[player_id])
        for player_id in state.player_ids
    )


def play_automatic_game(game, room, players) -> dict[str, int]:
    players_by_id = {player.id: player for player in players}
    animation_counts = Counter()
    action_count = 0
    while room.phase == "playing" and action_count < 12_000:
        state = room.state
        assert_table_invariants(room)
        if state.stage == "select":
            for player_id in list(state.player_ids):
                if state.stage != "select" or player_id in state.forfeited_ids:
                    break
                hand = state.hands[player_id]
                offset = (state.turn_number + state.player_ids.index(player_id)) % len(hand)
                select(
                    game, room, players_by_id[player_id], hand[offset].number,
                )
                action_count += 1
        if state.animation and state.animation["complete"]:
            assert [
                play["card"]["number"] for play in state.animation["revealed"]
            ] == sorted(
                play["card"]["number"] for play in state.animation["revealed"]
            )
            for step in state.animation["steps"]:
                animation_counts[step["type"]] += 1
                assert step["penalty"] == sum(
                    card["bullheads"] for card in step["takenCards"]
                )
        if room.phase == "playing" and state.stage == "round_summary":
            game.act(
                room,
                players[0],
                "next_round",
                {"roundNumber": state.round_number},
            )
            action_count += 1
        elif room.phase == "playing":
            assert state.stage == "select"

    assert action_count < 12_000, "automatic game did not reach a terminal state"
    return dict(animation_counts)


def test_card_penalties_cover_the_complete_104_card_deck() -> None:
    game = load_engine()
    _, value = engine_symbols(game)

    distribution = Counter(value(number) for number in range(1, 105))

    assert distribution == Counter({1: 76, 2: 9, 3: 10, 5: 8, 7: 1})
    assert sum(points * count for points, count in distribution.items()) == 171
    assert value(5) == 2
    assert value(10) == 3
    assert value(11) == 5
    assert value(55) == 7
    assert value(104) == 1
    with pytest.raises(ValueError):
        value(0)


@pytest.mark.parametrize("player_count", [2, 3, 6, 10])
def test_start_deals_ten_unique_cards_each_and_four_row_heads(player_count: int) -> None:
    _, room, players = make_room(player_count)
    state = room.state
    dealt = [
        card.number
        for player in players
        for card in state.hands[player.id]
    ]
    row_heads = [row[0].number for row in state.rows]

    assert room.phase == "playing"
    assert state.stage == "select"
    assert state.round_number == room.round_number == 1
    assert all(len(state.hands[player.id]) == 10 for player in players)
    assert len(state.rows) == 4
    assert all(len(row) == 1 for row in state.rows)
    assert row_heads == sorted(row_heads)
    assert len(set(dealt + row_heads)) == player_count * 10 + 4


@pytest.mark.parametrize("player_count", range(4, 9))
def test_four_to_eight_players_complete_full_games(player_count: int) -> None:
    game, room, players = make_room(player_count)

    animation_counts = play_automatic_game(game, room, players)

    assert room.phase == "finished"
    assert room.state.stage == "finished"
    assert room.state.round_number >= 1
    active_scores = {
        player.id: room.state.scores[player.id]
        for player in players
    }
    lowest = min(active_scores.values())
    assert room.winner_player_ids == [
        player.id for player in players
        if active_scores[player.id] == lowest
    ]
    assert max(active_scores.values()) >= 66
    assert animation_counts["place"] > 0
    assert animation_counts["take_low"] > 0


def test_locked_card_is_private_until_everyone_commits() -> None:
    game, room, players = make_room(3)
    select(game, room, players[0], 1)

    owner_view = game.view(room, players[0])
    other_view = game.view(room, players[1])

    assert owner_view["committedCard"]["number"] == 1
    assert owner_view["sceneId"] == "turn.waiting"
    assert other_view["committedCard"] is None
    assert other_view["committedPlayerIds"] == [players[0].id]
    assert [card["number"] for card in other_view["hand"]] == list(range(11, 21))
    assert "selections" not in json.dumps(other_view)
    with pytest.raises(GameRuleError, match="已经锁定"):
        select(game, room, players[0], 2)


def test_revealed_cards_resolve_in_ascending_order_by_row_head_range() -> None:
    game, room, players = make_room(2)
    configure_turn(
        game, room,
        {players[0].id: [22], players[1].id: [35]},
        [[10], [20], [30], [40]],
    )

    select(game, room, players[1], 35)
    select(game, room, players[0], 22)

    assert [[card.number for card in row] for row in room.state.rows] == [
        [10], [20, 22], [30, 35], [40],
    ]
    assert [play.card.number for play in room.state.revealed] == [22, 35]
    assert [step["rowIndex"] for step in room.state.animation["steps"]] == [1, 2]
    assert room.state.stage == "round_summary"


def test_sixth_card_collects_the_existing_five_and_starts_a_new_row() -> None:
    game, room, players = make_room(2)
    configure_turn(
        game, room,
        {players[0].id: [6], players[1].id: [50]},
        [[1, 2, 3, 4, 5], [20], [30], [40]],
    )

    select(game, room, players[0], 6)
    select(game, room, players[1], 50)

    assert [card.number for card in room.state.rows[0]] == [6]
    assert [card.number for card in room.state.captured[players[0].id]] == [1, 2, 3, 4, 5]
    assert room.state.round_penalties[players[0].id] == 6
    take_step = room.state.animation["steps"][0]
    assert take_step["type"] == "take_full"
    assert take_step["penalty"] == 6
    assert [card["number"] for card in take_step["takenCards"]] == [1, 2, 3, 4, 5]


def test_low_card_automatically_takes_first_sorted_row_and_resolution_continues() -> None:
    game, room, players = make_room(2)
    configure_turn(
        game, room,
        {players[0].id: [4], players[1].id: [98]},
        [[15], [77], [24, 66], [80, 104]],
    )
    select(game, room, players[0], 4)
    select(game, room, players[1], 98)

    assert [[card.number for card in row] for row in room.state.rows] == [
        [4], [24, 66], [77], [98],
    ]
    assert [card.number for card in room.state.captured[players[0].id]] == [15]
    assert [card.number for card in room.state.captured[players[1].id]] == [80, 104]
    assert room.state.scores[players[0].id] == 2
    assert room.state.scores[players[1].id] == 4
    assert [step["type"] for step in room.state.animation["steps"]] == [
        "take_low", "take_low",
    ]
    assert room.state.stage == "round_summary"
    view = game.view(room, players[0])
    assert view["canChooseRow"] is False
    assert "take_row" not in view["actions"]
    with pytest.raises(GameRuleError, match="系统自动判定"):
        game.act(room, players[0], "take_row", {"rowIndex": 1, "turnNumber": 1})


def test_card_inside_a_row_range_takes_that_row_and_becomes_its_head() -> None:
    game, room, players = make_room(2)
    configure_turn(
        game, room,
        {players[0].id: [50], players[1].id: [90]},
        [[15], [77], [24, 66], [80]],
    )

    select(game, room, players[0], 50)
    select(game, room, players[1], 90)

    assert [[card.number for card in row] for row in room.state.rows] == [
        [15], [50], [77], [80, 90],
    ]
    assert [card.number for card in room.state.captured[players[0].id]] == [24, 66]
    assert room.state.animation["steps"][0]["type"] == "take_low"
    assert room.state.animation["steps"][0]["rowIndex"] == 1


def test_stale_turn_and_invalid_card_are_rejected() -> None:
    game, room, players = make_room(2)
    with pytest.raises(GameRuleError, match="桌面已更新"):
        game.act(room, players[0], "select_card", {
            "cardId": "card-001", "turnNumber": 99,
        })
    with pytest.raises(GameRuleError, match="不在你的手牌"):
        game.act(room, players[0], "select_card", {
            "cardId": "card-104", "turnNumber": 1,
        })


def test_round_summary_keeps_scores_and_deals_a_fresh_round() -> None:
    game, room, players = make_room(2)
    configure_turn(
        game, room,
        {players[0].id: [22], players[1].id: [35]},
        [[10], [20], [30], [40]],
        turn_number=10,
        scores={players[0].id: 4, players[1].id: 9},
    )
    select(game, room, players[0], 22)
    select(game, room, players[1], 35)

    assert room.state.stage == "round_summary"
    assert room.state.round_summary["totals"] == {
        players[0].id: 4, players[1].id: 9,
    }
    game.act(room, players[1], "next_round", {"roundNumber": 1})

    assert room.state.stage == "select"
    assert room.state.round_number == room.round_number == 2
    assert room.state.scores == {players[0].id: 4, players[1].id: 9}
    assert all(len(room.state.hands[player.id]) == 10 for player in players)
    assert all(value == 0 for value in room.state.round_penalties.values())


def test_sixty_six_is_checked_after_the_round_and_lowest_score_wins() -> None:
    game, room, players = make_room(2)
    configure_turn(
        game, room,
        {players[0].id: [1], players[1].id: [100]},
        [[55], [60], [70], [80]],
        turn_number=10,
        scores={players[0].id: 65, players[1].id: 1},
    )
    select(game, room, players[0], 1)
    select(game, room, players[1], 100)

    assert room.phase == "finished"
    assert room.state.scores[players[0].id] == 72
    assert room.winner_player_ids == [players[1].id]
    assert "66" in room.win_reason


def test_equal_lowest_scores_share_the_win() -> None:
    game, room, players = make_room(3)
    room.state.scores = {
        players[0].id: 14,
        players[1].id: 14,
        players[2].id: 68,
    }
    room.state.round_summary = {"thresholdReached": True}

    game._finish_game(room, room.state)

    assert room.winner_player_ids == [players[0].id, players[1].id]
    assert room.state.rankings[:2] == [players[0].id, players[1].id]
    assert game.player_result(room, players[0]) == (
        "第 1 名 · 14 牛头分", "player", True,
    )
    assert game.player_result(room, players[1]) == (
        "第 1 名 · 14 牛头分", "player", True,
    )
    assert game.view(room, players[0])["players"][1]["rank"] == 1
    assert game.view(room, players[0])["players"][2]["rank"] == 3


def test_forfeit_does_not_interrupt_automatic_forced_collection() -> None:
    game, room, players = make_room(3)
    configure_turn(
        game, room,
        {
            players[0].id: [5],
            players[1].id: [50],
            players[2].id: [60],
        },
        [[10], [11], [20], [55]],
    )
    select(game, room, players[0], 5)
    assert game.manual_forfeit(room, players[1]) is True
    select(game, room, players[2], 60)

    assert players[1].id in room.state.forfeited_ids
    assert [card.number for card in room.state.rows[0]] == [5]
    assert room.state.round_penalties[players[0].id] == 3
    assert room.state.stage == "round_summary"
