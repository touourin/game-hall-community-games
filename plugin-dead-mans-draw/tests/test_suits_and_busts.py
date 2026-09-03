from __future__ import annotations

import pytest

from backend.app.games.plugin_api import GameRuleError

from dead_mans_draw_test_helpers import (
    choose_option,
    draw_exact,
    pending_choice,
    put_bank,
    put_discard,
    remove_card,
    started_room,
)


def test_anchor_bust_banks_only_the_prefix_before_anchor() -> None:
    game, room, players = started_room(2)
    current = players[0]
    draw_exact(game, room, current, "loot-mermaid-5")
    draw_exact(game, room, current, "loot-anchor-3")
    draw_exact(game, room, current, "loot-mermaid-6")

    assert room.state.turn.actor_id == players[1].id
    assert room.state.players[current.id].bank["mermaid"] == ["loot-mermaid-5"]
    assert "loot-anchor-3" in room.state.discard_pile
    assert "loot-mermaid-6" in room.state.discard_pile
    assert any(event.type == "bust_detected" for event in room.state.events)
    assert any(event.type == "protected_split" for event in room.state.events)


def test_hook_must_take_a_bank_top_card_and_can_force_a_bust() -> None:
    game, room, players = started_room(2)
    current = players[0]
    put_bank(game, room, current.id, "loot-mermaid-9")
    draw_exact(game, room, current, "loot-mermaid-5")
    draw_exact(game, room, current, "loot-hook-4")

    choice = pending_choice(room)
    assert choice.kind == "hook-stack"
    assert next(item for item in choice.options if item.card_id == "loot-mermaid-9").causes_immediate_bust
    choose_option(game, room, current, card_id="loot-mermaid-9")

    assert room.state.turn.actor_id == players[1].id
    assert not room.state.players[current.id].bank["mermaid"]
    assert {"loot-mermaid-5", "loot-hook-4", "loot-mermaid-9"}.issubset(room.state.discard_pile)


def test_cannon_discards_only_the_selected_opponent_top_card() -> None:
    game, room, players = started_room(2)
    put_bank(game, room, players[1].id, "loot-mermaid-9", "loot-mermaid-6")
    draw_exact(game, room, players[0], "loot-cannon-4")
    choice = pending_choice(room)
    assert choice.kind == "cannon-target"
    choose_option(game, room, players[0], player_id=players[1].id, suit="mermaid")

    assert room.state.players[players[1].id].bank["mermaid"] == ["loot-mermaid-6"]
    assert "loot-mermaid-9" in room.state.discard_pile


def test_key_chest_collects_an_equal_number_of_discard_rewards_without_abilities() -> None:
    game, room, players = started_room(2)
    current = players[0]
    initial_discard_count = len(room.state.discard_pile)
    draw_exact(game, room, current, "loot-key-3")
    draw_exact(game, room, current, "loot-chest-3")
    game.act(room, current, "collect", {})

    board = room.state.players[current.id]
    assert sum(len(pile) for pile in board.bank.values()) == 4
    assert board.bank["key"] == ["loot-key-3"]
    assert board.bank["chest"] == ["loot-chest-3"]
    assert len(room.state.discard_pile) == initial_discard_count - 2
    bonus = next(event for event in room.state.events if event.type == "key_chest_bonus")
    assert bonus.data["count"] == 2


def test_map_reveals_exactly_three_discard_cards_and_selected_card_enters_lane() -> None:
    game, room, players = started_room(2)
    current = players[0]
    keep = {"loot-mermaid-4", "loot-anchor-2", "loot-key-2"}
    for identifier in list(room.state.discard_pile):
        if identifier not in keep:
            put_bank(game, room, players[1].id, identifier)
    draw_exact(game, room, current, "loot-map-3")

    choice = pending_choice(room)
    assert choice.kind == "map-card"
    assert len(choice.options) == 3
    assert set(room.state.turn.map_reveal_card_ids) == keep
    choose_option(game, room, current, card_id="loot-mermaid-4")

    assert [entry.card_id for entry in room.state.turn.play_area] == ["loot-map-3", "loot-mermaid-4"]
    assert not room.state.turn.map_reveal_card_ids
    assert {"loot-anchor-2", "loot-key-2"}.issubset(room.state.discard_pile)


