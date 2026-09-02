from __future__ import annotations

import copy
import importlib
import json
import pickle
import random
from collections import Counter, deque
from pathlib import Path

import pytest

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError
from backend.app.games.plugins import _load_engine_factory


PLUGIN_ROOT = Path(__file__).resolve().parents[1]

ARTWORK_SPAWNS = {
    "magma_crucible": (
        (3, 2), (16, 16), (16, 2), (3, 16),
        (10, 2), (10, 16), (2, 9), (17, 9),
    ),
    "frost_fracture": (
        (3, 3), (16, 16), (16, 3), (3, 16),
        (9, 3), (9, 16), (3, 9), (16, 9),
    ),
    "neon_reactor": (
        (3, 2), (17, 17), (16, 2), (2, 17),
        (10, 2), (9, 17), (1, 9), (18, 9),
    ),
    "jungle_ziggurat": (
        (8, 8), (11, 10), (11, 8), (8, 10),
        (9, 8), (10, 10), (10, 8), (9, 10),
    ),
    "sky_citadel": (
        (6, 2), (13, 17), (13, 2), (6, 17),
        (8, 2), (11, 17), (11, 2), (8, 17),
    ),
    "clockwork_foundry": (
        (2, 4), (17, 15), (17, 4), (2, 15),
        (2, 7), (17, 12), (17, 7), (2, 12),
    ),
    "haunted_catacombs": (
        (2, 2), (17, 16), (17, 2), (2, 16),
        (2, 4), (17, 15), (17, 4), (2, 15),
    ),
    "storm_dockyard": (
        (4, 4), (15, 15), (15, 4), (4, 15),
        (6, 5), (13, 13), (13, 5), (6, 13),
    ),
    "crystal_rift": (
        (4, 3), (15, 16), (15, 3), (4, 16),
        (9, 6), (9, 13), (7, 10), (12, 10),
    ),
    "solar_collapse": (
        (4, 4), (15, 14), (12, 6), (5, 14),
        (7, 12), (12, 12), (9, 16), (9, 9),
    ),
}


@pytest.fixture(scope="module")
def loaded():
    factory = _load_engine_factory(PLUGIN_ROOT, "plugin-bomb-people")
    engine = factory()
    package = type(engine).__module__.rsplit(".", 1)[0]
    return type(engine), importlib.import_module(f"{package}.state"), importlib.import_module(f"{package}.maps"), importlib.import_module(f"{package}.engine")


def players(count: int) -> list[ArcadePlayer]:
    return [
        ArcadePlayer(f"p{i}", f"a{i}", f"玩家{i + 1}", "test-token", i)
        for i in range(count)
    ]


def new_room(engine, count: int = 4):
    members = players(count)
    room = ArcadeRoom("BOMB", engine.key, members[0].id, members, engine.initial_state())
    return room, members


def start_active(engine, count: int = 4, map_key: str = "magma_crucible"):
    room, members = new_room(engine, count)
    force_next_map(engine, map_key)
    engine.start(room)
    for _ in range(3 * engine.realtime_tick_rate):
        engine.tick(room)
    assert room.state.stage == "active"
    return room, members


def clear_board(room):
    size = len(room.state.board)
    room.state.board = [[0 for _ in range(size)] for _ in range(size)]


def press(engine, room, player, sequence: int, bit: int):
    engine.apply_input(room, player, sequence, bit)
    engine.tick(room)
    engine.apply_input(room, player, sequence + 1, 0)


def force_next_map(engine, map_key: str):
    engine._choose_round_map = lambda _previous: map_key


def test_manifest_and_engine_contract_match(loaded):
    Engine, _, _, _ = loaded
    manifest = json.loads((PLUGIN_ROOT / "manifest.json").read_text(encoding="utf-8"))
    engine = Engine(random.Random(1))
    assert (engine.key, engine.name) == (manifest["id"], manifest["name"])
    assert (engine.min_players, engine.max_players) == (2, 8)
    assert manifest["roomLayout"] == "immersive"
    assert manifest["records"]["scoreKind"] == "outcome"


