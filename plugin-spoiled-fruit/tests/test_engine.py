from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import pytest

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError
from backend.app.games.plugins import _load_engine_factory


PLUGIN_DIR = Path(__file__).resolve().parents[1]


def assert_view_matches_contract(view: dict[str, Any]) -> None:
    schema = json.loads(
        (PLUGIN_DIR / "model" / "view-state.schema.json").read_text(encoding="utf-8")
    )
    assert set(view) == set(schema["properties"])
    assert view["schemaVersion"] == schema["properties"]["schemaVersion"]["const"]
    assert view["phase"] in schema["properties"]["phase"]["enum"]
    assert view["sceneId"] in schema["properties"]["sceneId"]["enum"]
    player_keys = set(schema["$defs"]["playerView"]["properties"])
    card_keys = set(schema["$defs"]["cardView"]["properties"])
    for player in view["players"]:
        assert set(player) == player_keys
        for slot in player["handSlots"]:
            if slot["card"] is not None:
                assert set(slot["card"]) == card_keys


def make_engine(seed: int = 20260902):
    game = _load_engine_factory(PLUGIN_DIR, "plugin-spoiled-fruit")()
    game.rng = random.Random(seed)
    return game


def started_room(player_count: int = 4, seed: int = 20260902):
    game = make_engine(seed)
    players = [
        ArcadePlayer(
            f"p{index + 1}",
            f"a{index + 1}",
            f"果客{index + 1}",
            f"token-{index + 1}",
            index,
        )
        for index in range(player_count)
    ]
    room = ArcadeRoom(
        "FRUT",
        game.key,
        players[0].id,
        players,
        game.initial_state(),
        options={"firstPlayer": "host", "mode": "standard"},
    )
    game.start(room)
    return game, room, players


def test_lobby_view_uses_the_same_complete_safe_view_contract() -> None:
    game = make_engine()
    players = [
        ArcadePlayer(f"p{index + 1}", f"a{index + 1}", f"果客{index + 1}", "token", index)
        for index in range(4)
    ]
    room = ArcadeRoom("FRUT", game.key, players[0].id, players, game.initial_state())
    view = game.view(room, players[0])

    assert view["phase"] == "lobby"
    assert view["players"] == []
    assert_view_matches_contract(view)


def available_indexes(board: Any) -> list[int]:
    return [
        index for index, card in enumerate(board.hand)
        if card.instance_id != board.protected_card_id
    ]


def run_bot_game(player_count: int, seed: int) -> tuple[Any, Any, int]:
    game, room, players = started_room(player_count, seed)
    policy_rng = random.Random(seed ^ 0x5F3759DF)
    actions = 0
    while room.phase == "playing" and actions < 12_000:
        state = room.state
        pending = state.pending_choice
        if pending is None:
            actor = room.player(state.current_player_id)
            source_id = game._draw_source(state, actor.id)
            assert source_id is not None
            choices = available_indexes(state.boards[source_id])
            game.act(
                room,
                actor,
                "draw_card",
                {"slotIndex": policy_rng.choice(choices)},
            )
        elif pending["type"] == "optional":
            actor = room.player(pending["requiredPlayerIds"][0])
            game.act(room, actor, "resolve_optional", {"use": False})
        elif pending["type"] == "extra_draw":
            actor = room.player(pending["requiredPlayerIds"][0])
            source_id = pending["sourcePlayerId"]
            game.act(
                room,
                actor,
                "draw_extra",
                {"slotIndex": policy_rng.choice(available_indexes(state.boards[source_id]))},
            )
        elif pending["type"] == "half_select":
            actor_id = next(
                player_id for player_id in pending["requiredPlayerIds"]
                if player_id not in pending["selections"]
            )
            choices = [
                card.instance_id
                for card in game._available_cards(state.boards[actor_id])
            ]
            selected = policy_rng.sample(choices, pending["selectionCount"])
            game.act(
                room,
                room.player(actor_id),
                "select_exchange_cards",
                {"cardIds": selected},
            )
        elif pending["type"] == "insert":
            actor_id = next(
                player_id for player_id in pending["requiredPlayerIds"]
                if player_id not in pending["placements"]
            )
            incoming = list(pending["received"][actor_id])
            policy_rng.shuffle(incoming)
            base_size = len(state.boards[actor_id].hand)
            indexes = [policy_rng.randint(0, base_size + offset) for offset in range(len(incoming))]
            game.act(
                room,
                room.player(actor_id),
                "place_received",
                {
                    "orderedCardIds": [card.instance_id for card in incoming],
                    "insertionIndexes": indexes,
                },
            )
        else:  # pragma: no cover - a new state must force a test update
            raise AssertionError(f"unknown pending choice: {pending['type']}")
        actions += 1
    assert actions < 12_000, "bot policy failed to settle within the safety limit"
    return game, room, actions


