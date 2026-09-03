from __future__ import annotations

import pytest

from .live_browser_harness.server import autoplay, preview, scenario


@pytest.mark.parametrize("count", (3, 4, 5))
def test_preview_uses_real_engine_and_expected_worker_count(count: int) -> None:
    snapshot = preview(count)["snapshot"]
    view = snapshot["game"]
    expected = 4 if count == 3 else 3
    assert snapshot["phase"] == "playing"
    assert view["stage"] == "placement"
    assert len(view["players"]) == count
    assert all(player["workerCount"] == expected for player in view["players"])
    assert len(view["punts"]) == 3


@pytest.mark.parametrize(
    ("name", "stage"),
    [
        ("auction", "auction"),
        ("placement", "placement"),
        ("movement", "move_order"),
        ("pirate", "pirate_board"),
        ("pilot", "pilot_large"),
        ("settlement", "voyage_summary"),
        ("finished", "finished"),
    ],
)
def test_visual_scenario_has_expected_server_stage(name: str, stage: str) -> None:
    snapshot = scenario(name)["snapshot"]
    assert snapshot["game"]["stage"] == stage
    if name == "settlement":
        assert snapshot["game"]["settlement"]["entries"]
    if name == "finished":
        assert snapshot["phase"] == "finished"
        assert len(snapshot["winnerPlayerIds"]) == 5


@pytest.mark.parametrize("count", (3, 4, 5))
def test_browser_autoplay_completes_every_supported_player_count(count: int) -> None:
    payload = autoplay(count)
    snapshot = payload["snapshot"]
    report = payload["report"]
    assert snapshot["phase"] == "finished"
    assert report["playerCount"] == count
    assert report["actionCount"] > 0
    assert report["voyageCount"] >= 4
    assert report["winnerPlayerIds"]
    assert 30 in report["market"].values()

