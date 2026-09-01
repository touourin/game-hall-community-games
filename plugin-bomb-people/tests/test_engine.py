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


def start_active(engine, count: int = 4):
    room, members = new_room(engine, count)
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
        room.state.selected_map = spec.key
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


def test_clash_maps_spawn_close_with_loadouts_while_fortress_maps_spread_out(loaded):
    Engine, _, _, _ = loaded
    engine = Engine(random.Random(17))
    room, _ = new_room(engine, 8)
    room.state.selected_map = "sky_citadel"
    engine.start(room)
    actors = list(room.state.players.values())
    assert max(actor.x for actor in actors) - min(actor.x for actor in actors) <= 7
    assert max(actor.y for actor in actors) - min(actor.y for actor in actors) <= 7
    assert all(actor.speed_level == 2 and actor.bomb_capacity == 2 and actor.can_kick for actor in actors)

    room, _ = new_room(engine, 8)
    room.state.selected_map = "clockwork_foundry"
    engine.start(room)
    actors = list(room.state.players.values())
    assert max(actor.x for actor in actors) - min(actor.x for actor in actors) >= 17
    assert all(actor.speed_level == 0 and actor.bomb_capacity == 1 for actor in actors)


@pytest.mark.parametrize("count", (0, 1, 9))
def test_player_count_is_enforced(loaded, count):
    Engine, _, _, _ = loaded
    engine = Engine(random.Random(1))
    members = players(max(1, count))[:count]
    host = members[0].id if members else "missing"
    room = ArcadeRoom("BOMB", engine.key, host, members, engine.initial_state())
    with pytest.raises(GameRuleError, match="2–8"):
        engine.start(room)


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


def test_host_map_proposal_requires_every_players_consent(loaded):
    Engine, _, maps_module, _ = loaded
    engine = Engine(random.Random(8))
    room, members = new_room(engine, 4)
    target = maps_module.MAP_SPECS[4].key
    with pytest.raises(GameRuleError, match="房主"):
        engine.act(room, members[1], "propose_map", {"mapKey": target})
    engine.act(room, members[0], "propose_map", {"mapKey": target})
    assert room.state.selected_map != target
    assert room.state.map_approvals == {members[0].id}
    for player in members[1:3]:
        engine.act(room, player, "vote_map", {"accept": True})
        assert room.state.selected_map != target
    engine.act(room, members[3], "vote_map", {"accept": True})
    assert room.state.selected_map == target
    assert room.state.proposed_map is None


def test_a_rejection_cancels_the_map_proposal(loaded):
    Engine, _, maps_module, _ = loaded
    engine = Engine(random.Random(9))
    room, members = new_room(engine, 3)
    engine.act(room, members[0], "propose_map", {"mapKey": maps_module.MAP_SPECS[2].key})
    engine.act(room, members[1], "vote_map", {"accept": False})
    assert room.state.proposed_map is None
    assert room.state.map_approvals == set()


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
