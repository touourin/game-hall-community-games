from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import select

# Host internals are used only by these integration tests, never by plugin runtime code.
import backend.app.arcade.realtime as realtime_module
from backend.app.accounts import AccountStore
from backend.app.arcade.realtime import ArcadeRealtime
from backend.app.arcade.rooms import ArcadeRoomManager
from backend.app.database import match_players
from backend.app.games.registry import game_registration


GAME_KEY = "plugin-blokus"


@pytest.fixture
def session(tmp_path, monkeypatch):
    store = AccountStore(tmp_path / "blokus.sqlite3")
    accounts = [
        store.register(f"blokus_{index}", "local-test-pass", f"玩家{index + 1}")[0]
        for index in range(4)
    ]
    runtime = ArcadeRealtime()
    monkeypatch.setattr(realtime_module, "account_store", lambda: store)
    engine = runtime.engines[GAME_KEY]
    manager = ArcadeRoomManager({GAME_KEY: engine})
    yield SimpleNamespace(store=store, accounts=accounts, runtime=runtime, engine=engine, manager=manager)
    store.dispose()


def start_room(session, *, guest=False):
    host_account, *other_accounts = session.accounts
    room, host, _ = session.manager.create_room(
        GAME_KEY, host_account.player_name, host_account.id,
        {"firstPlayer": "host", "allowGuests": guest},
    )
    for index, account in enumerate(other_accounts):
        session.manager.join_room(
            room.code, GAME_KEY, account.player_name, account.id,
            is_guest=guest and index == 2,
        )
    session.manager.start(room, host.id)
    return room


def stored_scores(session, match_id):
    with session.store.engine.connect() as connection:
        rows = connection.execute(select(
            match_players.c.account_id, match_players.c.score_value,
        ).where(match_players.c.match_id == match_id))
        return {account_id: score for account_id, score in rows}


def test_complete_game_records_signed_points_with_the_existing_outcome_api(session):
    assert game_registration(GAME_KEY).records.score_kind == "outcome"
    room = start_room(session)
    while room.phase == "playing":
        player_id = room.state.current_player_id
        session.manager.act(room, player_id, "place", session.engine.find_move(room, player_id))
    session.runtime._record_room(room)
    assert room.recorded
    expected_scores = {}
    for rank, (player_id, points) in enumerate(zip(room.state.rankings, (2, 1, 0, -1), strict=True), 1):
        player = room.player(player_id)
        expected_scores[player.account_id] = points
        score_text = ("+2", "+1", "0", "-1")[rank - 1]
        label = f"第 {rank} 名 · {score_text} 分"
        history = session.store.history_for_account(player.account_id, game_key=GAME_KEY)
        assert len(history) == 1
        assert history[0]["role"] == label
        assert history[0]["outcome"] == ("win" if rank == 1 else "loss")
        detail = session.store.match_for_account(room.game_id, player.account_id)
        assert f"{player.name}：{label}" in detail["reason"]
        assert detail["details"]["state"]["scores"] == room.state.scores
        assert detail["details"]["state"]["rankings"] == room.state.rankings
        assert next(item for item in detail["details"]["players"] if item["id"] == player_id)["role"] == label
        summary = session.store.summary_for_account(player.account_id, game_key=GAME_KEY)
        assert summary["games"] == 1
        assert summary["wins"] == (rank == 1)
        assert "totalPoints" not in summary
    assert stored_scores(session, room.game_id) == expected_scores
    leaderboard = session.store.leaderboard(game_key=GAME_KEY)
    assert len(leaderboard) == 4
    assert leaderboard[0]["accountId"] == room.player(room.state.rankings[0]).account_id
    assert all("totalPoints" not in entry for entry in leaderboard)


def test_rematches_keep_separate_scores_and_duplicate_persistence_does_not_add_games(session):
    room = start_room(session)
    for round_number in (1, 2):
        assert room.round_number == round_number
        assert session.engine.player_score(room, room.players[0]) is None
        for player in list(room.players)[:3]:
            session.manager.act(room, player.id, "resign", {})
        session.runtime._record_room(room)
        assert room.recorded
        session.runtime._record_room(room)
        # Simulate a retry after the response was lost; the DB still rejects the duplicate.
        room.recorded = False
        session.runtime._record_room(room)
        assert sorted(stored_scores(session, room.game_id).values()) == [-1, 0, 1, 2]
        for account in session.accounts:
            history = session.store.history_for_account(account.id, game_key=GAME_KEY)
            assert len(history) == round_number
        if round_number == 1:
            first_match_id = room.game_id
            for player in list(room.players):
                session.manager.restart(room, player.id)
            assert room.game_id != first_match_id
            assert room.state.scores == {}
    assert all(entry["games"] == 2 for entry in session.store.leaderboard(game_key=GAME_KEY))


def test_guest_game_shows_all_four_points_without_saving_any_account_records(session):
    room = start_room(session, guest=True)
    assert room.stats_eligible is False
    for player in list(room.players)[:3]:
        session.manager.act(room, player.id, "resign", {})
    view = session.engine.view(room, room.players[0])
    assert sorted(player["points"] for player in view["players"]) == [-1, 0, 1, 2]
    session.runtime._record_room(room)
    assert room.recorded
    assert stored_scores(session, room.game_id) == {}
    assert session.store.leaderboard(game_key=GAME_KEY) == []
    for account in session.accounts:
        assert session.store.history_for_account(account.id, game_key=GAME_KEY) == []
