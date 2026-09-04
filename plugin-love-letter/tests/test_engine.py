from __future__ import annotations

import json
from collections import Counter

import pytest

from backend.app.games.plugin_api import ArcadeRoom, GameRuleError

from .helpers import (
    all_physical_cards,
    card,
    configure_play,
    make_engine,
    make_players,
    play_type,
    resolve_choice,
    started_room,
    symbols,
)


@pytest.mark.parametrize(
    ("count", "deck_count", "face_up_count", "favor_target"),
    [(2, 16, 3, 6), (3, 18, 0, 5), (4, 17, 0, 4)],
)
def test_setup_is_exact_for_every_supported_player_count(
    count: int, deck_count: int, face_up_count: int, favor_target: int,
) -> None:
    game, room, players = started_room(count)
    state = room.state

    assert game.min_players == 2 and game.max_players == 4
    assert state.current_player_id == players[0].id
    assert state.stage == "draw"
    assert len(state.deck) == deck_count
    assert len(state.face_up_set_aside) == face_up_count
    assert state.reserve is not None
    assert all(len(state.hands[player.id]) == 1 for player in players)
    assert state.favor_target == favor_target
    physical = all_physical_cards(room)
    assert len(physical) == 22
    assert len({item.id for item in physical}) == 22
    _, expected_counts, _ = symbols(game)
    assert Counter(item.type_id for item in physical) == Counter(expected_counts)


@pytest.mark.parametrize("count", [1, 5])
def test_rejects_player_counts_outside_two_to_four(count: int) -> None:
    game = make_engine()
    players = make_players(count)
    room = ArcadeRoom("BAD", game.key, players[0].id, players, game.initial_state())
    with pytest.raises(GameRuleError, match="2–4"):
        game.start(room)


def test_last_card_is_never_drawn_revealed_or_recorded() -> None:
    game, room, players = started_room(2)
    sealed = card(game, "spy", "permanently-sealed")
    configure_play(
        game, room,
        {"p1": ["countess", "king"], "p2": ["prince"]},
        deck=["spy"],
    )
    room.state.deck = [sealed]

    play_type(game, room, players, "countess")

    summary = room.state.round_summary
    assert room.state.stage == "round_summary"
    assert summary["endReason"] == "one-card-left"
    assert summary["roundWinnerIds"] == ["p1"]
    assert summary["sealedCardCount"] == 1
    assert summary["sealedCardRevealed"] is False
    assert room.state.deck == [sealed]
    view = game.view(room, players[0])
    record = game.record_state(room)
    assert view["deckCount"] == 1 and view["sealedCardCount"] == 1
    assert view["roundSummary"]["sealedCardRevealed"] is False
    assert sealed.id not in json.dumps(view, ensure_ascii=False)
    assert sealed.id not in json.dumps(record, ensure_ascii=False)


def test_effect_finishes_before_one_card_showdown_and_prince_uses_reserve() -> None:
    game, room, players = started_room(2)
    configure_play(
        game, room,
        {"p1": ["prince", "guard"], "p2": ["king"]},
        deck=["spy"], reserve="queen",
    )
    sealed_id = room.state.deck[0].id
    play_type(game, room, players, "prince")

    assert room.state.stage == "choice"
    assert room.state.round_summary is None
    resolve_choice(game, room, players, targetPlayerId="p2")

    assert room.state.round_summary["endReason"] == "one-card-left"
    assert room.state.round_summary["sealedCardRevealed"] is False
    assert room.state.deck[0].id == sealed_id
    assert room.state.reserve is None
    assert any(event["kind"] == "force_redraw" for event in room.state.events)


def test_draw_action_refuses_the_sealed_last_card() -> None:
    game, room, players = started_room(2)
    room.state.deck = [card(game, "guard", "sealed")]
    room.state.stage = "draw"
    with pytest.raises(GameRuleError, match="封存"):
        game.act(room, players[0], "draw_card", {"turnNumber": room.state.turn_number})


