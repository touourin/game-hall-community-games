from __future__ import annotations

import html
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / "data" / "components.json").read_text(encoding="utf-8"))
IMAGE_DIR = ROOT / "images"
ASSET_DIR = ROOT / "frontend" / "assets"


def esc(value: object) -> str:
    return html.escape(str(value))


def fund_atlas() -> None:
    card_width, card_height = 184, 246
    gap, margin, header = 14, 28, 78
    columns, rows = 9, 8
    width = margin * 2 + columns * card_width + (columns - 1) * gap
    height = header + margin + rows * card_height + (rows - 1) * gap + margin
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#17312e"/>',
        '<text x="28" y="42" fill="#e7d5ad" font-family="Georgia,serif" font-size="28" font-weight="700">庞氏骗局 · 72 张资金／贷款牌工程图</text>',
        '<text x="28" y="66" fill="#aeb9ad" font-family="sans-serif" font-size="13">唯一编号 F009–F080 · 原创无插画数字系统 · 金额 / 循环周期 / 利息 / 均压 / 收益率</text>',
    ]
    for index, card in enumerate(CATALOG["fundCards"]):
        column, row = index % columns, index // columns
        x = margin + column * (card_width + gap)
        y = header + margin + row * (card_height + gap)
        is_bear = card["kind"] == "bear"
        is_start = card["kind"] == "starting"
        fill = "#4b312f" if is_bear else ("#d6e0d2" if is_start else "#e5dcc7")
        ink = "#f1dfbd" if is_bear else "#282a25"
        edge = "#c35b47" if is_bear else ("#6e927b" if is_start else "#9e8150")
        parts.extend([
            f'<g transform="translate({x} {y})">',
            f'<rect width="{card_width}" height="{card_height}" rx="8" fill="{fill}" stroke="{edge}" stroke-width="4"/>',
            f'<rect x="9" y="9" width="{card_width - 18}" height="{card_height - 18}" rx="4" fill="none" stroke="{ink}" opacity=".28"/>',
            f'<text x="16" y="28" fill="{ink}" font-family="monospace" font-size="12" font-weight="700">{esc(card["id"])}</text>',
            f'<text x="{card_width - 16}" y="28" text-anchor="end" fill="{edge}" font-family="sans-serif" font-size="11" font-weight="700">{"熊市" if is_bear else ("起始" if is_start else "常规")}</text>',
            f'<text x="16" y="91" fill="{ink}" font-family="Georgia,serif" font-size="58" font-weight="700">{card["amount"]}</text>',
            f'<text x="17" y="111" fill="{ink}" opacity=".7" font-family="sans-serif" font-size="11" letter-spacing="2">到账现金</text>',
            f'<line x1="16" y1="127" x2="{card_width - 16}" y2="127" stroke="{ink}" opacity=".35"/>',
            f'<text x="16" y="156" fill="{ink}" font-family="sans-serif" font-size="16" font-weight="700">利息 {card["interest"]}</text>',
            f'<text x="{card_width - 16}" y="156" text-anchor="end" fill="{ink}" font-family="sans-serif" font-size="16" font-weight="700">每 {card["period"]} 轮</text>',
            f'<rect x="16" y="174" width="{card_width - 32}" height="42" rx="4" fill="{edge}" opacity=".2"/>',
            f'<text x="24" y="192" fill="{ink}" font-family="sans-serif" font-size="10">平均轮压</text>',
            f'<text x="24" y="209" fill="{ink}" font-family="Georgia,serif" font-size="17" font-weight="700">{card["averageBurden"]}</text>',
            f'<text x="{card_width - 24}" y="192" text-anchor="end" fill="{ink}" font-family="sans-serif" font-size="10">名义收益率</text>',
            f'<text x="{card_width - 24}" y="209" text-anchor="end" fill="{ink}" font-family="Georgia,serif" font-size="17" font-weight="700">{card["yieldPercent"]}%</text>',
            '</g>',
        ])
    parts.append('</svg>')
    (IMAGE_DIR / "fund-card-atlas.svg").write_text("\n".join(parts), encoding="utf-8")


