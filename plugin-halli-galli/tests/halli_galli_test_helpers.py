"""Uniquely named helpers so multi-plugin pytest collection cannot alias modules."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import random
from typing import Any

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom
from backend.app.games.plugins import _load_engine_factory


PLUGIN_DIR = Path(__file__).resolve().parents[1]


@dataclass
class TestClock:
    value: int = 1_800_000_000_000

    def __call__(self) -> int:
        return self.value

    def advance(self, milliseconds: int = 400) -> None:
        self.value += milliseconds


def load_engine(seed: int = 7, clock: TestClock | None = None):
    factory = _load_engine_factory(PLUGIN_DIR, "plugin-halli-galli")
    game = factory()
    game.rng = random.Random(seed)
    test_clock = clock or TestClock()
    game.clock_ms = test_clock
    return game, test_clock


def make_room(player_count: int = 4, seed: int = 7):
    game, clock = load_engine(seed)
    names = ["阿梨", "白川", "青禾", "赤岩", "云雀", "墨川"]
    players = [
        ArcadePlayer(
            id=f"p{index + 1}",
            account_id=f"a{index + 1}",
            name=names[index],
            token_hash=f"token-{index + 1}",
            seat=index,
        )
        for index in range(player_count)
    ]
    room = ArcadeRoom(
        code=f"HG{player_count}",
        game_key=game.key,
        host_id=players[0].id,
        players=players,
        state=game.initial_state(),
        options={"firstPlayer": "host", "rulesProfile": "official_last_bell"},
    )
    game.start(room)
    return game, room, players, clock


def dispatch(
    game: Any,
    room: ArcadeRoom,
    player: ArcadePlayer,
    action: str,
    payload: dict[str, Any] | None = None,
    *,
    action_id: str | None = None,
) -> str:
    body = dict(payload or {})
    generated = action_id or f"test-action-{room.revision}-{room.state.event_seq}-{action}"
    body.setdefault("actionId", generated)
    if action == "flip_card":
        body.setdefault("revision", room.revision)
        body.setdefault("expectedBoardEpoch", room.state.board_epoch)
    elif action in {"ring_bell", "settle_no_progress"}:
        body.setdefault("boardEpoch", room.state.board_epoch)
    if action == "ring_bell":
        body.setdefault("inputMethod", "test")
    game.act(room, player, action, body)
    room.revision += 1
    return generated


def flatten_cards(room: ArcadeRoom) -> list[Any]:
    return [
        card
        for player_id in room.state.player_ids
        for card in (
            room.state.players[player_id].draw_pile
            + room.state.players[player_id].discard_pile
        )
    ]


def configure_state(
    game: Any,
    room: ArcadeRoom,
    *,
    discards: dict[str, list[tuple[str, int]]] | None = None,
    fixed_draw_counts: dict[str, int] | None = None,
    draw_tops: dict[str, tuple[str, int]] | None = None,
    statuses: dict[str, str] | None = None,
    remainder_to: str | None = None,
    current_player_id: str | None = None,
    board_epoch: int = 20,
    final_duel_armed: bool | None = None,
) -> None:
    module = __import__(type(game).__module__, fromlist=["ALL_CARDS"])
    pool = list(module.ALL_CARDS)
    discard_specs = discards or {}
    top_specs = draw_tops or {}
    status_map = statuses or {}
    fixed = fixed_draw_counts or {}

    def take(spec: tuple[str, int]):
        fruit_id, fruit_count = spec
        card = next(
            card for card in pool
            if card.fruit_id == fruit_id and card.fruit_count == fruit_count
        )
        pool.remove(card)
        return card

    selected_discards = {
        player_id: [take(spec) for spec in specs]
        for player_id, specs in discard_specs.items()
    }
    selected_tops = {
        player_id: take(spec) for player_id, spec in top_specs.items()
    }
    for player_id in room.state.player_ids:
        domain = room.state.players[player_id]
        domain.draw_pile = []
        domain.discard_pile = selected_discards.get(player_id, [])
        domain.status = status_map.get(player_id, "eligible")
        domain.elimination_reason = None if domain.status == "eligible" else "fixture"

    for player_id, count in fixed.items():
        if count < 0:
            raise ValueError("draw count cannot be negative")
        first = []
        if player_id in selected_tops:
            if count == 0:
                raise ValueError("draw top requires a positive draw count")
            first = [selected_tops[player_id]]
        needed = count - len(first)
        room.state.players[player_id].draw_pile = first + pool[:needed]
        del pool[:needed]

    for player_id, card in selected_tops.items():
        if player_id not in fixed:
            room.state.players[player_id].draw_pile = [card]

    assigned_top_only = set(selected_tops) - set(fixed)
    if pool:
        target = remainder_to or next(
            player_id for player_id in room.state.player_ids
            if player_id not in fixed and player_id not in assigned_top_only
        )
        room.state.players[target].draw_pile.extend(pool)
        pool = []

    state = room.state
    state.stage = "playing"
    state.current_player_id = current_player_id or next(
        (
            player_id for player_id in state.player_ids
            if state.players[player_id].status == "eligible"
            and state.players[player_id].draw_pile
        ),
        None,
    )
    state.turn_number = 12
    state.board_epoch = board_epoch
    state.earliest_next_flip_at_ms = game.clock_ms()
    state.fruit_totals, state.valid_fruit_ids = module.recompute_fruit_totals(state)
    state.final_duel_armed = (
        len(module.eligible_player_ids(state)) == 2
        if final_duel_armed is None
        else final_duel_armed
    )
    state.bell_resolution = None
    state.no_progress_deadline_ms = None
    state.event_seq = 0
    state.events = []
    state.result = None
    state.processed_actions = {}
    state.processed_action_order = []
    room.phase = "playing"
    room.winner = None
    room.winner_player_ids = []
    room.win_reason = None
    game.assert_invariants(room)


def autoplay_game(player_count: int, seed: int, *, wrong_bells: bool = True):
    game, room, players, clock = make_room(player_count, seed)
    players_by_id = {player.id: player for player in players}
    action_mix: Counter[str] = Counter()
    last_wrong_turn = -1
    for step in range(1, 30_001):
        if room.phase == "finished":
            break
        state = room.state
        game.assert_invariants(room)
        eligible = [
            player_id for player_id in state.player_ids
            if state.players[player_id].status == "eligible"
        ]
        if state.valid_fruit_ids:
            actor_id = eligible[(seed + step) % len(eligible)]
            dispatch(game, room, players_by_id[actor_id], "ring_bell")
            action_mix["correct_bell"] += 1
        elif (
            wrong_bells
            and not state.final_duel_armed
            and len(eligible) > 2
            and state.turn_number > 0
            and state.turn_number % 19 == 0
            and last_wrong_turn != state.turn_number
            and not (
                state.bell_resolution
                and state.bell_resolution.get("boardEpoch") == state.board_epoch
            )
        ):
            candidates = [
                player_id for player_id in eligible
                if state.players[player_id].draw_pile
            ]
            if candidates:
                actor_id = min(
                    candidates,
                    key=lambda player_id: len(state.players[player_id].draw_pile),
                )
                dispatch(game, room, players_by_id[actor_id], "ring_bell")
                last_wrong_turn = state.turn_number
                action_mix["wrong_bell"] += 1
            else:
                last_wrong_turn = state.turn_number
        elif state.current_player_id is not None:
            clock.advance(400)
            dispatch(
                game,
                room,
                players_by_id[state.current_player_id],
                "flip_card",
            )
            action_mix["flip"] += 1
        elif state.no_progress_deadline_ms is not None:
            clock.value = state.no_progress_deadline_ms
            dispatch(
                game,
                room,
                players[0],
                "settle_no_progress",
            )
            action_mix["no_progress"] += 1
        else:
            raise AssertionError("simulation reached an unhandled stalled state")
    else:
        raise AssertionError(f"{player_count}-player seed {seed} exceeded action limit")
    game.assert_invariants(room)
    return game, room, players, action_mix, step