def test_all_ten_maps_are_exactly_twenty_by_twenty_and_vary_density(loaded):
    Engine, _, maps_module, _ = loaded
    engine = Engine(random.Random(7))
    counts = []
    for spec in maps_module.MAP_SPECS:
        room, members = new_room(engine, 8)
        force_next_map(engine, spec.key)
        engine.start(room)
        assert len(room.state.board) == 20
        assert all(len(row) == 20 for row in room.state.board)
        assert len(room.state.collapse_order) == 400
        assert len(set(room.state.collapse_order)) == 400
        cell_counts = Counter(cell for row in room.state.board for cell in row)
        assert cell_counts[1] >= 28
        assert cell_counts[2] >= 116
        counts.append((cell_counts[1], cell_counts[2]))
        actors = list(room.state.players.values())
        for actor in actors:
            assert room.state.board[actor.y][actor.x] == 0
        reachable = {(actors[0].x, actors[0].y)}
        queue = deque(reachable)
        while queue:
            x, y = queue.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                cell = (x + dx, y + dy)
                if (
                    0 <= cell[0] < 20 and 0 <= cell[1] < 20
                    and cell not in reachable
                    and room.state.board[cell[1]][cell[0]] != 1
                ):
                    reachable.add(cell)
                    queue.append(cell)
        assert all((actor.x, actor.y) in reachable for actor in actors)
    assert len(maps_module.MAP_SPECS) == 10
    assert len(set(counts)) >= 8
    assert maps_module.spiral_collapse_order()[:5] == [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]


def test_every_map_uses_its_artwork_spawn_markers_for_two_to_eight_players(loaded):
    Engine, _, maps_module, _ = loaded
    engine = Engine(random.Random(17))
    assert set(ARTWORK_SPAWNS) == {spec.key for spec in maps_module.MAP_SPECS}

    for spec in maps_module.MAP_SPECS:
        expected = ARTWORK_SPAWNS[spec.key]
        assert spec.spawn_points == expected
        assert len(expected) == len(set(expected)) == 8
        assert all(0 <= x < 20 and 0 <= y < 20 for x, y in expected)
        for count in range(2, 9):
            room, _ = new_room(engine, count)
            force_next_map(engine, spec.key)
            engine.start(room)
            actual = tuple((actor.x, actor.y) for actor in room.state.players.values())
            assert actual == expected[:count]
            assert all(room.state.board[y][x] == 0 for x, y in actual)


def test_map_specific_starting_loadouts_are_preserved(loaded):
    Engine, _, _, _ = loaded
    engine = Engine(random.Random(17))
    room, _ = new_room(engine, 8)
    force_next_map(engine, "sky_citadel")
    engine.start(room)
    assert all(
        actor.speed_level == 2 and actor.bomb_capacity == 2 and actor.can_kick
        for actor in room.state.players.values()
    )

    room, _ = new_room(engine, 8)
    force_next_map(engine, "clockwork_foundry")
    engine.start(room)
    assert all(
        actor.speed_level == 0 and actor.bomb_capacity == 1
        for actor in room.state.players.values()
    )


@pytest.mark.parametrize("count", (0, 1, 9))
def test_player_count_is_enforced(loaded, count):
    Engine, _, _, _ = loaded
    engine = Engine(random.Random(1))
    members = players(max(1, count))[:count]
    host = members[0].id if members else "missing"
    room = ArcadeRoom("BOMB", engine.key, host, members, engine.initial_state())
    with pytest.raises(GameRuleError, match="2–8"):
        engine.start(room)


@pytest.mark.parametrize(
    ("speed_level", "expected_steps", "expected_interval"),
    (
        (0, 5, 4.0),
        (1, 6, 3.2),
        (2, 8, 2.6),
        (3, 10, 2.0),
    ),
)
def test_movement_starts_faster_and_scales_smoothly_with_speed_items(
    loaded,
    speed_level,
    expected_steps,
    expected_interval,
):
    Engine, _, _, engine_module = loaded
    engine = Engine(random.Random(100 + speed_level))
    room, members = start_active(engine, 2)
    clear_board(room)
    actor = room.state.players[members[0].id]
    opponent = room.state.players[members[1].id]
    actor.x, actor.y = 1, 10
    actor.speed_level = speed_level
    opponent.x, opponent.y = 18, 18
    engine.apply_input(room, members[0], 1, engine_module.INPUT_RIGHT)

    for _ in range(engine_module.TICK_RATE):
        engine.tick(room)

    assert actor.x == 1 + expected_steps
    view = engine.view(room, members[0])
    own = next(player for player in view["players"] if player["id"] == actor.player_id)
    assert own["moveIntervalTicks"] == expected_interval

    room.state.ice_tiles[(actor.x, actor.y)] = room.state.tick + 10
    slowed = engine.view(room, members[0])
    own = next(player for player in slowed["players"] if player["id"] == actor.player_id)
    assert own["moveIntervalTicks"] == expected_interval + 2.0