@pytest.mark.parametrize(
    ("player_count", "old_maids", "total_cards"),
    ((4, 2, 62), (5, 2, 62), (6, 3, 63), (7, 3, 63), (8, 4, 64)),
)
def test_standard_setup_uses_60_plus_dynamic_old_maids_without_initial_effects(
    player_count: int,
    old_maids: int,
    total_cards: int,
) -> None:
    game, room, players = started_room(player_count)
    state = room.state
    held = [card for board in state.boards.values() for card in board.hand]
    removed_cards = state.removed_pair_count * 2

    assert state.old_maid_count == old_maids
    assert state.total_card_count == total_cards
    assert len(held) + removed_cards == total_cards
    assert sum(
        card.catalog_id.startswith("old-maid-") for card in held
    ) == old_maids
    assert state.effect_queue == []
    assert state.pending_choice is None
    assert state.skip_count == 0
    assert not any(
        event["type"] in {
            "harvest", "shuffle", "skip", "peek", "sweet_share",
            "half_exchange", "protect", "move", "extra_draw", "market_conveyor",
        }
        for event in state.events
    )
    assert game.view(room, players[0])["playerCount"] == player_count
    assert_view_matches_contract(game.view(room, players[0]))


@pytest.mark.parametrize("player_count", (3, 9))
def test_rejects_non_standard_player_counts(player_count: int) -> None:
    with pytest.raises(GameRuleError, match="4–8"):
        started_room(player_count)


def test_normal_draw_preserves_source_order_and_appends_right() -> None:
    game, room, players = started_room(6, seed=91)
    state = room.state
    actor_id = state.current_player_id
    source_id = game._draw_source(state, actor_id)
    actor = state.boards[actor_id]
    source = state.boards[source_id]
    actor_catalogs = {card.catalog_id for card in actor.hand}
    slot = next(
        index for index, card in enumerate(source.hand)
        if card.catalog_id not in actor_catalogs
    )
    drawn = source.hand[slot]
    actor_before = list(actor.hand)
    source_before = list(source.hand)

    game.act(room, room.player(actor_id), "draw_card", {"slotIndex": slot})

    assert actor.hand == actor_before + [drawn]
    assert source.hand == source_before[:slot] + source_before[slot + 1:]
    assert state.events[-2]["type"] == "draw"
    assert state.events[-2]["destinationIndex"] == len(actor.hand) - 1


def test_other_hands_and_private_peek_do_not_leak() -> None:
    game, room, players = started_room(4, seed=42)
    state = room.state
    owner_id = state.current_player_id
    target_id = next(player.id for player in players if player.id != owner_id)
    owner_view = game.view(room, room.player(owner_id))
    target_view = next(item for item in owner_view["players"] if item["playerId"] == target_id)
    assert all(slot["card"] is None for slot in target_view["handSlots"])

    state.private_peeks[owner_id] = {
        "targetPlayerId": target_id,
        "orderedCards": [{"catalogId": "fruit-01"}],
    }
    assert game.view(room, room.player(owner_id))["privatePeek"] is not None
    assert game.view(room, room.player(target_id))["privatePeek"] is None


def test_peek_reveals_complete_order_only_to_effect_owner() -> None:
    game, room, players = started_room(4, seed=11)
    state = room.state
    owner_id = state.current_player_id
    target_id = next(player.id for player in players if player.id != owner_id and state.boards[player.id].hand)
    CardType = type(state.boards[owner_id].hand[0])
    state.boards[owner_id].hand.extend((
        CardType("peek-a", "fruit-15"),
        CardType("peek-b", "fruit-15"),
    ))
    game._sweep_pairs(state, [owner_id])
    game._resolve_until_blocked(room, state)
    assert state.pending_choice["effectId"] == "peek_hand"

    game.act(
        room,
        room.player(owner_id),
        "resolve_optional",
        {"use": True, "targetPlayerId": target_id},
    )

    peek = game.view(room, room.player(owner_id))["privatePeek"]
    assert [card["instanceId"] for card in peek["orderedCards"]] == [
        card.instance_id for card in state.boards[target_id].hand
    ]
    assert game.view(room, room.player(target_id))["privatePeek"] is None


