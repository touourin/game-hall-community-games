from __future__ import annotations

import random
import importlib.util
from pathlib import Path
import sys

import pytest

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError


PLUGIN_DIRECTORY = Path(__file__).resolve().parents[1]
ENGINE_PATH = PLUGIN_DIRECTORY / "backend" / "engine.py"
ENGINE_SPEC = importlib.util.spec_from_file_location("plugin_uno_engine", ENGINE_PATH)
assert ENGINE_SPEC is not None and ENGINE_SPEC.loader is not None
ENGINE_MODULE = importlib.util.module_from_spec(ENGINE_SPEC)
sys.modules[ENGINE_SPEC.name] = ENGINE_MODULE
ENGINE_SPEC.loader.exec_module(ENGINE_MODULE)


def engine():
    return ENGINE_MODULE.UnoEngine(random.Random(20260902))


def started_room(player_count: int = 4):
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
        "PRISM",
        game.key,
        players[0].id,
        players,
        game.initial_state(),
        options={"firstPlayer": "host"},
    )
    game.start(room)
    return game, room, players


def card(game, *, color=None, kind=None, value=None):
    return next(
        item
        for item in game._new_deck()
        if (color is None or item.color == color)
        and (kind is None or item.kind == kind)
        and (value is None or item.value == value)
    )


def test_deck_has_classic_108_card_distribution() -> None:
    game = engine()
    deck = game._new_deck()

    assert len(deck) == 108
    assert len({item.id for item in deck}) == 108
    assert sum(item.kind == "wild" for item in deck) == 4
    assert sum(item.kind == "wild_draw_four" for item in deck) == 4
    for color_id in ("red", "yellow", "green", "blue"):
        colored = [item for item in deck if item.color == color_id]
        assert len(colored) == 25
        assert sum(item.kind == "number" and item.value == 0 for item in colored) == 1
        assert all(
            sum(item.kind == "number" and item.value == value for item in colored) == 2
            for value in range(1, 10)
        )
        assert sum(item.kind == "skip" for item in colored) == 2
        assert sum(item.kind == "reverse" for item in colored) == 2
        assert sum(item.kind == "draw_two" for item in colored) == 2


@pytest.mark.parametrize("player_count", (3, 4, 5, 6, 7, 8))
def test_start_deals_seven_and_hides_other_hands(player_count: int) -> None:
    game, room, players = started_room(player_count)
    state = room.state

    assert room.phase == "playing"
    assert state.current_player_id == players[0].id
    assert state.discard_pile[-1].kind == "number"
    assert all(len(state.hands[player.id]) == 7 for player in players)
    assert len(state.draw_pile) == 108 - player_count * 7 - 1

    view = game.view(room, players[0])
    assert len(view["hand"]) == 7
    assert view["cardCounts"] == {player.id: 7 for player in players}
    assert "hands" not in view
    assert "draw_pile" not in view


@pytest.mark.parametrize("player_count", (1, 9))
def test_rejects_unsupported_player_counts(player_count: int) -> None:
    with pytest.raises(GameRuleError, match="2–8"):
        started_room(player_count)


def test_skip_jumps_over_next_player() -> None:
    game, room, players = started_room(3)
    state = room.state
    skip = card(game, color="red", kind="skip")
    spare = card(game, color="blue", kind="number", value=8)
    state.hands[players[0].id] = [skip, spare]
    state.discard_pile = [card(game, color="red", kind="number", value=4)]
    state.active_color = "red"

    game.act(room, players[0], "play_card", {"cardId": skip.id, "callUno": True})

    assert state.current_player_id == players[2].id
    assert state.latest_event["type"] == "skip"
    assert state.latest_event["targetPlayerId"] == players[1].id


def test_reverse_is_a_skip_in_two_player_game() -> None:
    game, room, players = started_room(2)
    state = room.state
    reverse = card(game, color="blue", kind="reverse")
    spare = card(game, color="green", kind="number", value=6)
    state.hands[players[0].id] = [reverse, spare]
    state.discard_pile = [card(game, color="blue", kind="number", value=4)]
    state.active_color = "blue"

    game.act(room, players[0], "play_card", {"cardId": reverse.id, "callUno": True})

    assert state.direction == -1
    assert state.current_player_id == players[0].id
    assert state.latest_event["type"] == "reverse"


