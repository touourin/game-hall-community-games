from __future__ import annotations

import random

import pytest

from backend.app.games.plugin_api import GameRuleError

from dead_mans_draw_test_helpers import (
    choose_option,
    draw_exact,
    pending_choice,
    put_bank,
    rebuild_remaining_as_discard,
    set_trait,
    started_room,
)


def finish_for_score(game, room, reason: str = "draw-pile-exhausted") -> None:
    room.state.discard_pile.extend(room.state.draw_pile)
    room.state.draw_pile = []
    game._finish_game(room, room.state, reason)
    game.assert_invariants(room.state)


def result_row(room, player_id: str):
    return next(row for row in room.state.result.scores if row.player_id == player_id)


def test_last_draw_finishes_only_after_current_player_collects() -> None:
    game, room, players = started_room(2)
    put_bank(game, room, players[0].id, "loot-anchor-7")
    put_bank(game, room, players[1].id, "loot-mermaid-8")
    rebuild_remaining_as_discard(game, room, ["loot-mermaid-9"])

    game.act(room, players[0], "draw", {})
    assert room.phase == "playing"
    assert game.view(room, players[0])["actions"]["canCollect"] is True
    game.act(room, players[0], "collect", {})

    assert room.phase == "finished"
    assert room.winner_player_ids == [players[0].id]
    assert result_row(room, players[0].id).total == 16
    assert result_row(room, players[1].id).total == 8


def test_score_uses_only_highest_card_per_suit_and_card_count_breaks_tie() -> None:
    game, room, players = started_room(2)
    put_bank(game, room, players[0].id, "loot-anchor-7")
    put_bank(game, room, players[1].id, "loot-hook-7", "loot-hook-2")
    finish_for_score(game, room)

    assert result_row(room, players[0].id).total == 7
    assert result_row(room, players[1].id).total == 7
    assert room.winner_player_ids == [players[1].id]
    assert room.win_reason.endswith("7 分获胜")


def test_equal_score_and_equal_bank_count_share_victory() -> None:
    game, room, players = started_room(3)
    put_bank(game, room, players[0].id, "loot-anchor-7", "loot-hook-2")
    put_bank(game, room, players[1].id, "loot-cannon-7", "loot-key-2")
    put_bank(game, room, players[2].id, "loot-mermaid-5")
    finish_for_score(game, room)

    assert room.winner_player_ids == [players[0].id, players[1].id]
    assert room.state.result.outcome == "shared-win"
    assert result_row(room, players[0].id).bank_card_count == 2
    assert result_row(room, players[1].id).bank_card_count == 2


def test_golden_scales_is_applied_before_final_comparison() -> None:
    game, room, players = started_room(2)
    set_trait(room, players[0].id, "trait-golden-scales")
    put_bank(game, room, players[0].id, "loot-mermaid-7")
    put_bank(game, room, players[1].id, "loot-anchor-7", "loot-hook-4")
    finish_for_score(game, room)

    assert result_row(room, players[0].id).total == 12
    assert result_row(room, players[0].id).card_adjustments == 5
    assert room.winner_player_ids == [players[0].id]


def test_key_chest_reward_takes_all_when_discard_is_short() -> None:
    game, room, players = started_room(2)
    only_reward = "loot-anchor-2"
    for identifier in list(room.state.discard_pile):
        if identifier != only_reward:
            put_bank(game, room, players[1].id, identifier)
    draw_exact(game, room, players[0], "loot-key-3")
    draw_exact(game, room, players[0], "loot-chest-3")
    game.act(room, players[0], "collect", {})

    assert not room.state.discard_pile
    assert room.state.players[players[0].id].bank["anchor"] == [only_reward]
    assert next(event for event in room.state.events if event.type == "key_chest_bonus").data["count"] == 1


def test_anchored_key_chest_bonus_is_resolved_before_new_bust_cards_sink() -> None:
    game, room, players = started_room(2)
    current = players[0]
    draw_exact(game, room, current, "loot-key-3")
    draw_exact(game, room, current, "loot-chest-3")
    draw_exact(game, room, current, "loot-anchor-4")
    draw_exact(game, room, current, "loot-key-4")

    board_cards = {
        card_id for pile in room.state.players[current.id].bank.values() for card_id in pile
    }
    assert {"loot-key-3", "loot-chest-3"}.issubset(board_cards)
    assert "loot-anchor-4" in room.state.discard_pile
    assert "loot-key-4" in room.state.discard_pile
    assert "loot-anchor-4" not in board_cards
    assert "loot-key-4" not in board_cards


def test_empty_deck_clears_unfulfillable_kraken_debt_then_allows_collection() -> None:
    game, room, players = started_room(2)
    rebuild_remaining_as_discard(game, room, ["loot-kraken-7"])
    game.act(room, players[0], "draw", {})

    assert room.state.turn.kraken_debt == 0
    assert game.view(room, players[0])["actions"]["canCollect"] is True
    game.act(room, players[0], "collect", {})
    assert room.phase == "finished"


def test_last_card_casanova_direct_bank_finishes_without_empty_lane_deadlock() -> None:
    game, room, players = started_room(2)
    set_trait(room, players[0].id, "trait-casanova")
    rebuild_remaining_as_discard(game, room, ["loot-mermaid-9"])
    game.act(room, players[0], "draw", {})

    assert room.phase == "finished"
    assert room.state.players[players[0].id].bank["mermaid"] == ["loot-mermaid-9"]
    assert room.winner_player_ids == [players[0].id]


