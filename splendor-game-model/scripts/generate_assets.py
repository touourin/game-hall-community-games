#!/usr/bin/env python3
"""Generate original functional card and table SVG prototypes from the models."""

from __future__ import annotations

import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "model"
ASSETS = ROOT / "assets"
MODEL_VERSION = "1.0.0"
COLORS = ("white", "blue", "green", "red", "black")
FILL = {
    "white": "#E8E3D8",
    "blue": "#3A739A",
    "green": "#4E8068",
    "red": "#A8524B",
    "black": "#353A3D",
    "gold": "#C79B43",
}
NAMES = {
    "white": "钻石",
    "blue": "蓝宝石",
    "green": "祖母绿",
    "red": "红宝石",
    "black": "缟玛瑙",
    "gold": "黄金",
}
SYMBOLS = {
    "white": "◇",
    "blue": "◆",
    "green": "⬟",
    "red": "⬢",
    "black": "●",
    "gold": "★",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = "\n".join(line.rstrip() for line in value.splitlines()) + "\n"
    path.write_text(normalized, encoding="utf-8")


def text_color(color: str) -> str:
    return "#20292D" if color == "white" else "#FFFFFF"


def cost_badges(cost: dict[str, int], width: int, y: int) -> str:
    nonzero = [(color, cost[color]) for color in COLORS if cost[color] > 0]
    if not nonzero:
        return f'<text x="{width / 2}" y="{y}" class="micro" text-anchor="middle">免费</text>'
    spacing = min(25, (width - 20) / len(nonzero))
    total = spacing * len(nonzero)
    start = (width - total) / 2 + spacing / 2
    parts = []
    for index, (color, amount) in enumerate(nonzero):
        x = start + index * spacing
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y - 5}" r="10.5" fill="{FILL[color]}" '
            f'stroke="#172225" stroke-width="1.5"/>'
            f'<text x="{x:.1f}" y="{y - 1}" class="cost" text-anchor="middle" '
            f'fill="{text_color(color)}">{amount}</text>'
        )
    return "".join(parts)


def gem_motif(color: str, cx: int = 70, cy: int = 87) -> str:
    stroke = FILL[color]
    return (
        f'<polygon points="{cx},{cy - 35} {cx + 35},{cy - 10} {cx + 24},{cy + 31} '
        f'{cx - 24},{cy + 31} {cx - 35},{cy - 10}" fill="none" stroke="{stroke}" stroke-width="5"/>'
        f'<path d="M{cx - 35} {cy - 10} L{cx + 24} {cy + 31} M{cx + 35} {cy - 10} '
        f'L{cx - 24} {cy + 31} M{cx} {cy - 35} V{cy + 31}" fill="none" '
        f'stroke="{stroke}" stroke-width="2.5" opacity="0.75"/>'
    )


def card_svg(card: dict, x: int, y: int, width: int = 140, height: int = 190) -> str:
    bonus = card["bonusColor"]
    prestige = card["prestige"]
    score = str(prestige) if prestige else "-"
    label = html.escape(card["accessibility"]["labelZh"])
    return f"""
    <g transform="translate({x} {y})" data-card-id="{card['id']}" role="img" aria-label="{label}">
      <title>{label}</title>
      <rect width="{width}" height="{height}" rx="13" fill="#F7F3EA" stroke="#C7BDAA" stroke-width="2"/>
      <rect x="5" y="5" width="{width - 10}" height="42" rx="10" fill="{FILL[bonus]}"/>
      <text x="16" y="33" class="score" fill="{text_color(bonus)}">{score}</text>
      <text x="{width - 14}" y="31" class="bonus" text-anchor="end" fill="{text_color(bonus)}">{SYMBOLS[bonus]}</text>
      <text x="{width / 2}" y="62" class="micro" text-anchor="middle">{card['level']} 级 · {NAMES[bonus]}奖励</text>
      {gem_motif(bonus, width // 2, 105)}
      <rect x="7" y="148" width="{width - 14}" height="35" rx="9" fill="#E6DFD2" stroke="#C7BDAA"/>
      {cost_badges(card['cost'], width, 172)}
      <text x="10" y="143" class="id">{card['id']}</text>
    </g>"""