def test_draw_two_and_wild_draw_four_form_a_mixed_penalty_chain() -> None:
    game, room, players = started_room(3)
    state = room.state
    draw_two = card(game, color="yellow", kind="draw_two")
    wild_four = card(game, kind="wild_draw_four")
    state.hands[players[0].id] = [
        draw_two,
        card(game, color="blue", kind="number", value=8),
    ]
    state.hands[players[1].id] = [
        wild_four,
        card(game, color="green", kind="number", value=5),
    ]
    state.discard_pile = [card(game, color="yellow", kind="number", value=5)]
    state.active_color = "yellow"
    target_before = len(state.hands[players[2].id])

    game.act(
        room,
        players[0],
        "play_card",
        {"cardId": draw_two.id, "callUno": True},
    )

    assert state.pending_draw_total == 2
    assert state.pending_draw_target_id == players[1].id
    assert state.current_player_id == players[1].id
    assert state.latest_event["stackTotal"] == 2
    assert state.latest_event["stacked"] is False

    view = game.view(room, players[1])
    assert view["canTakePenalty"] is True
    assert view["canDraw"] is False
    assert view["playableCardIds"] == [wild_four.id]

    game.act(
        room,
        players[1],
        "play_card",
        {
            "cardId": wild_four.id,
            "chosenColor": "blue",
            "callUno": True,
        },
    )

    assert state.pending_draw_total == 6
    assert state.pending_draw_target_id == players[2].id
    assert state.current_player_id == players[2].id
    assert state.latest_event["count"] == 4
    assert state.latest_event["stackTotal"] == 6
    assert state.latest_event["stacked"] is True

    game.act(room, players[2], "take_penalty", {})

    assert len(state.hands[players[2].id]) == target_before + 6
    assert state.pending_draw_total == 0
    assert state.pending_draw_target_id is None
    assert state.current_player_id == players[0].id
    assert state.latest_event["type"] == "take_penalty"
    assert state.latest_event["count"] == 6
    assert state.latest_event["stackTotal"] == 6


def test_only_draw_cards_can_be_played_during_penalty_chain() -> None:
    game, room, players = started_room(3)
    state = room.state
    draw_two = card(game, color="red", kind="draw_two")
    matching_number = card(game, color="red", kind="number", value=7)
    state.hands[players[0].id] = [
        draw_two,
        card(game, color="blue", kind="number", value=2),
    ]
    state.hands[players[1].id] = [
        matching_number,
        card(game, color="green", kind="number", value=3),
    ]
    state.discard_pile = [card(game, color="red", kind="number", value=4)]
    state.active_color = "red"

    game.act(
        room,
        players[0],
        "play_card",
        {"cardId": draw_two.id, "callUno": True},
    )

    with pytest.raises(GameRuleError, match="累计摸牌尚未结算"):
        game.act(
            room,
            players[1],
            "play_card",
            {"cardId": matching_number.id, "callUno": True},
        )
    with pytest.raises(GameRuleError, match="接下累计惩罚"):
        game.act(room, players[1], "draw_card", {})


def test_stacked_wild_draw_four_still_checks_current_color() -> None:
    game, room, players = started_room(3)
    state = room.state
    draw_two = card(game, color="yellow", kind="draw_two")
    wild_four = card(game, kind="wild_draw_four")
    matching = card(game, color="yellow", kind="number", value=2)
    state.hands[players[0].id] = [
        draw_two,
        card(game, color="blue", kind="number", value=6),
    ]
    state.hands[players[1].id] = [wild_four, matching]
    state.discard_pile = [card(game, color="yellow", kind="number", value=5)]
    state.active_color = "yellow"

    game.act(
        room,
        players[0],
        "play_card",
        {"cardId": draw_two.id, "callUno": True},
    )

    with pytest.raises(GameRuleError, match=r"不能打出变色 \+4"):
        game.act(
            room,
            players[1],
            "play_card",
            {
                "cardId": wild_four.id,
                "chosenColor": "blue",
                "callUno": True,
            },
        )


def test_wild_draw_four_is_rejected_when_matching_color_is_held() -> None:
    game, room, players = started_room(3)
    state = room.state
    wild_four = card(game, kind="wild_draw_four")
    matching = card(game, color="green", kind="number", value=2)
    state.hands[players[0].id] = [wild_four, matching]
    state.discard_pile = [card(game, color="green", kind="number", value=9)]
    state.active_color = "green"

    with pytest.raises(GameRuleError, match=r"不能打出变色 \+4"):
        game.act(
            room,
            players[0],
            "play_card",
            {"cardId": wild_four.id, "chosenColor": "blue", "callUno": True},
        )

    assert [item.id for item in state.hands[players[0].id]] == [
        wild_four.id,
        matching.id,
    ]


