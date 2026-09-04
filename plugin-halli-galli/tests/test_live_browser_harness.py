from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


SERVER_PATH = Path(__file__).resolve().parents[1] / "dev" / "server.py"
SPEC = importlib.util.spec_from_file_location("halli_galli_browser_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
SERVER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SERVER
SPEC.loader.exec_module(SERVER)


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6])
def test_browser_preview_uses_the_real_engine_for_every_player_count(count: int) -> None:
    payload = SERVER.preview(count)
    snapshot = payload["snapshot"]
    view = snapshot["game"]
    assert snapshot["phase"] == "playing"
    assert len(view["players"]) == count
    assert view["modelVersion"] == "1.0.0"
    assert view["profileId"] == "official_last_bell"
    assert all(player["topCard"] is not None for player in view["players"])
    assert "fruitTotals" not in view


@pytest.mark.parametrize(
    ("name", "count", "phase", "scene"),
    [
        ("exact-five", 4, "playing", "exact_five_visible"),
        ("wrong-bell", 4, "playing", "bell_resolved_wrong"),
        ("last-chance", 4, "playing", "last_chance_player"),
        ("final-duel", 2, "playing", "exact_five_visible"),
        ("final-wrong", 2, "playing", "playing_self_turn"),
        ("last-player", 3, "finished", "finished"),
        ("resignation", 2, "finished", "finished"),
        ("shared-win", 2, "finished", "finished"),
        ("no-progress", 3, "finished", "finished"),
    ],
)
def test_browser_scenarios_cover_visual_settlement_states(
    name: str,
    count: int,
    phase: str,
    scene: str,
) -> None:
    snapshot = SERVER.scenario(name)["snapshot"]
    assert snapshot["phase"] == phase
    assert len(snapshot["game"]["players"]) == count
    assert snapshot["game"]["sceneId"] == scene
    if name == "exact-five":
        assert snapshot["game"]["result"] is None
    elif name == "wrong-bell":
        assert snapshot["game"]["bell"]["lastResolution"]["kind"] == "wrong"
    elif name == "last-chance":
        assert snapshot["game"]["players"][0]["displayStatus"] == "last_chance"
    elif name == "final-duel":
        assert snapshot["game"]["finalDuelArmed"] is True
    elif name == "final-wrong":
        assert snapshot["game"]["finalDuelArmed"] is True
        assert snapshot["game"]["result"] is None
    elif name == "last-player":
        assert snapshot["game"]["result"]["reasonCode"] == "last_player"
    elif name == "resignation":
        assert snapshot["game"]["result"]["reasonCode"] == "resignation"
    elif name == "shared-win":
        assert snapshot["game"]["result"]["sharedWin"] is True
    elif name == "no-progress":
        assert snapshot["game"]["result"]["reasonCode"] == "no_progress"


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6])
def test_browser_autoplay_finishes_every_supported_player_count(count: int) -> None:
    payload = SERVER.autoplay(count)
    assert payload["snapshot"]["phase"] == "finished"
    assert payload["report"]["playerCount"] == count
    assert payload["report"]["actionCount"] > 0
    assert payload["report"]["winnerPlayerIds"]
    assert payload["report"]["ending"] in {
        "final_correct_bell", "final_wrong_bell", "last_player", "no_progress",
    }