def test_oracle_publicly_peeks_without_changing_next_draw() -> None:
    game, room, players = started_room(2)
    current = players[0]
    remove_card(room.state, "loot-oracle-3")
    remove_card(room.state, "loot-mermaid-6")
    room.state.draw_pile[:0] = ["loot-oracle-3", "loot-mermaid-6"]
    game.assert_invariants(room.state)

    game.act(room, current, "draw", {})
    view = game.view(room, players[1])
    assert view["turn"]["oraclePeekCardIds"] == ["loot-mermaid-6"]
    assert room.state.draw_pile[0] == "loot-mermaid-6"

    game.act(room, current, "draw", {})
    assert room.state.turn.oracle_peek_card_ids == []
    assert [entry.card_id for entry in room.state.turn.play_area][-1] == "loot-mermaid-6"


def test_sword_steals_missing_suit_and_respects_actor_bank_restriction() -> None:
    game, room, players = started_room(2)
    put_bank(game, room, players[1].id, "loot-mermaid-9")
    draw_exact(game, room, players[0], "loot-sword-4")
    choose_option(game, room, players[0], player_id=players[1].id, suit="mermaid")
    assert not room.state.players[players[1].id].bank["mermaid"]
    assert [entry.card_id for entry in room.state.turn.play_area] == ["loot-sword-4", "loot-mermaid-9"]

    game, room, players = started_room(2, seed=77)
    put_bank(game, room, players[0].id, "loot-mermaid-8")
    put_bank(game, room, players[1].id, "loot-mermaid-9")
    draw_exact(game, room, players[0], "loot-sword-4")
    assert room.state.turn.pending_choice is None
    assert room.state.players[players[1].id].bank["mermaid"] == ["loot-mermaid-9"]


def test_kraken_debt_is_paid_by_hook_and_its_successful_child_entry() -> None:
    game, room, players = started_room(2)
    current = players[0]
    put_bank(game, room, current.id, "loot-mermaid-9")
    draw_exact(game, room, current, "loot-kraken-3")
    assert room.state.turn.kraken_debt == 2
    draw_exact(game, room, current, "loot-hook-4")
    assert room.state.turn.kraken_debt == 1
    choose_option(game, room, current, card_id="loot-mermaid-9")
    assert room.state.turn.kraken_debt == 0
    assert game.view(room, current)["actions"]["canCollect"] is True


def test_mermaid_has_no_entry_choice_and_keeps_high_value() -> None:
    game, room, players = started_room(2)
    draw_exact(game, room, players[0], "loot-mermaid-9")
    assert room.state.phase == "turn"
    assert room.state.turn.pending_choice is None
    game.act(room, players[0], "collect", {})
    assert room.state.players[players[0].id].bank["mermaid"] == ["loot-mermaid-9"]


def test_busting_card_never_executes_its_ability() -> None:
    game, room, players = started_room(2)
    put_bank(game, room, players[1].id, "loot-mermaid-9")
    draw_exact(game, room, players[0], "loot-cannon-3")
    choose_option(game, room, players[0], player_id=players[1].id, suit="mermaid")
    put_bank(game, room, players[1].id, "loot-mermaid-9")
    draw_exact(game, room, players[0], "loot-cannon-4")

    assert room.state.turn.actor_id == players[1].id
    assert room.state.players[players[1].id].bank["mermaid"] == ["loot-mermaid-9"]
    assert room.state.turn.pending_choice is None


def test_collect_is_rejected_while_kraken_debt_or_effect_choice_remains() -> None:
    game, room, players = started_room(2)
    draw_exact(game, room, players[0], "loot-kraken-3")
    with pytest.raises(GameRuleError, match="海怪仍要求"):
        game.act(room, players[0], "collect", {})

    game, room, players = started_room(2, seed=88)
    put_bank(game, room, players[0].id, "loot-mermaid-9")
    draw_exact(game, room, players[0], "loot-hook-4")
    with pytest.raises(GameRuleError, match="先解决"):
        game.act(room, players[0], "collect", {})
