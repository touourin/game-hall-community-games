#!/usr/bin/env python3
"""Generate the Manila share catalog and original SVG model sheets."""

from __future__ import annotations

import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "model"
ASSET_DIR = ROOT / "assets"
MODEL_VERSION = "1.0.0"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, value: dict) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2))


def generate_card_catalog(card_model: dict) -> dict:
    cards = []
    for commodity in card_model["commodities"]:
        for copy_index in range(1, card_model["copiesPerCommodity"] + 1):
            cards.append(
                {
                    "id": f"share-{commodity['id']}-{copy_index:02d}",
                    "kind": "commodity_share",
                    "commodityId": commodity["id"],
                    "commodityLabel": commodity["label"],
                    "commodityCode": commodity["code"],
                    "copyIndex": copy_index,
                    "pattern": commodity["pattern"],
                    "semanticColor": commodity["semanticColor"],
                    "ariaLabel": (
                        f"{commodity['label']}份额，第 {copy_index} 张"
                    ),
                }
            )
    return {
        "schemaVersion": 1,
        "modelVersion": MODEL_VERSION,
        "gameKey": "manila",
        "modelId": card_model["modelId"],
        "source": "./card-model.json",
        "cardCount": len(cards),
        "cardsPerCommodity": card_model["copiesPerCommodity"],
        "cards": cards,
    }


def commodity_art(commodity_id: str, color: str) -> str:
    if commodity_id == "ginseng":
        return (
            f'<path d="M90 94 C68 110 72 139 54 158 M90 94 '
            f'C111 111 105 142 125 158 M90 112 L90 168" '
            f'fill="none" stroke="{color}" stroke-width="7" '
            'stroke-linecap="round"/>'
        )
    if commodity_id == "nutmeg":
        circles = [
            (65, 112, 15),
            (101, 101, 17),
            (125, 136, 15),
            (83, 149, 18),
        ]
        return "".join(
            f'<circle cx="{x}" cy="{y}" r="{radius}" '
            f'fill="none" stroke="{color}" stroke-width="6"/>'
            for x, y, radius in circles
        )
    if commodity_id == "silk":
        return "".join(
            f'<path d="M45 {y} C75 {y - 18} 108 {y + 18} 138 {y}" '
            f'fill="none" stroke="{color}" stroke-width="7" '
            'stroke-linecap="round"/>'
            for y in (104, 128, 152)
        )
    return (
        f'<polygon points="91,86 133,113 119,160 63,160 49,113" '
        f'fill="none" stroke="{color}" stroke-width="7"/>'
        f'<path d="M49 113 L119 160 M133 113 L63 160 M91 86 L91 160" '
        f'fill="none" stroke="{color}" stroke-width="4"/>'
    )


def card_front_svg(commodity: dict, x: int, y: int) -> str:
    color = commodity["semanticColor"]
    label = html.escape(commodity["label"])
    label_en = html.escape(commodity["labelEn"])
    code = html.escape(commodity["code"])
    art = commodity_art(commodity["id"], color)
    return f"""
    <g transform="translate({x} {y})" role="img"
       aria-label="{label}份额卡正面">
      <rect width="180" height="260" rx="18" fill="#F4F0E7"
            stroke="#D8CDBB" stroke-width="3"/>
      <rect x="13" y="13" width="154" height="234" rx="12"
            fill="#FBF8F1" stroke="{color}" stroke-width="3"/>
      <text x="25" y="42" class="micro">{code} · 货物份额</text>
      <line x1="25" y1="53" x2="155" y2="53" stroke="{color}"
            stroke-width="3"/>
      {art}
      <text x="90" y="200" class="card-title" text-anchor="middle">{label}</text>
      <text x="90" y="224" class="card-en" text-anchor="middle">{label_en}</text>
      <text x="90" y="243" class="micro" text-anchor="middle">SHARE 01-05</text>
    </g>"""


