from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError
from backend.app.games.plugins import discover_game_plugins


PLUGIN_ROOT = Path(__file__).resolve().parents[2]


def engine():
    game = next(
        plugin.engine
        for plugin in discover_game_plugins(PLUGIN_ROOT)
        if plugin.engine.key == "plugin-skull"
    )
    game.rng = random.Random(20260831)
    return game


def room_players(count: int) -> list[ArcadePlayer]:
    return [
        ArcadePlayer(
            f"p{index + 1}",
            f"a{index + 1}",
            f"玩家{index + 1}",
            f"token-{index + 1}",
            index,
        )
        for index in range(count)
    ]


def started_room(count: int = 3, *, last_chance: bool = True):
    game = engine()
    players = room_players(count)
    room = ArcadeRoom(
        "SKUL",
        game.key,
        players[0].id,
        players,
        game.initial_state(),
        options={
            "firstPlayer": "host",
            "lastChanceEnabled": last_chance,
        },
    )
    game.start(room)
    return game, room, players


def hand_disc_id(room: ArcadeRoom, player_id: str, kind: str) -> str:
    return next(
        disc.id for disc in room.state.players[player_id].hand
        if disc.kind == kind
    )


def commit_round(
    game,
    room: ArcadeRoom,
    players: list[ArcadePlayer],
    kinds: dict[str, str] | None = None,
) -> None:
    kinds = kinds or {}
    round_state = room.state.round
    first_id = round_state.first_player_id
    ordered = [player for player in players if player.id != first_id]
    ordered.append(room.player(first_id))
    for player in ordered:
        kind = kinds.get(player.id, "flower")
        game.act(
            room,
            player,
            "commit_initial",
            {"discId": hand_disc_id(room, player.id, kind)},
        )


def make_player_one_challenger(game, room: ArcadeRoom, players: list[ArcadePlayer], bid: int = 1) -> None:
    game.act(room, players[0], "open_bid", {"count": bid})
    for player in players[1:]:
        game.act(room, player, "pass_bid", {})


def test_lobby_view_is_safe_before_start() -> None:
    game = engine()
    players = room_players(3)
    room = ArcadeRoom(
        "WAIT",
        game.key,
        players[0].id,
        players,
        game.initial_state(),
        options={"lastChanceEnabled": True},
    )

    view = game.view(room, players[0])

    assert view["phase"] == "lobby"
    assert view["sceneId"] == "setup.table"
    assert len(view["players"]) == 3
    assert view["hand"] == []
    assert view["actions"] == []


@pytest.mark.parametrize("count", (3, 4, 5, 6))
def test_start_builds_one_unique_four_disc_set_per_player(count: int) -> None:
    game, room, players = started_room(count)
    state = room.state

    assert room.phase == "playing"
    assert state.round.first_player_id == players[0].id
    assert state.phase == "round_setup"
    assert len(state.players) == count
    assert len({state.players[player.id].theme_index for player in players}) == count
    for player in players:
        held = state.players[player.id].hand
        assert [disc.kind for disc in held].count("flower") == 3
        assert [disc.kind for disc in held].count("skull") == 1
        assert len({disc.id for disc in held}) == 4


@pytest.mark.parametrize("count", (2, 7))
def test_rejects_unsupported_player_counts(count: int) -> None:
    game = engine()
    players = room_players(count)
    room = ArcadeRoom(
        "NOPE",
        game.key,
        players[0].id,
        players,
        game.initial_state(),
        options={"firstPlayer": "host"},
    )
    with pytest.raises(GameRuleError, match="3–6"):
        game.start(room)


def test_initial_commit_is_simultaneous_and_hides_other_disc_identity() -> None:
    game, room, players = started_room()

    with pytest.raises(GameRuleError, match="首家"):
        game.act(
            room,
            players[0],
            "commit_initial",
            {"discId": hand_disc_id(room, players[0].id, "skull")},
        )

    p2_skull = hand_disc_id(room, players[1].id, "skull")
    game.act(room, players[1], "commit_initial", {"discId": p2_skull})
    game.act(
        room,
        players[2],
        "commit_initial",
        {"discId": hand_disc_id(room, players[2].id, "flower")},
    )
    before_resolve = game.view(room, players[0])
    assert before_resolve["round"]["committedCount"] == 2
    assert all(not player["stack"] for player in before_resolve["players"])

    game.act(
        room,
        players[0],
        "commit_initial",
        {"discId": hand_disc_id(room, players[0].id, "flower")},
    )

    own_view = game.view(room, players[0])
    other_stack = next(
        player["stack"] for player in own_view["players"]
        if player["id"] == players[1].id
    )
    own_stack = next(
        player["stack"] for player in own_view["players"]
        if player["id"] == players[0].id
    )
    assert room.state.phase == "placement"
    assert own_view["round"]["hasCommitted"] is False
    assert "place_disc" in own_view["actions"]
    assert own_stack[0]["kind"] == "flower"
    assert own_stack[0]["knowledge"] == "self"
    assert other_stack[0]["kind"] == "unknown"
    assert other_stack[0]["knowledge"] == "hidden"
    assert p2_skull not in json.dumps(own_view, ensure_ascii=False)


