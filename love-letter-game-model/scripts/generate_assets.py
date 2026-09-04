from __future__ import annotations

import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "model"
ASSET_DIR = ROOT / "assets"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def wrap_cjk(text: str, width: int) -> list[str]:
    normalized = "".join(text.split())
    return [normalized[index : index + width] for index in range(0, len(normalized), width)]


def card_atlas(catalog: dict) -> str:
    cards = catalog["cards"]
    column_count = 5
    row_count = (len(cards) + column_count - 1) // column_count
    width, height = 1240, 72 + row_count * 326 + 35
    chunks = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<metadata>love-letter card catalog model {esc(catalog["modelVersion"])}; original functional prototype</metadata>',
        "<defs>",
        '<filter id="shadow" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="7" stdDeviation="7" flood-color="#12090D" flood-opacity="0.45"/></filter>',
        '<pattern id="paper" width="18" height="18" patternUnits="userSpaceOnUse"><path d="M0 17.5H18M17.5 0V18" stroke="#5B3541" stroke-opacity="0.08"/></pattern>',
        "</defs>",
        f'<rect width="{width}" height="{height}" fill="#24151C"/>',
        '<text x="40" y="45" fill="#FFF7E8" font-size="28" font-family="Segoe UI, Noto Sans SC, sans-serif" font-weight="700">《情书》角色卡功能原型 · 22 张皇后扩展版</text>',
        f'<text x="1200" y="43" text-anchor="end" fill="#D6A84B" font-size="15" font-family="Segoe UI, Noto Sans SC, sans-serif">非官方美术 · model v{esc(catalog["modelVersion"])}</text>',
    ]

    card_width, card_height = 210, 300
    for index, card in enumerate(cards):
        col, row = index % column_count, index // column_count
        items_in_row = min(column_count, len(cards) - row * column_count)
        row_width = items_in_row * card_width + (items_in_row - 1) * 28
        x, y = (width - row_width) / 2 + col * 238, 72 + row * 326
        color = esc(card["visual"]["color"])
        text_color = esc(card["visual"]["textColor"])
        group_id = f'card-{esc(card["id"])}'
        chunks.extend(
            [
                f'<g id="{group_id}" data-card-type-id="{esc(card["id"])}" transform="translate({x} {y})" filter="url(#shadow)">',
                f'<rect width="{card_width}" height="{card_height}" rx="14" fill="{color}"/>',
                '<rect x="8" y="8" width="194" height="284" rx="10" fill="url(#paper)" stroke="#FFF7E8" stroke-opacity="0.68"/>',
                f'<text x="18" y="37" fill="{text_color}" font-size="27" font-family="Georgia, serif" font-weight="700">{card["value"]}</text>',
                f'<text x="192" y="283" text-anchor="end" fill="{text_color}" font-size="27" font-family="Georgia, serif" font-weight="700">{card["value"]}</text>',
                f'<text x="105" y="34" text-anchor="middle" fill="{text_color}" font-size="20" font-family="Segoe UI, Noto Sans SC, sans-serif" font-weight="700">{esc(card["nameZh"])}</text>',
                f'<text x="105" y="55" text-anchor="middle" fill="{text_color}" fill-opacity="0.82" font-size="11" font-family="Segoe UI, sans-serif" letter-spacing="1.2">{esc(card["nameEn"].upper())}</text>',
                '<circle cx="105" cy="116" r="42" fill="#FFF7E8" fill-opacity="0.93" stroke="#D6A84B" stroke-width="3"/>',
                f'<text x="105" y="129" text-anchor="middle" fill="{color}" font-size="34" font-family="Segoe UI, Noto Sans SC, sans-serif" font-weight="800">{esc(card["visual"]["symbol"])}</text>',
                f'<text x="105" y="168" text-anchor="middle" fill="{text_color}" font-size="13" font-family="Segoe UI, Noto Sans SC, sans-serif" font-weight="700">{esc(card["visual"]["prototypeLabel"])}</text>',
            ]
        )
        lines = wrap_cjk(card["effect"]["summaryZh"], 13)[:4]
        for line_index, line in enumerate(lines):
            chunks.append(
                f'<text x="105" y="{196 + line_index * 19}" text-anchor="middle" fill="{text_color}" font-size="12" font-family="Segoe UI, Noto Sans SC, sans-serif">{esc(line)}</text>'
            )
        chunks.extend(
            [
                f'<text x="105" y="274" text-anchor="middle" fill="{text_color}" fill-opacity="0.88" font-size="10" font-family="Segoe UI, Noto Sans SC, sans-serif">扩展 ×{card["queenVariantCount"]} · 现行 ×{card["count"]} · 经典 ×{card["classicCount"]}</text>',
                "</g>",
            ]
        )

    chunks.append("</svg>")
    return "\n".join(chunks) + "\n"