def test_uncalled_uno_can_be_caught_before_next_main_action() -> None:
    game, room, players = started_room(3)
    state = room.state
    played = card(game, color="red", kind="number", value=7)
    last = card(game, color="blue", kind="number", value=2)
    state.hands[players[0].id] = [played, last]
    state.discard_pile = [card(game, color="red", kind="number", value=4)]
    state.active_color = "red"

    game.act(
        room,
        players[0],
        "play_card",
        {"cardId": played.id, "callUno": False},
    )
    assert state.uno_vulnerable_player_id == players[0].id
    assert state.current_player_id == players[1].id

    game.act(room, players[1], "catch_uno", {})

    assert len(state.hands[players[0].id]) == 3
    assert state.uno_vulnerable_player_id is None
    assert state.current_player_id == players[1].id
    assert state.latest_event["type"] == "catch_uno"


def test_drawn_playable_card_can_be_kept_to_end_turn() -> None:
    game, room, players = started_room(3)
    state = room.state
    drawn = card(game, color="blue", kind="number", value=5)
    state.discard_pile = [card(game, color="blue", kind="number", value=9)]
    state.active_color = "blue"
    state.draw_pile.append(drawn)

    game.act(room, players[0], "draw_card", {})

    assert state.stage == "after_draw"
    assert state.drawn_card_id == drawn.id
    assert state.current_player_id == players[0].id

    game.act(room, players[0], "keep_drawn", {})

    assert state.stage == "turn"
    assert state.drawn_card_id is None
    assert state.current_player_id == players[1].id


def test_playing_last_card_finishes_match() -> None:
    game, room, players = started_room(3)
    state = room.state
    winner = card(game, color="yellow", kind="number", value=6)
    state.hands[players[0].id] = [winner]
    state.discard_pile = [card(game, color="yellow", kind="number", value=3)]
    state.active_color = "yellow"

    game.act(
        room,
        players[0],
        "play_card",
        {"cardId": winner.id, "callUno": False},
    )

    assert room.phase == "finished"
    assert room.winner_player_ids == [players[0].id]
    assert game.player_result(room, players[0]) == ("光域胜者", "solo", True)
    assert "hands" not in game.record_state(room)


def test_last_card_must_be_a_number() -> None:
    game, room, players = started_room(3)
    state = room.state
    final_action = card(game, color="red", kind="skip")
    state.hands[players[0].id] = [final_action]
    state.discard_pile = [card(game, color="red", kind="number", value=3)]
    state.active_color = "red"

    view = game.view(room, players[0])
    assert view["playableCardIds"] == []
    assert view["canDraw"] is True

    with pytest.raises(GameRuleError, match="最后一张必须是数字牌"):
        game.act(
            room,
            players[0],
            "play_card",
            {"cardId": final_action.id, "callUno": False},
        )

    assert room.phase == "playing"
    assert state.hands[players[0].id] == [final_action]


@pytest.mark.parametrize("player_count", (3, 4, 5, 6, 7, 8))
def test_three_to_eight_player_penalty_chain_settles_and_numeric_card_wins(
    player_count: int,
) -> None:
    game, room, players = started_room(player_count)
    state = room.state
    draw_two = card(game, color="yellow", kind="draw_two")
    wild_four = card(game, kind="wild_draw_four")
    final_number = card(game, color="blue", kind="number", value=8)
    state.hands[players[0].id] = [draw_two, final_number]
    state.hands[players[1].id] = [
        wild_four,
        card(game, color="green", kind="number", value=5),
    ]
    state.discard_pile = [card(game, color="yellow", kind="number", value=4)]
    state.active_color = "yellow"

    game.act(
        room,
        players[0],
        "play_card",
        {"cardId": draw_two.id, "callUno": True},
    )
    game.act(
        room,
        players[1],
        "play_card",
        {
            "cardId": wild_four.id,
            "chosenColor": "blue",
            "callUno": True,
        },
    )
    game.act(room, players[2], "take_penalty", {})

    for index in range(3, player_count):
        blue_number = card(
            game,
            color="blue",
            kind="number",
            value=index % 10,
        )
        state.hands[players[index].id] = [
            blue_number,
            card(game, color="red", kind="number", value=(index + 1) % 10),
        ]
        assert state.current_player_id == players[index].id
        game.act(
            room,
            players[index],
            "play_card",
            {"cardId": blue_number.id, "callUno": True},
        )

    assert state.current_player_id == players[0].id
    game.act(
        room,
        players[0],
        "play_card",
        {"cardId": final_number.id, "callUno": False},
    )

    assert room.phase == "finished"
    assert room.winner_player_ids == [players[0].id]
    assert state.pending_draw_total == 0