@pytest.mark.parametrize("count", (2, 3, 4))
def test_last_remaining_player_wins_after_forfeits(count: int) -> None:
    game, room, players = started_room(count)
    for player in players[1:]:
        assert game.manual_forfeit(room, player)
        if player is not players[-1]:
            assert room.phase == "playing"

    assert room.phase == "finished"
    assert room.winner_player_ids == [players[0].id]
    assert room.state.result.reason == "player-exit"
    assert game.player_result(room, players[0])[2] is True
    assert all(game.player_result(room, player)[0] == "已退出" for player in players[1:])


def test_resign_action_advances_revision_exactly_once() -> None:
    game, room, players = started_room(3)
    before = room.state.revision

    game.act(room, players[0], "resign", {"revision": before})

    assert room.phase == "playing"
    assert room.state.revision == before + 1
    assert room.state.players[players[0].id].forfeited is True
    assert room.state.turn.actor_id == players[1].id


def test_current_player_resigning_on_empty_deck_finishes_without_ghost_turn() -> None:
    game, room, players = started_room(3)
    rebuild_remaining_as_discard(game, room, [])
    before_turn_number = room.state.turn_number

    game.act(room, players[0], "resign", {"revision": room.state.revision})

    assert room.phase == "finished"
    assert room.state.result.reason == "draw-pile-exhausted"
    assert room.state.turn_number == before_turn_number
    assert players[0].id not in room.winner_player_ids


def test_invalid_and_stale_effect_options_do_not_mutate_state() -> None:
    game, room, players = started_room(2)
    put_bank(game, room, players[0].id, "loot-mermaid-9")
    draw_exact(game, room, players[0], "loot-hook-4")
    choice = pending_choice(room)
    bank_before = list(room.state.players[players[0].id].bank["mermaid"])
    with pytest.raises(GameRuleError, match="合法选项"):
        game.act(room, players[0], "resolve_effect", {"choiceId": choice.choice_id, "optionId": "option-forged"})
    assert room.state.players[players[0].id].bank["mermaid"] == bank_before
    assert room.state.turn.pending_choice.choice_id == choice.choice_id

    choose_option(game, room, players[0], card_id="loot-mermaid-9")
    with pytest.raises(GameRuleError, match="没有等待"):
        game.act(room, players[0], "resolve_effect", {"choiceId": choice.choice_id, "optionId": choice.options[0].option_id})


def choose_bot_action(game, room, player, rng: random.Random) -> bool:
    view = game.view(room, player)
    actions = view["actions"]
    if actions["canChooseTrait"]:
        game.act(room, player, "choose_trait", {"traitId": view["self"]["traitOffer"][0]["id"]})
        return True
    if actions["canChooseLockerTarget"]:
        target_id = next(item["id"] for item in view["players"] if item["id"] != player.id and not item["forfeited"])
        game.act(room, player, "choose_locker_target", {"playerId": target_id})
        return True
    if actions["canResolveEffect"]:
        choice = view["turn"]["pendingChoice"]
        safe = [item for item in choice["options"] if not item["causesImmediateBust"]]
        option = rng.choice(safe or choice["options"])
        game.act(room, player, "resolve_effect", {"choiceId": choice["choiceId"], "optionId": option["optionId"]})
        return True
    if actions["canDraw"] and (
        not actions["canCollect"]
        or len(view["playArea"]) < 5 and rng.random() < 0.58
    ):
        game.act(room, player, "draw", {})
        return True
    if actions["canCollect"]:
        game.act(room, player, "collect", {})
        return True
    return False


def independently_score_board(board) -> tuple[int, int]:
    total = 0
    count = 0
    for suit, pile in board.bank.items():
        count += len(pile)
        if pile:
            value = max(int(card_id.rsplit("-", 1)[1]) for card_id in pile)
            if suit == "mermaid" and board.trait_id == "trait-golden-scales":
                value += 5
            total += value
    return total, count


@pytest.mark.parametrize("count", (2, 3, 4))
def test_seeded_complete_games_never_deadlock_and_settle_independently(count: int) -> None:
    entered_suits: set[str] = set()
    for sample in range(32):
        game, room, players = started_room(
            count,
            seed=900_000 + count * 1_000 + sample,
            traits_enabled=True,
        )
        bot_rng = random.Random(700_000 + count * 1_000 + sample)
        last_seq = 0
        for _ in range(1_200):
            if room.phase == "finished":
                break
            acted = False
            for player in players:
                if choose_bot_action(game, room, player, bot_rng):
                    acted = True
                    break
            assert acted, f"牌局卡死在 {room.state.phase}"
            game.assert_invariants(room.state)
            for event in room.state.events:
                if event.seq > last_seq and event.type == "card_entered":
                    entered_suits.add(event.data["card"]["suit"])
            last_seq = room.state.event_counter
        else:
            pytest.fail("完整牌局超过 1200 个动作")

        assert room.phase == "finished"
        expected = {
            player.id: independently_score_board(room.state.players[player.id])
            for player in players
        }
        for row in room.state.result.scores:
            assert (row.total, row.bank_card_count) == expected[row.player_id]
        winning_key = max(expected.values())
        expected_winners = [player.id for player in players if expected[player.id] == winning_key]
        assert room.winner_player_ids == expected_winners
        assert game.record_state(room)["winnerPlayerIds"] == expected_winners

    assert entered_suits == {
        "anchor", "hook", "cannon", "key", "chest",
        "map", "oracle", "sword", "kraken", "mermaid",
    }