def test_bombs_have_an_authoritative_two_second_fuse(loaded):
    Engine, _, _, engine_module = loaded
    engine = Engine(random.Random(2))
    room, members = start_active(engine, 2)
    clear_board(room)
    actor = room.state.players[members[0].id]
    actor.x = actor.y = 5
    press(engine, room, members[0], 1, engine_module.INPUT_BOMB)
    assert len(room.state.bombs) == 1
    bomb = next(iter(room.state.bombs.values()))
    assert bomb.fuse_ticks == engine_module.BOMB_FUSE_TICKS
    actor.x, actor.y = 9, 9
    for _ in range(engine_module.BOMB_FUSE_TICKS - 1):
        engine.tick(room)
    assert len(room.state.bombs) == 1
    engine.tick(room)
    assert not room.state.bombs
    assert room.state.flames
    assert any(effect.kind == "bomb_exploded" for effect in room.state.effects)


def test_forfeit_during_countdown_immediately_awards_the_last_survivor(loaded):
    Engine, _, _, _ = loaded
    engine = Engine(random.Random(21))
    room, members = new_room(engine, 2)
    engine.start(room)
    assert room.state.stage == "countdown"
    assert engine.manual_forfeit(room, members[1]) is True
    assert room.phase == "finished"
    assert room.winner_player_ids == [members[0].id]


def test_kick_punch_and_throw_work_on_an_opponents_bomb(loaded):
    Engine, state_module, _, engine_module = loaded
    engine = Engine(random.Random(3))
    room, members = start_active(engine, 3)
    clear_board(room)
    actor = room.state.players[members[0].id]
    actor.x, actor.y = 4, 5
    actor.facing_x, actor.facing_y = 1, 0
    actor.can_kick = actor.can_punch = actor.can_throw = True

    enemy = state_module.BombState(1, members[1].id, members[1].id, 5, 5, room.state.tick, 40, 2)
    room.state.bombs = {1: enemy}
    engine.apply_input(room, members[0], 1, engine_module.INPUT_RIGHT)
    engine.tick(room)
    assert (actor.x, actor.y) == (5, 5)
    assert (enemy.x, enemy.y) == (6, 5)
    assert enemy.credit_player_id == members[0].id

    actor.x, actor.y = 4, 7
    actor.facing_x, actor.facing_y = 1, 0
    enemy.x, enemy.y = 5, 7
    engine.apply_input(room, members[0], 2, engine_module.INPUT_PUNCH)
    engine.tick(room)
    assert enemy.x >= 6 and enemy.credit_player_id == members[0].id
    engine.apply_input(room, members[0], 3, 0)

    actor.x, actor.y = 4, 9
    actor.facing_x, actor.facing_y = 1, 0
    enemy.x, enemy.y = 5, 9
    enemy.motion_dx = enemy.motion_dy = 0
    engine.apply_input(room, members[0], 4, engine_module.INPUT_THROW)
    engine.tick(room)
    assert (enemy.x, enemy.y) == (8, 9)
    assert enemy.owner_id == members[1].id
    assert enemy.credit_player_id == members[0].id
    effect_kinds = {effect.kind for effect in room.state.effects}
    assert {"bomb_kicked", "bomb_punched", "bomb_thrown"} <= effect_kinds

    view = engine.view(room, members[0])
    throw_effect = next(effect for effect in view["effects"] if effect["kind"] == "bomb_thrown")
    assert throw_effect == {
        "id": throw_effect["id"],
        "kind": "bomb_thrown",
        "tick": room.state.tick,
        "remainingTicks": engine_module.ACTION_EFFECT_TICKS,
        "actorId": members[0].id,
        "bombId": enemy.bomb_id,
        "x": 5,
        "y": 9,
        "targetX": 8,
        "targetY": 9,
        "directionX": 1,
        "directionY": 0,
    }


def test_timer_can_trigger_early_but_never_extends_the_two_second_limit(loaded):
    Engine, _, _, engine_module = loaded
    engine = Engine(random.Random(4))
    room, members = start_active(engine, 2)
    clear_board(room)
    actor = room.state.players[members[0].id]
    actor.x = actor.y = 5
    actor.can_timer = True
    press(engine, room, members[0], 1, engine_module.INPUT_BOMB)
    actor.x, actor.y = 10, 10
    press(engine, room, members[0], 3, engine_module.INPUT_BOMB)
    assert not room.state.bombs
    assert room.state.flames


