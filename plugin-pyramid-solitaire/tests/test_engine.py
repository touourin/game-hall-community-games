from __future__ import annotations

import random
from pathlib import Path

import pytest

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError
from backend.app.games.plugins import discover_game_plugins


PLUGIN_ROOT = Path(__file__).resolve().parents[2]


def load_engine():
    engine = next(
        plugin.engine
        for plugin in discover_game_plugins(PLUGIN_ROOT)
        if plugin.engine.key == "plugin-pyramid-solitaire"
    )
    engine.rng = random.Random(20260813)
    return engine


def make_room(game, now: list[float]):
    game.clock = lambda: now[0]
    player = ArcadePlayer("p1", "a1", "解谜者", "token", 0)
    room = ArcadeRoom(
        "SOLO",
        game.key,
        player.id,
        [player],
        game.initial_state(),
    )
    game.start(room)
    return room, player


def card_factory(state):
    card_type = type(next(card for card in state.pyramid if card is not None))

    def make_card(card_id: str, rank: int, suit: str = "spades"):
        return card_type(id=card_id, suit=suit, rank=rank)

    return make_card


def test_deals_a_unique_deck_and_hides_the_stock_order() -> None:
    now = [100.0]
    game = load_engine()
    room, player = make_room(game, now)
    state = room.state
    all_cards = [card for card in state.pyramid if card is not None] + state.stock

    assert len(state.pyramid) == 28
    assert len(state.stock) == 24
    assert len(all_cards) == 52
    assert len({card.id for card in all_cards}) == 52

    view = game.view(room, player)
    assert view["stockRemaining"] == 24
    assert view["wasteTop"] is None
    assert "stock" not in view
    assert all(view["pyramid"][index]["exposed"] for index in range(21, 28))
    assert view["pyramid"][0]["exposed"] is False
    assert game._is_solvable_deal(state.pyramid, state.stock)


def test_every_generated_deal_is_solvable_and_keeps_stock_hidden() -> None:
    game = load_engine()

    for _ in range(12):
        state = game.initial_state()
        assert game._is_solvable_deal(state.pyramid, state.stock)

        room = ArcadeRoom(
            "SOLO",
            game.key,
            "p1",
            [ArcadePlayer("p1", "a1", "解谜者", "token", 0)],
            state,
        )
        room.phase = "playing"
        view = game.view(room, room.players[0])
        assert "stock" not in view
        assert "solution" not in view
        assert view["wasteTop"] is None
        assert view["stockRemaining"] == 24


def test_deal_generation_retries_until_solver_accepts(monkeypatch) -> None:
    game = load_engine()
    checks = iter([False, False, True])
    checked_deals: list[tuple[list[object], list[object]]] = []

    def fake_solver(pyramid, stock):
        checked_deals.append((pyramid, stock))
        return next(checks)

    monkeypatch.setattr(game, "_is_solvable_deal", fake_solver)

    state = game.initial_state()

    assert len(checked_deals) == 3
    assert state.pyramid == checked_deals[-1][0]
    assert state.stock == checked_deals[-1][1]


def test_solver_rejects_a_known_unsolvable_deal() -> None:
    game = load_engine()
    card_type = type(next(card for card in game.initial_state().pyramid if card is not None))
    deck = [
        card_type(id=f"{suit}-{rank}", suit=suit, rank=rank)
        for suit in ("spades", "hearts", "diamonds", "clubs")
        for rank in range(1, 14)
    ]
    by_rank = {
        rank: [card for card in deck if card.rank == rank]
        for rank in range(1, 14)
    }
    blocked_bottom = by_rank[1] + by_rank[2][:3]
    buried_complements = by_rank[11] + by_rank[12]
    used_ids = {card.id for card in blocked_bottom + buried_complements}
    remaining = [card for card in deck if card.id not in used_ids]
    pyramid = buried_complements + remaining[:13] + blocked_bottom
    stock = list(reversed(remaining[13:]))

    assert len(pyramid) == 28
    assert len(stock) == 24
    assert game._is_solvable_deal(pyramid, stock) is False


def test_only_exposed_cards_can_pair_and_removing_coverers_exposes_parent() -> None:
    now = [10.0]
    game = load_engine()
    room, player = make_room(game, now)
    make_card = card_factory(room.state)
    parent = make_card("parent-5", 5)
    six = make_card("child-6", 6, "clubs")
    seven = make_card("child-7", 7, "hearts")
    spare = make_card("stock-2", 2, "diamonds")
    room.state.pyramid = [None] * 28
    room.state.pyramid[0] = parent
    room.state.pyramid[1] = six
    room.state.pyramid[2] = seven
    room.state.stock = [spare]

    with pytest.raises(GameRuleError, match="没有被压住"):
        game.act(room, player, "remove", {"cardIds": [parent.id]})

    game.act(room, player, "remove", {"cardIds": [six.id, seven.id]})

    assert room.state.pyramid[1:3] == [None, None]
    assert room.state.removal_moves == 1
    assert room.state.cards_removed == 2
    parent_view = game.view(room, player)["pyramid"][0]
    assert parent_view["exposed"] is True


