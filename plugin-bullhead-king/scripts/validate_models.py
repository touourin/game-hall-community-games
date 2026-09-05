from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path: str):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def expected_bullheads(number: int) -> int:
    if number == 55:
        return 7
    if number % 11 == 0:
        return 5
    if number % 10 == 0:
        return 3
    if number % 5 == 0:
        return 2
    return 1


def main() -> None:
    card_model = load_json("model/card-model.json")
    catalog = load_json("model/generated-card-catalog.json")
    scenes = load_json("model/scene-catalog.json")
    machine = load_json("model/state-machine.json")
    animations = load_json("model/animation-timeline.json")

    assert card_model["range"] == {
        "minimum": 1, "maximum": 104, "unique": True,
    }
    cards = catalog["cards"]
    assert len(cards) == 104
    assert [card["number"] for card in cards] == list(range(1, 105))
    assert len({card["id"] for card in cards}) == 104
    for card in cards:
        assert card["id"] == f"card-{card['number']:03d}"
        assert card["bullheads"] == expected_bullheads(card["number"])
        assert card["ariaLabel"].endswith("牛头分")
    distribution = Counter(card["bullheads"] for card in cards)
    assert distribution == Counter({1: 76, 2: 9, 3: 10, 5: 8, 7: 1})
    assert sum(card["bullheads"] for card in cards) == 171
    assert catalog["statistics"]["totalBullheads"] == 171

    states = set(machine["states"])
    actions = set(machine["actions"])
    scene_ids = [scene["id"] for scene in scenes["scenes"]]
    assert len(scene_ids) == len(set(scene_ids)) == 6
    for scene in scenes["scenes"]:
        assert scene["stage"] in states
        assert set(scene["actions"]) <= actions
    clip_ids = {clip["id"] for clip in animations["clips"]}
    assert {
        "card.commit", "cards.reveal", "card.place",
        "row.take-full", "row.take-low", "round.deal",
    } == clip_ids
    assert set(animations["eventShape"]["stepTypes"]) == {
        "place", "take_full", "take_low",
    }
    assert animations["motionSafety"]["layer"] == "component-overlay-above-table"
    assert animations["motionSafety"]["takeStackMaximumCards"] == 5
    assert animations["motionSafety"]["rulesOverlayAlwaysAboveMotion"] is True
    assert scenes["viewportPolicy"]["mode"] == "browser-fill"
    assert scenes["viewportPolicy"]["pageLevelHorizontalOverflow"] is False

    for relative_path in (
        "assets/card-model-sheet.svg",
        "assets/table-scene-blueprint.svg",
    ):
        svg = (ROOT / relative_path).read_text(encoding="utf-8")
        assert 'data-model-version="1"' in svg
        assert "<svg" in svg and "</svg>" in svg

    print(
        "Bullhead models valid: 104 cards, 171 bullheads, "
        "6 scenes, 6 animation clips, 2 SVG sheets."
    )


if __name__ == "__main__":
    main()
