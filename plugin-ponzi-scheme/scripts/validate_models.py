from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:  # Bundled artifact runtime intentionally stays small.
    Draft202012Validator = None


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    data = json.loads((ROOT / "data" / "components.json").read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "model" / "component-catalog.schema.json").read_text(encoding="utf-8"))
    if Draft202012Validator is not None:
        Draft202012Validator(schema).validate(data)
    else:
        assert set(schema["required"]) <= set(data)

    cards = data["fundCards"]
    assert [card["id"] for card in cards] == [f"F{amount:03d}" for amount in range(9, 81)]
    assert [card["amount"] for card in cards] == list(range(9, 81))
    assert sum(card["kind"] == "starting" for card in cards) == 9
    assert sum(card["kind"] == "regular" for card in cards) == 45
    assert sum(card["kind"] == "bear" for card in cards) == 18
    assert sum(industry["supply"] for industry in data["industries"]) == 60
    assert [bill["value"] for bill in data["money"]["denominations"]] == [1, 5, 10, 20]
    assert [(item["cost"], item["points"]) for item in data["luxuries"]] == [
        (30, 1), (56, 2), (78, 3), (96, 4)
    ]
    for card in cards:
        expected_burden = (2 * card["interest"] + card["period"]) // (2 * card["period"])
        assert card["averageBurden"] == expected_burden, card["id"]

    atlas = (ROOT / "images" / "fund-card-atlas.svg").read_text(encoding="utf-8")
    assert all(card["id"] in atlas for card in cards)
    for name in ("catalog-dark.webp", "catalog-light.webp"):
        with Image.open(ROOT / "frontend" / "assets" / name) as image:
            assert image.size == (768, 768)
            assert image.mode == "RGB"
    print("component catalog, 72-card atlas and catalog images: OK")


if __name__ == "__main__":
    main()
