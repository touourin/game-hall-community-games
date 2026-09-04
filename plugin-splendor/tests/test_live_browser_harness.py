from __future__ import annotations

import pytest

from live_browser_harness.server import autoplay, preview, scenario


@pytest.mark.parametrize("count", [2, 3, 4])
def test_browser_preview_is_backed_by_real_engine(count: int) -> None:
    payload = preview(count)
    snapshot = payload["snapshot"]
    view = snapshot["game"]
    assert snapshot["phase"] == "playing"
    assert len(view["players"]) == count
    assert len(view["tiers"]) == 3
    assert sum(len(tier["slots"]) for tier in view["tiers"]) == 12
    assert view["modelVersion"] == "1.0.0"


@pytest.mark.parametrize(
    ("name", "phase", "scene"),
    [
        ("payment", "turn_action", "turn_idle"),
        ("return", "return_tokens", "return_tokens"),
        ("noble", "choose_noble", "choose_noble"),
        ("final-round", "turn_action", "final_round"),
        ("shared", "finished", "game_finished"),
    ],
)
def test_visual_scenarios_use_expected_engine_state(name: str, phase: str, scene: str) -> None:
    snapshot = scenario(name)["snapshot"]
    assert snapshot["game"]["phase"] == phase
    assert snapshot["game"]["sceneId"] == scene
    if name == "shared":
        assert snapshot["game"]["result"]["outcome"] == "shared-win"
    if name == "payment":
        tier = next(item for item in snapshot["game"]["tiers"] if item["level"] == 1)
        card = tier["slots"][0]["card"]
        assert card["id"] == "dev-white-1-04"
        assert card["legal"]["buy"] is True
        assert card["payment"]["affordable"] is True


@pytest.mark.parametrize("count", [2, 3, 4])
def test_browser_autoplay_finishes_every_supported_player_count(count: int) -> None:
    payload = autoplay(count)
    assert payload["snapshot"]["phase"] == "finished"
    assert payload["report"]["playerCount"] == count
    assert payload["report"]["actionCount"] > 0
    assert payload["report"]["winnerPlayerIds"]