def generate_share_sheet(card_model: dict) -> str:
    cards = []
    for index, commodity in enumerate(card_model["commodities"]):
        cards.append(card_front_svg(commodity, 60 + index * 235, 215))

    return f"""<svg xmlns="http://www.w3.org/2000/svg"
  width="1600" height="720" viewBox="0 0 1600 720"
  data-model-version="{MODEL_VERSION}" role="img"
  aria-labelledby="title description">
  <title id="title">马尼拉份额卡原创模型板</title>
  <desc id="description">四种份额卡正面、统一牌背和抵押状态。</desc>
  <defs>
    <pattern id="back-grid" width="22" height="22"
      patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <rect width="22" height="22" fill="#213A3C"/>
      <path d="M0 0 V22 M11 0 V22" stroke="#426164" stroke-width="3"/>
    </pattern>
    <style>
      text {{
        font-family: "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
        fill: #263234;
      }}
      .eyebrow {{ font-size: 18px; font-weight: 700; letter-spacing: 2px; fill: #B4862C; }}
      .title {{ font-size: 40px; font-weight: 800; }}
      .subtitle {{ font-size: 18px; fill: #607074; }}
      .card-title {{ font-size: 30px; font-weight: 800; }}
      .card-en {{ font-size: 15px; fill: #687579; }}
      .micro {{ font-size: 13px; font-weight: 700; letter-spacing: 1px; }}
      .note {{ font-size: 16px; fill: #D6E0DE; }}
      .state {{ font-size: 18px; font-weight: 800; fill: #F2E6C8; }}
    </style>
  </defs>
  <rect width="1600" height="720" fill="#16282A"/>
  <rect x="28" y="28" width="1544" height="664" rx="28"
        fill="#EEF0EA" stroke="#607D79" stroke-width="2"/>
  <text x="60" y="82" class="eyebrow">GAME HALL · CARD MODEL v1.0.0</text>
  <text x="60" y="132" class="title">马尼拉 · 货物份额卡</text>
  <text x="60" y="170" class="subtitle">
    规则身份由文字、代码与纹样共同表达；颜色不是唯一编码。
  </text>
  {''.join(cards)}
  <g transform="translate(1010 215)" role="img" aria-label="统一份额牌背">
    <rect width="180" height="260" rx="18" fill="#172728"
          stroke="#D7BE81" stroke-width="3"/>
    <rect x="13" y="13" width="154" height="234" rx="12"
          fill="url(#back-grid)" stroke="#8DA7A3" stroke-width="2"/>
    <path d="M45 132 H135 M90 87 V177" stroke="#D7BE81"
          stroke-width="8" stroke-linecap="round"/>
    <circle cx="90" cy="132" r="46" fill="none"
            stroke="#D7BE81" stroke-width="4"/>
    <text x="90" y="222" class="state" text-anchor="middle">私密份额</text>
  </g>
  <g transform="translate(1245 215)" role="img" aria-label="抵押份额状态">
    <rect width="260" height="260" rx="18" fill="#F4F0E7"
          stroke="#9A5C3A" stroke-width="3"/>
    <rect x="18" y="18" width="224" height="224" rx="12"
          fill="#FBF8F1" stroke="#D8CDBB" stroke-width="2"/>
    <text x="130" y="66" class="card-title" text-anchor="middle">已抵押</text>
    <text x="130" y="105" class="subtitle" text-anchor="middle">获得 12 比索</text>
    <line x1="42" y1="128" x2="218" y2="128" stroke="#9A5C3A"
          stroke-width="4"/>
    <text x="130" y="171" class="card-title" text-anchor="middle">赎回 15</text>
    <text x="130" y="207" class="subtitle" text-anchor="middle">仍计货物市值</text>
    <text x="130" y="231" class="micro" text-anchor="middle">对手只看抵押数量</text>
  </g>
  <rect x="60" y="530" width="1445" height="108" rx="18" fill="#223A3C"/>
  <text x="88" y="569" class="note">隐私：本人看牌面与实例 ID；对手和中立视角只看份额数与抵押数。</text>
  <text x="88" y="603" class="note">版权边界：原创中性几何，不复刻官方 Logo、卡面插画、字体或扫描图。</text>
</svg>"""


