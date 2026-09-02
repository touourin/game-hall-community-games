from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT / "model"
ASSET_ROOT = ROOT / "assets"


def bullheads(number: int) -> int:
    if number == 55:
        return 7
    if number % 11 == 0:
        return 5
    if number % 10 == 0:
        return 3
    if number % 5 == 0:
        return 2
    return 1


def tier(points: int) -> str:
    return {
        1: "single",
        2: "double",
        3: "triple",
        5: "quintuple",
        7: "royal",
    }[points]


def card_catalog() -> dict[str, object]:
    cards = [
        {
            "id": f"card-{number:03d}",
            "number": number,
            "bullheads": bullheads(number),
            "tier": tier(bullheads(number)),
            "ariaLabel": f"{number}，{bullheads(number)} 牛头分",
        }
        for number in range(1, 105)
    ]
    distribution = Counter(card["bullheads"] for card in cards)
    return {
        "schemaVersion": 1,
        "generatedFrom": "card-model.json",
        "cards": cards,
        "statistics": {
            "cardCount": len(cards),
            "totalBullheads": sum(card["bullheads"] for card in cards),
            "distribution": {
                str(points): distribution[points]
                for points in (1, 2, 3, 5, 7)
            },
        },
    }


def horn_uses(points: int) -> str:
    width = (points - 1) * 12
    return "".join(
        f'<use href="#horn" x="{52 - width / 2 + index * 12:.1f}" y="116"/>'
        for index in range(points)
    )


def card_group(number: int, index: int) -> str:
    points = bullheads(number)
    palette = {
        1: ("#214d4d", "#5f8f82"),
        2: ("#78541f", "#d6a447"),
        3: ("#994835", "#df7354"),
        5: ("#6f365f", "#b9679b"),
        7: ("#7f281f", "#e24d35"),
    }[points]
    x = 42 + index * 132
    return f"""
    <g transform="translate({x} 108)" aria-label="{number}，{points} 牛头分">
      <rect width="104" height="148" rx="13" fill="#fff8e9" stroke="#142f32" stroke-width="4"/>
      <rect x="7" y="7" width="90" height="134" rx="9" fill="none" stroke="{palette[1]}" stroke-width="2"/>
      <text x="52" y="78" text-anchor="middle" fill="{palette[0]}" class="number">{number}</text>
      <g fill="{palette[1]}">{horn_uses(points)}</g>
      <text x="52" y="137" text-anchor="middle" fill="{palette[0]}" class="points">{points} 分</text>
    </g>"""


def model_sheet() -> str:
    samples = (1, 5, 10, 11, 55, 104)
    groups = "".join(card_group(number, index) for index, number in enumerate(samples))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 860 300" data-model-version="1" role="img" aria-labelledby="title desc">
  <title id="title">谁是牛头王卡牌模型板</title>
  <desc id="desc">普通、尾数五、整十、对子、五十五和一百零四号牌的原创视觉模型。</desc>
  <defs>
    <path id="horn" d="M1 4c2.5 0 3.5-2 4-4 .5 2 1.5 4 4 4-1 4-2.4 6-4 7-1.6-1-3-3-4-7Z"/>
    <style>
      .number {{ font: 800 43px Georgia, serif; }}
      .points {{ font: 700 10px 'Microsoft YaHei', sans-serif; letter-spacing: .08em; }}
      .label {{ font: 700 13px 'Microsoft YaHei', sans-serif; letter-spacing: .12em; }}
    </style>
  </defs>
  <rect width="860" height="300" rx="24" fill="#071f23"/>
  <path d="M22 62h816" stroke="#c49444" stroke-width="1" opacity=".45"/>
  <text x="30" y="39" fill="#f6e8c8" class="label">NUMBER CARD SYSTEM · 68 × 96 LOGICAL UNITS</text>
  {groups}
</svg>
"""


def table_blueprint() -> str:
    row_markup = []
    for row in range(4):
        y = 218 + row * 118
        slots = "".join(
            f'<rect x="{326 + column * 126}" y="{y}" width="102" height="92" rx="10" class="slot"/>'
            for column in range(5)
        )
        row_markup.append(
            f'<text x="212" y="{y + 55}" class="row-label">第 {row + 1} 行</text>{slots}'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 900" data-model-version="1" role="img" aria-labelledby="title desc">
  <title id="title">谁是牛头王牌桌场景蓝图</title>
  <desc id="desc">包括玩家计分轨、同时揭示轨、四条五卡行和底部私有手牌区。</desc>
  <style>
    .label {{ font: 700 18px 'Microsoft YaHei', sans-serif; fill: #f6e8c8; letter-spacing: .08em; }}
    .row-label {{ font: 700 17px 'Microsoft YaHei', sans-serif; fill: #c8ded8; }}
    .hint {{ font: 500 14px 'Microsoft YaHei', sans-serif; fill: #89aaa4; }}
    .zone {{ fill: #0c3437; stroke: #ba8b3f; stroke-width: 2; }}
    .slot {{ fill: #f8f0dd; fill-opacity: .08; stroke: #7fa099; stroke-width: 2; stroke-dasharray: 7 6; }}
  </style>
  <rect width="1440" height="900" rx="30" fill="#061a1d"/>
  <rect x="54" y="48" width="1332" height="86" rx="18" class="zone"/>
  <text x="82" y="83" class="label">PLAYER SCORE RAIL</text>
  <text x="82" y="112" class="hint">2–10 个席位：提交状态 / 本轮牛头 / 累计牛头</text>
  <rect x="242" y="156" width="956" height="560" rx="34" fill="#0a3032" stroke="#315d59" stroke-width="3"/>
  <rect x="326" y="169" width="628" height="36" rx="18" class="zone"/>
  <text x="640" y="193" text-anchor="middle" class="hint">同时揭示轨 · 由小到大</text>
  {''.join(row_markup)}
  <rect x="142" y="744" width="1156" height="112" rx="24" class="zone"/>
  <text x="178" y="783" class="label">PRIVATE HAND · VIEWER ONLY</text>
  <text x="178" y="817" class="hint">横向滚动容器，不产生页面级溢出；锁定后只向本人显示牌面</text>
  <path d="M1110 184c94 38 120 93 82 166" fill="none" stroke="#d6a447" stroke-width="4" stroke-dasharray="11 9"/>
  <path d="m1184 344 6 18 14-12" fill="none" stroke="#d6a447" stroke-width="4"/>
  <text x="1110" y="161" class="hint">出牌弧线</text>
  <path d="M1046 594c124 44 145 96 102 144" fill="none" stroke="#df7354" stroke-width="4" stroke-dasharray="11 9"/>
  <path d="m1141 732 5 18 15-11" fill="none" stroke="#df7354" stroke-width="4"/>
  <text x="1070" y="584" class="hint">收牌飞向计分区</text>
</svg>
"""


def main() -> None:
    MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    ASSET_ROOT.mkdir(parents=True, exist_ok=True)
    (MODEL_ROOT / "generated-card-catalog.json").write_text(
        json.dumps(card_catalog(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (ASSET_ROOT / "card-model-sheet.svg").write_text(
        model_sheet(), encoding="utf-8",
    )
    (ASSET_ROOT / "table-scene-blueprint.svg").write_text(
        table_blueprint(), encoding="utf-8",
    )
    print("Generated 104 card records and 2 SVG model sheets.")


if __name__ == "__main__":
    main()