def card_back(level: int, x: int, y: int, scale: float = 1.0) -> str:
    marks = " ".join("◇" for _ in range(level))
    return f"""
    <g transform="translate({x} {y}) scale({scale})" role="img" aria-label="{level}级发展卡牌背">
      <rect width="88" height="118" rx="11" fill="#24383D" stroke="#C79B43" stroke-width="2"/>
      <rect x="8" y="8" width="72" height="102" rx="8" fill="url(#backPattern)" stroke="#718487"/>
      <text x="44" y="54" class="back-level" text-anchor="middle">{level} 级</text>
      <text x="44" y="80" class="back-marks" text-anchor="middle">{marks}</text>
    </g>"""


def noble_svg(noble: dict, x: int, y: int, size: int = 140) -> str:
    req = [(color, noble["requirement"][color]) for color in COLORS if noble["requirement"][color]]
    label = html.escape(noble["accessibility"]["labelZh"])
    badges = []
    spacing = 34
    start = size / 2 - spacing * (len(req) - 1) / 2
    for index, (color, amount) in enumerate(req):
        bx = start + index * spacing
        badges.append(
            f'<circle cx="{bx:.1f}" cy="112" r="14" fill="{FILL[color]}" stroke="#172225" stroke-width="2"/>'
            f'<text x="{bx:.1f}" y="117" class="noble-cost" text-anchor="middle" fill="{text_color(color)}">{amount}</text>'
        )
    return f"""
    <g transform="translate({x} {y})" data-noble-id="{noble['id']}" role="img" aria-label="{label}">
      <title>{label}</title>
      <rect width="{size}" height="{size}" rx="15" fill="#EFE3C9" stroke="#B78A3F" stroke-width="3"/>
      <text x="14" y="31" class="score" fill="#60461E">3</text>
      <circle cx="70" cy="61" r="23" fill="#73665B" opacity="0.28"/>
      <path d="M35 96 Q70 64 105 96" fill="#73665B" opacity="0.28"/>
      {''.join(badges)}
      <text x="70" y="134" class="noble-id" text-anchor="middle">{noble['id'].replace('noble-', '')}</text>
    </g>"""


