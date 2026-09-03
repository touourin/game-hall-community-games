from __future__ import annotations

import pytest

from dead_mans_draw_live_browser_harness import autoplay, scenario


def test_trait_browser_scenario_exposes_only_the_viewers_two_choices() -> None:
    view = scenario("trait")["snapshot"]["game"]

    assert view["phase"] == "trait_selection"
    assert view["actions"]["canChooseTrait"] is True
    assert len(view["self"]["traitOffer"]) == 2
    assert all("traitOffer" not in player for player in view["players"])


def test_effect_browser_scenario_marks_the_physical_forced_bust() -> None:
    view = scenario("effect")["snapshot"]["game"]
    choice = view["turn"]["pendingChoice"]

    assert view["phase"] == "effect_choice"
    assert choice["kind"] == "hook-stack"
    assert len(choice["options"]) == 1
    assert choice["options"][0]["causesImmediateBust"] is True


def test_shared_win_browser_scenario_has_two_rank_one_winners() -> None:
    snapshot = scenario("shared")["snapshot"]
    result = snapshot["game"]["result"]

    assert snapshot["phase"] == "finished"
    assert result["outcome"] == "shared-win"
    assert result["winnerIds"] == ["p1", "p2"]
    assert [row["rank"] for row in result["scores"][:2]] == [1, 1]


@pytest.mark.parametrize("count", (2, 3, 4))
def test_browser_autoplay_endpoint_completes_and_reports_each_player(count: int) -> None:
    payload = autoplay(count)
    snapshot = payload["snapshot"]
    report = payload["report"]

    assert snapshot["phase"] == "finished"
    assert report["playerCount"] == count
    assert report["actionCount"] > 0
    assert report["turnCount"] > 0
    assert len(report["settlement"]) == count
    assert set(report["winnerPlayerIds"]) == set(snapshot["winnerPlayerIds"])