def test_draws_waste_card_pairs_to_win_and_records_server_time() -> None:
    now = [30.0]
    game = load_engine()
    room, player = make_room(game, now)
    make_card = card_factory(room.state)
    four = make_card("pyramid-4", 4, "clubs")
    nine = make_card("stock-9", 9, "diamonds")
    room.state.pyramid = [None] * 28
    room.state.pyramid[21] = four
    room.state.stock = [nine]
    room.state.waste = []

    now[0] += 1.2
    game.act(room, player, "draw", {})
    assert room.phase == "playing"
    assert game.view(room, player)["wasteTop"]["id"] == nine.id

    now[0] += 0.8
    game.act(room, player, "remove", {"cardIds": [four.id, nine.id]})

    assert room.phase == "finished"
    assert room.winner == "completed"
    assert room.winner_player_ids == [player.id]
    assert room.state.elapsed_ms == 2_000
    assert game.player_score(room, player) == 2_000
    assert game.view(room, player)["pyramidCleared"] == 28
    assert game.record_state(room) == {
        "pyramid_cleared": 28,
        "removal_moves": 1,
        "draws": 1,
        "cards_removed": 2,
        "elapsed_ms": 2_000,
        "result": "completed",
    }


def test_king_can_be_removed_by_itself() -> None:
    now = [5.0]
    game = load_engine()
    room, player = make_room(game, now)
    make_card = card_factory(room.state)
    king = make_card("pyramid-king", 13, "hearts")
    room.state.pyramid = [None] * 28
    room.state.pyramid[21] = king
    room.state.stock = []

    now[0] += 0.5
    game.act(room, player, "remove", {"cardIds": [king.id]})

    assert room.phase == "finished"
    assert room.state.cards_removed == 1
    assert room.state.elapsed_ms == 500


def test_invalid_sum_does_not_change_cards() -> None:
    now = [5.0]
    game = load_engine()
    room, player = make_room(game, now)
    make_card = card_factory(room.state)
    five = make_card("five", 5)
    seven = make_card("seven", 7)
    room.state.pyramid = [None] * 28
    room.state.pyramid[21] = five
    room.state.pyramid[22] = seven
    room.state.stock = [make_card("spare", 2)]

    with pytest.raises(GameRuleError, match="合计必须为 13"):
        game.act(room, player, "remove", {"cardIds": [five.id, seven.id]})

    assert room.state.pyramid[21] == five
    assert room.state.pyramid[22] == seven
    assert room.state.removal_moves == 0


def test_exhausted_stock_without_a_pair_finishes_as_failure() -> None:
    now = [8.0]
    game = load_engine()
    room, player = make_room(game, now)
    make_card = card_factory(room.state)
    five = make_card("five", 5, "clubs")
    two = make_card("two", 2, "diamonds")
    room.state.pyramid = [None] * 28
    room.state.pyramid[21] = five
    room.state.stock = [two]
    room.state.waste = []

    now[0] += 1.0
    game.act(room, player, "draw", {})

    assert room.phase == "finished"
    assert room.winner == "failed"
    assert room.winner_player_ids == []
    assert "没有可用组合" in (room.win_reason or "")
    assert game.player_score(room, player) is None


def test_only_top_waste_card_is_available() -> None:
    now = [15.0]
    game = load_engine()
    room, player = make_room(game, now)
    make_card = card_factory(room.state)
    four = make_card("four", 4)
    hidden_nine = make_card("hidden-nine", 9, "hearts")
    top_eight = make_card("top-eight", 8, "clubs")
    room.state.pyramid = [None] * 28
    room.state.pyramid[21] = four
    room.state.stock = [make_card("spare", 2)]
    room.state.waste = [hidden_nine, top_eight]

    view = game.view(room, player)
    assert view["wasteTop"]["id"] == top_eight.id
    assert hidden_nine.id not in view["availableCardIds"]
    with pytest.raises(GameRuleError, match="弃牌堆顶牌"):
        game.act(
            room,
            player,
            "remove",
            {"cardIds": [four.id, hidden_nine.id]},
        )


def test_reset_redeals_and_restarts_the_timer() -> None:
    now = [20.0]
    game = load_engine()
    room, player = make_room(game, now)
    original_state = room.state
    game.act(room, player, "draw", {})
    now[0] += 4.0

    game.act(room, player, "reset", {})

    assert room.phase == "playing"
    assert room.state is not original_state
    assert len(room.state.pyramid) == 28
    assert len(room.state.stock) == 24
    assert room.state.waste == []
    assert room.state.draws == 0
    assert room.state.elapsed_ms == 0