def table_scene(scene: dict) -> str:
    theme = scene["theme"]
    canvas = scene["logicalCanvas"]
    layout = next(item for item in scene["seatLayouts"] if item["playerCount"] == 4)
    width, height = canvas["width"], canvas["height"]
    chunks = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" data-player-count="4">',
        f'<metadata>love-letter table scene model {esc(scene["modelVersion"])}; original information architecture prototype</metadata>',
        "<defs>",
        '<filter id="softShadow" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#10080C" flood-opacity="0.5"/></filter>',
        '<pattern id="cloth" width="44" height="44" patternUnits="userSpaceOnUse"><path d="M0 22H44M22 0V44" stroke="#FFF7E8" stroke-opacity="0.025"/><circle cx="22" cy="22" r="2" fill="#D6A84B" fill-opacity="0.08"/></pattern>',
        "</defs>",
        f'<rect width="{width}" height="{height}" fill="{esc(theme["background"])}"/>',
        f'<ellipse cx="800" cy="470" rx="685" ry="345" fill="{esc(theme["table"])}" stroke="{esc(theme["tableEdge"])}" stroke-width="8" filter="url(#softShadow)"/>',
        '<ellipse cx="800" cy="470" rx="650" ry="315" fill="url(#cloth)"/>',
        f'<rect x="42" y="20" width="1516" height="66" rx="18" fill="{esc(theme["paper"])}" fill-opacity="0.96"/>',
        f'<text x="72" y="61" fill="{esc(theme["ink"])}" font-size="25" font-family="Segoe UI, Noto Sans SC, sans-serif" font-weight="700">第 2 轮 · 阿梨行动 · 抽牌阶段</text>',
        f'<text x="1524" y="61" text-anchor="end" fill="{esc(theme["mutedInk"])}" font-size="18" font-family="Segoe UI, Noto Sans SC, sans-serif">皇后扩展 22 张牌版 · 牌堆 9</text>',
    ]

    player_names = ["你 · 阿梨", "白川", "沉舟", "冬青"]
    for seat in layout["seats"]:
        seat_index = seat["relativeSeat"]
        x, y = seat["x"] * width, seat["y"] * height
        is_self = seat_index == 0
        seat_width = 300 if is_self else 210
        seat_height = 92 if is_self else 76
        sx, sy = x - seat_width / 2, y - seat_height / 2
        fill = theme["paper"] if is_self else "#3B2430"
        ink = theme["ink"] if is_self else theme["paper"]
        stroke = theme["focus"] if is_self else theme["tableEdge"]
        chunks.extend(
            [
                f'<g id="seat-{seat_index}" data-relative-seat="{seat_index}">',
                f'<rect x="{sx:.1f}" y="{sy:.1f}" width="{seat_width}" height="{seat_height}" rx="18" fill="{esc(fill)}" stroke="{esc(stroke)}" stroke-width="{4 if is_self else 2}"/>',
                f'<text x="{x:.1f}" y="{y - 5:.1f}" text-anchor="middle" fill="{esc(ink)}" font-size="{21 if is_self else 17}" font-family="Segoe UI, Noto Sans SC, sans-serif" font-weight="700">{esc(player_names[seat_index])}</text>',
                f'<text x="{x:.1f}" y="{y + 24:.1f}" text-anchor="middle" fill="{esc(ink)}" fill-opacity="0.82" font-size="14" font-family="Segoe UI, Noto Sans SC, sans-serif">♥ {1 if seat_index in (0, 2) else 0} · 手牌 1 · 在局</text>',
                "</g>",
            ]
        )

    def card_back(x: int, y: int, label: str, count: str) -> None:
        chunks.extend(
            [
                f'<g transform="translate({x} {y})">',
                f'<rect width="112" height="168" rx="12" fill="{esc(theme["ink"])}" stroke="{esc(theme["gold"])}" stroke-width="3"/>',
                f'<path d="M18 84L56 42L94 84L56 126Z" fill="none" stroke="{esc(theme["wax"])}" stroke-width="4"/>',
                f'<circle cx="56" cy="84" r="15" fill="{esc(theme["wax"])}"/>',
                f'<text x="56" y="194" text-anchor="middle" fill="{esc(theme["paper"])}" font-size="15" font-family="Segoe UI, Noto Sans SC, sans-serif">{esc(label)} {esc(count)}</text>',
                "</g>",
            ]
        )

    card_back(660, 365, "暗置", "×1")
    card_back(804, 365, "牌堆", "×9")
    chunks.extend(
        [
            f'<g id="recent-play" transform="translate(960 352)"><rect width="152" height="216" rx="14" fill="{esc(theme["paper"])}" stroke="{esc(theme["wax"])}" stroke-width="4"/><text x="76" y="52" text-anchor="middle" fill="{esc(theme["ink"])}" font-size="18" font-family="Segoe UI, Noto Sans SC, sans-serif" font-weight="700">最近打出</text><text x="76" y="112" text-anchor="middle" fill="{esc(theme["wax"])}" font-size="40" font-family="Segoe UI, Noto Sans SC, sans-serif">烛</text><text x="76" y="151" text-anchor="middle" fill="{esc(theme["ink"])}" font-size="20" font-family="Segoe UI, Noto Sans SC, sans-serif">牧师 · 2</text><text x="76" y="184" text-anchor="middle" fill="{esc(theme["mutedInk"])}" font-size="13" font-family="Segoe UI, Noto Sans SC, sans-serif">私密查看已完成</text></g>',
            f'<g id="public-history"><rect x="56" y="668" width="318" height="164" rx="20" fill="{esc(theme["paper"])}" fill-opacity="0.94"/><text x="82" y="706" fill="{esc(theme["ink"])}" font-size="20" font-family="Segoe UI, Noto Sans SC, sans-serif" font-weight="700">公开出牌历史</text><text x="82" y="744" fill="{esc(theme["mutedInk"])}" font-size="15" font-family="Segoe UI, Noto Sans SC, sans-serif">阿梨：牧师 2 · 卫兵 1</text><text x="82" y="774" fill="{esc(theme["mutedInk"])}" font-size="15" font-family="Segoe UI, Noto Sans SC, sans-serif">白川：卫兵 1 · 侍女 4 ◈保护</text><text x="82" y="804" fill="{esc(theme["mutedInk"])}" font-size="15" font-family="Segoe UI, Noto Sans SC, sans-serif">点击展开完整计牌</text></g>',
            f'<g id="private-log"><rect x="1226" y="668" width="318" height="164" rx="20" fill="{esc(theme["paper"])}" fill-opacity="0.94"/><text x="1252" y="706" fill="{esc(theme["ink"])}" font-size="20" font-family="Segoe UI, Noto Sans SC, sans-serif" font-weight="700">仅你可见 · 线索</text><text x="1252" y="744" fill="{esc(theme["mutedInk"])}" font-size="15" font-family="Segoe UI, Noto Sans SC, sans-serif">白川：公主 9（仍可能有效）</text><text x="1252" y="774" fill="{esc(theme["mutedInk"])}" font-size="15" font-family="Segoe UI, Noto Sans SC, sans-serif">来源：第 1 回合牧师</text><text x="1252" y="804" fill="{esc(theme["danger"])}" font-size="15" font-family="Segoe UI, Noto Sans SC, sans-serif">当前受保护，不能选为目标</text></g>',
            f'<g id="self-hand" transform="translate(680 650)"><rect x="0" y="0" width="112" height="168" rx="12" fill="#9A3412" stroke="{esc(theme["focus"])}" stroke-width="4"/><text x="56" y="42" text-anchor="middle" fill="#FFFFFF" font-size="19" font-family="Segoe UI, Noto Sans SC, sans-serif" font-weight="700">卫兵 · 1</text><circle cx="56" cy="88" r="28" fill="{esc(theme["paper"])}"/><text x="56" y="99" text-anchor="middle" fill="#9A3412" font-size="26" font-family="Segoe UI, Noto Sans SC, sans-serif">盾</text><text x="56" y="142" text-anchor="middle" fill="#FFFFFF" font-size="13" font-family="Segoe UI, Noto Sans SC, sans-serif">你的手牌</text></g>',
            f'<g id="primary-action"><rect x="808" y="735" width="154" height="54" rx="27" fill="{esc(theme["wax"])}"/><text x="885" y="769" text-anchor="middle" fill="#FFFFFF" font-size="18" font-family="Segoe UI, Noto Sans SC, sans-serif" font-weight="700">抽一张牌</text></g>',
            '<text x="800" y="875" text-anchor="middle" fill="#FFF7E8" fill-opacity="0.68" font-size="14" font-family="Segoe UI, Noto Sans SC, sans-serif">原创信息架构原型 · 不含官方美术</text>',
            "</svg>",
        ]
    )
    return "\n".join(chunks) + "\n"


def main() -> None:
    catalog = load_json(MODEL_DIR / "card-catalog.json")
    scene = load_json(MODEL_DIR / "scene-catalog.json")
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    (ASSET_DIR / "card-atlas.svg").write_text(card_atlas(catalog), encoding="utf-8")
    (ASSET_DIR / "table-scene.svg").write_text(table_scene(scene), encoding="utf-8")
    print("generated assets/card-atlas.svg")
    print("generated assets/table-scene.svg")


if __name__ == "__main__":
    main()