def test_skull_removes_equipment_and_blocks_bombs_for_five_seconds(loaded):
    Engine, state_module, _, engine_module = loaded
    engine = Engine(random.Random(5))
    room, members = start_active(engine, 2)
    clear_board(room)
    actor = room.state.players[members[0].id]
    actor.bomb_capacity = 4
    actor.blast_range = 6
    actor.speed_level = 3
    actor.can_kick = actor.can_punch = actor.can_throw = actor.can_timer = True
    room.state.items[1] = state_module.ItemState(1, "skull", actor.x, actor.y)
    engine.tick(room)
    assert actor.cursed_ticks == engine_module.CURSE_TICKS
    assert (actor.bomb_capacity, actor.blast_range, actor.speed_level) == (1, 2, 0)
    assert not actor.can_kick and not actor.can_punch and not actor.can_throw
    press(engine, room, members[0], 1, engine_module.INPUT_BOMB)
    assert not room.state.bombs
    for _ in range(engine_module.CURSE_TICKS):
        engine.tick(room)
    press(engine, room, members[0], 3, engine_module.INPUT_BOMB)
    assert room.state.bombs


def test_ghost_lasts_five_seconds_crosses_only_soft_walls_and_can_bomb_them(loaded):
    Engine, state_module, _, engine_module = loaded
    engine = Engine(random.Random(51))
    room, members = start_active(engine, 2)
    clear_board(room)
    actor = room.state.players[members[0].id]
    opponent = room.state.players[members[1].id]
    actor.x, actor.y = 5, 5
    opponent.x, opponent.y = 18, 18
    room.state.items[1] = state_module.ItemState(1, "ghost", actor.x, actor.y)
    engine.tick(room)
    assert actor.ghost_ticks == engine_module.GHOST_TICKS

    room.state.board[5][6] = state_module.CELL_SOFT
    room.state.board[5][7] = state_module.CELL_HARD
    room.state.board[6][6] = state_module.CELL_STONE
    press(engine, room, members[0], 1, engine_module.INPUT_RIGHT)
    assert (actor.x, actor.y) == (6, 5)

    actor.move_cooldown = 0
    press(engine, room, members[0], 3, engine_module.INPUT_RIGHT)
    assert (actor.x, actor.y) == (6, 5)

    actor.x, actor.y = 5, 6
    actor.move_cooldown = 0
    press(engine, room, members[0], 5, engine_module.INPUT_RIGHT)
    assert (actor.x, actor.y) == (5, 6)

    actor.x, actor.y = 6, 5
    actor.ghost_ticks = 0
    press(engine, room, members[0], 7, engine_module.INPUT_BOMB)
    assert not room.state.bombs

    engine._grant_item(room.state, actor, "ghost", room=None, announce=False)
    assert actor.ghost_ticks == engine_module.GHOST_TICKS
    press(engine, room, members[0], 9, engine_module.INPUT_BOMB)
    assert len(room.state.bombs) == 1
    assert room.state.board[5][6] == state_module.CELL_SOFT

    actor.x, actor.y = 15, 15
    for _ in range(engine_module.BOMB_FUSE_TICKS):
        engine.tick(room)
    assert not room.state.bombs
    assert room.state.board[5][6] == state_module.CELL_FLOOR
    assert any(effect.kind == "bomb_exploded" for effect in room.state.effects)

    engine._grant_item(room.state, actor, "ghost", room=None, announce=False)
    for _ in range(engine_module.GHOST_TICKS - 1):
        engine.tick(room)
    assert actor.ghost_ticks == 1
    engine.tick(room)
    assert actor.ghost_ticks == 0


def test_items_are_automatically_collected_and_stacks_are_capped(loaded):
    Engine, state_module, _, _ = loaded
    engine = Engine(random.Random(6))
    room, members = start_active(engine, 2)
    clear_board(room)
    actor = room.state.players[members[0].id]
    for index in range(8):
        room.state.items[index + 1] = state_module.ItemState(index + 1, "bomb_up", actor.x, actor.y)
        engine.tick(room)
    assert actor.bomb_capacity == 6
    assert not room.state.items