def test_half_exchange_locks_both_sides_then_allows_arbitrary_insertions() -> None:
    game, room, players = started_room(4, seed=5)
    state = room.state
    owner_id, target_id = players[0].id, players[1].id
    CardType = type(next(card for board in state.boards.values() for card in board.hand))
    for board in state.boards.values():
        board.hand = [CardType(f"single-{board.player_id}", "old-maid-01")]
        board.safe = False
        board.harvest_pair_ids.clear()
    state.current_player_id = owner_id
    state.effect_queue.clear()
    state.pending_choice = None
    state.removed_pair_count = 0
    state.boards[owner_id].hand = [
        CardType("half-a", "fruit-21"), CardType("half-b", "fruit-21"),
        CardType("owner-1", "fruit-01"), CardType("owner-2", "fruit-02"),
        CardType("owner-3", "old-maid-01"),
    ]
    state.boards[target_id].hand = [
        CardType("target-1", "fruit-03"), CardType("target-2", "fruit-04"),
        CardType("target-3", "old-maid-02"),
    ]
    game._sweep_pairs(state, [owner_id])
    game._resolve_until_blocked(room, state)
    pending = state.pending_choice
    assert pending["type"] == "half_select"
    assert pending["selectionCount"] == 2
    assert set(pending["requiredPlayerIds"]) == {owner_id, target_id}

    game.act(
        room,
        room.player(owner_id),
        "select_exchange_cards",
        {"cardIds": ["owner-1", "owner-3"]},
    )
    assert state.pending_choice["type"] == "half_select"
    assert game.view(room, room.player(owner_id))["privateChoice"] is None
    assert game.view(room, room.player(target_id))["privateChoice"] is not None
    game.act(
        room,
        room.player(target_id),
        "select_exchange_cards",
        {"cardIds": ["target-1", "target-3"]},
    )
    assert state.pending_choice["type"] == "insert"

    owner_incoming = state.pending_choice["received"][owner_id]
    target_incoming = state.pending_choice["received"][target_id]
    game.act(
        room,
        room.player(owner_id),
        "place_received",
        {
            "orderedCardIds": [card.instance_id for card in reversed(owner_incoming)],
            "insertionIndexes": [0, 2],
        },
    )
    game.act(
        room,
        room.player(target_id),
        "place_received",
        {
            "orderedCardIds": [card.instance_id for card in target_incoming],
            "insertionIndexes": [1, 2],
        },
    )
    assert any(event["type"] == "half_exchange" for event in state.events)
    assert "target-3" in [card.instance_id for card in state.boards[owner_id].hand]
    assert "owner-3" in [card.instance_id for card in state.boards[target_id].hand]


@pytest.mark.parametrize("player_count", (4, 5, 6, 7, 8))
@pytest.mark.parametrize("seed", (17, 83))
def test_bot_games_for_every_supported_player_count_finish_cleanly(
    player_count: int,
    seed: int,
) -> None:
    game, room, actions = run_bot_game(player_count, seed + player_count * 100)
    state = room.state
    assert room.phase == "finished"
    assert state.removed_pair_count == 30
    assert state.effect_queue == []
    assert state.pending_choice is None
    assert sum(len(board.hand) for board in state.boards.values()) == player_count // 2
    assert all(
        card.catalog_id.startswith("old-maid-")
        for board in state.boards.values()
        for card in board.hand
    )
    assert set(room.winner_player_ids) == set(state.finished["winnerIds"])
    assert set(state.finished["winnerIds"]).isdisjoint(state.finished["loserIds"])
    assert set(state.finished["winnerIds"]) | set(state.finished["loserIds"]) == set(state.turn_order)
    assert actions > 0
    assert_view_matches_contract(game.view(room, room.player(state.turn_order[0])))


def test_illegal_player_cannot_act_for_another_private_choice() -> None:
    game, room, players = started_room(4, seed=29)
    state = room.state
    owner_id = state.current_player_id
    CardType = type(state.boards[owner_id].hand[0])
    state.boards[owner_id].hand.extend((
        CardType("guard-a", "fruit-23"),
        CardType("guard-b", "fruit-23"),
    ))
    game._sweep_pairs(state, [owner_id])
    game._resolve_until_blocked(room, state)
    intruder = next(player for player in players if player.id != owner_id)
    with pytest.raises(GameRuleError, match="不属于你"):
        game.act(room, intruder, "resolve_optional", {"use": False})


