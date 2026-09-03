from __future__ import annotations

from dead_mans_draw_test_helpers import (
    choose_option,
    draw_exact,
    pending_choice,
    put_bank,
    remove_card,
    set_trait,
    started_room,
)


def test_golden_scales_adds_five_to_the_scoring_mermaid() -> None:
    game, room, players = started_room(2)
    set_trait(room, players[0].id, "trait-golden-scales")
    put_bank(game, room, players[0].id, "loot-mermaid-9", "loot-mermaid-5")

    view = game.view(room, players[0])
    player = next(item for item in view["players"] if item["id"] == players[0].id)
    assert player["liveScore"] == 14


def test_casanova_banks_drawn_mermaid_before_entry_without_paying_kraken_debt() -> None:
    game, room, players = started_room(2)
    set_trait(room, players[0].id, "trait-casanova")
    draw_exact(game, room, players[0], "loot-kraken-3")
    draw_exact(game, room, players[0], "loot-mermaid-9")

    assert room.state.turn.kraken_debt == 2
    assert room.state.players[players[0].id].bank["mermaid"] == ["loot-mermaid-9"]
    assert [entry.card_id for entry in room.state.turn.play_area] == ["loot-kraken-3"]


def test_plunderer_replaces_key_chest_discard_reward_with_one_opponent_bank() -> None:
    game, room, players = started_room(2)
    set_trait(room, players[0].id, "trait-plunderer")
    put_bank(game, room, players[1].id, "loot-anchor-7")
    discard_before = len(room.state.discard_pile)
    draw_exact(game, room, players[0], "loot-key-3")
    draw_exact(game, room, players[0], "loot-chest-3")
    game.act(room, players[0], "collect", {})

    assert pending_choice(room).kind == "plunderer-target"
    choose_option(game, room, players[0], player_id=players[1].id)
    assert room.state.players[players[0].id].bank["anchor"] == ["loot-anchor-7"]
    assert not room.state.players[players[1].id].bank["anchor"]
    assert len(room.state.discard_pile) == discard_before


def test_treasure_hunter_doubles_key_chest_reward_count() -> None:
    game, room, players = started_room(2)
    set_trait(room, players[0].id, "trait-treasure-hunter")
    draw_exact(game, room, players[0], "loot-key-3")
    draw_exact(game, room, players[0], "loot-chest-3")
    game.act(room, players[0], "collect", {})

    board = room.state.players[players[0].id]
    assert sum(len(pile) for pile in board.bank.values()) == 6
    assert next(event for event in room.state.events if event.type == "key_chest_bonus").data["count"] == 4


def test_navigator_uses_the_entire_discard_as_map_candidates() -> None:
    game, room, players = started_room(2)
    set_trait(room, players[0].id, "trait-navigator")
    discard_before = set(room.state.discard_pile)
    draw_exact(game, room, players[0], "loot-map-3")

    choice = pending_choice(room)
    assert choice.kind == "map-card"
    assert {option.card_id for option in choice.options} == discard_before
    assert not room.state.discard_pile


def test_master_gunner_discards_the_entire_selected_stack() -> None:
    game, room, players = started_room(2)
    set_trait(room, players[0].id, "trait-master-gunner")
    put_bank(game, room, players[1].id, "loot-mermaid-9", "loot-mermaid-6")
    draw_exact(game, room, players[0], "loot-cannon-4")
    choose_option(game, room, players[0], player_id=players[1].id, suit="mermaid")

    assert not room.state.players[players[1].id].bank["mermaid"]
    assert {"loot-mermaid-9", "loot-mermaid-6"}.issubset(room.state.discard_pile)


def test_scavenger_banks_the_card_removed_by_cannon() -> None:
    game, room, players = started_room(2)
    set_trait(room, players[0].id, "trait-scavenger")
    put_bank(game, room, players[1].id, "loot-mermaid-9")
    draw_exact(game, room, players[0], "loot-cannon-4")
    choose_option(game, room, players[0], player_id=players[1].id, suit="mermaid")

    assert room.state.players[players[0].id].bank["mermaid"] == ["loot-mermaid-9"]
    assert "loot-mermaid-9" not in room.state.discard_pile


def test_mystic_peeks_the_next_three_cards_in_fixed_order() -> None:
    game, room, players = started_room(2)
    set_trait(room, players[0].id, "trait-mystic")
    sequence = ["loot-oracle-3", "loot-mermaid-5", "loot-key-4", "loot-anchor-5"]
    for identifier in sequence:
        remove_card(room.state, identifier)
    room.state.draw_pile[:0] = sequence
    game.assert_invariants(room.state)

    game.act(room, players[0], "draw", {})
    assert room.state.turn.oracle_peek_card_ids == sequence[1:]
    assert room.state.draw_pile[:3] == sequence[1:]


def test_swordsman_can_steal_a_suit_already_present_in_own_bank() -> None:
    game, room, players = started_room(2)
    set_trait(room, players[0].id, "trait-swordsman")
    put_bank(game, room, players[0].id, "loot-mermaid-8")
    put_bank(game, room, players[1].id, "loot-mermaid-9")
    draw_exact(game, room, players[0], "loot-sword-4")
    choose_option(game, room, players[0], player_id=players[1].id, suit="mermaid")
    assert [entry.card_id for entry in room.state.turn.play_area] == ["loot-sword-4", "loot-mermaid-9"]