def test_dropped_items_persist_through_explosions_until_collected(loaded):
    Engine, state_module, _, engine_module = loaded
    engine = Engine(random.Random(61))
    room, members = start_active(engine, 2)
    clear_board(room)
    collector = room.state.players[members[0].id]
    opponent = room.state.players[members[1].id]
    collector.x, collector.y = 15, 15
    opponent.x, opponent.y = 17, 17
    room.state.items[1] = state_module.ItemState(1, "speed", 6, 5)
    room.state.bombs[1] = state_module.BombState(
        1,
        collector.player_id,
        collector.player_id,
        5,
        5,
        room.state.tick,
        1,
        2,
    )

    engine.tick(room)
    assert room.state.items[1].kind == "speed"
    for _ in range(engine_module.FLAME_TICKS + 10):
        engine.tick(room)
    assert room.state.items[1].kind == "speed"

    collector.x, collector.y = 6, 5
    engine.tick(room)
    assert 1 not in room.state.items
    assert collector.speed_level == 1


def test_ninety_seconds_transitions_to_spiral_stones_and_stones_crush(loaded):
    Engine, _, _, _ = loaded
    engine = Engine(random.Random(7))
    room, members = start_active(engine, 2)
    clear_board(room)
    room.state.round_ticks_remaining = 1
    engine.tick(room)
    assert room.state.stage == "collapse"
    victim = room.state.players[members[1].id]
    victim.x, victim.y = 0, 0
    engine.tick(room)
    assert room.state.board[0][0] == 3
    assert not victim.alive
    assert victim.elimination_reason == "stone"
    assert room.phase == "finished"


def test_every_round_randomizes_the_map_without_consecutive_repeats(loaded):
    Engine, _, maps_module, _ = loaded
    engine = Engine(random.Random(8))
    room, members = new_room(engine, 4)
    selected_maps = []
    for round_index in range(20):
        if round_index:
            room.phase = "finished"
            room.state.stage = "finished"
        engine.start(room)
        selected_maps.append(room.state.selected_map)

    assert set(selected_maps) <= {spec.key for spec in maps_module.MAP_SPECS}
    assert all(current != previous for previous, current in zip(selected_maps, selected_maps[1:]))
    view = engine.view(room, members[0])
    assert view["mapRotation"] == "random_no_repeat"
    assert view["mapProposal"] is None
    assert view["canProposeMap"] is False
    assert view["canVoteMap"] is False


def test_manual_map_voting_is_rejected_because_rounds_are_random(loaded):
    Engine, _, _, _ = loaded
    engine = Engine(random.Random(9))
    room, members = new_room(engine, 3)
    with pytest.raises(GameRuleError, match="每局开始时随机切换"):
        engine.act(room, members[0], "propose_map", {"mapKey": "sky_citadel"})
    with pytest.raises(GameRuleError, match="每局开始时随机切换"):
        engine.act(room, members[1], "vote_map", {"accept": True})


def test_kills_championships_and_win_rate_are_recorded(loaded):
    Engine, state_module, _, _ = loaded
    engine = Engine(random.Random(10))
    room, members = start_active(engine, 2)
    clear_board(room)
    winner = room.state.players[members[0].id]
    victim = room.state.players[members[1].id]
    winner.x, winner.y = 10, 10
    victim.x, victim.y = 6, 5
    room.state.bombs[1] = state_module.BombState(
        1, winner.player_id, winner.player_id, 5, 5, room.state.tick - 1, 0, 2
    )
    engine.tick(room)
    assert room.phase == "finished"
    assert winner.kills == 1
    view = engine.view(room, members[0])
    own = next(player for player in view["players"] if player["id"] == winner.player_id)
    assert own["stats"] == {"kills": 1, "championships": 1, "matches": 1, "winRate": 100.0}
    record = engine.record_state(room)
    assert record["players"][winner.player_id]["killsThisMatch"] == 1
    assert engine.player_result(room, members[0])[-1] is True
    assert engine.player_result(room, members[1])[-1] is False


