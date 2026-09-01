from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any

import pytest

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom
from backend.app.games.plugins import discover_game_plugins


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
ENGINE_FACTORY = next(
    plugin.registration.create_engine
    for plugin in discover_game_plugins(PLUGIN_ROOT)
    if plugin.registration.key == "plugin-skull"
)


def _players(count: int) -> list[ArcadePlayer]:
    return [
        ArcadePlayer(
            id=f"p{index + 1}",
            account_id=f"account-{index + 1}",
            name=f"玩家{index + 1}",
            token_hash=f"token-{index + 1}",
            seat=index,
        )
        for index in range(count)
    ]


def _started_game(
    count: int,
    seed: int,
    *,
    last_chance_enabled: bool,
) -> tuple[Any, ArcadeRoom, list[ArcadePlayer]]:
    engine = ENGINE_FACTORY()
    engine.rng = random.Random(seed)
    players = _players(count)
    room = ArcadeRoom(
        code="SOAK",
        game_key=engine.key,
        host_id=players[0].id,
        players=players,
        state=engine.initial_state(),
        options={
            "firstPlayer": "random",
            "lastChanceEnabled": last_chance_enabled,
        },
    )
    engine.start(room)
    return engine, room, players


def _assert_state_invariants(room: ArcadeRoom) -> None:
    state = room.state
    for player_state in state.players.values():
        personal = [
            disc
            for disc in player_state.hand + player_state.stack + player_state.removed
            if disc.origin == "personal"
        ]
        assert len(personal) == 4
        assert len({disc.id for disc in personal}) == 4
        if player_state.status == "active":
            assert any(
                disc.origin == "personal"
                for disc in player_state.hand + player_state.stack
            )

        reached_face_up_suffix = False
        for disc in player_state.stack:
            if disc.face_up:
                reached_face_up_suffix = True
            else:
                assert not reached_face_up_suffix


def _assert_safe_views(engine: Any, room: ArcadeRoom, players: list[ArcadePlayer]) -> None:
    for viewer in players:
        view = engine.view(room, viewer)
        serialized = json.dumps(view, ensure_ascii=False)
        json.loads(serialized)

        for owner_id, owner_state in room.state.players.items():
            if owner_id == viewer.id:
                continue
            for disc in owner_state.hand + owner_state.stack + owner_state.removed:
                assert disc.id not in serialized

        for player_view in view["players"]:
            if player_view["id"] == viewer.id:
                continue
            assert player_view["removed"] == []
            for disc_view in player_view["stack"]:
                if disc_view["faceUp"]:
                    assert disc_view["knowledge"] == "public"
                elif disc_view["origin"] == "last_chance":
                    assert disc_view["kind"] == "last_chance_flower"
                    assert disc_view["knowledge"] == "public"
                else:
                    assert disc_view["kind"] == "unknown"
                    assert disc_view["knowledge"] == "hidden"


def _choose_action(
    view: dict[str, Any],
    rng: random.Random,
) -> tuple[str, dict[str, Any]]:
    actions = set(view["actions"])
    if "commit_initial" in actions:
        disc = rng.choice(view["hand"])
        return "commit_initial", {"discId": disc["id"]}
    if "choose_penalty" in actions:
        return "choose_penalty", {
            "slotId": rng.choice(view["round"]["penaltySlots"]),
        }
    if "choose_self_penalty" in actions:
        disc = rng.choice(view["round"]["selfPenaltyCandidates"])
        return "choose_self_penalty", {"discId": disc["id"]}
    if "choose_next_first" in actions:
        return "choose_next_first", {
            "playerId": rng.choice(view["round"]["eligibleNextFirstPlayerIds"]),
        }
    if "reveal_disc" in actions:
        return "reveal_disc", {
            "ownerId": rng.choice(view["legalRevealOwnerIds"]),
        }
    if "place_disc" in actions and (
        "open_bid" not in actions or rng.random() < 0.58
    ):
        disc = rng.choice(view["hand"])
        return "place_disc", {"discId": disc["id"]}
    if "open_bid" in actions:
        return "open_bid", {
            "count": rng.randint(view["minimumBid"], view["maximumBid"]),
        }
    if "raise_bid" in actions and (
        "pass_bid" not in actions or rng.random() < 0.56
    ):
        return "raise_bid", {
            "count": rng.randint(view["minimumBid"], view["maximumBid"]),
        }
    if "pass_bid" in actions:
        return "pass_bid", {}
    raise AssertionError(f"没有可执行动作：{view['phase']} / {sorted(actions)}")


def _play_game(
    count: int,
    seed: int,
    *,
    last_chance_enabled: bool,
) -> tuple[ArcadeRoom, int]:
    engine, room, players = _started_game(
        count,
        seed,
        last_chance_enabled=last_chance_enabled,
    )
    rng = random.Random(seed ^ 0x5A17)

    for action_count in range(1, 1_501):
        _assert_state_invariants(room)
        _assert_safe_views(engine, room, players)
        if room.phase == "finished":
            break

        actors: list[tuple[ArcadePlayer, dict[str, Any]]] = []
        for player in players:
            view = engine.view(room, player)
            if view["actions"]:
                actors.append((player, view))
        assert actors, f"牌局卡死在 {room.state.phase}"

        player, view = rng.choice(actors)
        action, payload = _choose_action(view, rng)
        engine.act(room, player, action, payload)
    else:
        raise AssertionError("完整牌局超过 1500 个动作仍未结束")

    assert room.phase == "finished"
    assert len(room.winner_player_ids) == 1
    assert room.winner_player_ids[0] in {player.id for player in players}
    json.dumps(engine.record_state(room), ensure_ascii=False)
    for player in players:
        role, score_kind, won = engine.player_result(room, player)
        assert role
        assert score_kind == "individual"
        assert won is (player.id in room.winner_player_ids)
    return room, action_count


@pytest.mark.parametrize(
    "count",
    (3, 4, 5, 6),
    ids=lambda count: f"{count}-players",
)
def test_randomized_complete_games_finish_without_deadlock_or_information_leak(
    count: int,
) -> None:
    result_reasons: set[str] = set()
    last_chance_was_used = False
    longest_game = 0
    samples = int(os.environ.get("SKULL_SOAK_SAMPLES", "24"))
    seed_offset = int(os.environ.get("SKULL_SOAK_SEED_OFFSET", "0"))

    for last_chance_enabled in (False, True):
        for sample in range(samples):
            seed = (
                seed_offset
                + count * 100_000
                + int(last_chance_enabled) * 10_000
                + sample
            )
            room, action_count = _play_game(
                count,
                seed,
                last_chance_enabled=last_chance_enabled,
            )
            result_reasons.add(room.state.result_reason)
            longest_game = max(longest_game, action_count)
            last_chance_was_used = last_chance_was_used or any(
                player.last_chance_used
                for player in room.state.players.values()
            )

    assert result_reasons == {"two_challenges", "last_player_remaining"}
    assert last_chance_was_used
    assert longest_game < 1_500