def component_blueprint() -> None:
    industries = CATALOG["industries"]
    luxuries = CATALOG["luxuries"]
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1200" viewBox="0 0 1800 1200">
<rect width="1800" height="1200" fill="#ece1c8"/>
<path d="M0 82H1800M0 1120H1800" stroke="#223b3d" stroke-width="7"/>
<text x="70" y="58" fill="#223b3d" font-family="Georgia,serif" font-size="34" font-weight="700">庞氏骗局 · 桌游组件建模蓝图</text>
<text x="70" y="110" fill="#76674f" font-family="sans-serif" font-size="16">比例示意，不复刻任何商业版插画；数字与交互关系对应服务端数据模型</text>
<g transform="translate(70 155)">
  <text x="0" y="0" fill="#223b3d" font-family="sans-serif" font-size="19" font-weight="700">A · 三排资金市场</text>
  <rect x="0" y="24" width="720" height="390" rx="8" fill="#d5c49e" stroke="#665434" stroke-width="5"/>
  <g fill="#f4eddd" stroke="#665434" stroke-width="2">{''.join(f'<rect x="{110 + (i % 3) * 190}" y="{50 + (i // 3) * 116}" width="155" height="96" rx="5"/>' for i in range(9))}</g>
  <g fill="#293a3a" font-family="sans-serif" font-size="14">{''.join(f'<text x="22" y="{108 + i * 116}">第 {i + 1} 排</text>' for i in range(3))}</g>
  <path d="M670 55l24 42h-48z" fill="#8f3d36"/><text x="670" y="118" text-anchor="middle" fill="#8f3d36" font-family="sans-serif" font-size="12">熊市阈值 = 玩家数</text>
</g>
<g transform="translate(875 155)">
  <text x="0" y="0" fill="#223b3d" font-family="sans-serif" font-size="19" font-weight="700">B · 时间轮与循环贷款</text>
  <circle cx="230" cy="220" r="175" fill="#c9b580" stroke="#755c32" stroke-width="12"/>
  <circle cx="230" cy="220" r="70" fill="#263b3d" stroke="#ae8a4b" stroke-width="5"/>
  {''.join(f'<circle cx="{230 + dx}" cy="{220 + dy}" r="34" fill="#f0e4c6" stroke="#755c32" stroke-width="2"/><text x="{230 + dx}" y="{226 + dy}" text-anchor="middle" fill="#2c312c" font-family="Georgia,serif" font-size="22" font-weight="700">{i}</text>' for i, (dx, dy) in enumerate([(0,-142),(135,-44),(84,115),(-84,115),(-135,-44)], 1))}
  <path d="M18 200l45-20v40z" fill="#963e36"/><text x="18" y="244" fill="#963e36" font-family="sans-serif" font-size="13">到期箭头</text>
  <text x="230" y="210" text-anchor="middle" fill="#e7d7b4" font-family="sans-serif" font-size="13">每轮 +1</text><text x="230" y="235" text-anchor="middle" fill="#e7d7b4" font-family="sans-serif" font-size="13">崩盘 +2</text>
</g>
<g transform="translate(70 625)">
  <text x="0" y="0" fill="#223b3d" font-family="sans-serif" font-size="19" font-weight="700">C · 产业、现金与奢侈品</text>
  {''.join(f'<g transform="translate({i * 150} 35)"><rect width="120" height="120" rx="12" fill="{item["color"]}" stroke="#384443" stroke-width="3"/><circle cx="60" cy="46" r="24" fill="#f2e8d2" opacity=".8"/><text x="60" y="96" text-anchor="middle" fill="#fff8e8" font-family="sans-serif" font-size="15" font-weight="700">{esc(item["shortName"])}</text><text x="60" y="145" text-anchor="middle" fill="#4b4335" font-family="sans-serif" font-size="12">15 枚</text></g>' for i, item in enumerate(industries))}
  <g transform="translate(0 225)">{''.join(f'<g transform="translate({i * 145} 0)"><rect width="120" height="58" rx="4" fill="{bill["color"]}" stroke="#5c543f" stroke-width="2"/><text x="60" y="39" text-anchor="middle" fill="#263332" font-family="Georgia,serif" font-size="28" font-weight="700">{bill["value"]}</text></g>' for i, bill in enumerate(CATALOG["money"]["denominations"]))}<text x="0" y="92" fill="#6d6049" font-family="sans-serif" font-size="13">数字银行无限供应；面额 1 / 5 / 10 / 20</text></g>
  <g transform="translate(640 35)">{''.join(f'<g transform="translate({i * 165} 0)"><path d="M10 20h130l-12 100H22z" fill="#253c3e" stroke="#b28b49" stroke-width="4"/><circle cx="75" cy="65" r="25" fill="none" stroke="#d1ad63" stroke-width="6"/><text x="75" y="150" text-anchor="middle" fill="#3d3a31" font-family="sans-serif" font-size="13">{esc(item["name"])}</text><text x="75" y="170" text-anchor="middle" fill="#7c5831" font-family="sans-serif" font-size="12">{item["cost"]} / {item["points"]} 分</text></g>' for i, item in enumerate(luxuries))}</g>