@pytest.mark.parametrize("count", range(2, 9))
def test_complete_explosion_match_and_rematch_for_every_supported_player_count(loaded, count):
    Engine, state_module, _, _ = loaded
    engine = Engine(random.Random(1000 + count))
    room, members = start_active(engine, count)
    clear_board(room)

    winner = room.state.players[members[0].id]
    winner.x, winner.y = 18, 18
    victims = members[1:]
    for offset, member in enumerate(victims, start=1):
        actor = room.state.players[member.id]
        actor.x, actor.y = 5 + offset, 5

    room.state.bombs[1] = state_module.BombState(
        1,
        winner.player_id,
        winner.player_id,
        5,
        5,
        room.state.tick - 1,
        0,
        8,
    )
    engine.tick(room)

    assert room.phase == "finished"
    assert room.state.stage == "finished"
    assert room.winner == "last_standing"
    assert room.winner_player_ids == [winner.player_id]
    assert winner.kills == count - 1
    assert all(not room.state.players[member.id].alive for member in victims)
    assert all(
        room.state.players[member.id].eliminated_by == winner.player_id
        and room.state.players[member.id].elimination_reason == "blast"
        for member in victims
    )
    assert any(effect.kind == "bomb_exploded" for effect in room.state.effects)

    for member in members:
        view = engine.view(room, member)
        own = next(player for player in view["players"] if player["id"] == member.id)
        assert own["stats"]["matches"] == 1
        assert own["stats"]["championships"] == (1 if member.id == winner.player_id else 0)
        assert own["stats"]["kills"] == (count - 1 if member.id == winner.player_id else 0)
        assert engine.player_result(room, member)[-1] is (member.id == winner.player_id)

    records_after_finish = copy.deepcopy(room.state.session_records)
    engine.tick(room)
    assert room.state.session_records == records_after_finish

    engine.start(room)
    assert room.phase == "playing"
    assert room.state.stage == "countdown"
    assert room.state.session_records == records_after_finish
    winner_view = engine.view(room, members[0])
    own = next(player for player in winner_view["players"] if player["id"] == winner.player_id)
    assert own["stats"] == {
        "kills": count - 1,
        "championships": 1,
        "matches": 1,
        "winRate": 100.0,
    }


def test_simultaneous_blast_is_a_draw_and_settles_exactly_once(loaded):
    Engine, state_module, _, _ = loaded
    engine = Engine(random.Random(2002))
    room, members = start_active(engine, 2)
    clear_board(room)
    owner = room.state.players[members[0].id]
    opponent = room.state.players[members[1].id]
    owner.x, owner.y = 5, 5
    opponent.x, opponent.y = 6, 5
    room.state.bombs[1] = state_module.BombState(
        1,
        owner.player_id,
        owner.player_id,
        5,
        5,
        room.state.tick - 1,
        0,
        2,
    )

    engine.tick(room)

    assert room.phase == "finished"
    assert room.winner == "draw"
    assert room.winner_player_ids == []
    assert room.state.match_winner_id is None
    assert all(not actor.alive for actor in room.state.players.values())
    assert all(record.matches == 1 for record in room.state.session_records.values())
    assert all(record.championships == 0 for record in room.state.session_records.values())
    assert all(engine.player_result(room, member)[-1] is False for member in members)

    records_after_finish = copy.deepcopy(room.state.session_records)
    engine.tick(room)
    engine._check_finish(room, room.state)
    assert room.state.session_records == records_after_finish


@pytest.mark.parametrize("count", range(2, 9))
def test_spiral_collapse_can_finish_every_supported_player_count(loaded, count):
    Engine, _, _, engine_module = loaded
    engine = Engine(random.Random(3000 + count))
    room, members = start_active(engine, count)
    clear_board(room)
    room.state.stage = "collapse"
    room.state.collapse_index = 0
    room.state.collapse_cooldown = 0

    for index, member in enumerate(members[:-1]):
        actor = room.state.players[member.id]
        actor.x, actor.y = room.state.collapse_order[index]
    survivor = room.state.players[members[-1].id]
    survivor.x, survivor.y = room.state.collapse_order[-1]

    max_ticks = (count - 1) * engine_module.COLLAPSE_INTERVAL_TICKS + 1
    for _ in range(max_ticks):
        engine.tick(room)
        if room.phase == "finished":
            break

    assert room.phase == "finished"
    assert room.winner_player_ids == [survivor.player_id]
    assert survivor.alive
    assert all(
        not room.state.players[member.id].alive
        and room.state.players[member.id].elimination_reason == "stone"
        for member in members[:-1]
    )


def test_view_is_detached_public_and_state_is_pickle_safe(loaded):
    Engine, _, _, _ = loaded
    engine = Engine(random.Random(11))
    room, members = start_active(engine, 4)
    before = copy.deepcopy(room.state)
    view = engine.view(room, members[0])
    assert len(view["board"]) == 20 and len(view["mapCatalog"]) == 10
    assert view["controls"] == {
        "move": "WASD", "bomb": "Space", "punch": "Z", "throw": "X", "kick": "automatic",
    }
    view["board"][0][0] = 99
    view["players"][0]["equipment"]["bombCapacity"] = 99
    assert room.state == before
    assert "test-token" not in json.dumps(engine.view(room, members[0]), ensure_ascii=False)
    restored = pickle.loads(pickle.dumps(room))
    assert restored.state == room.state