def test_bid_pass_and_two_successful_challenges_finish_the_game() -> None:
    game, room, players = started_room()

    for expected_round in (1, 2):
        commit_round(game, room, players)
        make_player_one_challenger(game, room, players)
        assert room.state.phase == "reveal"
        game.act(room, players[0], "reveal_disc", {"ownerId": players[0].id})
        if expected_round == 1:
            assert room.phase == "playing"
            assert room.state.phase == "round_setup"
            assert room.state.round.number == 2

    assert room.phase == "finished"
    assert room.winner_player_ids == [players[0].id]
    assert room.state.result_reason == "two_challenges"
    assert next(
        player for player in game.view(room, players[0])["players"]
        if player["id"] == players[0].id
    )["matSide"] == "flower"
    assert game.player_result(room, players[0]) == ("胜者", "individual", True)
    assert game.player_result(room, players[1]) == ("0 次挑战", "individual", False)
    recorded = game.record_state(room)
    assert recorded["roundsPlayed"] == 2
    assert recorded["winnerPlayerIds"] == [players[0].id]
    serialized = json.dumps(recorded, ensure_ascii=False)
    assert "hand" not in serialized
    assert "stack" not in serialized
    assert "skull" not in serialized.lower()


@pytest.mark.parametrize("count", (3, 4, 5, 6))
def test_pass_applies_only_to_latest_bid_and_raise_reactivates_every_player(
    count: int,
) -> None:
    game, room, players = started_room(count)
    commit_round(game, room, players)

    # Add one complete placement lap so a three-player table can raise to three
    # without triggering the maximum-bid shortcut.
    for player in players:
        game.act(
            room,
            player,
            "place_disc",
            {"discId": hand_disc_id(room, player.id, "flower")},
        )

    game.act(room, players[0], "open_bid", {"count": 1})
    game.act(room, players[1], "pass_bid", {})
    assert room.state.round.passed_player_ids == [players[1].id]
    assert room.state.players[players[1].id].passed_bid is True

    game.act(room, players[2], "raise_bid", {"count": 2})
    assert room.state.round.passed_player_ids == []
    assert all(
        room.state.players[player.id].passed_bid is False
        for player in players
    )

    # Everyone between the new high bidder and p2 declines this bid. The first
    # player who declined the previous bid must then receive a fresh turn.
    while room.state.round.current_player_id != players[1].id:
        actor_id = room.state.round.current_player_id
        assert actor_id is not None
        game.act(room, room.player(actor_id), "pass_bid", {})
        assert room.state.phase == "bidding"

    reactivated_view = game.view(room, players[1])
    assert {"raise_bid", "pass_bid"}.issubset(reactivated_view["actions"])
    game.act(room, players[1], "raise_bid", {"count": 3})
    assert room.state.round.high_bidder_id == players[1].id
    assert room.state.round.passed_player_ids == []

    # A challenge begins only when every other active player declines the new
    # highest bid, never because they declined an older one.
    for pass_number in range(1, count):
        actor_id = room.state.round.current_player_id
        assert actor_id is not None
        assert actor_id != players[1].id
        game.act(room, room.player(actor_id), "pass_bid", {})
        if pass_number < count - 1:
            assert room.state.phase == "bidding"

    assert room.state.phase == "reveal"
    assert room.state.round.challenger_id == players[1].id
    assert room.state.round.target_bid == 3
    assert set(room.state.round.passed_player_ids) == {
        player.id for player in players if player.id != players[1].id
    }

    game.act(room, players[1], "reveal_disc", {"ownerId": players[1].id})
    game.act(room, players[1], "reveal_disc", {"ownerId": players[1].id})
    game.act(room, players[1], "reveal_disc", {"ownerId": players[0].id})
    assert room.state.phase == "round_setup"
    assert room.state.round.number == 2
    assert room.state.players[players[1].id].challenge_wins == 1


