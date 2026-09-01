from __future__ import annotations

import copy
import importlib
import json
import random
import pickle
from collections import Counter
from pathlib import Path

import pytest

from backend.app.arcade.models import ArcadeSpectator
from backend.app.arcade.rooms import ArcadeRoomError, ArcadeRoomManager
from backend.app.arcade.views import build_room_view, build_spectator_room_view
from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError


ROOT = Path(__file__).resolve().parents[2]
CATALOG = json.loads((ROOT / "plugin-blokus/pieces.json").read_text(encoding="utf-8"))
SHAPES = {
    item["id"]: {(x, y) for y, row in enumerate(item["rows"]) for x, value in enumerate(row) if value == "#"}
    for item in CATALOG
}
DUO_STARTS = ((4, 4), (9, 9))
FOUR_STARTS = ((0, 0), (19, 0), (19, 19), (0, 19))


class IdentityRng:
    def shuffle(self, values):
        return None


@pytest.fixture(scope="module")
def factory():
    from backend.app.games.registry import game_registration

    engine = game_registration("plugin-blokus").create_engine()
    return type(engine)


@pytest.fixture
def match(factory):
    engine = factory(rng=IdentityRng())
    players = [ArcadePlayer(f"p{i}", f"a{i}", f"玩家{i + 1}", "test-token", i) for i in range(4)]
    room = ArcadeRoom("BLOK", engine.key, players[0].id, players, engine.initial_state())
    engine.start(room)
    return engine, room, players


@pytest.fixture
def duo_match(factory):
    engine = factory(rng=IdentityRng())
    players = [ArcadePlayer(f"d{i}", f"da{i}", f"双人玩家{i + 1}", "test-token", i) for i in range(2)]
    room = ArcadeRoom("DUO", engine.key, players[0].id, players, engine.initial_state())
    engine.start(room)
    return engine, room, players


def place(engine, room, player, piece="M1", x=0, y=0, rotation=0, flipped=False, **extra):
    payload = {"pieceId": piece, "x": x, "y": y, "rotation": rotation, "flipped": flipped, "turnNumber": room.state.turn_number}
    payload.update(extra)
    engine.act(room, player, "place", payload)


def open_starts(engine, room, players):
    for player, (x, y) in zip(players, room.state.start_points, strict=True):
        place(engine, room, player, x=x, y=y)


def variants(shape):
    result = set()
    for swap in (False, True):
        for sx in (-1, 1):
            for sy in (-1, 1):
                cells = [(sx * (y if swap else x), sy * (x if swap else y)) for x, y in shape]
                left, top = min(x for x, _ in cells), min(y for _, y in cells)
                result.add(tuple(sorted((x - left, y - top) for x, y in cells)))
    return result


def canonical(shape):
    return min(variants(shape))


def test_inventory_is_the_complete_set_of_free_polyominoes():
    # Independently grow all connected polyominoes; this catches omitted or mirrored duplicates.
    generated = {((0, 0),)}
    all_shapes = set(generated)
    for _ in range(2, 6):
        expanded = set()
        for shape in generated:
            for x, y in shape:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if (x + dx, y + dy) not in shape:
                        expanded.add(canonical((*shape, (x + dx, y + dy))))
        generated = expanded
        all_shapes.update(generated)
    assert {canonical(shape) for shape in SHAPES.values()} == all_shapes
    assert Counter(map(len, SHAPES.values())) == {1: 1, 2: 1, 3: 2, 4: 5, 5: 12}
    assert len(SHAPES) == 21
    assert sum(map(len, SHAPES.values())) == 89


def test_four_identical_hands_and_distinct_clockwise_starts(match):
    engine, room, players = match
    view = engine.view(room, players[0])
    assert len(view["board"]) == 20 and all(len(row) == 20 for row in view["board"])
    assert view["mode"] == "classic"
    assert [tuple(player["start"]) for player in view["players"]] == list(FOUR_STARTS)
    assert [player["color"] for player in view["players"]] == ["blue", "yellow", "red", "green"]
    assert all(player["remainingSquares"] == 89 and len(player["remainingPieces"]) == 21 for player in view["players"])
    assert view["rankPoints"] == [2, 1, 0, -1]
    open_starts(engine, room, players)
    assert [room.state.board[y][x] for x, y in FOUR_STARTS] == [0, 1, 2, 3]
    assert room.state.current_player_id == players[0].id