def reset_small_state(game: Any, room: Any, players: list[Any]) -> Any:
    state = room.state
    CardType = type(next(card for board in state.boards.values() for card in board.hand))
    for index, player in enumerate(players):
        board = state.boards[player.id]
        board.hand = [CardType(f"base-{player.id}", f"fruit-{index + 1:02d}")]
        board.safe = False
        board.pending_empty = False
        board.protected_card_id = None
        board.shield_pair_id = None
        board.harvest_pair_ids.clear()
    state.current_player_id = players[0].id
    state.effect_queue.clear()
    state.pending_choice = None
    state.private_peeks.clear()
    state.safe_order.clear()
    state.removed_pair_count = 0
    state.skip_count = 0
    return CardType


def stage_pair(game: Any, room: Any, owner_id: str, catalog_id: str, CardType: Any) -> None:
    board = room.state.boards[owner_id]
    board.hand.extend((
        CardType(f"{catalog_id}-a", catalog_id),
        CardType(f"{catalog_id}-b", catalog_id),
    ))
    game._sweep_pairs(room.state, [owner_id])
    game._resolve_until_blocked(room, room.state)


def test_shake_basket_randomizes_only_the_owners_existing_order() -> None:
    game, room, players = started_room(4, seed=7)
    CardType = reset_small_state(game, room, players)
    owner_id = players[0].id
    board = room.state.boards[owner_id]
    board.hand = [
        CardType("shake-1", "fruit-01"),
        CardType("shake-2", "fruit-02"),
        CardType("shake-3", "fruit-03"),
    ]
    expected_set = {card.instance_id for card in board.hand}

    stage_pair(game, room, owner_id, "fruit-09", CardType)

    assert {card.instance_id for card in board.hand} == expected_set
    assert any(event["type"] == "shuffle" for event in room.state.events)


def test_sour_skip_is_consumed_only_when_the_queue_hands_off_the_turn() -> None:
    game, room, players = started_room(4, seed=8)
    CardType = reset_small_state(game, room, players)
    owner_id = players[0].id

    stage_pair(game, room, owner_id, "fruit-12", CardType)

    assert room.state.current_player_id == players[2].id
    assert room.state.skip_count == 0
    skip_event = next(event for event in room.state.events if event["type"] == "skip")
    assert skip_event["skipCount"] == 1


def test_shell_guard_blocks_its_slot_and_ends_after_another_normal_draw() -> None:
    game, room, players = started_room(4, seed=9)
    CardType = reset_small_state(game, room, players)
    owner_id = players[1].id
    owner = room.state.boards[owner_id]
    owner.hand = [
        CardType("guarded", "fruit-01"),
        CardType("unguarded", "fruit-02"),
        CardType("spare", "fruit-03"),
    ]
    room.state.current_player_id = players[0].id
    stage_pair(game, room, owner_id, "fruit-23", CardType)
    assert room.state.pending_choice["effectId"] == "shell_guard"
    game.act(
        room,
        room.player(owner_id),
        "resolve_optional",
        {"use": True, "cardId": "guarded"},
    )
    assert owner.protected_card_id == "guarded"

    room.state.current_player_id = players[0].id
    with pytest.raises(GameRuleError, match="硬壳保护"):
        game.act(room, players[0], "draw_card", {"slotIndex": 0})
    game.act(room, players[0], "draw_card", {"slotIndex": 1})
    assert owner.protected_card_id is None
    assert owner.shield_pair_id is None


def test_careful_stocking_moves_one_card_and_keeps_all_other_relative_order() -> None:
    game, room, players = started_room(4, seed=10)
    CardType = reset_small_state(game, room, players)
    owner_id = players[0].id
    board = room.state.boards[owner_id]
    board.hand = [
        CardType("a", "fruit-01"), CardType("b", "fruit-02"),
        CardType("c", "fruit-03"), CardType("d", "fruit-04"),
    ]
    stage_pair(game, room, owner_id, "fruit-25", CardType)
    game.act(
        room,
        players[0],
        "resolve_optional",
        {"use": True, "cardId": "b", "toIndex": 3},
    )
    assert [card.instance_id for card in board.hand] == ["a", "c", "d", "b"]