@pytest.mark.parametrize(
    ("hand", "legal_type"),
    [
        (["queen", "king"], "queen"),
        (["queen", "countess"], "queen"),
        (["countess", "king"], "countess"),
        (["countess", "prince"], "countess"),
    ],
)
def test_queen_and_countess_forced_play_constraints(hand: list[str], legal_type: str) -> None:
    game, room, players = started_room(2)
    configure_play(game, room, {"p1": hand, "p2": ["guard"]})
    view = game.view(room, players[0])
    legal = [card for card in view["players"][0]["visibleHand"] if card["id"] in view["legalCardIds"]]
    assert [item["typeId"] for item in legal] == [legal_type]
    illegal = next(item for item in room.state.hands["p1"] if item.type_id != legal_type)
    with pytest.raises(GameRuleError, match="强制出牌"):
        game.act(room, players[0], "play_card", {"cardId": illegal.id, "turnNumber": room.state.turn_number})


def test_guard_hit_miss_invalid_guess_and_queen_defence() -> None:
    game, room, players = started_room(3)
    configure_play(game, room, {"p1": ["guard", "spy"], "p2": ["priest"], "p3": ["king"]})
    play_type(game, room, players, "guard")
    pending_id = room.state.pending_choice.id
    with pytest.raises(GameRuleError, match="猜测角色无效"):
        resolve_choice(game, room, players, targetPlayerId="p2", cardTypeId="guard")
    assert room.state.pending_choice.id == pending_id
    resolve_choice(game, room, players, targetPlayerId="p2", cardTypeId="baron")
    assert "p2" not in room.state.out_player_ids
    assert room.state.events[-1]["kind"] == "guess_miss"

    configure_play(game, room, {"p1": ["queen", "spy"], "p2": ["priest"], "p3": ["king"]})
    play_type(game, room, players, "queen")
    resolve_choice(game, room, players, targetPlayerId="p2", cardTypeId="priest")
    assert "p2" in room.state.out_player_ids
    assert room.state.events[-1]["kind"] in {"guess_hit", "round_end"}

    configure_play(game, room, {"p1": ["guard", "spy"], "p2": ["queen"], "p3": ["king"]}, deck=["guard"], reserve="priest")
    sealed_id = room.state.deck[0].id
    play_type(game, room, players, "guard")
    resolve_choice(game, room, players, targetPlayerId="p2", cardTypeId="queen")
    assert "p2" not in room.state.out_player_ids
    assert room.state.reserve is None
    assert room.state.deck[0].id == sealed_id
    assert any(entry.reason == "guard-hit" and entry.card.type_id == "queen" for entry in room.state.played["p2"])
    assert any(event["kind"] == "queen_escape" for event in room.state.events)


def test_priest_knowledge_is_private_and_becomes_stale_after_swap() -> None:
    game, room, players = started_room(3)
    configure_play(game, room, {"p1": ["priest", "guard"], "p2": ["princess"], "p3": ["king"]})
    play_type(game, room, players, "priest")
    resolve_choice(game, room, players, targetPlayerId="p2")

    p1_view = game.view(room, players[0])
    p3_view = game.view(room, players[2])
    assert p1_view["privateInfo"]["knownHands"][0]["card"]["typeId"] == "princess"
    assert p3_view["privateInfo"]["knownHands"] == []
    assert "princess" not in json.dumps(p3_view["events"], ensure_ascii=False)

    room.state.current_player_id = "p3"
    room.state.stage = "play"
    room.state.hands["p3"] = [card(game, "king", "swap"), card(game, "spy", "kept")]
    room.state.protected_player_ids = []
    play_type(game, room, players, "king")
    resolve_choice(game, room, players, targetPlayerId="p2")
    assert game.view(room, players[0])["privateInfo"]["knownHands"][0]["current"] is False


@pytest.mark.parametrize(
    ("actor_card", "target_card", "loser"),
    [("guard", "princess", "p1"), ("princess", "guard", "p2"), ("guard", "guard", None)],
)
def test_baron_all_comparison_outcomes(actor_card: str, target_card: str, loser: str | None) -> None:
    game, room, players = started_room(3)
    configure_play(game, room, {"p1": ["baron", actor_card], "p2": [target_card], "p3": ["priest"]})
    play_type(game, room, players, "baron")
    resolve_choice(game, room, players, targetPlayerId="p2")
    if loser:
        assert loser in room.state.out_player_ids
    else:
        assert "p1" not in room.state.out_player_ids and "p2" not in room.state.out_player_ids
    event = next(event for event in reversed(room.state.events) if event["kind"] == "compare_hands")
    assert event["data"]["outcome"] == ("tie" if loser is None else "eliminated")


