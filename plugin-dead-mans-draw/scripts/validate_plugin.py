from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT.parent / "dead-mans-draw-game-model"

MIRRORS = {
    ROOT / "data" / "card-catalog.json": MODEL_ROOT / "model" / "card-catalog.json",
    ROOT / "data" / "rules-profiles.json": MODEL_ROOT / "model" / "rules-profiles.json",
    ROOT / "data" / "scene-catalog.json": MODEL_ROOT / "model" / "scene-catalog.json",
    ROOT / "docs" / "RULEBOOK.md": MODEL_ROOT / "docs" / "RULEBOOK.md",
    ROOT / "docs" / "IMPLEMENTATION_PLAN.md": MODEL_ROOT / "docs" / "IMPLEMENTATION_PLAN.md",
    ROOT / "docs" / "CARD_MODEL.md": MODEL_ROOT / "docs" / "CARD_MODEL.md",
    ROOT / "docs" / "SCENE_MODEL.md": MODEL_ROOT / "docs" / "SCENE_MODEL.md",
    ROOT / "docs" / "SOURCES.md": MODEL_ROOT / "SOURCES.md",
    ROOT / "docs" / "table-scene-reference.svg": MODEL_ROOT / "assets" / "table-scene.svg",
    ROOT / "docs" / "loot-card-atlas-reference.svg": MODEL_ROOT / "assets" / "loot-card-atlas.svg",
    ROOT / "docs" / "trait-card-atlas-reference.svg": MODEL_ROOT / "assets" / "trait-card-atlas.svg",
}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def main() -> None:
    missing = [str(path) for pair in MIRRORS.items() for path in pair if not path.is_file()]
    assert not missing, f"缺少建模或镜像文件: {missing}"
    drift = [local.name for local, source in MIRRORS.items() if local.read_bytes() != source.read_bytes()]
    assert not drift, f"实现目录中的建模镜像已漂移: {drift}"

    cards = load_json(ROOT / "data" / "card-catalog.json")
    scene = load_json(ROOT / "data" / "scene-catalog.json")
    profiles = load_json(ROOT / "data" / "rules-profiles.json")
    manifest = load_json(ROOT / "manifest.json")

    summary = cards["componentSummary"]
    assert summary == {"lootCards": 60, "baseTraits": 17, "suits": 10, "cardsPerSuit": 6}
    assert len(cards["suits"]) == 10
    assert len(cards["traits"]) == 17
    assert profiles["defaultProfileId"] == "tabletop_base_2015"
    assert manifest["defaultOptions"]["rulesProfile"] == profiles["defaultProfileId"]
    assert manifest["players"] == {"min": 2, "max": 4, "label": "2–4 人"}

    css = (ROOT / "frontend" / "GameView.vue").read_text(encoding="utf-8").lower()
    for color in scene["theme"].values():
        assert color.lower() in css, f"场景模型色值未进入前端: {color}"
    for cue in scene["animationCues"]:
        assert cue["id"] in css, f"动画提示未进入前端: {cue['id']}"
    for breakpoint in (1179, 759, 390):
        assert f"max-width: {breakpoint}px" in css
    assert 'grid-template-areas: ". north ." "west center east" ". self ." ". dock ."' in css
    for area in ("north", "west", "east", "self", "dock", "center"):
        assert f"grid-area: {area}" in css, f"宽屏座位区没有映射到建模区域: {area}"

    for name in ("catalog-dark.webp", "catalog-light.webp"):
        path = ROOT / "frontend" / "assets" / name
        with Image.open(path) as icon:
            assert icon.format == "WEBP"
            assert icon.size == (768, 768)
            assert icon.mode == "RGB"

    print("OK: 11 个建模镜像逐字节一致")
    print("OK: 60 张牌 / 10 种花色 / 17 种特性 / 常规规则配置一致")
    print("OK: 场景色板、环桌座位、11 个动画提示、3 个响应式断点一致")
    print("OK: 深浅目录图均为 768×768 RGB WebP")


if __name__ == "__main__":
    main()