def test_duo_uses_official_14_by_14_center_starts_and_two_scores(duo_match):
    engine, room, players = duo_match
    view = engine.view(room, players[0])
    assert view["mode"] == "duo"
    assert len(view["board"]) == 14 and all(len(row) == 14 for row in view["board"])
    assert [tuple(player["start"]) for player in view["players"]] == list(DUO_STARTS)
    assert [player["color"] for player in view["players"]] == ["blue", "yellow"]
    assert view["rankPoints"] == [2, 1]
    open_starts(engine, room, players)
    assert [room.state.board[y][x] for x, y in DUO_STARTS] == [0, 1]
    assert room.state.current_player_id == players[0].id


@pytest.mark.parametrize("count", (1, 3, 5))
def test_requires_exactly_two_or_four_players(factory, count):
    engine = factory(rng=IdentityRng())
    players = [ArcadePlayer(str(i), str(i), str(i), "t", i) for i in range(count)]
    room = ArcadeRoom("BLOK", engine.key, players[0].id, players, engine.initial_state())
    with pytest.raises(GameRuleError, match="2 位或 4 位"):
        engine.start(room)


@pytest.mark.parametrize("player_count", (2, 4))
def test_every_game_uses_a_fresh_random_order(factory, player_count):
    seed = 20260831 + player_count
    engine = factory(rng=random.Random(seed))
    expected_rng = random.Random(seed)
    players = [ArcadePlayer(f"p{i}", f"a{i}", f"玩家{i + 1}", "t", i) for i in range(player_count)]
    room = ArcadeRoom("BLOK", engine.key, players[0].id, players, engine.initial_state())
    seat_order = [player.id for player in players]
    observed = []
    for _ in range(5):
        expected = list(seat_order)
        expected_rng.shuffle(expected)
        engine.start(room)
        observed.append(tuple(room.state.player_ids))
        assert room.state.player_ids == expected
        assert room.state.current_player_id == expected[0]
    assert len(set(observed)) > 1


def test_every_rotation_and_reflection_matches_independent_geometry(match):
    engine, _, _ = match
    pieces_module = importlib.import_module(type(engine).__module__.rsplit(".", 1)[0] + ".pieces")
    for piece_id, shape in SHAPES.items():
        actual = {tuple(sorted(cells)) for _, _, cells in pieces_module.orientations(piece_id)}
        assert actual == variants(shape)
    assert sum(len(pieces_module.orientations(key)) for key in SHAPES) == 91