@pytest.mark.parametrize("count", (3, 4, 5, 6))
def test_full_safe_challenge_flow_and_settlement_for_every_supported_table_size(
    count: int,
) -> None:
    game, room, players = started_room(count)

    for expected_round in (1, 2):
        commit_round(game, room, players)
        assert room.state.phase == "placement"
        assert sum(
            len(room.state.players[player.id].stack)
            for player in players
        ) == count

        game.act(room, players[0], "open_bid", {"count": count})
        assert room.state.phase == "reveal"
        for owner in players:
            game.act(room, players[0], "reveal_disc", {"ownerId": owner.id})

        if expected_round == 1:
            assert room.phase == "playing"
            assert room.state.phase == "round_setup"
            assert room.state.round.number == 2
            assert room.state.players[players[0].id].challenge_wins == 1
            assert all(
                len(room.state.players[player.id].hand) == 4
                and not room.state.players[player.id].stack
                for player in players
            )

    assert room.phase == "finished"
    assert room.winner_player_ids == [players[0].id]
    assert room.state.result_reason == "two_challenges"

    recorded = game.record_state(room)
    assert recorded["roundsPlayed"] == 2
    assert recorded["winnerPlayerIds"] == [players[0].id]
    assert recorded["resultReason"] == "two_challenges"
    assert len(recorded["players"]) == count
    assert recorded["players"][0]["challengeWins"] == 2
    assert all(
        player_record["challengeWins"] == 0
        for player_record in recorded["players"][1:]
    )

    for player in players:
        role, score_kind, won = game.player_result(room, player)
        assert score_kind == "individual"
        assert won is (player.id == players[0].id)
        assert role == ("胜者" if won else "0 次挑战")

        result_view = game.view(room, player)
        assert result_view["phase"] == "finished"
        assert result_view["actions"] == []
        assert result_view["result"] == {
            "winnerIds": [players[0].id],
            "reason": "two_challenges",
            "summary": room.win_reason,
            "statsEligible": True,
        }


@pytest.mark.parametrize("count", (3, 4, 5, 6))
def test_last_player_remaining_flow_and_settlement_for_every_supported_table_size(
    count: int,
) -> None:
    game, room, players = started_room(count)

    for loser_index, loser in enumerate(players[1:], start=1):
        assert game.manual_forfeit(room, loser) is True
        if loser_index < count - 1:
            assert room.phase == "playing"
            assert room.winner_player_ids == []

    assert room.phase == "finished"
    assert room.winner_player_ids == [players[0].id]
    assert room.state.result_reason == "last_player_remaining"
    assert room.state.eliminated_order == [player.id for player in players[1:]]

    recorded = game.record_state(room)
    assert recorded["winnerPlayerIds"] == [players[0].id]
    assert recorded["resultReason"] == "last_player_remaining"
    assert recorded["eliminatedOrder"] == [player.id for player in players[1:]]
    assert len(recorded["players"]) == count
    assert recorded["players"][0]["status"] == "active"
    assert all(
        player_record["status"] == "eliminated"
        and player_record["removedCount"] == 4
        for player_record in recorded["players"][1:]
    )

    for player in players:
        role, score_kind, won = game.player_result(room, player)
        assert score_kind == "individual"
        assert won is (player.id == players[0].id)
        assert role == ("胜者" if won else "淘汰 · 0 次挑战")

        result_view = game.view(room, player)
        assert result_view["phase"] == "finished"
        assert result_view["actions"] == []
        assert result_view["result"]["winnerIds"] == [players[0].id]
        assert result_view["result"]["reason"] == "last_player_remaining"
        assert result_view["result"]["statsEligible"] is True


def test_challenger_must_reveal_own_stack_before_an_opponent() -> None:
    game, room, players = started_room()
    commit_round(game, room, players)
    make_player_one_challenger(game, room, players, bid=2)

    with pytest.raises(GameRuleError, match="先翻完自己"):
        game.act(room, players[0], "reveal_disc", {"ownerId": players[1].id})

    game.act(room, players[0], "reveal_disc", {"ownerId": players[0].id})
    game.act(room, players[0], "reveal_disc", {"ownerId": players[1].id})
    assert room.state.players[players[0].id].challenge_wins == 1
    assert room.state.phase == "round_setup"