def test_handmaid_protection_blocks_targets_and_expires_before_own_draw() -> None:
    game, room, players = started_room(3)
    configure_play(game, room, {"p1": ["handmaid", "guard"], "p2": ["guard"], "p3": ["priest"]})
    play_type(game, room, players, "handmaid")
    assert "p1" in room.state.protected_player_ids

    room.state.current_player_id = "p2"
    room.state.stage = "play"
    room.state.hands["p2"] = [card(game, "guard", "attack"), card(game, "spy", "stay")]
    play_type(game, room, players, "guard")
    assert "p1" not in room.state.pending_choice.candidate_player_ids

    room.state.pending_choice = None
    room.state.current_player_id = "p3"
    room.state.stage = "play"
    room.state.hands["p3"] = [card(game, "countess", "skip"), card(game, "spy", "stay")]
    play_type(game, room, players, "countess")
    assert room.state.current_player_id == "p1"
    assert room.state.stage == "draw"
    assert "p1" not in room.state.protected_player_ids
    assert any(event["kind"] == "protection_expired" for event in room.state.events)


def test_all_other_players_protected_makes_other_target_effect_noop_but_prince_can_self_target() -> None:
    game, room, players = started_room(3)
    configure_play(
        game, room,
        {"p1": ["guard", "spy"], "p2": ["priest"], "p3": ["king"]},
        protected=["p2", "p3"],
    )
    play_type(game, room, players, "guard")
    assert room.state.pending_choice is None
    assert any(event["kind"] == "no_legal_target" for event in room.state.events)

    configure_play(
        game, room,
        {"p1": ["prince", "spy"], "p2": ["priest"], "p3": ["king"]},
        protected=["p2", "p3"],
    )
    play_type(game, room, players, "prince")
    assert room.state.pending_choice.candidate_player_ids == ["p1"]


def test_prince_self_other_princess_and_spy_discard_cases() -> None:
    game, room, players = started_room(3)
    configure_play(game, room, {"p1": ["prince", "spy"], "p2": ["priest"], "p3": ["king"]}, deck=["guard", "baron"])
    play_type(game, room, players, "prince")
    resolve_choice(game, room, players, targetPlayerId="p1")
    assert "p1" in room.state.spy_player_ids
    assert next(item for item in room.state.round_summary["revealedHands"] if item["playerId"] == "p1")["card"]["typeId"] == "baron"
    assert any(entry.reason == "prince" and entry.card.type_id == "spy" for entry in room.state.played["p1"])

    configure_play(game, room, {"p1": ["prince", "guard"], "p2": ["princess"], "p3": ["king"]})
    play_type(game, room, players, "prince")
    resolve_choice(game, room, players, targetPlayerId="p2")
    assert "p2" in room.state.out_player_ids
    assert room.state.hands["p2"] == []
    assert any(event["kind"] == "prince_princess" for event in room.state.events)


@pytest.mark.parametrize(("deck", "expected_candidates"), [(["guard"], 1), (["guard", "priest"], 2), (["guard", "priest", "baron"], 3)])
def test_chancellor_never_draws_the_final_card(deck: list[str], expected_candidates: int) -> None:
    game, room, players = started_room(3)
    configure_play(game, room, {"p1": ["chancellor", "king"], "p2": ["priest"], "p3": ["guard"]}, deck=deck)
    sealed_before = room.state.deck[0].id
    play_type(game, room, players, "chancellor")
    if expected_candidates == 1:
        assert room.state.round_summary["endReason"] == "one-card-left"
        assert room.state.deck[0].id == sealed_before
        return
    pending = room.state.pending_choice
    assert pending is not None
    assert len(pending.private_card_ids) == expected_candidates
    keep_id = pending.private_card_ids[-1]
    bottom_ids = list(reversed(pending.private_card_ids[:-1]))
    resolve_choice(game, room, players, keepCardId=keep_id, bottomCardIds=bottom_ids)
    assert room.state.hands["p1"][0].id == keep_id
    assert [item.id for item in room.state.deck[: len(bottom_ids)]] == bottom_ids
    assert sealed_before in [item.id for item in room.state.deck]