def generate_scene_blueprint(component_catalog: dict) -> str:
    commodities = component_catalog["commodities"]
    market_rows = []
    for index, commodity in enumerate(commodities):
        y = 246 + index * 82
        color = commodity["semanticColor"]
        values = "  ".join(str(value) for value in component_catalog["marketTrack"])
        market_rows.append(
            f'<g transform="translate(0 {y})">'
            f'<rect x="56" y="0" width="224" height="62" rx="12" fill="#203638" '
            f'stroke="{color}" stroke-width="3"/>'
            f'<text x="76" y="26" class="zone-title">{html.escape(commodity["label"])} '
            f'· {html.escape(commodity["code"])}</text>'
            f'<text x="76" y="49" class="micro">{values}</text>'
            '</g>'
        )

    route_groups = []
    route_specs = [
        ("lane-1", "人参 · GS", "#B4862C", 4),
        ("lane-2", "肉豆蔻 · NM", "#9A5C3A", 3),
        ("lane-3", "玉石 · JD", "#3F806E", 2),
    ]
    for index, (lane_id, label, color, position) in enumerate(route_specs):
        y = 300 + index * 150
        ticks = []
        for value in range(14):
            x = 386 + value * 54
            tick_color = "#E0B55E" if value == 13 else "#607B7E"
            ticks.append(
                f'<line x1="{x}" y1="{y + 34}" x2="{x}" y2="{y + 50}" '
                f'stroke="{tick_color}" stroke-width="3"/>'
                f'<text x="{x}" y="{y + 72}" class="tick" text-anchor="middle">{value}</text>'
            )
        boat_x = 386 + position * 54 - 35
        route_groups.append(
            f'<g id="{lane_id}">'
            f'<text x="360" y="{y + 4}" class="micro">{lane_id}</text>'
            f'<text x="360" y="{y + 28}" class="zone-title">{label}</text>'
            f'<line x1="386" y1="{y + 42}" x2="1088" y2="{y + 42}" '
            'stroke="#759497" stroke-width="7" stroke-linecap="round"/>'
            f'{''.join(ticks)}'
            f'<g transform="translate({boat_x} {y + 8})">'
            f'<rect width="70" height="52" rx="18" fill="{color}" stroke="#F3E6C9" stroke-width="3"/>'
            '<circle cx="22" cy="26" r="8" fill="#F3E6C9"/>'
            '<circle cx="48" cy="26" r="8" fill="#F3E6C9"/>'
            '</g></g>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg"
  width="1600" height="1000" viewBox="0 0 1600 1000"
  data-model-version="{MODEL_VERSION}" role="img"
  aria-labelledby="scene-title scene-description">
  <title id="scene-title">马尼拉数字牌桌场景蓝图</title>
  <desc id="scene-description">
    顶部玩家轨、左侧黑市、中部三条航线、右侧港口船坞、特殊岛和底部私密操作区。
  </desc>
  <defs>
    <style>
      text {{
        font-family: "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
        fill: #E8EFEC;
      }}
      .eyebrow {{ font-size: 15px; font-weight: 800; letter-spacing: 2px; fill: #E0B55E; }}
      .title {{ font-size: 31px; font-weight: 800; }}
      .zone-title {{ font-size: 17px; font-weight: 800; }}
      .body {{ font-size: 15px; fill: #B9CAC7; }}
      .micro {{ font-size: 13px; fill: #B9CAC7; }}
      .tick {{ font-size: 12px; fill: #C8D5D2; }}
      .slot {{ font-size: 14px; font-weight: 800; }}
    </style>
  </defs>
  <rect width="1600" height="1000" fill="#102426"/>
  <rect x="24" y="24" width="1552" height="952" rx="28"
        fill="#183033" stroke="#547477" stroke-width="2"/>

  <text x="48" y="68" class="eyebrow">GAME HALL · SCENE BLUEPRINT v1.0.0</text>
  <text x="48" y="108" class="title">马尼拉 · 沉浸式牌桌</text>

  <g id="player-rail">
    <rect x="48" y="132" width="1504" height="92" rx="18"
          fill="#213A3D" stroke="#48686B" stroke-width="2"/>
    <text x="68" y="160" class="micro">玩家财务轨 · 现金公开 · 份额种类私密</text>
    {''.join(
        f'<g transform="translate({70 + index * 292} 172)">'
        f'<rect width="264" height="38" rx="10" fill="{"#5C4930" if index == 0 else "#29464A"}" '
        f'stroke="{"#E0B55E" if index == 0 else "#607F82"}" stroke-width="2"/>'
        f'<text x="16" y="25" class="slot">P{index + 1} · '
        f'{"港务长" if index == 0 else "现金 30 · 份额 2"}</text></g>'
        for index in range(5)
    )}
  </g>

  <g id="market">
    <rect x="48" y="244" width="248" height="494" rx="18"
          fill="#172B2D" stroke="#48686B" stroke-width="2"/>
    <text x="68" y="278" class="zone-title">黑市与份额供应</text>
    {''.join(market_rows)}
    <text x="68" y="698" class="body">价值轨：0 → 5 → 10 → 20 → 30</text>
    <text x="68" y="722" class="micro">港务长每航行可买 0-1 张</text>
  </g>

  <g id="route-board">
    <rect x="320" y="244" width="804" height="494" rx="18"
          fill="#15383C" stroke="#5D8487" stroke-width="2"/>
    <text x="344" y="278" class="zone-title">三条航线 · 0-13</text>
    {''.join(route_groups)}
    <rect x="1056" y="290" width="52" height="424" rx="16"
          fill="#6C382F" opacity="0.58"/>
    <rect x="894" y="253" width="206" height="32" rx="10"
          fill="#6C382F" stroke="#A7685B" stroke-width="2"/>
    <text x="997" y="275" class="slot" text-anchor="middle">13 格 · 海盗检查</text>
  </g>

  <g id="destinations">
    <rect x="1148" y="244" width="404" height="494" rx="18"
          fill="#172B2D" stroke="#48686B" stroke-width="2"/>
    <text x="1170" y="278" class="zone-title">目的地区</text>
    <text x="1170" y="314" class="zone-title">港口</text>
    {''.join(
        f'<g transform="translate(1170 {326 + index * 64})">'
        f'<rect width="166" height="50" rx="12" fill="#244A49" stroke="#4F8580" stroke-width="2"/>'
        f'<text x="16" y="31" class="slot">{slot} · 成本 {cost} / 收益 {payout}</text></g>'
        for index, (slot, cost, payout) in enumerate((("A", 4, 6), ("B", 3, 8), ("C", 2, 15)))
    )}
    <text x="1360" y="314" class="zone-title">船坞</text>
    {''.join(
        f'<g transform="translate(1360 {326 + index * 64})">'
        f'<rect width="166" height="50" rx="12" fill="#483E35" stroke="#9A7550" stroke-width="2"/>'
        f'<text x="16" y="31" class="slot">{slot} · {cost} / {payout}</text></g>'
        for index, (slot, cost, payout) in enumerate((("A", 4, 6), ("B", 3, 8), ("C", 2, 15)))
    )}
    <g id="special-island" transform="translate(1170 548)">
      <rect width="356" height="164" rx="14" fill="#203638" stroke="#58777A" stroke-width="2"/>
      <text x="18" y="30" class="zone-title">特殊岛</text>
      <text x="18" y="61" class="body">海盗：船长 5 · 船员 5</text>
      <text x="18" y="89" class="body">引航：小 2 / ±1 · 大 5 / 总量 2</text>
      <text x="18" y="117" class="body">保险：立即 +10 · 承担入坞修理</text>
      <text x="18" y="145" class="micro">所有位置显示文字，不依赖颜色</text>
    </g>
  </g>

  <g id="private-zone">
    <rect x="48" y="760" width="1504" height="184" rx="18"
          fill="#111F21" stroke="#E0B55E" stroke-width="2"/>
    <text x="70" y="793" class="zone-title">本人私密区</text>
    <g transform="translate(70 814)">
      <rect width="82" height="110" rx="10" fill="#F3EFE6" stroke="#B4862C" stroke-width="3"/>
      <text x="41" y="58" text-anchor="middle" style="fill:#273436;font-size:18px;font-weight:800">GS</text>
      <text x="41" y="86" text-anchor="middle" style="fill:#273436;font-size:14px">人参</text>
    </g>
    <g transform="translate(168 814)">
      <rect width="82" height="110" rx="10" fill="#F3EFE6" stroke="#456F9E" stroke-width="3"/>
      <text x="41" y="58" text-anchor="middle" style="fill:#273436;font-size:18px;font-weight:800">SK</text>
      <text x="41" y="86" text-anchor="middle" style="fill:#273436;font-size:14px">丝绸</text>
    </g>
    <rect x="286" y="814" width="294" height="110" rx="14"
          fill="#203638" stroke="#58777A" stroke-width="2"/>
    <text x="308" y="847" class="slot">财务</text>
    <text x="308" y="878" class="body">现金 24 · 可抵押 2</text>
    <text x="308" y="906" class="body">抵押 +12 · 赎回 -15</text>
    <rect x="606" y="814" width="920" height="110" rx="14"
          fill="#29464A" stroke="#6D9295" stroke-width="2"/>
    <text x="630" y="848" class="slot">当前行动：部署助手</text>
    <text x="630" y="879" class="body">合法目标由服务端返回；成本、收益、风险同时展示。</text>
    <text x="630" y="908" class="micro">最小点击目标 44 x 44 · 键盘可达 · 动画不推进规则</text>
  </g>
</svg>"""


def main() -> None:
    card_model = load_json(MODEL_DIR / "card-model.json")
    component_catalog = load_json(MODEL_DIR / "component-catalog.json")
    if card_model["modelVersion"] != MODEL_VERSION:
        raise ValueError("card model version does not match generator")
    if component_catalog["modelVersion"] != MODEL_VERSION:
        raise ValueError("component model version does not match generator")

    write_json(
        MODEL_DIR / "card-catalog.json",
        generate_card_catalog(card_model),
    )
    write_text(
        ASSET_DIR / "share-card-sheet.svg",
        generate_share_sheet(card_model),
    )
    write_text(
        ASSET_DIR / "table-scene-blueprint.svg",
        generate_scene_blueprint(component_catalog),
    )
    print("Generated 20 share cards and 2 original SVG model sheets.")


if __name__ == "__main__":
    main()