def test_miser_protects_hook_and_each_direct_hook_child() -> None:
    game, room, players = started_room(2)
    set_trait(room, players[0].id, "trait-miser")
    put_bank(game, room, players[0].id, "loot-mermaid-9")
    draw_exact(game, room, players[0], "loot-hook-4")
    choose_option(game, room, players[0], card_id="loot-mermaid-9")
    assert all(entry.protection_reasons for entry in room.state.turn.play_area)

    draw_exact(game, room, players[0], "loot-mermaid-6")
    bank = room.state.players[players[0].id].bank
    assert bank["hook"] == ["loot-hook-4"]
    assert bank["mermaid"] == ["loot-mermaid-9"]
    assert "loot-mermaid-6" in room.state.discard_pile


def test_captains_hook_recomputes_and_takes_two_bank_tops_in_sequence() -> None:
    game, room, players = started_room(2)
    set_trait(room, players[0].id, "trait-captains-hook")
    put_bank(game, room, players[0].id, "loot-mermaid-9", "loot-anchor-7")
    draw_exact(game, room, players[0], "loot-hook-4")
    choose_option(game, room, players[0], card_id="loot-mermaid-9")
    assert pending_choice(room).kind == "hook-stack"
    choose_option(game, room, players[0], card_id="loot-anchor-7")

    assert [entry.card_id for entry in room.state.turn.play_area] == [
        "loot-hook-4", "loot-mermaid-9", "loot-anchor-7",
    ]


def test_safe_harbor_protects_anchor_and_next_two_successful_entries() -> None:
    game, room, players = started_room(2)
    set_trait(room, players[0].id, "trait-safe-harbor")
    draw_exact(game, room, players[0], "loot-anchor-3")
    draw_exact(game, room, players[0], "loot-mermaid-5")
    draw_exact(game, room, players[0], "loot-cannon-4")
    assert all(entry.protection_reasons for entry in room.state.turn.play_area)
    assert room.state.turn.safe_harbor_slots == 0

    draw_exact(game, room, players[0], "loot-mermaid-6")
    board = room.state.players[players[0].id].bank
    assert board["anchor"] == ["loot-anchor-3"]
    assert board["mermaid"] == ["loot-mermaid-5"]
    assert board["cannon"] == ["loot-cannon-4"]


def test_fisherman_banks_drawn_kraken_without_entry_or_debt() -> None:
    game, room, players = started_room(2)
    set_trait(room, players[0].id, "trait-fisherman")
    draw_exact(game, room, players[0], "loot-kraken-7")
    assert room.state.players[players[0].id].bank["kraken"] == ["loot-kraken-7"]
    assert not room.state.turn.play_area
    assert room.state.turn.kraken_debt == 0


def test_opponent_beastmaster_replaces_kraken_debt_with_four() -> None:
    game, room, players = started_room(2)
    set_trait(room, players[1].id, "trait-beastmaster")
    draw_exact(game, room, players[0], "loot-kraken-3")
    assert room.state.turn.kraken_debt == 4


def test_misfire_forces_opponent_cannon_to_discard_own_top_card() -> None:
    game, room, players = started_room(2)
    set_trait(room, players[1].id, "trait-misfire")
    put_bank(game, room, players[0].id, "loot-mermaid-9", "loot-mermaid-6")
    draw_exact(game, room, players[0], "loot-cannon-4")
    choice = pending_choice(room)
    assert {option.player_id for option in choice.options} == {players[0].id}
    choose_option(game, room, players[0], player_id=players[0].id, suit="mermaid")
    assert room.state.players[players[0].id].bank["mermaid"] == ["loot-mermaid-6"]
    assert "loot-mermaid-9" in room.state.discard_pile


def test_misfire_passive_override_wins_over_actor_master_gunner() -> None:
    game, room, players = started_room(2, seed=44)
    set_trait(room, players[0].id, "trait-master-gunner")
    set_trait(room, players[1].id, "trait-misfire")
    put_bank(game, room, players[0].id, "loot-mermaid-9", "loot-mermaid-6")
    draw_exact(game, room, players[0], "loot-cannon-4")
    choose_option(game, room, players[0], player_id=players[0].id, suit="mermaid")
    assert room.state.players[players[0].id].bank["mermaid"] == ["loot-mermaid-6"]


def test_parry_forces_sword_to_kraken_or_discards_sword_when_missing() -> None:
    game, room, players = started_room(2)
    set_trait(room, players[1].id, "trait-parry")
    put_bank(game, room, players[1].id, "loot-kraken-7")
    draw_exact(game, room, players[0], "loot-sword-4")
    choice = pending_choice(room)
    assert len(choice.options) == 1
    assert choice.options[0].player_id == players[1].id
    assert choice.options[0].suit == "kraken"
    choose_option(game, room, players[0], player_id=players[1].id, suit="kraken")
    assert [entry.card_id for entry in room.state.turn.play_area] == ["loot-sword-4", "loot-kraken-7"]

    game, room, players = started_room(2, seed=45)
    set_trait(room, players[1].id, "trait-parry")
    draw_exact(game, room, players[0], "loot-sword-4")
    assert not room.state.turn.play_area
    assert "loot-sword-4" in room.state.discard_pile
    assert room.state.turn.pending_choice is None


def test_davy_jones_locker_receives_unprotected_bust_cards() -> None:
    game, room, players = started_room(2)
    set_trait(room, players[1].id, "trait-davy-jones-locker")
    room.state.players[players[1].id].locker_target_id = players[0].id
    draw_exact(game, room, players[0], "loot-mermaid-5")
    draw_exact(game, room, players[0], "loot-mermaid-6")

    assert room.state.players[players[1].id].bank["mermaid"] == [
        "loot-mermaid-6", "loot-mermaid-5",
    ]
    assert "loot-mermaid-5" not in room.state.discard_pile
    assert "loot-mermaid-6" not in room.state.discard_pile