def test_own_skull_uses_private_known_penalty_and_keeps_result_secret() -> None:
    game, room, players = started_room()
    commit_round(
        game,
        room,
        players,
        {players[0].id: "skull"},
    )
    make_player_one_challenger(game, room, players)
    game.act(room, players[0], "reveal_disc", {"ownerId": players[0].id})

    owner_view = game.view(room, players[0])
    public_view = game.view(room, players[1])
    candidates = owner_view["round"]["selfPenaltyCandidates"]
    assert room.state.phase == "penalty"
    assert room.state.round.penalty_mode == "self_known"
    assert len(candidates) == 4
    assert public_view["round"]["selfPenaltyCandidates"] == []

    flower_id = next(card["id"] for card in candidates if card["kind"] == "flower")
    game.act(room, players[0], "choose_self_penalty", {"discId": flower_id})

    assert room.state.phase == "round_setup"
    assert len(room.state.players[players[0].id].removed) == 1
    assert game.view(room, players[0])["lastPrivatePenalty"]["kind"] == "flower"
    assert game.view(room, players[1])["lastPrivatePenalty"] is None


def test_opponent_skull_exposes_only_opaque_server_shuffled_slots() -> None:
    game, room, players = started_room()
    commit_round(
        game,
        room,
        players,
        {players[1].id: "skull"},
    )
    make_player_one_challenger(game, room, players, bid=2)
    game.act(room, players[0], "reveal_disc", {"ownerId": players[0].id})
    game.act(room, players[0], "reveal_disc", {"ownerId": players[1].id})

    chooser_view = game.view(room, players[1])
    challenger_view = game.view(room, players[0])
    slots = chooser_view["round"]["penaltySlots"]
    challenger_ids = {
        disc.id
        for disc in room.state.players[players[0].id].hand
        + room.state.players[players[0].id].stack
        if disc.origin == "personal"
    }
    assert room.state.round.penalty_mode == "blind"
    assert len(slots) == 4
    assert all(slot.startswith("opaque-") for slot in slots)
    assert challenger_view["round"]["penaltySlots"] == []
    chooser_payload = json.dumps(chooser_view, ensure_ascii=False)
    assert challenger_ids.isdisjoint(set(chooser_payload.split('"')))

    game.act(room, players[1], "choose_penalty", {"slotId": slots[0]})
    assert room.state.phase == "round_setup"
    assert room.state.round.first_player_id == players[0].id
    assert len(room.state.players[players[0].id].removed) == 1


def test_last_chance_is_granted_once_and_failure_eliminates_holder() -> None:
    game, room, players = started_room(last_chance=True)
    challenger = room.state.players[players[0].id]
    for _ in range(2):
        removed = challenger.hand.pop(0)
        challenger.removed.append(removed)

    commit_round(
        game,
        room,
        players,
        {players[0].id: "skull"},
    )
    make_player_one_challenger(game, room, players)
    game.act(room, players[0], "reveal_disc", {"ownerId": players[0].id})
    flower_id = next(
        candidate_id
        for candidate_id in room.state.round.penalty_candidate_ids
        if candidate_id != room.state.round.failed_disc_id
    )
    game.act(room, players[0], "choose_self_penalty", {"discId": flower_id})

    assert room.state.round.number == 2
    assert room.state.last_chance_holder_id == players[0].id
    assert any(
        disc.kind == "last_chance_flower"
        for disc in room.state.players[players[0].id].hand
    )

    commit_round(
        game,
        room,
        players,
        {players[0].id: "skull"},
    )
    make_player_one_challenger(game, room, players)
    game.act(room, players[0], "reveal_disc", {"ownerId": players[0].id})

    assert room.state.players[players[0].id].status == "eliminated"
    assert room.state.phase == "round_end"
    eliminated_view = game.view(room, players[0])
    assert "choose_next_first" in eliminated_view["actions"]
    game.act(
        room,
        players[0],
        "choose_next_first",
        {"playerId": players[1].id},
    )
    assert room.state.round.number == 3
    assert room.state.round.first_player_id == players[1].id
    assert room.state.last_chance_holder_id is None


def test_forfeit_is_recorded_and_last_remaining_player_wins() -> None:
    game, room, players = started_room()
    assert game.manual_forfeit(room, players[1]) is True
    assert room.state.players[players[1].id].status == "eliminated"
    assert room.phase == "playing"

    assert game.manual_forfeit(room, players[2]) is True
    assert room.phase == "finished"
    assert room.winner_player_ids == [players[0].id]
    assert room.state.result_reason == "last_player_remaining"
    assert game.manual_forfeit(room, players[0]) is False


def test_rejects_invalid_bids_and_out_of_turn_actions() -> None:
    game, room, players = started_room()
    commit_round(game, room, players)

    with pytest.raises(GameRuleError, match="还没有轮到"):
        game.act(room, players[1], "open_bid", {"count": 1})
    with pytest.raises(GameRuleError, match="整数"):
        game.act(room, players[0], "open_bid", {"count": True})
    with pytest.raises(GameRuleError, match="介于"):
        game.act(room, players[0], "open_bid", {"count": 99})