def test_sweet_share_transfers_simultaneously_then_uses_both_insertions() -> None:
    game, room, players = started_room(4, seed=12)
    CardType = reset_small_state(game, room, players)
    owner_id, target_id = players[0].id, players[1].id
    room.state.boards[owner_id].hand = [
        CardType("owner-out", "fruit-01"), CardType("owner-stay", "old-maid-01"),
    ]
    room.state.boards[target_id].hand = [
        CardType("target-return", "fruit-02"), CardType("target-stay", "old-maid-02"),
    ]
    stage_pair(game, room, owner_id, "fruit-18", CardType)
    game.act(
        room,
        players[0],
        "resolve_optional",
        {
            "use": True,
            "targetPlayerId": target_id,
            "outgoingCardId": "owner-out",
            "returnSlotIndex": 0,
        },
    )
    assert room.state.pending_choice["type"] == "insert"
    game.act(
        room,
        players[0],
        "place_received",
        {"orderedCardIds": ["target-return"], "insertionIndexes": [0]},
    )
    game.act(
        room,
        players[1],
        "place_received",
        {"orderedCardIds": ["owner-out"], "insertionIndexes": [1]},
    )
    assert [card.instance_id for card in room.state.boards[owner_id].hand] == [
        "target-return", "owner-stay",
    ]
    assert [card.instance_id for card in room.state.boards[target_id].hand] == [
        "target-stay", "owner-out",
    ]
    assert any(event["type"] == "sweet_share" for event in room.state.events)


def test_extra_pick_waits_for_owner_slot_choice_and_appends_right() -> None:
    game, room, players = started_room(4, seed=13)
    CardType = reset_small_state(game, room, players)
    owner_id, source_id = players[0].id, players[1].id
    room.state.boards[owner_id].hand = [CardType("owner-stay", "fruit-01")]
    room.state.boards[source_id].hand = [CardType("picked", "fruit-02")]
    stage_pair(game, room, owner_id, "fruit-27", CardType)
    assert room.state.pending_choice == {
        "type": "extra_draw",
        "queueId": room.state.effect_queue[0].queue_id,
        "effectId": "extra_pick",
        "requiredPlayerIds": [owner_id],
        "sourcePlayerId": source_id,
    }
    game.act(room, players[0], "draw_extra", {"slotIndex": 0})
    assert [card.instance_id for card in room.state.boards[owner_id].hand] == [
        "owner-stay", "picked",
    ]


def test_market_conveyor_passes_every_leftmost_card_clockwise_before_pair_sweep() -> None:
    game, room, players = started_room(4, seed=14)
    CardType = reset_small_state(game, room, players)
    for index, player in enumerate(players):
        room.state.boards[player.id].hand = [
            CardType(f"left-{player.id}", f"fruit-{index + 1:02d}")
        ]
    stage_pair(game, room, players[0].id, "fruit-29", CardType)
    assert room.state.pending_choice["type"] == "insert"
    for player in players:
        incoming = room.state.pending_choice["received"][player.id]
        game.act(
            room,
            player,
            "place_received",
            {"orderedCardIds": [incoming[0].instance_id], "insertionIndexes": [0]},
        )
    assert [room.state.boards[player.id].hand[0].instance_id for player in players] == [
        "left-p4", "left-p1", "left-p2", "left-p3",
    ]
    assert any(event["type"] == "market_conveyor" for event in room.state.events)


def test_final_pair_resolves_its_effect_before_old_maid_settlement() -> None:
    game, room, players = started_room(4, seed=15)
    CardType = reset_small_state(game, room, players)
    state = room.state
    state.removed_pair_count = 29
    state.boards[players[0].id].hand = [
        CardType("last-a", "fruit-09"), CardType("last-b", "fruit-09"),
        CardType("bad-1", "old-maid-01"),
    ]
    state.boards[players[1].id].hand = [CardType("bad-2", "old-maid-02")]
    state.boards[players[2].id].hand = []
    state.boards[players[3].id].hand = []

    game._sweep_pairs(state, [players[0].id])
    assert room.phase == "playing"
    game._resolve_until_blocked(room, state)

    assert room.phase == "finished"
    event_types = [event["type"] for event in state.events]
    assert event_types.index("shuffle") < event_types.index("finish")
    assert set(state.finished["loserIds"]) == {players[0].id, players[1].id}