def test_chancellor_rejects_invalid_partition_without_consuming_choice() -> None:
    game, room, players = started_room(3)
    configure_play(game, room, {"p1": ["chancellor", "king"], "p2": ["priest"], "p3": ["guard"]}, deck=["spy", "guard", "baron"])
    play_type(game, room, players, "chancellor")
    choice_id = room.state.pending_choice.id
    cards_before = [item.id for item in room.state.hands["p1"]]
    with pytest.raises(GameRuleError, match="恰好覆盖"):
        resolve_choice(game, room, players, keepCardId=cards_before[0], bottomCardIds=[cards_before[0]])
    assert room.state.pending_choice.id == choice_id
    assert [item.id for item in room.state.hands["p1"]] == cards_before


def test_king_swaps_hands_without_publicly_revealing_them() -> None:
    game, room, players = started_room(3)
    configure_play(game, room, {"p1": ["king", "guard"], "p2": ["princess"], "p3": ["priest"]})
    play_type(game, room, players, "king")
    resolve_choice(game, room, players, targetPlayerId="p2")
    assert room.state.hands["p1"][0].type_id == "princess"
    assert room.state.hands["p2"][0].type_id == "guard"
    public_event = next(event for event in reversed(room.state.events) if event["kind"] == "trade_hands")
    assert "princess" not in json.dumps(public_event)
    assert game.view(room, players[2])["players"][0]["visibleHand"] == []


def test_playing_princess_eliminates_self_and_last_player_wins_before_deck_check() -> None:
    game, room, players = started_room(2)
    configure_play(game, room, {"p1": ["princess", "guard"], "p2": ["spy"]}, deck=["priest"])
    play_type(game, room, players, "princess")
    assert room.state.round_summary["endReason"] == "last-player"
    assert room.state.round_summary["roundWinnerIds"] == ["p2"]


def test_one_card_showdown_can_have_multiple_winners_and_queen_beats_king() -> None:
    game, room, players = started_room(4)
    configure_play(
        game, room,
        {"p1": ["countess", "prince"], "p2": ["queen"], "p3": ["queen"], "p4": ["king"]},
        deck=["spy"],
    )
    play_type(game, room, players, "countess")
    assert room.state.round_summary["roundWinnerIds"] == ["p2", "p3"]
    assert room.state.favors["p2"] == 1 and room.state.favors["p3"] == 1
    assert room.state.round_summary["sealedCardRevealed"] is False


def test_spy_bonus_unique_multiple_eliminated_and_stacks_with_round_win() -> None:
    game, room, players = started_room(3)
    configure_play(game, room, {"p1": ["countess", "princess"], "p2": ["queen"], "p3": ["guard"]}, deck=["spy"])
    room.state.spy_player_ids = ["p1"]
    play_type(game, room, players, "countess")
    assert room.state.round_summary["roundWinnerIds"] == ["p1"]
    assert room.state.round_summary["spyBonusPlayerId"] == "p1"
    assert room.state.round_summary["rewardDeltas"]["p1"] == 2

    configure_play(game, room, {"p1": ["countess", "princess"], "p2": ["queen"], "p3": ["guard"]}, deck=["spy"])
    room.state.spy_player_ids = ["p1", "p2"]
    play_type(game, room, players, "countess")
    assert room.state.round_summary["spyBonusPlayerId"] is None

    configure_play(game, room, {"p1": ["countess", "princess"], "p2": [], "p3": ["guard"]}, deck=["spy"], out=["p2"])
    room.state.spy_player_ids = ["p2"]
    play_type(game, room, players, "countess")
    assert room.state.round_summary["spyBonusPlayerId"] is None


def test_simultaneous_game_winners_are_preserved() -> None:
    game, room, players = started_room(4)
    configure_play(
        game, room,
        {"p1": ["countess", "prince"], "p2": ["queen"], "p3": ["queen"], "p4": ["king"]},
        deck=["spy"],
    )
    room.state.favors.update({"p1": 0, "p2": 3, "p3": 3, "p4": 0})
    play_type(game, room, players, "countess")
    assert room.phase == "finished"
    assert room.winner_player_ids == ["p2", "p3"]
    assert room.state.game_winner_ids == ["p2", "p3"]


def test_next_round_starts_from_a_round_winner_and_resets_round_state() -> None:
    game, room, players = started_room(2)
    configure_play(game, room, {"p1": ["countess", "king"], "p2": ["prince"]}, deck=["spy"])
    play_type(game, room, players, "countess")
    assert room.state.round_summary["roundWinnerIds"] == ["p1"]
    old_round = room.state.round_number
    game.act(room, players[1], "next_round", {"roundNumber": old_round})
    assert room.state.round_number == old_round + 1
    assert room.state.start_player_id == "p1"
    assert room.state.current_player_id == "p1"
    assert room.state.stage == "draw"
    assert room.state.round_summary is None
    assert room.state.out_player_ids == []