</g>
<g transform="translate(70 1025)">
  <text x="0" y="0" fill="#223b3d" font-family="sans-serif" font-size="19" font-weight="700">D · 暗盘交易状态机</text>
  <g transform="translate(270 -38)"><path d="M0 0h210v92H0z" fill="#cfb984" stroke="#765e35" stroke-width="3"/><path d="M0 0l105 56L210 0" fill="#bca574" stroke="#765e35" stroke-width="2"/></g>
  <text x="245" y="80" text-anchor="middle" fill="#343830" font-family="sans-serif" font-size="14">发起人：装入任意现金</text><path d="M500 40h120" stroke="#7d5e33" stroke-width="4" marker-end="url(#a)"/>
  <text x="795" y="20" text-anchor="middle" fill="#343830" font-family="sans-serif" font-size="14">目标玩家必须二选一</text>
  <rect x="650" y="36" width="290" height="58" rx="5" fill="#6b927c"/><text x="795" y="71" text-anchor="middle" fill="white" font-family="sans-serif" font-size="15">收钱 → 卖出 1 枚产业</text>
  <rect x="980" y="36" width="350" height="58" rx="5" fill="#8c5c55"/><text x="1155" y="71" text-anchor="middle" fill="white" font-family="sans-serif" font-size="15">补入等额 → 反向买入 1 枚</text>
  <text x="1450" y="69" fill="#6d6049" font-family="sans-serif" font-size="13">价格仅双方可见</text>
</g>
<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0l10 5-10 5z" fill="#7d5e33"/></marker></defs>
</svg>'''
    (IMAGE_DIR / "component-blueprint.svg").write_text(svg, encoding="utf-8")


def catalog_icon(theme: str) -> None:
    light = theme == "light"
    image = Image.new("RGB", (768, 768), "#eee4d0" if light else "#102925")
    draw = ImageDraw.Draw(image)
    table = "#1d4038" if light else "#17342f"
    paper = "#e8dcc3" if light else "#d5c7aa"
    ink = "#263a39" if light else "#172a2b"
    gold = "#b48c49"
    red = "#91423a"
    draw.rounded_rectangle((82, 88, 686, 680), radius=42, fill=table, outline=gold, width=8)
    draw.rounded_rectangle((132, 148, 636, 452), radius=12, fill="#c8b58f", outline="#755f3b", width=6)
    for row in range(3):
        for column in range(3):
            x = 182 + column * 140
            y = 176 + row * 84
            fill = red if row == 2 and column == 2 else paper
            draw.rounded_rectangle((x, y, x + 105, y + 66), radius=8, fill=fill, outline=ink, width=3)
            draw.ellipse((x + 13, y + 15, x + 46, y + 48), fill=gold)
            draw.line((x + 60, y + 22, x + 91, y + 22), fill=ink, width=5)
            draw.line((x + 60, y + 38, x + 85, y + 38), fill=ink, width=4)
    draw.ellipse((126, 486, 326, 686), fill="#c8b27b", outline=gold, width=8)
    draw.ellipse((179, 539, 273, 633), fill=ink, outline="#dfc782", width=5)
    for angle_box in ((204, 495, 248, 539), (270, 539, 314, 583), (245, 624, 289, 668), (162, 616, 206, 660), (136, 540, 180, 584)):
        draw.ellipse(angle_box, fill=paper, outline="#715d39", width=3)
    draw.polygon(((382, 520), (635, 520), (635, 666), (382, 666)), fill="#cfb67f", outline="#6e5733")
    draw.polygon(((382, 520), (509, 603), (635, 520)), fill="#bba26f", outline="#6e5733")
    draw.ellipse((485, 568, 533, 616), fill=red, outline="#6e2926", width=5)
    image.save(ASSET_DIR / f"catalog-{theme}.webp", "WEBP", quality=90, method=6)


def main() -> None:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    fund_atlas()
    component_blueprint()
    catalog_icon("dark")
    catalog_icon("light")


if __name__ == "__main__":
    main()
