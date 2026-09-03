#!/usr/bin/env python3
"""Generate original SVG card and table prototypes from the JSON models."""

from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "model"
ASSET_DIR = ROOT / "assets"
CATALOG_PATH = MODEL_DIR / "card-catalog.json"
SCENE_PATH = MODEL_DIR / "scene-catalog.json"
FONT_STACK = "'Microsoft YaHei','Noto Sans CJK SC','PingFang SC',sans-serif"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def svg_document(width: int, height: int, body: str, *, title: str, model_version: str, source_sha: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"
     role="img" aria-labelledby="title desc" data-model-version="{esc(model_version)}" data-source-sha256="{source_sha}">
  <title id="title">{esc(title)}</title>
  <desc id="desc">原创功能建模图，不含官方插画、Logo 或扫描素材。</desc>
  <metadata>Generated from model/card-catalog.json and model/scene-catalog.json</metadata>
  {body}
</svg>
'''


def icon_svg(icon: str, cx: float, cy: float, scale: float, stroke: str = "#FFF9EA") -> str:
    common = f'fill="none" stroke="{stroke}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"'
    shapes = {
        "anchor": f'''<circle cx="0" cy="-25" r="10"/><path d="M0 -15V31 M-29 10C-22 31 -9 39 0 31C9 39 22 31 29 10 M-29 10L-17 6 M29 10L17 6"/>''',
        "hook": f'''<path d="M4 -38V10C4 29 -7 39 -22 34C-36 29 -38 12 -29 2 M-29 2L-31 18 M-29 2L-14 8"/><path d="M-6 -38H14"/>''',
        "cannon": f'''<path d="M-35 -14L20 -5L16 17L-39 8Z"/><circle cx="-8" cy="24" r="13"/><path d="M20 -2L35 -8 M-35 -4L-43 -7 M18 -9C24 -20 29 -22 35 -26"/>''',
        "key": f'''<circle cx="-21" cy="-10" r="15"/><circle cx="-21" cy="-10" r="5"/><path d="M-9 0L29 30 M13 16L22 7 M23 25L31 17"/>''',
        "chest": f'''<path d="M-36 -3V-12C-36 -27 -23 -36 0 -36C23 -36 36 -27 36 -12V-3 M-39 -3H39V34H-39Z"/><path d="M-39 8H39 M0 -3V34"/><rect x="-7" y="8" width="14" height="13" rx="3"/>''',
        "map": f'''<path d="M-38 -31L-13 -38L13 -30L38 -38V31L13 38L-13 30L-38 38Z M-13 -38V30 M13 -30V38"/><path d="M-27 17C-12 2 -8 -14 4 -12C16 -10 13 7 28 13 M23 8L30 15 M30 8L23 15"/>''',
        "oracle": f'''<circle cx="0" cy="-5" r="32"/><path d="M-25 19L-34 37H34L25 19 M-18 -8C-7 -24 9 -25 20 -12C9 -14 1 -7 0 4C-9 -1 -15 -4 -18 -8Z"/>''',
        "sword": f'''<path d="M-29 31L24 -31L31 -39L29 -27L-22 36Z"/><path d="M-33 12L-7 34 M-28 37L-19 46"/>''',
        "kraken": f'''<path d="M-27 1C-27 -23 -16 -36 0 -36C16 -36 27 -23 27 1V12"/><circle cx="-9" cy="-9" r="3" fill="{stroke}" stroke="none"/><circle cx="9" cy="-9" r="3" fill="{stroke}" stroke="none"/><path d="M-27 10C-42 18 -37 39 -20 37C-6 36 -12 16 -1 13C12 9 3 39 20 38C38 37 42 17 27 10 M-10 15C-19 25 -15 42 -4 43 M11 15C20 25 17 42 7 44"/>''',
        "mermaid": f'''<path d="M0 -37C-18 -30 -29 -15 -29 4C-29 26 -12 39 0 45C12 39 29 26 29 4C29 -15 18 -30 0 -37Z"/><path d="M0 -31V39 M-23 -8C-10 -3 10 -3 23 -8 M-27 9C-11 14 11 14 27 9 M-19 27C-7 28 7 28 19 27"/>''',
    }
    inner = shapes.get(icon, f'<circle cx="0" cy="0" r="30"/><text x="0" y="10" text-anchor="middle" fill="{stroke}" stroke="none">?</text>')
    return f'<g transform="translate({cx:.1f} {cy:.1f}) scale({scale:.3f})" {common}>{inner}</g>'


def wrap_zh(text: str, limit: int) -> list[str]:
    lines: list[str] = []
    current = ""
    closing_punctuation = set("，。；：！？、）」】》’”")
    for char in text:
        weight = 1 if ord(char) > 127 else 0.55
        current_weight = sum(1 if ord(item) > 127 else 0.55 for item in current)
        if current and current_weight + weight > limit:
            if char in closing_punctuation:
                current += char
            else:
                lines.append(current)
                current = char
        else:
            current += char
    if current:
        lines.append(current)
    # Avoid visually awkward final lines such as a lone number plus full stop.
    if len(lines) >= 2:
        while len(lines[-1]) < 5 and len(lines[-2]) > 9:
            lines[-1] = lines[-2][-1] + lines[-1]
            lines[-2] = lines[-2][:-1]
    return lines


def loot_card_group(suit: dict, value: int, x: int, y: int, width: int, height: int) -> str:
    card_id = f"loot-{suit['id']}-{value}"
    color = suit["color"]
    category_labels = {
        "protection": "保护",
        "replay": "取牌",
        "attack": "攻击",
        "combo": "组合",
        "selection": "选择",
        "information": "预览",
        "forced": "强制",
        "scoring": "高分",
    }
    icon = icon_svg(suit["icon"], width / 2, height * 0.47, 0.62, color)
    return f'''
    <g data-card-id="{card_id}" transform="translate({x} {y})">
      <rect width="{width}" height="{height}" rx="14" fill="#F7EBD2" stroke="#D1BC91" stroke-width="2"/>
      <rect x="7" y="7" width="{width - 14}" height="42" rx="9" fill="{color}"/>
      <text x="17" y="39" font-family="{FONT_STACK}" font-size="30" font-weight="700" fill="#FFF9EA">{value}</text>
      <text x="{width - 17}" y="36" text-anchor="end" font-family="{FONT_STACK}" font-size="18" font-weight="700" fill="#FFF9EA">{esc(suit['symbol'])}</text>
      {icon}
      <text x="{width / 2}" y="{height - 52}" text-anchor="middle" font-family="{FONT_STACK}" font-size="19" font-weight="700" fill="#1E2928">{esc(suit['nameZh'])}</text>
      <rect x="12" y="{height - 38}" width="{width - 24}" height="25" rx="7" fill="{color}" opacity="0.14"/>
      <text x="{width / 2}" y="{height - 20}" text-anchor="middle" font-family="{FONT_STACK}" font-size="13" font-weight="700" fill="{color}">{category_labels[suit['category']]}</text>
    </g>'''


def build_loot_atlas(catalog: dict, source_sha: str) -> str:
    card_w, card_h, gap_x, gap_y = 160, 224, 18, 20
    margin_x, top = 48, 108
    width = margin_x * 2 + card_w * 6 + gap_x * 5
    height = top + card_h * 10 + gap_y * 9 + 62
    parts = [
        f'<rect width="{width}" height="{height}" fill="#142F2F"/>',
        f'<text x="48" y="48" font-family="{FONT_STACK}" font-size="30" font-weight="700" fill="#FFF9EA">亡命神抽 · 60 张战利品牌建模总览</text>',
        f'<text x="48" y="78" font-family="{FONT_STACK}" font-size="16" fill="#C9D2CC">基础版点数 · 原创功能原型 · model {esc(catalog["modelVersion"])}</text>',
    ]
    for row, suit in enumerate(catalog["suits"]):
        for col, value in enumerate(suit["values"]["base"]):
            x = margin_x + col * (card_w + gap_x)
            y = top + row * (card_h + gap_y)
            parts.append(loot_card_group(suit, value, x, y, card_w, card_h))
    parts.append(f'<text x="{width - 48}" y="{height - 24}" text-anchor="end" font-family="{FONT_STACK}" font-size="13" fill="#9FB2AA">非官方建模资产 · 不含官方美术</text>')
    return svg_document(width, height, "".join(parts), title="亡命神抽 60 张战利品牌建模总览", model_version=catalog["modelVersion"], source_sha=source_sha)


def build_trait_atlas(catalog: dict, source_sha: str) -> str:
    card_w, card_h, gap = 310, 184, 20
    columns = 3
    rows = (len(catalog["traits"]) + columns - 1) // columns
    margin_x, top = 44, 106
    width = margin_x * 2 + card_w * columns + gap * (columns - 1)
    height = top + card_h * rows + gap * (rows - 1) + 58
    suits = {suit["id"]: suit for suit in catalog["suits"]}
    parts = [
        f'<rect width="{width}" height="{height}" fill="#E7DBC2"/>',
        f'<text x="44" y="46" font-family="{FONT_STACK}" font-size="30" font-weight="700" fill="#1E2928">亡命神抽 · 17 张基础特性牌</text>',
        f'<text x="44" y="76" font-family="{FONT_STACK}" font-size="15" fill="#5E6965">规则修改器总览 · 每位玩家基础规则选择一张</text>',
    ]
    for index, trait in enumerate(catalog["traits"]):
        row, col = divmod(index, columns)
        x = margin_x + col * (card_w + gap)
        y = top + row * (card_h + gap)
        applies = trait["appliesTo"][0]
        suit = suits.get(applies)
        color = suit["color"] if suit else "#6F4F32"
        icon_name = suit["icon"] if suit else "anchor"
        # The description column is 203 px wide. Fourteen full-width glyphs at
        # 13 px leave enough breathing room even with font fallback on Windows.
        lines = wrap_zh(trait["summaryZh"], 14)[:3]
        text_lines = "".join(
            f'<text x="92" y="{101 + line_no * 20}" font-family="{FONT_STACK}" font-size="13" fill="#34413E">{esc(line)}</text>'
            for line_no, line in enumerate(lines)
        )
        parts.append(f'''
        <g data-trait-id="{esc(trait['id'])}" transform="translate({x} {y})">
          <rect width="{card_w}" height="{card_h}" rx="16" fill="#FFF7E5" stroke="#B9A477" stroke-width="2"/>
          <rect width="12" height="{card_h}" rx="6" fill="{color}"/>
          <circle cx="52" cy="73" r="34" fill="{color}" opacity="0.13"/>
          {icon_svg(icon_name, 52, 73, 0.42, color)}
          <text x="92" y="36" font-family="{FONT_STACK}" font-size="21" font-weight="700" fill="#1E2928">{esc(trait['nameZh'])}</text>
          <text x="92" y="59" font-family="{FONT_STACK}" font-size="12" fill="#6A736F">{esc(trait['nameEn'])}</text>
          <rect x="92" y="70" width="104" height="21" rx="10" fill="{color}" opacity="0.15"/>
          <text x="144" y="85" text-anchor="middle" font-family="{FONT_STACK}" font-size="11" font-weight="700" fill="{color}">强制特性 · {esc(applies)}</text>
          {text_lines}
          <text x="{card_w - 15}" y="{card_h - 13}" text-anchor="end" font-family="{FONT_STACK}" font-size="10" fill="#8B806B">{index + 1:02d} / 17</text>
        </g>''')
    parts.append(f'<text x="{width - 44}" y="{height - 22}" text-anchor="end" font-family="{FONT_STACK}" font-size="12" fill="#746A58">非官方建模资产 · 人物区为抽象占位</text>')
    return svg_document(width, height, "".join(parts), title="亡命神抽 17 张基础特性牌建模总览", model_version=catalog["modelVersion"], source_sha=source_sha)


def mini_card(suit: dict, value: int, x: float, y: float, *, width: float = 78, height: float = 110, protected: bool = False) -> str:
    outline = "#F2C96D" if protected else "#CBB98D"
    badge = '<circle cx="62" cy="16" r="9" fill="#4F7F78"/><text x="62" y="20" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#FFF">✓</text>' if protected else ""
    return f'''
      <g transform="translate({x:.1f} {y:.1f})">
        <rect width="{width}" height="{height}" rx="9" fill="#F7EBD2" stroke="{outline}" stroke-width="2"/>
        <rect x="5" y="5" width="{width - 10}" height="24" rx="6" fill="{suit['color']}"/>
        <text x="12" y="24" font-family="{FONT_STACK}" font-size="17" font-weight="700" fill="#FFF9EA">{value}</text>
        {icon_svg(suit['icon'], width / 2, height * 0.55, 0.28, suit['color'])}
        <text x="{width / 2}" y="{height - 10}" text-anchor="middle" font-family="{FONT_STACK}" font-size="11" font-weight="700" fill="#1E2928">{esc(suit['nameZh'])}</text>
        {badge}
      </g>'''


def build_table_scene(catalog: dict, scene: dict, source_sha: str) -> str:
    width, height = scene["logicalCanvas"]["width"], scene["logicalCanvas"]["height"]
    theme = scene["theme"]
    suits = {suit["id"]: suit for suit in catalog["suits"]}
    parts = [
        f'<rect width="{width}" height="{height}" fill="#0D2526"/>',
        f'<rect x="24" y="18" width="1552" height="864" rx="54" fill="{theme["tableEdge"]}"/>',
        f'<rect x="39" y="33" width="1522" height="834" rx="46" fill="{theme["table"]}" stroke="#2A5754" stroke-width="3"/>',
    ]
    for zone in scene["zones"]:
        rect = zone["rect"]
        x, y = rect["x"] * width, rect["y"] * height
        w, h = rect["width"] * width, rect["height"] * height
        parts.append(f'<g data-zone-id="{esc(zone["id"])}"><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="#FFFFFF" opacity="0.001"/></g>')

    parts.extend([
        f'<rect x="48" y="22" width="1504" height="60" rx="18" fill="{theme["panel"]}" stroke="#3E6562"/>',
        f'<text x="74" y="59" font-family="{FONT_STACK}" font-size="20" font-weight="700" fill="{theme["white"]}">第 4 回合 · 阿岚行动</text>',
        f'<text x="800" y="58" text-anchor="middle" font-family="{FONT_STACK}" font-size="16" fill="#C9D5CF">实体基础版 · 特性开启</text>',
        f'<text x="1525" y="58" text-anchor="end" font-family="{FONT_STACK}" font-size="16" fill="{theme["focus"]}">抽牌堆 33</text>',
    ])

    def player_panel(x: int, y: int, w: int, h: int, name: str, trait: str, score: int, active: bool = False) -> str:
        stroke = theme["focus"] if active else "#557370"
        return f'''
        <g>
          <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="17" fill="#153332" stroke="{stroke}" stroke-width="{3 if active else 1.5}"/>
          <circle cx="{x + 31}" cy="{y + 31}" r="18" fill="#B28A4A" opacity="0.85"/>
          <text x="{x + 58}" y="{y + 30}" font-family="{FONT_STACK}" font-size="18" font-weight="700" fill="#FFF9EA">{esc(name)}</text>
          <text x="{x + 58}" y="{y + 52}" font-family="{FONT_STACK}" font-size="12" fill="#AFC0B9">{esc(trait)}</text>
          <text x="{x + w - 20}" y="{y + 37}" text-anchor="end" font-family="{FONT_STACK}" font-size="26" font-weight="700" fill="#F2C96D">{score}</text>
          <rect x="{x + 18}" y="{y + h - 31}" width="{w - 36}" height="12" rx="6" fill="#274846"/>
          <rect x="{x + 18}" y="{y + h - 31}" width="{(w - 36) * 0.62:.1f}" height="12" rx="6" fill="#6B9891"/>
        </g>'''

    parts.append(player_panel(590, 92, 420, 104, "白露", "哑火 · 火炮", 13))
    parts.append(player_panel(52, 208, 272, 128, "青禾", "安全港 · 船锚", 18))
    parts.append(player_panel(1276, 208, 272, 128, "赤岩", "魔柜 → 阿岚", 14))

    parts.extend([
        f'<text x="205" y="379" text-anchor="middle" font-family="{FONT_STACK}" font-size="13" fill="#B7C8C1">弃牌 · 2</text>',
        f'<rect x="168" y="392" width="76" height="108" rx="9" fill="#D6C69F" stroke="#8B7855" stroke-width="2" transform="rotate(-4 206 446)"/>',
        f'<rect x="174" y="388" width="76" height="108" rx="9" fill="#EADDBF" stroke="#B49A68" stroke-width="2"/>',
        f'<path d="M190 424C210 407 230 441 236 420M188 452C213 436 229 468 239 447" fill="none" stroke="#6F4F32" stroke-width="4"/>',
        f'<text x="1394" y="379" text-anchor="middle" font-family="{FONT_STACK}" font-size="13" fill="#B7C8C1">抽牌 · 33</text>',
        f'<rect x="1356" y="397" width="78" height="110" rx="10" fill="#203F3E" stroke="#B28A4A" stroke-width="2"/>',
        f'<path d="M1372 419L1418 485M1418 419L1372 485" stroke="#B28A4A" stroke-width="5" opacity="0.65"/>',
        f'<rect x="1371" y="412" width="48" height="80" rx="18" fill="none" stroke="#789A92" stroke-width="2"/>',
    ])

    lane_x, lane_y = 390, 302
    lane_cards = [
        ("cannon", 6, True),
        ("anchor", 5, False),
        ("map", 4, False),
        ("kraken", 3, False),
        ("mermaid", 8, False),
    ]
    parts.append(f'<rect x="360" y="273" width="880" height="270" rx="30" fill="#102F2E" stroke="#39605D" stroke-dasharray="8 8"/>')
    parts.append(f'<text x="386" y="298" font-family="{FONT_STACK}" font-size="15" font-weight="700" fill="#C6D6CF">本回合航道</text>')
    for index, (suit_id, value, protected) in enumerate(lane_cards):
        parts.append(mini_card(suits[suit_id], value, lane_x + index * 145, lane_y, protected=protected))
        parts.append(f'<text x="{lane_x + index * 145 + 39}" y="{lane_y + 128}" text-anchor="middle" font-family="{FONT_STACK}" font-size="11" fill="#8FACA5">{index + 1}</text>')
    parts.append(f'<path d="M390 438H468" stroke="{theme["protected"]}" stroke-width="4"/><text x="429" y="458" text-anchor="middle" font-family="{FONT_STACK}" font-size="11" fill="#93B7AE">船锚保护</text>')

    parts.extend([
        f'<rect x="535" y="557" width="530" height="58" rx="20" fill="#203F3E" stroke="#4F7F78"/>',
        f'<text x="568" y="592" font-family="{FONT_STACK}" font-size="16" fill="#FFF9EA">爆牌花色：炮 · 锚 · 图 · 怪 · 鱼</text>',
        f'<rect x="938" y="568" width="101" height="34" rx="17" fill="#A3473D" opacity="0.85"/>',
        f'<text x="988" y="591" text-anchor="middle" font-family="{FONT_STACK}" font-size="14" font-weight="700" fill="#FFF9EA">海怪 1</text>',
        f'<text x="244" y="650" font-family="{FONT_STACK}" font-size="17" font-weight="700" fill="#FFF9EA">你的银行 · 阿岚 · 13 分 · 领航员</text>',
    ])
    for index, suit in enumerate(catalog["suits"]):
        x = 236 + index * 113
        value = [7, 6, 0, 0, 0, 0, 0, 0, 0, 0][index]
        parts.append(f'<rect x="{x}" y="670" width="96" height="104" rx="13" fill="#183534" stroke="#496B67"/>')
        parts.append(icon_svg(suit["icon"], x + 48, 708, 0.20, suit["color"]))
        parts.append(f'<text x="{x + 48}" y="752" text-anchor="middle" font-family="{FONT_STACK}" font-size="13" fill="#DCE7E1">{esc(suit["nameZh"])}</text>')
        parts.append(f'<text x="{x + 82}" y="696" text-anchor="end" font-family="{FONT_STACK}" font-size="20" font-weight="700" fill="#F2C96D">{value if value else "—"}</text>')

    parts.extend([
        f'<rect x="500" y="805" width="256" height="66" rx="22" fill="#B28A4A"/>',
        f'<text x="628" y="846" text-anchor="middle" font-family="{FONT_STACK}" font-size="22" font-weight="700" fill="#172E2D">继续抽牌</text>',
        f'<rect x="778" y="805" width="256" height="66" rx="22" fill="#284847" stroke="#668882" stroke-width="2"/>',
        f'<text x="906" y="846" text-anchor="middle" font-family="{FONT_STACK}" font-size="21" font-weight="700" fill="#879B96">收牌（海怪未完成）</text>',
        f'<text x="1522" y="850" text-anchor="end" font-family="{FONT_STACK}" font-size="12" fill="#78958E">原创场景原型 · 1600×900</text>',
    ])
    return svg_document(width, height, "".join(parts), title="亡命神抽四人牌桌场景原型", model_version=catalog["modelVersion"], source_sha=source_sha)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def main() -> int:
    catalog = load_json(CATALOG_PATH)
    scene = load_json(SCENE_PATH)
    combined_source = CATALOG_PATH.read_bytes() + b"\n" + SCENE_PATH.read_bytes()
    source_sha = sha256_bytes(combined_source)
    outputs = {
        "loot-card-atlas.svg": build_loot_atlas(catalog, source_sha),
        "trait-card-atlas.svg": build_trait_atlas(catalog, source_sha),
        "table-scene.svg": build_table_scene(catalog, scene, source_sha),
    }
    for filename, content in outputs.items():
        write_text(ASSET_DIR / filename, content)

    manifest = {
        "schemaVersion": 1,
        "modelVersion": catalog["modelVersion"],
        "generator": "scripts/generate_assets.py",
        "sourceFiles": {
            "model/card-catalog.json": sha256_file(CATALOG_PATH),
            "model/scene-catalog.json": sha256_file(SCENE_PATH),
        },
        "combinedSourceSha256": source_sha,
        "outputs": [
            {
                "path": f"assets/{filename}",
                "sha256": sha256_file(ASSET_DIR / filename),
                "bytes": (ASSET_DIR / filename).stat().st_size,
            }
            for filename in outputs
        ],
    }
    write_text(ASSET_DIR / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    for item in manifest["outputs"]:
        print(f"Generated {item['path']} ({item['bytes']} bytes)")
    print("Generated assets/manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