@pytest.mark.parametrize("fixture_name", ("duo_match", "match"))
def test_first_piece_must_cover_that_players_start(request, fixture_name):
    engine, room, players = request.getfixturevalue(fixture_name)
    for index, player in enumerate(players):
        engine.start(room)
        room.state.current_player_id = player.id
        with pytest.raises(GameRuleError, match="起始点"):
            place(engine, room, player, x=room.state.board_size // 2, y=0)
        for other, (x, y) in enumerate(room.state.start_points):
            if other != index:
                with pytest.raises(GameRuleError, match="起始点"):
                    place(engine, room, player, x=x, y=y)
        x, y = room.state.start_points[index]
        place(engine, room, player, x=x, y=y)


@pytest.mark.parametrize("fixture_name", ("duo_match", "match"))
def test_all_shapes_can_open_from_each_start_under_some_transform(request, fixture_name):
    engine, room, players = request.getfixturevalue(fixture_name)
    starts = list(room.state.start_points)
    board_size = room.state.board_size
    for index, player in enumerate(players):
        for key in SHAPES:
            engine.start(room)
            room.state.current_player_id = player.id
            # Keep all 21 pieces but put the candidate first within its area group.
            module = importlib.import_module(type(engine).__module__.rsplit(".", 1)[0] + ".pieces")
            possibilities = []
            for rotation, flipped, cells in module.orientations(key):
                for sx, sy in cells:
                    x, y = starts[index][0] - sx, starts[index][1] - sy
                    if all(0 <= x + cx < board_size and 0 <= y + cy < board_size for cx, cy in cells):
                        possibilities.append((x, y, rotation, flipped))
            # The cross cannot cover a classic corner of its bounding box.
            if not possibilities:
                assert fixture_name == "match" and key == "X5"
                continue
            x, y, rotation, flipped = possibilities[0]
            place(engine, room, player, key, x, y, rotation, flipped)
            assert room.state.board[starts[index][1]][starts[index][0]] == index


def test_same_color_corner_only_and_foreign_color_edges_allowed(match):
    engine, room, players = match
    open_starts(engine, room, players)
    with pytest.raises(GameRuleError, match="不能边接"):
        place(engine, room, players[0], "D2", 1, 0)
    with pytest.raises(GameRuleError, match="角接"):
        place(engine, room, players[0], "D2", 8, 8)
    room.state.board[1][3] = 1
    place(engine, room, players[0], "D2", 1, 1)
    assert room.state.board[1][2] == 0 and room.state.board[1][3] == 1


def test_overlap_out_of_bounds_and_reusing_a_piece_are_rejected(match):
    engine, room, players = match
    open_starts(engine, room, players)
    before = copy.deepcopy(room.state)
    with pytest.raises(GameRuleError, match="重叠"):
        place(engine, room, players[0], "D2", 0, 0)
    with pytest.raises(GameRuleError, match="超出"):
        place(engine, room, players[0], "I5", 19, 19)
    with pytest.raises(GameRuleError, match="已经使用"):
        place(engine, room, players[0], "M1", 1, 1)
    assert room.state == before


@pytest.mark.parametrize("field,value", [
    ("x", True), ("x", 0.5), ("x", "0"), ("x", -1), ("x", 20),
    ("y", None), ("y", 20), ("rotation", True), ("rotation", 4),
    ("rotation", -1), ("rotation", "1"), ("flipped", 1), ("flipped", None),
    ("pieceId", []), ("pieceId", "fake"), ("turnNumber", True), ("turnNumber", 0),
])
def test_rejects_malformed_inputs_without_mutating_state(match, field, value):
    engine, room, players = match
    payload = {"pieceId": "M1", "x": 0, "y": 0, "rotation": 0, "flipped": False, "turnNumber": 1, field: value}
    before = copy.deepcopy(room.state)
    with pytest.raises(GameRuleError):
        engine.act(room, players[0], "place", payload)
    assert room.state == before


def test_rejects_out_of_turn_spectator_stale_turn_and_voluntary_pass(match):
    engine, room, players = match
    with pytest.raises(GameRuleError, match="还没有轮到"):
        place(engine, room, players[1], x=19, y=0)
    outsider = ArcadePlayer("outsider", "outside", "旁观者", "t", 4)
    with pytest.raises(GameRuleError, match="本局玩家"):
        place(engine, room, outsider)
    with pytest.raises(GameRuleError, match="自动跳过"):
        engine.act(room, players[0], "pass", {})
    open_starts(engine, room, players)
    with pytest.raises(GameRuleError, match="棋盘已更新"):
        place(engine, room, players[0], "D2", 1, 1, turnNumber=1)


def test_blocked_corner_is_automatically_skipped_and_other_players_continue(match):
    engine, room, players = match
    room.state.board[0][19] = 0
    place(engine, room, players[0])
    assert room.state.current_player_id == players[2].id
    assert room.state.blocked_ids == [players[1].id]
    assert room.phase == "playing"
    assert "自动跳过" in room.state.events[0]


def independent_legal(board, color, cells, first, start):
    size = len(board)
    if any(not (0 <= x < size and 0 <= y < size) or board[y][x] != -1 for x, y in cells):
        return False
    if first:
        return start in cells
    old = {(x, y) for y, row in enumerate(board) for x, value in enumerate(row) if value == color}
    edge = any(abs(x - ox) + abs(y - oy) == 1 for x, y in cells for ox, oy in old)
    corner = any(abs(x - ox) == 1 and abs(y - oy) == 1 for x, y in cells for ox, oy in old)
    return corner and not edge


@pytest.mark.parametrize("fixture_name", ("duo_match", "match"))
@pytest.mark.parametrize("seed", (13, 57))
def test_complete_games_obey_all_rules_and_finish_with_exact_rank_points(
    request, fixture_name, seed,
):
    engine, room, players = request.getfixturevalue(fixture_name)
    player_count = len(players)
    expected_points = [2, 1, 0, -1][:player_count]
    rng = random.Random(seed)
    for hand in room.state.remaining.values():
        rng.shuffle(hand)
    while room.phase == "playing":
        state = room.state
        assert len(state.moves) < 21 * player_count
        player_id = state.current_player_id
        color = state.player_ids.index(player_id)
        hand = state.remaining[player_id]
        move = engine.find_move(room, player_id)
        assert move is not None
        before = copy.deepcopy(state.board)
        first = len(hand) == 21
        engine.act(room, room.player(player_id), "place", move)
        cells = [tuple(cell) for cell in state.moves[-1]["cells"]]
        assert independent_legal(
            before, color, cells, first, tuple(state.start_points[color]),
        )
        assert canonical(cells) == canonical(SHAPES[move["pieceId"]])
        assert sum(value != -1 for row in state.board for value in row) == sum(len(move["cells"]) for move in state.moves)
    assert len(room.state.rankings) == player_count
    assert len(set(room.state.rankings)) == player_count
    assert [
        engine.player_score(room, room.player(pid))
        for pid in room.state.rankings
    ] == expected_points
    assert room.winner_player_ids == room.state.rankings[:1]
    assert (
        sum(len(move["cells"]) for move in room.state.moves)
        + sum(
            len(SHAPES[key])
            for hand in room.state.remaining.values()
            for key in hand
        )
    ) == 89 * player_count
    for color, player_id in enumerate(room.state.player_ids):
        # Brute-force oracle deliberately does not use the engine's anchor search.
        for key in room.state.remaining[player_id]:
            for shape in variants(SHAPES[key]):
                for y in range(room.state.board_size):
                    for x in range(room.state.board_size):
                        cells = [(x + sx, y + sy) for sx, sy in shape]
                        assert not independent_legal(
                            room.state.board, color, cells, False,
                            tuple(room.state.start_points[color]),
                        )
    with pytest.raises(GameRuleError, match="已经结束"):
        place(engine, room, players[0])


@pytest.mark.parametrize("fixture_name", ("duo_match", "match"))
def test_ranking_uses_the_mode_specific_tiebreak(
    request, fixture_name,
):
    engine, room, players = request.getfixturevalue(fixture_name)
    hands = (
        (["I3"], ["D2"])
        if len(players) == 2
        else (["I3"], ["M1", "D2"], ["I4"], ["D2"])
    )
    # Classic players 0 and 1 both retain 3 squares. Player 1 ranks higher
    # despite retaining more pieces because their opening position was later.
    expected_indices = (1, 0) if len(players) == 2 else (3, 1, 0, 2)
    room.state.remaining = {
        players[i].id: hand for i, hand in enumerate(hands)
    }
    engine._finish(room)
    assert room.state.rankings == [players[i].id for i in expected_indices]
    if len(players) == 4:
        assert room.state.scores[players[1].id] > room.state.scores[players[0].id]
    assert sorted(room.state.scores.values(), reverse=True) == [2, 1, 0, -1][
        :len(players)
    ]
    engine.start(room)
    for player in players:
        room.state.remaining[player.id] = []
    engine._finish(room)
    assert room.state.rankings == [player.id for player in reversed(players)]


def test_duo_first_forfeit_finishes_with_two_player_points(duo_match):
    engine, room, players = duo_match
    place(engine, room, players[0], x=4, y=4)
    before = copy.deepcopy(room.state.board)
    assert engine.manual_forfeit(room, players[0]) is True
    assert room.phase == "finished"
    assert room.state.board == before
    assert room.state.rankings == [players[1].id, players[0].id]
    assert [engine.player_score(room, player) for player in players] == [1, 2]


def test_forfeits_preserve_tiles_and_rank_earlier_departures_last(match):
    engine, room, players = match
    place(engine, room, players[0])
    before = copy.deepcopy(room.state.board)
    engine.manual_forfeit(room, players[0])
    assert room.state.current_player_id == players[1].id
    assert room.phase == "playing"
    assert engine.manual_forfeit(room, players[0]) is False
    with pytest.raises(GameRuleError, match="弃权"):
        place(engine, room, players[0])
    engine.disconnect_timeout(room, players[1])
    assert room.state.current_player_id == players[2].id
    engine.act(room, players[2], "resign", {})
    assert room.phase == "finished"
    assert room.state.board == before
    assert room.state.rankings == [player.id for player in reversed(players)]
    assert [engine.player_score(room, player) for player in players] == [-1, 0, 1, 2]


def test_view_is_public_detached_and_reconnection_keeps_hand_and_turn(match):
    engine, room, players = match
    place(engine, room, players[0])
    before = copy.deepcopy(room.state)
    players[1].connected = False
    players[1].connected = True
    view = engine.view(room, players[1])
    assert view["isMyTurn"] is True
    assert len(view["players"][1]["remainingPieces"]) == 21
    view["board"][0][0] = -1
    view["players"][0]["remainingPieces"].clear()
    view["lastMove"]["cells"].clear()
    assert room.state == before
    assert engine.player_score(room, players[0]) is None
    assert "token" not in json.dumps(engine.view(room, players[1]))


def test_registered_room_flow_reconnect_spectators_and_full_game(factory):
    engine = factory()
    manager = ArcadeRoomManager({engine.key: engine})
    room, host, host_token = manager.create_room(
        engine.key, "甲", "test-account-0", {},
    )
    with pytest.raises(ArcadeRoomError, match="2–4 名"):
        manager.start(room, host.id)
    manager.join_room(room.code, engine.key, "乙", "test-account-1")
    assert build_room_view(room, host, engine)["actions"]["canStart"] is True
    manager.join_room(room.code, engine.key, "丙", "test-account-2")
    assert build_room_view(room, host, engine)["actions"]["canStart"] is False
    manager.join_room(room.code, engine.key, "丁", "test-account-3")
    assert build_room_view(room, host, engine)["actions"]["canStart"] is True
    with pytest.raises(ArcadeRoomError, match="满员"):
        manager.join_room(room.code, engine.key, "第五位", "test-account-4")
    manager.start(room, host.id)
    assert room.game_id and room.started_at and room.round_number == 1
    for _ in range(4):
        player_id = room.state.current_player_id
        manager.act(room, player_id, "place", engine.find_move(room, player_id))
    before = copy.deepcopy(room.state)
    host.connected = False
    with pytest.raises(ArcadeRoomError, match="其他账号"):
        manager.resume(room.code, host_token, "someone-else")
    resumed_room, resumed_player = manager.resume(room.code, host_token, host.account_id)
    assert resumed_room is room and resumed_player.id == host.id and host.connected
    assert room.state == before
    restored = pickle.loads(pickle.dumps(room))
    assert restored.state == room.state
    current = restored.player(restored.state.current_player_id)
    assert engine.view(restored, current)["isMyTurn"] is True
    spectator = ArcadeSpectator("watcher", "test-observer", "观众", host.id)
    view = build_spectator_room_view(room, host, spectator, engine)
    assert not any(view["actions"].values())
    assert view["viewer"]["mode"] == "spectator"
    assert "accountId" not in view["self"]
    while room.phase == "playing":
        player_id = room.state.current_player_id
        manager.act(room, player_id, "place", engine.find_move(room, player_id))
    result = build_room_view(room, host, engine)
    assert sorted(player["points"] for player in result["game"]["players"]) == [-1, 0, 1, 2]
    assert result["phase"] == "finished"
    assert room.ended_at


@pytest.mark.parametrize("player_count", (2, 4))
@pytest.mark.parametrize("seed", (0, 5))
def test_rematches_preserve_seats_and_randomize_order_each_round(
    factory, player_count, seed,
):
    engine = factory(rng=random.Random(seed))
    expected_rng = random.Random(seed)
    manager = ArcadeRoomManager({engine.key: engine})
    room, host, _ = manager.create_room(engine.key, "甲", "a0", {})
    for index in range(1, player_count):
        manager.join_room(room.code, engine.key, f"玩家{index}", f"a{index}")
    manager.start(room, host.id)
    seat_order = [
        player.id for player in sorted(room.players, key=lambda player: player.seat)
    ]
    observed_orders = []
    for round_number in range(1, 7):
        expected_order = list(seat_order)
        expected_rng.shuffle(expected_order)
        observed_orders.append(tuple(room.state.player_ids))
        assert room.round_number == round_number
        assert room.state.player_ids == expected_order
        assert room.state.current_player_id == expected_order[0]
        assert all(len(hand) == 21 for hand in room.state.remaining.values())
        for color, player_id in enumerate(expected_order):
            x, y = room.state.start_points[color]
            manager.act(room, player_id, "place", {
                "pieceId": "M1", "x": x, "y": y, "rotation": 0,
                "flipped": False, "turnNumber": room.state.turn_number,
            })
            assert room.state.board[y][x] == color
        for player_id in expected_order[:player_count - 1]:
            manager.act(room, player_id, "resign", {})
        assert room.phase == "finished"
        assert [player.seat for player in room.players] == list(range(player_count))
        if round_number < 6:
            for player in list(room.players)[:-1]:
                manager.restart(room, player.id)
                assert room.phase == "finished"
            manager.restart(room, room.players[-1].id)
    assert len(set(observed_orders)) > 1


def test_platform_abandon_transfers_host_and_uses_placement_points(factory):
    engine = factory()
    manager = ArcadeRoomManager({engine.key: engine})
    room, host, _ = manager.create_room(engine.key, "甲", "a0", {})
    for index in range(1, 4):
        manager.join_room(room.code, engine.key, f"玩家{index}", f"a{index}")
    manager.start(room, host.id)
    current_player_id = room.state.current_player_id
    manager.act(
        room, current_player_id, "place",
        engine.find_move(room, current_player_id),
    )
    before = copy.deepcopy(room.state.board)
    assert manager.abandon(room, host.id) is True
    assert room.host_id == room.players[1].id and host.left_room
    assert room.phase == "playing"
    manager.abandon(room, room.players[1].id)
    manager.abandon(room, room.players[2].id)
    assert room.phase == "finished"
    assert room.state.board == before
    assert [engine.player_score(room, player) for player in room.players] == [-1, 0, 1, 2]
