from __future__ import annotations

import copy
import random
from typing import Any

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError

from .maps import MAP_BY_KEY, MAP_SPECS, build_board, map_catalog, spawn_positions, spiral_collapse_order
from .state import (
    BOARD_SIZE,
    CELL_FLOOR,
    CELL_HARD,
    CELL_SOFT,
    CELL_STONE,
    BombPeopleState,
    BombState,
    EventState,
    FlameState,
    ItemState,
    PlayerState,
    SessionRecord,
)


TICK_RATE = 20
SNAPSHOT_RATE = 10
COUNTDOWN_TICKS = 3 * TICK_RATE
ROUND_TICKS = 90 * TICK_RATE
BOMB_FUSE_TICKS = 2 * TICK_RATE
FLAME_TICKS = 7
SHIELD_GRACE_TICKS = TICK_RATE
CURSE_TICKS = 5 * TICK_RATE
GHOST_TICKS = 5 * TICK_RATE
STAR_TICKS = 5 * TICK_RATE
ICE_TICKS = 3 * TICK_RATE
ITEM_REFRESH_TICKS = 10 * TICK_RATE
ITEM_REFRESH_CHANCE = 0.24
CRATE_DROP_CHANCE = 0.38
COLLAPSE_INTERVAL_TICKS = 3

INPUT_UP = 1
INPUT_DOWN = 2
INPUT_LEFT = 4
INPUT_RIGHT = 8
INPUT_BOMB = 16
INPUT_PUNCH = 32
INPUT_THROW = 64
VALID_INPUT_MASK = (
    INPUT_UP
    | INPUT_DOWN
    | INPUT_LEFT
    | INPUT_RIGHT
    | INPUT_BOMB
    | INPUT_PUNCH
    | INPUT_THROW
)

PLAYER_COLORS = (
    "#ff5a55",
    "#4f8cff",
    "#ffd44f",
    "#50c878",
    "#ff914d",
    "#45d6dd",
    "#a970ff",
    "#d7b25b",
)

ITEM_LABELS = {
    "bomb_up": "多一个炸弹",
    "flame_up": "火焰增强",
    "speed": "加速靴",
    "kick": "脚踢雷",
    "punch": "拳击手套",
    "throw": "扔雷手套",
    "timer": "定时炸弹",
    "chain": "连锁引线",
    "shield": "能量护盾",
    "skull": "骷髅诅咒",
    "ghost": "幽灵相位",
    "magnet": "磁力线圈",
    "ice": "冰冻核心",
    "swap": "传送交换",
    "star": "无敌星盾",
}

ITEM_WEIGHTS = {
    "bomb_up": 18,
    "flame_up": 18,
    "speed": 15,
    "kick": 8,
    "punch": 8,
    "throw": 7,
    "timer": 7,
    "chain": 4,
    "shield": 5,
    "skull": 6,
    "ghost": 3,
    "magnet": 3,
    "ice": 3,
    "swap": 1,
    "star": 1,
}


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _inside(x: int, y: int) -> bool:
    return 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE


class BombPeopleEngine:
    key = "plugin-bomb-people"
    name = "炸弹超人"
    min_players = 2
    max_players = 8
    public_rooms = True
    realtime_tick_rate = TICK_RATE
    realtime_snapshot_rate = SNAPSHOT_RATE
    action_phases = frozenset({"lobby", "playing", "finished"})

    def __init__(
        self,
        rng: random.Random | random.SystemRandom | None = None,
    ) -> None:
        self.rng = rng or random.SystemRandom()

    def initial_state(self) -> BombPeopleState:
        return BombPeopleState(selected_map=MAP_SPECS[0].key)

    def start(self, room: ArcadeRoom) -> None:
        active_players = sorted(
            (player for player in room.players if not player.left_room),
            key=lambda player: (player.seat, player.id),
        )
        if not self.min_players <= len(active_players) <= self.max_players:
            raise GameRuleError("炸弹超人需要 2–8 名玩家")

        previous = room.state if isinstance(room.state, BombPeopleState) else None
        selected_map = (
            previous.selected_map
            if previous is not None and previous.selected_map in MAP_BY_KEY
            else MAP_SPECS[0].key
        )
        session_records = (
            copy.deepcopy(previous.session_records)
            if previous is not None
            else {}
        )
        for player in active_players:
            session_records.setdefault(player.id, SessionRecord())

        spec = MAP_BY_KEY[selected_map]
        positions = spawn_positions(len(active_players), spec.spawn_mode)
        variant = self.rng.randrange(1_000_000)
        state = BombPeopleState(
            tick=0,
            stage="countdown",
            stage_ticks_remaining=COUNTDOWN_TICKS,
            round_ticks_remaining=ROUND_TICKS,
            selected_map=selected_map,
            board=build_board(spec, positions, variant),
            collapse_order=spiral_collapse_order(),
            next_item_refresh_tick=COUNTDOWN_TICKS + ITEM_REFRESH_TICKS,
            session_records=session_records,
            map_variant=variant,
        )
        for player, (x, y) in zip(active_players, positions, strict=True):
            actor = PlayerState(player.id, player.seat, x, y)
            state.players[player.id] = actor
            for item in spec.starting_items:
                self._grant_item(state, actor, item, room=None, announce=False)

        room.state = state
        room.phase = "playing"
        self._add_event(
            state,
            "match_ready",
            message=f"{spec.name}：3 秒后开战",
        )
        if spec.starting_items:
            labels = "、".join(ITEM_LABELS[item] for item in spec.starting_items)
            self._add_event(
                state,
                "starting_loadout",
                message=f"本图初始装备：{labels}",
            )

    def act(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        action: str,
        payload: dict[str, Any],
    ) -> None:
        if action == "propose_map":
            self._propose_map(room, player, payload)
            return
        if action == "vote_map":
            self._vote_map(room, player, payload)
            return
        if action == "resign":
            self.manual_forfeit(room, player)
            return
        if room.phase != "playing":
            raise GameRuleError("当前对局还没有开始")
        if action == "heartbeat":
            sequence = payload.get("sequence", 0)
            if not _is_int(sequence) or sequence < 0:
                raise GameRuleError("时钟同步序号不正确")
            return
        if action != "input":
            raise GameRuleError("不支持这个炸弹超人操作")
        self.apply_input(
            room,
            player,
            payload.get("sequence"),
            payload.get("inputMask"),
        )

    def apply_input(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        sequence: Any,
        input_mask: Any,
    ) -> bool:
        if room.phase != "playing":
            raise GameRuleError("当前对局不接收移动输入")
        if not _is_int(sequence) or not 0 <= sequence <= 2_147_483_647:
            raise GameRuleError("输入序号不正确")
        if (
            not _is_int(input_mask)
            or input_mask < 0
            or input_mask & ~VALID_INPUT_MASK
        ):
            raise GameRuleError("移动输入不正确")
        state: BombPeopleState = room.state
        actor = state.players.get(player.id)
        if actor is None or player.left_room:
            raise GameRuleError("你已经不在当前对局中")
        if sequence <= actor.last_input_sequence:
            return False

        pressed = input_mask & ~actor.input_mask
        actor.last_input_sequence = sequence
        actor.input_mask = input_mask
        if pressed & INPUT_BOMB:
            actor.bomb_requested = True
        if pressed & INPUT_PUNCH:
            actor.punch_requested = True
        if pressed & INPUT_THROW:
            actor.throw_requested = True
        for bit, direction in (
            (INPUT_UP, (0, -1)),
            (INPUT_DOWN, (0, 1)),
            (INPUT_LEFT, (-1, 0)),
            (INPUT_RIGHT, (1, 0)),
        ):
            if pressed & bit:
                actor.facing_x, actor.facing_y = direction
        return True

    def tick(self, room: ArcadeRoom) -> bool:
        if room.phase != "playing":
            return False
        state: BombPeopleState = room.state
        room_players = {
            player.id: player
            for player in room.players
            if not player.left_room and player.id in state.players
        }
        if not room_players:
            return False
        if not any(player.connected for player in room_players.values()):
            changed = not state.frozen
            state.frozen = True
            return changed
        state.frozen = False
        state.tick += 1
        self._expire_fields(state)

        if state.stage == "countdown":
            self._clear_requests(state)
            state.stage_ticks_remaining = max(0, state.stage_ticks_remaining - 1)
            if state.stage_ticks_remaining == 0:
                state.stage = "active"
                state.stage_ticks_remaining = state.round_ticks_remaining
                self._add_event(state, "round_started", message="开战！90 秒后开始落石")
            return True

        self._advance_statuses(state)
        self._handle_requested_actions(room, state)
        self._move_players(room, state)
        self._advance_bombs(room, state)
        self._apply_persistent_hazards(room, state)
        self._collect_items(room, state)
        self._refresh_random_item(state)

        if room.phase == "finished":
            return True
        if state.stage == "active":
            state.round_ticks_remaining = max(0, state.round_ticks_remaining - 1)
            state.stage_ticks_remaining = state.round_ticks_remaining
            if state.round_ticks_remaining == 0:
                state.stage = "collapse"
                state.stage_ticks_remaining = 0
                state.collapse_cooldown = 0
                self._add_event(
                    state,
                    "collapse_started",
                    message="决胜落石开始：从左上沿边缘逐圈封场",
                )
        elif state.stage == "collapse":
            self._advance_collapse(room, state)

        self._check_finish(room, state)
        return True

    @staticmethod
    def _clear_requests(state: BombPeopleState) -> None:
        for actor in state.players.values():
            actor.bomb_requested = False
            actor.punch_requested = False
            actor.throw_requested = False

    @staticmethod
    def _advance_statuses(state: BombPeopleState) -> None:
        for actor in state.players.values():
            if not actor.alive:
                continue
            actor.cursed_ticks = max(0, actor.cursed_ticks - 1)
            actor.ghost_ticks = max(0, actor.ghost_ticks - 1)
            actor.invincible_ticks = max(0, actor.invincible_ticks - 1)

    @staticmethod
    def _expire_fields(state: BombPeopleState) -> None:
        state.flames = {
            cell: flame
            for cell, flame in state.flames.items()
            if flame.expires_tick > state.tick
        }
        state.ice_tiles = {
            cell: expires
            for cell, expires in state.ice_tiles.items()
            if expires > state.tick
        }

    def _handle_requested_actions(
        self,
        room: ArcadeRoom,
        state: BombPeopleState,
    ) -> None:
        for actor in sorted(state.players.values(), key=lambda item: (item.seat, item.player_id)):
            bomb_requested = actor.bomb_requested
            punch_requested = actor.punch_requested
            throw_requested = actor.throw_requested
            actor.bomb_requested = False
            actor.punch_requested = False
            actor.throw_requested = False
            if not actor.alive:
                continue
            if bomb_requested:
                self._place_or_trigger_bomb(room, state, actor)
            if punch_requested and actor.can_punch:
                self._punch_bomb(state, actor)
            if throw_requested and actor.can_throw:
                self._throw_bomb(state, actor)

    def _place_or_trigger_bomb(
        self,
        room: ArcadeRoom,
        state: BombPeopleState,
        actor: PlayerState,
    ) -> None:
        if actor.cursed_ticks > 0:
            return
        owned = sorted(
            (bomb for bomb in state.bombs.values() if bomb.owner_id == actor.player_id),
            key=lambda bomb: (bomb.placed_tick, bomb.bomb_id),
        )
        if len(owned) >= actor.bomb_capacity:
            if actor.can_timer and owned:
                target = owned[0]
                target.fuse_ticks = min(target.fuse_ticks, 1)
                self._add_event(
                    state,
                    "timer_triggered",
                    actor_id=actor.player_id,
                    message=f"{self._name(room, actor.player_id)}提前引爆定时炸弹",
                )
            return
        if self._bomb_at(state, actor.x, actor.y) is not None:
            return
        bomb = BombState(
            bomb_id=state.next_bomb_id,
            owner_id=actor.player_id,
            credit_player_id=actor.player_id,
            x=actor.x,
            y=actor.y,
            placed_tick=state.tick,
            fuse_ticks=BOMB_FUSE_TICKS,
            blast_range=actor.blast_range,
            chain=actor.can_chain,
            ice=actor.has_ice,
        )
        state.next_bomb_id += 1
        state.bombs[bomb.bomb_id] = bomb

    def _punch_bomb(self, state: BombPeopleState, actor: PlayerState) -> None:
        bomb = self._bomb_at(
            state,
            actor.x + actor.facing_x,
            actor.y + actor.facing_y,
        )
        if bomb is None:
            return
        bomb.credit_player_id = actor.player_id
        bomb.motion_dx = actor.facing_x
        bomb.motion_dy = actor.facing_y
        bomb.travel_left = 3
        bomb.motion_delay = 0
        self._move_bomb_once(state, bomb)

    def _throw_bomb(self, state: BombPeopleState, actor: PlayerState) -> None:
        bomb = self._bomb_at(
            state,
            actor.x + actor.facing_x,
            actor.y + actor.facing_y,
        )
        if bomb is None:
            return
        for distance in range(4, 0, -1):
            x = actor.x + actor.facing_x * distance
            y = actor.y + actor.facing_y * distance
            if self._bomb_destination_open(state, x, y, ignored_bomb=bomb.bomb_id):
                bomb.x = x
                bomb.y = y
                bomb.credit_player_id = actor.player_id
                self._stop_bomb(bomb)
                return

    def _move_players(self, room: ArcadeRoom, state: BombPeopleState) -> None:
        for actor in sorted(state.players.values(), key=lambda item: (item.seat, item.player_id)):
            if not actor.alive:
                continue
            if actor.move_cooldown > 0:
                actor.move_cooldown -= 1
                continue
            direction = self._movement_direction(actor)
            if direction == (0, 0):
                continue
            dx, dy = direction
            actor.facing_x, actor.facing_y = dx, dy
            target_x, target_y = actor.x + dx, actor.y + dy
            if not _inside(target_x, target_y):
                continue
            cell = state.board[target_y][target_x]
            if cell in {CELL_HARD, CELL_STONE}:
                continue
            if cell == CELL_SOFT and actor.ghost_ticks <= 0:
                continue

            bomb = self._bomb_at(state, target_x, target_y)
            if bomb is not None:
                if not actor.can_kick or not self._kick_bomb(state, bomb, actor, dx, dy):
                    continue
            if any(
                other.alive
                and other.player_id != actor.player_id
                and (other.x, other.y) == (target_x, target_y)
                for other in state.players.values()
            ):
                continue
            actor.x, actor.y = target_x, target_y
            interval = max(2, 5 - actor.speed_level)
            if (actor.x, actor.y) in state.ice_tiles:
                interval += 2
            actor.move_cooldown = interval - 1
            self._collect_at(room, state, actor, actor.x, actor.y)

    @staticmethod
    def _movement_direction(actor: PlayerState) -> tuple[int, int]:
        horizontal = int(bool(actor.input_mask & INPUT_RIGHT)) - int(bool(actor.input_mask & INPUT_LEFT))
        vertical = int(bool(actor.input_mask & INPUT_DOWN)) - int(bool(actor.input_mask & INPUT_UP))
        if horizontal and vertical:
            if actor.facing_x == horizontal:
                return horizontal, 0
            if actor.facing_y == vertical:
                return 0, vertical
            return horizontal, 0
        return horizontal, vertical

    def _kick_bomb(
        self,
        state: BombPeopleState,
        bomb: BombState,
        actor: PlayerState,
        dx: int,
        dy: int,
    ) -> bool:
        bomb.motion_dx = dx
        bomb.motion_dy = dy
        bomb.motion_delay = 0
        bomb.travel_left = -1
        bomb.credit_player_id = actor.player_id
        return self._move_bomb_once(state, bomb)

    def _advance_bombs(self, room: ArcadeRoom, state: BombPeopleState) -> None:
        for bomb in sorted(state.bombs.values(), key=lambda item: item.bomb_id):
            if bomb.motion_dx or bomb.motion_dy:
                if bomb.motion_delay > 0:
                    bomb.motion_delay -= 1
                else:
                    self._move_bomb_once(state, bomb)
            if state.tick > bomb.placed_tick:
                bomb.fuse_ticks -= 1
            if (bomb.x, bomb.y) in state.flames:
                bomb.fuse_ticks = 0
        self._explode_due_bombs(room, state)

    def _move_bomb_once(self, state: BombPeopleState, bomb: BombState) -> bool:
        x = bomb.x + bomb.motion_dx
        y = bomb.y + bomb.motion_dy
        if not self._bomb_destination_open(state, x, y, ignored_bomb=bomb.bomb_id):
            self._stop_bomb(bomb)
            return False
        bomb.x, bomb.y = x, y
        bomb.motion_delay = 1
        if bomb.travel_left > 0:
            bomb.travel_left -= 1
            if bomb.travel_left == 0:
                self._stop_bomb(bomb)
        return True

    @staticmethod
    def _stop_bomb(bomb: BombState) -> None:
        bomb.motion_dx = 0
        bomb.motion_dy = 0
        bomb.motion_delay = 0
        bomb.travel_left = -1

    @staticmethod
    def _bomb_at(state: BombPeopleState, x: int, y: int) -> BombState | None:
        return next(
            (bomb for bomb in state.bombs.values() if (bomb.x, bomb.y) == (x, y)),
            None,
        )

    @staticmethod
    def _bomb_destination_open(
        state: BombPeopleState,
        x: int,
        y: int,
        *,
        ignored_bomb: int | None = None,
    ) -> bool:
        if not _inside(x, y) or state.board[y][x] != CELL_FLOOR:
            return False
        if any(
            bomb.bomb_id != ignored_bomb and (bomb.x, bomb.y) == (x, y)
            for bomb in state.bombs.values()
        ):
            return False
        return not any(
            actor.alive and (actor.x, actor.y) == (x, y)
            for actor in state.players.values()
        )

    def _explode_due_bombs(self, room: ArcadeRoom, state: BombPeopleState) -> None:
        processed: set[int] = set()
        while True:
            due = next(
                (
                    bomb for bomb in sorted(state.bombs.values(), key=lambda item: item.bomb_id)
                    if bomb.fuse_ticks <= 0 and bomb.bomb_id not in processed
                ),
                None,
            )
            if due is None:
                break
            processed.add(due.bomb_id)
            self._explode_bomb(room, state, due)

    def _explode_bomb(
        self,
        room: ArcadeRoom,
        state: BombPeopleState,
        bomb: BombState,
    ) -> None:
        if state.bombs.pop(bomb.bomb_id, None) is None:
            return
        blast_cells: list[tuple[int, int]] = [(bomb.x, bomb.y)]
        destroyed_crates: list[tuple[int, int]] = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for distance in range(1, bomb.blast_range + 1):
                x, y = bomb.x + dx * distance, bomb.y + dy * distance
                if not _inside(x, y):
                    break
                cell = state.board[y][x]
                if cell in {CELL_HARD, CELL_STONE}:
                    break
                blast_cells.append((x, y))
                if cell == CELL_SOFT:
                    state.board[y][x] = CELL_FLOOR
                    destroyed_crates.append((x, y))
                    break

        blast_set = set(blast_cells)
        for cell in blast_cells:
            state.flames[cell] = FlameState(
                cell[0], cell[1], bomb.credit_player_id, state.tick + FLAME_TICKS
            )
            if bomb.ice:
                state.ice_tiles[cell] = state.tick + FLAME_TICKS + ICE_TICKS
        for other in state.bombs.values():
            if (other.x, other.y) in blast_set:
                other.fuse_ticks = 0
        if bomb.chain:
            for other in state.bombs.values():
                if other.owner_id == bomb.owner_id:
                    other.fuse_ticks = 0
        for x, y in destroyed_crates:
            self._maybe_drop_item(state, x, y, "crate")
        for actor in state.players.values():
            if actor.alive and (actor.x, actor.y) in blast_set:
                self._hit_player(
                    room,
                    state,
                    actor,
                    bomb.credit_player_id,
                    "blast",
                )

    def _apply_persistent_hazards(
        self,
        room: ArcadeRoom,
        state: BombPeopleState,
    ) -> None:
        for actor in state.players.values():
            flame = state.flames.get((actor.x, actor.y))
            if actor.alive and flame is not None:
                self._hit_player(
                    room,
                    state,
                    actor,
                    flame.credit_player_id,
                    "blast",
                )

    def _hit_player(
        self,
        room: ArcadeRoom,
        state: BombPeopleState,
        actor: PlayerState,
        credit_player_id: str | None,
        reason: str,
    ) -> None:
        if not actor.alive or actor.invincible_ticks > 0:
            return
        if actor.shield_charges > 0 and reason == "blast":
            actor.shield_charges -= 1
            actor.invincible_ticks = SHIELD_GRACE_TICKS
            self._add_event(
                state,
                "shield_blocked",
                actor_id=actor.player_id,
                message=f"{self._name(room, actor.player_id)}的护盾挡住一次爆炸",
            )
            return
        actor.alive = False
        actor.input_mask = 0
        actor.eliminated_tick = state.tick
        actor.eliminated_by = credit_player_id
        actor.elimination_reason = reason
        actor.bomb_requested = actor.punch_requested = actor.throw_requested = False

        if (
            credit_player_id is not None
            and credit_player_id != actor.player_id
            and credit_player_id in state.players
        ):
            killer = state.players[credit_player_id]
            killer.kills += 1
            state.session_records.setdefault(credit_player_id, SessionRecord()).kills += 1
            message = (
                f"{self._name(room, credit_player_id)}淘汰了"
                f"{self._name(room, actor.player_id)}"
            )
        elif reason == "stone":
            message = f"{self._name(room, actor.player_id)}被落石压中"
        else:
            message = f"{self._name(room, actor.player_id)}被自己的爆炸淘汰"
        self._add_event(
            state,
            "player_eliminated",
            actor_id=credit_player_id,
            target_id=actor.player_id,
            message=message,
        )

    def _collect_items(self, room: ArcadeRoom, state: BombPeopleState) -> None:
        for actor in sorted(state.players.values(), key=lambda item: (item.seat, item.player_id)):
            if not actor.alive:
                continue
            self._collect_at(room, state, actor, actor.x, actor.y)
            if actor.has_magnet:
                nearby = sorted(
                    (
                        item for item in state.items.values()
                        if abs(item.x - actor.x) + abs(item.y - actor.y) <= 2
                    ),
                    key=lambda item: (
                        abs(item.x - actor.x) + abs(item.y - actor.y),
                        item.item_id,
                    ),
                )
                if nearby:
                    self._collect_item(room, state, actor, nearby[0])

    def _collect_at(
        self,
        room: ArcadeRoom,
        state: BombPeopleState,
        actor: PlayerState,
        x: int,
        y: int,
    ) -> None:
        item = next(
            (item for item in state.items.values() if (item.x, item.y) == (x, y)),
            None,
        )
        if item is not None:
            self._collect_item(room, state, actor, item)

    def _collect_item(
        self,
        room: ArcadeRoom,
        state: BombPeopleState,
        actor: PlayerState,
        item: ItemState,
    ) -> None:
        if state.items.pop(item.item_id, None) is None:
            return
        self._grant_item(state, actor, item.kind, room=room, announce=True)

    def _grant_item(
        self,
        state: BombPeopleState,
        actor: PlayerState,
        kind: str,
        *,
        room: ArcadeRoom | None,
        announce: bool,
    ) -> None:
        if kind == "bomb_up":
            actor.bomb_capacity = min(6, actor.bomb_capacity + 1)
        elif kind == "flame_up":
            actor.blast_range = min(8, actor.blast_range + 1)
        elif kind == "speed":
            actor.speed_level = min(3, actor.speed_level + 1)
        elif kind == "kick":
            actor.can_kick = True
        elif kind == "punch":
            actor.can_punch = True
        elif kind == "throw":
            actor.can_throw = True
        elif kind == "timer":
            actor.can_timer = True
        elif kind == "chain":
            actor.can_chain = True
        elif kind == "shield":
            actor.shield_charges = min(2, actor.shield_charges + 1)
        elif kind == "ghost":
            actor.ghost_ticks = max(actor.ghost_ticks, GHOST_TICKS)
        elif kind == "magnet":
            actor.has_magnet = True
        elif kind == "ice":
            actor.has_ice = True
        elif kind == "star":
            actor.invincible_ticks = max(actor.invincible_ticks, STAR_TICKS)
        elif kind == "swap":
            self._swap_with_opponent(state, actor)
        elif kind == "skull":
            self._apply_skull(actor)
        else:
            return

        if announce and room is not None:
            self._add_event(
                state,
                "item_collected",
                actor_id=actor.player_id,
                item=kind,
                message=(
                    f"{self._name(room, actor.player_id)}拾取了{ITEM_LABELS[kind]}"
                    + ("：5 秒不能放炸弹" if kind == "skull" else "")
                ),
            )

    @staticmethod
    def _apply_skull(actor: PlayerState) -> None:
        actor.bomb_capacity = 1
        actor.blast_range = 2
        actor.speed_level = 0
        actor.can_kick = False
        actor.can_punch = False
        actor.can_throw = False
        actor.can_timer = False
        actor.can_chain = False
        actor.has_magnet = False
        actor.has_ice = False
        actor.shield_charges = 0
        actor.ghost_ticks = 0
        actor.invincible_ticks = 0
        actor.cursed_ticks = CURSE_TICKS

    def _swap_with_opponent(self, state: BombPeopleState, actor: PlayerState) -> None:
        candidates = [
            other for other in state.players.values()
            if other.alive and other.player_id != actor.player_id
        ]
        if not candidates:
            return
        other = self.rng.choice(candidates)
        actor.x, other.x = other.x, actor.x
        actor.y, other.y = other.y, actor.y

    def _maybe_drop_item(
        self,
        state: BombPeopleState,
        x: int,
        y: int,
        source: str,
    ) -> None:
        if self.rng.random() >= CRATE_DROP_CHANCE:
            return
        kind = self.rng.choices(
            list(ITEM_WEIGHTS),
            weights=list(ITEM_WEIGHTS.values()),
            k=1,
        )[0]
        self._spawn_item(state, kind, x, y, source)

    def _spawn_item(
        self,
        state: BombPeopleState,
        kind: str,
        x: int,
        y: int,
        source: str,
    ) -> None:
        if any((item.x, item.y) == (x, y) for item in state.items.values()):
            return
        item = ItemState(state.next_item_id, kind, x, y, source)
        state.next_item_id += 1
        state.items[item.item_id] = item

    def _refresh_random_item(self, state: BombPeopleState) -> None:
        if state.tick < state.next_item_refresh_tick:
            return
        state.next_item_refresh_tick += ITEM_REFRESH_TICKS
        if self.rng.random() >= ITEM_REFRESH_CHANCE:
            return
        occupied = {
            (bomb.x, bomb.y) for bomb in state.bombs.values()
        } | {
            (item.x, item.y) for item in state.items.values()
        } | {
            (actor.x, actor.y) for actor in state.players.values() if actor.alive
        } | set(state.flames)
        candidates = [
            (x, y)
            for y, row in enumerate(state.board)
            for x, cell in enumerate(row)
            if cell == CELL_FLOOR and (x, y) not in occupied
        ]
        if not candidates:
            return
        x, y = self.rng.choice(candidates)
        kind = self.rng.choices(
            list(ITEM_WEIGHTS),
            weights=list(ITEM_WEIGHTS.values()),
            k=1,
        )[0]
        self._spawn_item(state, kind, x, y, "ambient")

    def _advance_collapse(self, room: ArcadeRoom, state: BombPeopleState) -> None:
        if state.collapse_index >= len(state.collapse_order):
            return
        if state.collapse_cooldown > 0:
            state.collapse_cooldown -= 1
            return
        state.collapse_cooldown = COLLAPSE_INTERVAL_TICKS - 1
        x, y = state.collapse_order[state.collapse_index]
        state.collapse_index += 1

        for bomb in state.bombs.values():
            if (bomb.x, bomb.y) == (x, y):
                bomb.fuse_ticks = 0
        self._explode_due_bombs(room, state)
        for actor in state.players.values():
            if actor.alive and (actor.x, actor.y) == (x, y):
                self._hit_player(room, state, actor, None, "stone")
        for item_id, item in list(state.items.items()):
            if (item.x, item.y) == (x, y):
                state.items.pop(item_id, None)
        state.flames.pop((x, y), None)
        state.ice_tiles.pop((x, y), None)
        state.board[y][x] = CELL_STONE

    def _check_finish(self, room: ArcadeRoom, state: BombPeopleState) -> None:
        if room.phase != "playing":
            return
        alive = [actor for actor in state.players.values() if actor.alive]
        if len(alive) > 1:
            return
        if alive:
            winner = alive[0]
            state.match_winner_id = winner.player_id
            reason = f"{self._name(room, winner.player_id)}成为最后生还者"
            winner_ids = [winner.player_id]
            winner_kind = "last_standing"
        else:
            reason = "所有玩家同时阵亡，本局平局"
            winner_ids = []
            winner_kind = "draw"
        self._settle_session(state, winner_ids)
        state.stage = "finished"
        state.stage_ticks_remaining = 0
        room.finish(winner_kind, winner_ids, reason)

    @staticmethod
    def _settle_session(state: BombPeopleState, winner_ids: list[str]) -> None:
        if state.settled:
            return
        state.settled = True
        for player_id in state.players:
            record = state.session_records.setdefault(player_id, SessionRecord())
            record.matches += 1
        for player_id in winner_ids:
            state.session_records.setdefault(player_id, SessionRecord()).championships += 1

    def manual_forfeit(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        if room.phase != "playing":
            return False
        state: BombPeopleState = room.state
        actor = state.players.get(player.id)
        if actor is None or not actor.alive:
            return False
        actor.alive = False
        actor.input_mask = 0
        actor.eliminated_tick = state.tick
        actor.elimination_reason = "forfeit"
        self._add_event(
            state,
            "player_forfeited",
            target_id=player.id,
            message=f"{player.name}退出了本局",
        )
        self._check_finish(room, state)
        return True

    def disconnect_timeout(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        return self.manual_forfeit(room, player)

    def _propose_map(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        if room.phase not in {"lobby", "finished"}:
            raise GameRuleError("只能在开局前或本局结束后协商地图")
        if player.id != room.host_id:
            raise GameRuleError("只有房主可以发起地图切换")
        map_key = payload.get("mapKey")
        if not isinstance(map_key, str) or map_key not in MAP_BY_KEY:
            raise GameRuleError("请选择有效地图")
        state: BombPeopleState = room.state
        state.proposed_map = map_key
        state.proposed_by = player.id
        state.map_approvals = {player.id}
        self._add_event(
            state,
            "map_proposed",
            actor_id=player.id,
            message=f"房主提议切换到{MAP_BY_KEY[map_key].name}",
        )
        self._commit_map_if_approved(room, state)

    def _vote_map(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        if room.phase not in {"lobby", "finished"}:
            raise GameRuleError("当前不能参与地图协商")
        state: BombPeopleState = room.state
        if state.proposed_map is None:
            raise GameRuleError("当前没有待确认的地图")
        accept = payload.get("accept")
        if not isinstance(accept, bool):
            raise GameRuleError("地图投票格式不正确")
        if not accept:
            self._add_event(
                state,
                "map_rejected",
                actor_id=player.id,
                message=f"{player.name}不同意本次地图切换",
            )
            state.proposed_map = None
            state.proposed_by = None
            state.map_approvals.clear()
            return
        state.map_approvals.add(player.id)
        self._commit_map_if_approved(room, state)

    def _commit_map_if_approved(
        self,
        room: ArcadeRoom,
        state: BombPeopleState,
    ) -> bool:
        required = {
            player.id for player in room.players if not player.left_room
        }
        if state.proposed_map is None or not required <= state.map_approvals:
            return False
        selected = state.proposed_map
        state.selected_map = selected
        state.proposed_map = None
        state.proposed_by = None
        state.map_approvals.clear()
        self._add_event(
            state,
            "map_changed",
            message=f"全员同意，地图已切换为{MAP_BY_KEY[selected].name}",
        )
        return True

    def view(self, room: ArcadeRoom, viewer: ArcadePlayer) -> dict[str, Any]:
        state: BombPeopleState = room.state
        names = {player.id: player.name for player in room.players}
        map_spec = MAP_BY_KEY.get(state.selected_map, MAP_SPECS[0])
        clock_leader = next(
            (
                player.id
                for player in sorted(room.players, key=lambda item: (item.seat, item.id))
                if player.connected and not player.left_room and player.id in state.players
            ),
            None,
        )
        required_ids = [
            player.id for player in room.players if not player.left_room
        ]
        return {
            "boardSize": BOARD_SIZE,
            "tick": state.tick,
            "tickRate": TICK_RATE,
            "stage": state.stage,
            "stageTicksRemaining": state.stage_ticks_remaining,
            "roundTicksRemaining": state.round_ticks_remaining,
            "collapsePlaced": state.collapse_index,
            "collapseTotal": len(state.collapse_order),
            "dangerCells": [
                [x, y]
                for x, y in state.collapse_order[
                    state.collapse_index:state.collapse_index + 5
                ]
            ] if state.stage == "collapse" else [],
            "selectedMap": state.selected_map,
            "currentMap": {
                "key": map_spec.key,
                "name": map_spec.name,
                "subtitle": map_spec.subtitle,
                "pace": map_spec.pace,
                "density": map_spec.density,
                "spawnMode": map_spec.spawn_mode,
                "startingItems": list(map_spec.starting_items),
            },
            "mapCatalog": map_catalog(),
            "mapProposal": (
                {
                    "mapKey": state.proposed_map,
                    "proposedBy": state.proposed_by,
                    "approvedPlayerIds": sorted(state.map_approvals),
                    "requiredPlayerIds": required_ids,
                    "approvalCount": len(state.map_approvals),
                    "requiredCount": len(required_ids),
                }
                if state.proposed_map is not None
                else None
            ),
            "canProposeMap": (
                viewer.id == room.host_id and room.phase in {"lobby", "finished"}
            ),
            "canVoteMap": (
                room.phase in {"lobby", "finished"}
                and state.proposed_map is not None
                and viewer.id not in state.map_approvals
            ),
            "board": [row[:] for row in state.board],
            "players": [
                self._player_view(state, actor, names.get(actor.player_id, "玩家"))
                for actor in sorted(state.players.values(), key=lambda item: (item.seat, item.player_id))
            ],
            "bombs": [
                {
                    "id": bomb.bomb_id,
                    "ownerId": bomb.owner_id,
                    "creditPlayerId": bomb.credit_player_id,
                    "x": bomb.x,
                    "y": bomb.y,
                    "fuseTicks": max(0, bomb.fuse_ticks),
                    "maxFuseTicks": BOMB_FUSE_TICKS,
                    "moving": bool(bomb.motion_dx or bomb.motion_dy),
                }
                for bomb in sorted(state.bombs.values(), key=lambda item: item.bomb_id)
            ],
            "items": [
                {"id": item.item_id, "kind": item.kind, "x": item.x, "y": item.y}
                for item in sorted(state.items.values(), key=lambda item: item.item_id)
            ],
            "flames": [
                {
                    "x": flame.x,
                    "y": flame.y,
                    "remainingTicks": max(0, flame.expires_tick - state.tick),
                }
                for flame in state.flames.values()
            ],
            "iceTiles": [
                {"x": x, "y": y, "remainingTicks": max(0, expires - state.tick)}
                for (x, y), expires in state.ice_tiles.items()
            ],
            "events": [
                {
                    "id": event.event_id,
                    "tick": event.tick,
                    "kind": event.kind,
                    "actorId": event.actor_id,
                    "targetId": event.target_id,
                    "item": event.item,
                    "message": event.message,
                }
                for event in state.events[-14:]
            ],
            "winnerId": state.match_winner_id,
            "clockLeaderId": clock_leader,
            "frozen": state.frozen,
            "selfInputSequence": state.players.get(
                viewer.id,
                PlayerState(viewer.id, viewer.seat, 0, 0),
            ).last_input_sequence,
            "controls": {
                "move": "WASD",
                "bomb": "Space",
                "punch": "Z",
                "throw": "X",
                "kick": "automatic",
            },
            "itemLabels": dict(ITEM_LABELS),
        }

    @staticmethod
    def _player_view(
        state: BombPeopleState,
        actor: PlayerState,
        name: str,
    ) -> dict[str, Any]:
        record = state.session_records.get(actor.player_id, SessionRecord())
        win_rate = (
            round(record.championships * 100 / record.matches, 1)
            if record.matches
            else 0
        )
        return {
            "id": actor.player_id,
            "name": name,
            "seat": actor.seat,
            "color": PLAYER_COLORS[actor.seat % len(PLAYER_COLORS)],
            "character": actor.seat % len(PLAYER_COLORS),
            "x": actor.x,
            "y": actor.y,
            "facingX": actor.facing_x,
            "facingY": actor.facing_y,
            "alive": actor.alive,
            "eliminatedBy": actor.eliminated_by,
            "eliminationReason": actor.elimination_reason,
            "kills": actor.kills,
            "stats": {
                "kills": record.kills,
                "championships": record.championships,
                "matches": record.matches,
                "winRate": win_rate,
            },
            "equipment": {
                "bombCapacity": actor.bomb_capacity,
                "blastRange": actor.blast_range,
                "speedLevel": actor.speed_level,
                "kick": actor.can_kick,
                "punch": actor.can_punch,
                "throw": actor.can_throw,
                "timer": actor.can_timer,
                "chain": actor.can_chain,
                "magnet": actor.has_magnet,
                "ice": actor.has_ice,
                "shieldCharges": actor.shield_charges,
                "ghostTicks": actor.ghost_ticks,
                "invincibleTicks": actor.invincible_ticks,
                "cursedTicks": actor.cursed_ticks,
            },
        }

    def player_result(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
    ) -> tuple[str, str, bool]:
        return (
            f"player_{player.seat + 1}",
            "contender",
            player.id in room.winner_player_ids,
        )

    def record_state(self, room: ArcadeRoom) -> dict[str, Any]:
        state: BombPeopleState = room.state
        return {
            "mapKey": state.selected_map,
            "ticks": state.tick,
            "collapsePlaced": state.collapse_index,
            "winnerId": state.match_winner_id,
            "players": {
                player_id: {
                    "killsThisMatch": actor.kills,
                    "alive": actor.alive,
                    "eliminationReason": actor.elimination_reason,
                    "sessionKills": state.session_records.get(player_id, SessionRecord()).kills,
                    "sessionChampionships": state.session_records.get(player_id, SessionRecord()).championships,
                    "sessionMatches": state.session_records.get(player_id, SessionRecord()).matches,
                }
                for player_id, actor in state.players.items()
            },
        }

    @staticmethod
    def _name(room: ArcadeRoom, player_id: str) -> str:
        try:
            return room.player(player_id).name
        except KeyError:
            return "玩家"

    @staticmethod
    def _add_event(
        state: BombPeopleState,
        kind: str,
        *,
        actor_id: str | None = None,
        target_id: str | None = None,
        item: str | None = None,
        message: str = "",
    ) -> None:
        state.events.append(
            EventState(
                state.next_event_id,
                state.tick,
                kind,
                actor_id,
                target_id,
                item,
                message,
            )
        )
        state.next_event_id += 1
        state.events = state.events[-32:]