def test_forfeit_finishes_match_when_only_one_player_remains() -> None:
    game, room, players = started_room(2)
    assert game.manual_forfeit(room, players[1]) is True
    assert room.phase == "finished"
    assert room.winner_player_ids == ["p1"]
    assert room.state.stage == "finished"


def test_non_actor_and_stale_choice_are_rejected_without_state_change() -> None:
    game, room, players = started_room(3)
    configure_play(game, room, {"p1": ["guard", "spy"], "p2": ["priest"], "p3": ["king"]})
    play_type(game, room, players, "guard")
    pending = room.state.pending_choice
    with pytest.raises(GameRuleError, match="只有牌效行动者"):
        game.act(room, players[1], "resolve_choice", {"choiceId": pending.id, "turnNumber": room.state.turn_number, "targetPlayerId": "p2", "cardTypeId": "priest"})
    with pytest.raises(GameRuleError, match="选择已过期"):
        game.act(room, players[0], "resolve_choice", {"choiceId": "choice-old", "turnNumber": room.state.turn_number, "targetPlayerId": "p2", "cardTypeId": "priest"})
    assert room.state.pending_choice is pending


def test_safe_views_never_leak_deck_reserve_or_other_hands() -> None:
    game, room, players = started_room(4)
    hidden_ids = {card.id for card in room.state.deck}
    hidden_ids.add(room.state.reserve.id)
    for viewer in players:
        view = game.view(room, viewer)
        text = json.dumps(view, ensure_ascii=False)
        assert not hidden_ids.intersection(text.split('"'))
        for player in view["players"]:
            if player["id"] == viewer.id:
                assert len(player["visibleHand"]) == player["handCount"]
            else:
                assert player["visibleHand"] == []


def autoplay_complete_match(count: int, seed: int) -> tuple[int, set[str]]:
    game, room, players = started_room(count, seed=seed)
    players_by_id = {player.id: player for player in players}
    actions = 0
    observed: set[str] = set()
    while room.phase == "playing" and actions < 2500:
        state = room.state
        observed.update(event["kind"] for event in state.events)
        if state.stage == "draw":
            actor = players_by_id[state.current_player_id]
            game.act(room, actor, "draw_card", {"turnNumber": state.turn_number})
        elif state.stage == "play":
            actor = players_by_id[state.current_player_id]
            legal = game._legal_card_ids(state.hands[actor.id])
            game.act(room, actor, "play_card", {"cardId": legal[0], "turnNumber": state.turn_number})
        elif state.stage == "choice":
            pending = state.pending_choice
            actor = players_by_id[pending.actor_id]
            payload = {"choiceId": pending.id, "turnNumber": state.turn_number}
            if pending.kind == "guess":
                target_id = pending.candidate_player_ids[0]
                actual = state.hands[target_id][0].type_id
                payload.update({"targetPlayerId": target_id, "cardTypeId": actual if actual != "guard" else "priest"})
            elif pending.kind == "target":
                payload["targetPlayerId"] = pending.candidate_player_ids[0]
            else:
                payload["keepCardId"] = pending.private_card_ids[0]
                payload["bottomCardIds"] = pending.private_card_ids[1:]
            game.act(room, actor, "resolve_choice", payload)
        elif state.stage == "round_summary":
            game.act(room, players_by_id[game._match_player_ids(state)[0]], "next_round", {"roundNumber": state.round_number})
        else:
            raise AssertionError(f"autoplay stalled at {state.stage}")
        actions += 1
        physical = all_physical_cards(room)
        assert len(physical) == 22
        assert len({card.id for card in physical}) == 22
        assert len(room.state.deck) >= 1
    assert actions < 2500
    assert room.phase == "finished"
    assert room.winner_player_ids
    return actions, observed


@pytest.mark.parametrize("count", [2, 3, 4])
def test_seeded_two_to_four_player_matches_finish_with_conservation(count: int) -> None:
    actions, observed = autoplay_complete_match(count, 7000 + count)
    assert actions > 5
    assert {"round_deal", "draw_card", "play_card", "round_end"}.issubset(observed)