def generate_atlas(catalog: dict) -> str:
    cards_by_level = {
        level: [card for card in catalog["developmentCards"] if card["level"] == level]
        for level in (1, 2, 3)
    }
    sections = []
    specs = {3: (150, 2), 2: (590, 3), 1: (1230, 4)}
    for level in (3, 2, 1):
        start_y, rows = specs[level]
        sections.append(
            f'<text x="70" y="{start_y}" class="section">{level} 级发展卡 · '
            f'{len(cards_by_level[level])} 张</text>'
        )
        for index, card in enumerate(cards_by_level[level]):
            row, col = divmod(index, 10)
            sections.append(card_svg(card, 70 + col * 158, start_y + 24 + row * 205))
        if rows != (len(cards_by_level[level]) + 9) // 10:
            raise ValueError("atlas row specification mismatch")

    nobles = []
    for index, noble in enumerate(catalog["nobles"]):
        nobles.append(noble_svg(noble, 70 + index * 158, 2240))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1720" height="2435" viewBox="0 0 1720 2435"
  data-model-version="{MODEL_VERSION}" role="img" aria-labelledby="atlas-title atlas-desc">
  <title id="atlas-title">璀璨宝石完整功能卡牌图集</title>
  <desc id="atlas-desc">90张发展卡、3种等级牌背与10张贵族板块的原创中性功能原型。</desc>
  <defs>
    <pattern id="backPattern" width="16" height="16" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <rect width="16" height="16" fill="#24383D"/>
      <path d="M0 0 V16 M8 0 V16" stroke="#3F575C" stroke-width="2"/>
    </pattern>
    <style>
      text {{ font-family: "Microsoft YaHei", "Noto Sans CJK SC", sans-serif; fill: #20292D; }}
      .eyebrow {{ font-size: 16px; font-weight: 800; letter-spacing: 2px; fill: #D5B66E; }}
      .title {{ font-size: 38px; font-weight: 900; fill: #F4F0E7; }}
      .subtitle {{ font-size: 16px; fill: #B7C8C6; }}
      .section {{ font-size: 22px; font-weight: 900; fill: #F4F0E7; }}
      .score {{ font-size: 25px; font-weight: 900; }}
      .bonus {{ font-size: 24px; font-weight: 900; }}
      .cost {{ font-size: 12px; font-weight: 900; }}
      .micro {{ font-size: 10px; font-weight: 800; }}
      .id {{ font-size: 7px; fill: #596468; }}
      .back-level {{ font-size: 16px; font-weight: 900; fill: #F4F0E7; }}
      .back-marks {{ font-size: 13px; fill: #D5B66E; }}
      .noble-cost {{ font-size: 15px; font-weight: 900; }}
      .noble-id {{ font-size: 7px; fill: #655B4D; }}
    </style>
  </defs>
  <rect width="1720" height="2435" fill="#102426"/>
  <text x="70" y="42" class="eyebrow">GAME HALL · FUNCTIONAL CARD ATLAS v1.0.0</text>
  <text x="70" y="88" class="title">璀璨宝石 · 90 张发展卡与 10 张贵族</text>
  <text x="70" y="116" class="subtitle">完整规则数值 · 原创几何占位 · 颜色、名称与符号双重编码</text>
  {card_back(1, 1380, 14)}
  {card_back(2, 1478, 14)}
  {card_back(3, 1576, 14)}
  {''.join(sections)}
  <text x="70" y="2210" class="section">贵族板块 · 10 张</text>
  {''.join(nobles)}
  <text x="70" y="2410" class="subtitle">仅用于软件建模与视觉 QA；不含任何官方美术或可印刷复刻素材。</text>
</svg>"""


def mini_card(card: dict, x: int, y: int) -> str:
    bonus = card["bonusColor"]
    return f"""
    <g transform="translate({x} {y})">
      <rect width="102" height="112" rx="10" fill="#F7F3EA" stroke="#C7BDAA" stroke-width="2"/>
      <rect x="5" y="5" width="92" height="27" rx="7" fill="{FILL[bonus]}"/>
      <text x="14" y="25" class="small-score" fill="{text_color(bonus)}">{card['prestige'] or '-'}</text>
      <text x="88" y="24" class="small-score" text-anchor="end" fill="{text_color(bonus)}">{SYMBOLS[bonus]}</text>
      <polygon points="51,43 74,58 66,84 36,84 28,58" fill="none" stroke="{FILL[bonus]}" stroke-width="4"/>
      {cost_badges(card['cost'], 102, 103)}
    </g>"""


def generate_table_scene(catalog: dict) -> str:
    by_level = {
        level: [card for card in catalog["developmentCards"] if card["level"] == level][:4]
        for level in (1, 2, 3)
    }
    market_rows = []
    row_y = {3: 364, 2: 516, 1: 668}
    for level in (3, 2, 1):
        y = row_y[level]
        cards = "".join(mini_card(card, 330 + index * 118, y) for index, card in enumerate(by_level[level]))
        market_rows.append(
            f'<g data-zone-id="tier_{level}_market">'
            f'<rect x="72" y="{y}" width="102" height="112" rx="10" fill="#24383D" stroke="#C79B43" stroke-width="2"/>'
            f'<text x="123" y="{y + 48}" class="deck" text-anchor="middle">{level} 级</text>'
            f'<text x="123" y="{y + 75}" class="deck-count" text-anchor="middle">牌堆</text>'
            f'<text x="204" y="{y + 61}" class="row-title">{level}级市场</text>{cards}</g>'
        )
    nobles = "".join(
        f'<g transform="translate({204 + index * 122} 236)"><rect width="108" height="108" rx="12" fill="#EFE3C9" stroke="#B78A3F" stroke-width="2"/>'
        f'<text x="14" y="27" class="small-score" fill="#60461E">3</text><circle cx="54" cy="50" r="19" fill="#75685B" opacity=".25"/>'
        f'<text x="54" y="89" class="tiny" text-anchor="middle">要求 {"4+4" if index < 2 else "3+3+3"}</text></g>'
        for index in range(4)
    )
    tokens = "".join(
        f'<g transform="translate({1142 + (index % 2) * 150} {286 + (index // 2) * 82})">'
        f'<circle cx="28" cy="28" r="25" fill="{FILL[color]}" stroke="#E9E2D4" stroke-width="2"/>'
        f'<text x="28" y="34" class="token-symbol" text-anchor="middle" fill="{text_color(color)}">{SYMBOLS[color]}</text>'
        f'<text x="66" y="24" class="token-name">{NAMES[color]}</text><text x="66" y="46" class="token-count">× {5 if color != "gold" else 4}</text></g>'
        for index, color in enumerate((*COLORS, "gold"))
    )
    engine = "".join(
        f'<g transform="translate({82 + index * 120} 866)"><rect width="104" height="75" rx="9" fill="#E9E4DA" stroke="{FILL[color]}" stroke-width="3"/>'
        f'<text x="52" y="31" class="engine-title" text-anchor="middle">{SYMBOLS[color]} {NAMES[color]}</text>'
        f'<text x="52" y="56" class="engine-count" text-anchor="middle">奖励 {index % 3}</text></g>'
        for index, color in enumerate(COLORS)
    )
    opponents = "".join(
        f'<g transform="translate({324 + index * 318} 112)"><rect width="294" height="76" rx="14" fill="#244144" stroke="{("#E8BD62" if index == 0 else "#537174")}" stroke-width="2"/>'
        f'<text x="18" y="28" class="opponent">P{index + 2} · {("当前行动" if index == 0 else "等待")}</text>'
        f'<text x="18" y="55" class="opponent-meta">威望 {index + 3} · 奖励 {index + 2} · 保留 {index % 2}</text></g>'
        for index in range(3)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000"
  data-model-version="{MODEL_VERSION}" role="img" aria-labelledby="scene-title scene-desc">
  <title id="scene-title">璀璨宝石四人数字牌桌场景</title>
  <desc id="scene-desc">顶部状态和对手轨、左侧贵族与三层市场、右侧棋子供应和事件、底部本人引擎与操作区。</desc>
  <defs><style>
    text {{ font-family: "Microsoft YaHei", "Noto Sans CJK SC", sans-serif; fill: #EDF1EC; }}
    .eyebrow {{ font-size: 14px; font-weight: 800; letter-spacing: 2px; fill: #E8BD62; }}
    .scene-title {{ font-size: 27px; font-weight: 900; }}
    .status {{ font-size: 17px; font-weight: 800; }}
    .opponent {{ font-size: 16px; font-weight: 800; }}
    .opponent-meta {{ font-size: 13px; fill: #B8CAC7; }}
    .zone-title {{ font-size: 18px; font-weight: 900; }}
    .row-title {{ font-size: 16px; font-weight: 800; }}
    .deck {{ font-size: 18px; font-weight: 900; fill: #F4F0E7; }}
    .deck-count {{ font-size: 11px; fill: #C5D1CF; }}
    .small-score {{ font-size: 17px; font-weight: 900; }}
    .cost {{ font-size: 10px; font-weight: 900; }}
    .tiny {{ font-size: 10px; fill: #554D43; }}
    .token-symbol {{ font-size: 22px; font-weight: 900; }}
    .token-name {{ font-size: 14px; font-weight: 800; }}
    .token-count {{ font-size: 13px; fill: #B8CAC7; }}
    .event {{ font-size: 13px; fill: #B8CAC7; }}
    .engine-title {{ font-size: 13px; font-weight: 800; fill: #293135; }}
    .engine-count {{ font-size: 12px; fill: #596468; }}
    .action {{ font-size: 16px; font-weight: 900; }}
    .action-meta {{ font-size: 12px; fill: #B8CAC7; }}
  </style></defs>
  <rect width="1600" height="1000" fill="#102426"/>
  <rect x="24" y="24" width="1552" height="952" rx="28" fill="#173B3A" stroke="#6A5138" stroke-width="4"/>
  <text x="52" y="52" class="eyebrow">GAME HALL · SCENE MODEL v1.0.0</text>
  <text x="52" y="83" class="scene-title">璀璨宝石 · 四人桌面功能线框</text>
  <g data-zone-id="status_bar"><rect x="640" y="42" width="908" height="48" rx="13" fill="#203638" stroke="#537174"/><text x="664" y="72" class="status">第 3 轮 · 轮到 P2 · 首位玩家 P1 · 尚未触发最终轮</text></g>
  <g data-zone-id="opponent_rail">{opponents}</g>
  <g data-zone-id="noble_row"><rect x="52" y="212" width="1000" height="140" rx="18" fill="#142D2E" stroke="#537174"/><text x="72" y="244" class="zone-title">贵族 · 4 张</text>{nobles}</g>
  {''.join(market_rows)}
  <g data-zone-id="gem_supply"><rect x="1108" y="212" width="440" height="324" rx="18" fill="#142D2E" stroke="#537174"/><text x="1132" y="248" class="zone-title">公共供应</text>{tokens}</g>
  <g data-zone-id="event_strip"><rect x="1108" y="552" width="440" height="244" rx="18" fill="#142D2E" stroke="#537174"/><text x="1132" y="588" class="zone-title">最近事件</text><text x="1132" y="624" class="event">P1 从 2 级牌堆盲保留一张牌</text><text x="1132" y="652" class="event">P2 拿取蓝、绿、红各一枚</text><text x="1132" y="680" class="event">2 级市场补充一张牌</text><text x="1132" y="744" class="event">盲保留身份仅持有者可见</text></g>
  <g data-zone-id="self_tableau"><rect x="52" y="826" width="642" height="130" rx="18" fill="#142D2E" stroke="#E8BD62" stroke-width="2"/><text x="76" y="856" class="zone-title">本人引擎 · 威望 4 · 已购 6</text>{engine}</g>
  <g data-zone-id="reserved_drawer"><rect x="714" y="826" width="310" height="130" rx="18" fill="#142D2E" stroke="#537174"/><text x="736" y="856" class="zone-title">保留牌 1 / 3</text>{card_back(2, 748, 866, 0.72)}</g>
  <g data-zone-id="action_dock"><rect x="1044" y="826" width="504" height="130" rx="18" fill="#203638" stroke="#E8BD62" stroke-width="2"/><text x="1068" y="860" class="action">选择一项主要行动</text><text x="1068" y="892" class="action-meta">取不同色 · 取同色两枚 · 保留 · 购买</text><rect x="1368" y="878" width="152" height="50" rx="12" fill="#B78A3F"/><text x="1444" y="909" class="action" text-anchor="middle" fill="#182325">确认</text></g>
  <g data-zone-id="payment_sheet" opacity="0"><rect x="848" y="120" width="700" height="740"/></g>
  <g data-zone-id="resolution_sheet" opacity="0"><rect x="400" y="200" width="800" height="600"/></g>
  <text x="52" y="986" class="event">原创功能原型 · 不含官方 Logo、插画、肖像、卡框或扫描素材</text>
</svg>"""


def main() -> None:
    catalog = load_json(MODEL / "card-catalog.json")
    if catalog["modelVersion"] != MODEL_VERSION:
        raise ValueError("card catalog version does not match generator")
    write_text(ASSETS / "development-card-atlas.svg", generate_atlas(catalog))
    write_text(ASSETS / "table-scene.svg", generate_table_scene(catalog))
    print("Generated complete 90-card atlas, 10 nobles, and table scene SVG.")


if __name__ == "__main__":
    main()
