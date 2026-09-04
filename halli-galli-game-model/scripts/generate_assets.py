from __future__ import annotations

import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "model" / "card-catalog.json"
SCENE_PATH = ROOT / "model" / "scene-catalog.json"
ASSET_DIR = ROOT / "assets"

CARD_W = 168
CARD_H = 261


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def fruit_symbol(fruit_id: str, x: float, y: float, size: float, palette: dict[str, str]) -> str:
    scale = size / 100
    transform = f'translate({number(x - size / 2)} {number(y - size / 2)}) scale({number(scale)})'
    base = palette["base"]
    dark = palette["dark"]
    light = palette["light"]
    if fruit_id == "banana":
        shape = f'''
          <path d="M17 18 C25 62 56 88 87 56 C70 68 45 57 36 12 Z" fill="{base}" stroke="{dark}" stroke-width="6" stroke-linejoin="round"/>
          <path d="M35 15 L39 4 L49 8 L43 20" fill="{dark}"/>
          <path d="M28 35 C40 60 59 68 77 59" fill="none" stroke="{light}" stroke-width="5" stroke-linecap="round"/>
          <path d="M20 25 L31 30 M26 46 L37 47 M39 65 L49 61" stroke="{dark}" stroke-width="3" stroke-linecap="round" opacity="0.45"/>
        '''
    elif fruit_id == "strawberry":
        shape = f'''
          <path d="M50 91 C31 78 16 55 20 37 C24 20 42 17 50 28 C58 17 76 20 80 37 C84 55 69 78 50 91 Z" fill="{base}" stroke="{dark}" stroke-width="5"/>
          <path d="M50 28 L33 14 L45 17 L50 5 L55 17 L68 14 Z" fill="{dark}" stroke="{dark}" stroke-width="3" stroke-linejoin="round"/>
          <g fill="{light}"><circle cx="36" cy="43" r="3"/><circle cx="58" cy="40" r="3"/><circle cx="47" cy="57" r="3"/><circle cx="65" cy="59" r="3"/><circle cx="42" cy="73" r="3"/></g>
        '''
    elif fruit_id == "lime":
        shape = f'''
          <circle cx="50" cy="52" r="39" fill="{base}" stroke="{dark}" stroke-width="6"/>
          <circle cx="50" cy="52" r="29" fill="{light}" stroke="{dark}" stroke-width="3"/>
          <path d="M50 52 L50 23 M50 52 L75 38 M50 52 L75 67 M50 52 L50 81 M50 52 L25 67 M50 52 L25 38" stroke="{dark}" stroke-width="3" stroke-linecap="round"/>
          <circle cx="50" cy="52" r="5" fill="{dark}"/>
        '''
    elif fruit_id == "plum":
        shape = f'''
          <ellipse cx="49" cy="57" rx="33" ry="38" fill="{base}" stroke="{dark}" stroke-width="6"/>
          <path d="M50 20 C53 8 61 5 68 4" fill="none" stroke="{dark}" stroke-width="5" stroke-linecap="round"/>
          <path d="M62 15 C73 4 90 10 91 24 C78 28 68 24 62 15 Z" fill="{light}" stroke="{dark}" stroke-width="4"/>
          <ellipse cx="37" cy="44" rx="9" ry="15" fill="{light}" opacity="0.72" transform="rotate(28 37 44)"/>
          <path d="M27 63 C39 76 60 81 73 68" fill="none" stroke="{dark}" stroke-width="3" opacity="0.38"/>
        '''
    else:
        raise ValueError(f"Unknown fruit: {fruit_id}")
    return f'<g data-fruit="{esc(fruit_id)}" transform="{transform}">{shape}</g>'


FRUIT_POSITIONS: dict[int, list[tuple[float, float, float]]] = {
    1: [(84, 132, 76)],
    2: [(57, 105, 54), (111, 160, 54)],
    3: [(56, 104, 45), (112, 104, 45), (84, 165, 45)],
    4: [(56, 105, 42), (112, 105, 42), (56, 164, 42), (112, 164, 42)],
    5: [(54, 101, 36), (114, 101, 36), (54, 169, 36), (114, 169, 36), (84, 135, 36)],
}


def card_body(face: dict[str, object], fruit: dict[str, object], show_copy_badge: bool = True) -> str:
    fruit_id = str(face["fruitId"])
    fruit_count = int(face["fruitCount"])
    copies = int(face["copies"])
    palette = dict(fruit["palette"])
    symbols = "".join(
        fruit_symbol(fruit_id, x, y, size, palette)
        for x, y, size in FRUIT_POSITIONS[fruit_count]
    )
    copy_badge = ""
    if show_copy_badge:
        copy_badge = f'''
          <g transform="translate(111 17)">
            <rect width="42" height="22" rx="11" fill="#E8E0D1"/>
            <text x="21" y="15" text-anchor="middle" class="copy">牌组 ×{copies}</text>
          </g>
        '''
    return f'''
      <rect width="{CARD_W}" height="{CARD_H}" rx="13" fill="#FFFDF7" stroke="#BEB39E" stroke-width="2"/>
      <rect x="8" y="8" width="152" height="245" rx="10" fill="none" stroke="{palette['dark']}" stroke-width="2" opacity="0.42"/>
      <text x="17" y="33" class="corner" fill="{palette['dark']}">{fruit_count}</text>
      {copy_badge}
      {symbols}
      <rect x="25" y="211" width="118" height="28" rx="14" fill="{palette['dark']}"/>
      <text x="84" y="230" text-anchor="middle" class="fruit-label" fill="#FFFFFF">{esc(face['labelZh'])}</text>
    '''


def card_svg(x: float, y: float, face: dict[str, object], fruit: dict[str, object], width: float = CARD_W, show_copy_badge: bool = True) -> str:
    scale = width / CARD_W
    return f'''
      <g id="{esc(face['id'])}" transform="translate({number(x)} {number(y)}) scale({number(scale)})" role="img" aria-label="{esc(face['altZh'])}">
        <title>{esc(face['labelZh'])}</title>
        {card_body(face, fruit, show_copy_badge)}
      </g>
    '''


def svg_document(width: int, height: int, title: str, description: str, body: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="svg-title svg-desc">
  <title id="svg-title">{esc(title)}</title>
  <desc id="svg-desc">{esc(description)}</desc>
  <style>
    text {{ font-family: "Microsoft YaHei", "Noto Sans CJK SC", sans-serif; }}
    .title {{ font-size: 34px; font-weight: 800; letter-spacing: 1px; }}
    .subtitle {{ font-size: 16px; font-weight: 500; }}
    .corner {{ font-size: 28px; font-weight: 900; }}
    .fruit-label {{ font-size: 15px; font-weight: 800; }}
    .copy {{ font-size: 10px; font-weight: 700; fill: #554D42; }}
    .seat-name {{ font-size: 20px; font-weight: 800; fill: #FFFDF7; }}
    .seat-meta {{ font-size: 14px; font-weight: 600; fill: #CEDBD5; }}
  </style>
  {body}
</svg>
'''


def build_card_atlas(catalog: dict[str, object], scene: dict[str, object]) -> str:
    fruits = {item["id"]: item for item in catalog["fruits"]}
    faces = {item["id"]: item for item in catalog["faces"]}
    theme = scene["theme"]
    width, height = 1020, 1320
    parts = [
        f'<rect width="{width}" height="{height}" fill="{theme["page"]}"/>',
        f'<rect x="26" y="24" width="968" height="1272" rx="30" fill="{theme["table"]}" stroke="{theme["tableEdge"]}" stroke-width="3"/>',
        '<text x="55" y="66" class="title" fill="#FFFDF7">德国心脏病 · 20 种唯一牌面</text>',
        '<text x="56" y="94" class="subtitle" fill="#C9D8D2">原创功能原型 · 四种水果各 14 张 · 总计 56 张</text>',
    ]
    start_x, start_y = 54, 122
    gap_x, gap_y = 18, 22
    for row, fruit_id in enumerate(["banana", "strawberry", "lime", "plum"]):
        for column, fruit_count in enumerate(range(1, 6)):
            face = faces[f"face-{fruit_id}-{fruit_count}"]
            x = start_x + column * (CARD_W + gap_x)
            y = start_y + row * (CARD_H + gap_y)
            parts.append(card_svg(x, y, face, fruits[fruit_id]))
    parts.extend([
        '<rect x="54" y="1268" width="912" height="2" fill="#B58A4A" opacity="0.7"/>',
        '<text x="54" y="1290" class="subtitle" fill="#C9D8D2">数量 1/2/3/4/5 的副本数依次为 5/3/3/2/1；几何图形不复制官方插画。</text>',
    ])
    return svg_document(width, height, "德国心脏病水果牌原型图集", "四行五列展示香蕉、草莓、青柠和李子的 1 至 5 数量牌面。", "".join(parts))


def draw_back(x: float, y: float, label: str, count: int) -> str:
    return f'''
      <g transform="translate({number(x)} {number(y)})">
        <rect x="8" y="8" width="102" height="158" rx="10" fill="#183B36" stroke="#B58A4A" stroke-width="2"/>
        <rect x="4" y="4" width="102" height="158" rx="10" fill="#214A44" stroke="#B58A4A" stroke-width="2"/>
        <rect width="102" height="158" rx="10" fill="#2B5A52" stroke="#D2B472" stroke-width="2"/>
        <circle cx="51" cy="75" r="29" fill="none" stroke="#D2B472" stroke-width="5"/>
        <path d="M28 77 Q51 43 74 77 Q51 109 28 77 Z" fill="none" stroke="#D2B472" stroke-width="4"/>
        <text x="51" y="138" text-anchor="middle" fill="#FFFDF7" font-size="14" font-weight="800">{esc(label)} · {count}</text>
      </g>
    '''


def mini_card(x: float, y: float, fruit_id: str, fruit_count: int, catalog: dict[str, object], width: float = 102) -> str:
    fruits = {item["id"]: item for item in catalog["fruits"]}
    faces = {item["id"]: item for item in catalog["faces"]}
    face = faces[f"face-{fruit_id}-{fruit_count}"]
    return card_svg(x, y, face, fruits[fruit_id], width=width, show_copy_badge=False)


def seat_group(zone_id: str, name: str, status: str, x: float, y: float, draw_count: int, fruit_id: str, fruit_count: int, catalog: dict[str, object], current: bool = False) -> str:
    border = "#F7D774" if current else "#527A70"
    return f'''
      <g id="{zone_id}" data-zone="{zone_id}" transform="translate({number(x)} {number(y)})">
        <rect width="360" height="210" rx="24" fill="#12302C" stroke="{border}" stroke-width="{4 if current else 2}"/>
        <text x="20" y="32" class="seat-name">{esc(name)}</text>
        <text x="340" y="30" text-anchor="end" class="seat-meta">{esc(status)}</text>
        {draw_back(18, 38, '抽牌', draw_count)}
        {mini_card(183, 38, fruit_id, fruit_count, catalog, width=102)}
      </g>
    '''


def build_table_scene(catalog: dict[str, object], scene: dict[str, object]) -> str:
    theme = scene["theme"]
    width, height = 1600, 900
    parts = [
        f'<rect width="{width}" height="{height}" fill="{theme["page"]}"/>',
        f'<rect id="table_stage" data-zone="table_stage" x="32" y="28" width="1536" height="790" rx="72" fill="{theme["table"]}" stroke="{theme["tableEdge"]}" stroke-width="5"/>',
        '<text x="72" y="78" class="title" fill="#FFFDF7">德国心脏病 · 四人牌桌信息架构</text>',
        '<text x="73" y="108" class="subtitle" fill="#C9D8D2">所有顶牌同时可见 · 中央铃固定 · 忠实模式不自动计算答案</text>',
        seat_group("seat_2", "青禾 · P3", "轮到翻牌", 70, 175, 11, "strawberry", 4, catalog, current=True),
        seat_group("seat_3", "白川 · P2", "可翻牌／可抢铃", 620, 105, 11, "banana", 3, catalog),
        seat_group("seat_5", "赤岩 · P4", "可翻牌／可抢铃", 1170, 175, 11, "plum", 1, catalog),
        seat_group("seat_0", "你 · 阿梨 · P1", "可翻牌／可抢铃", 620, 585, 11, "banana", 2, catalog),
        f'''
        <g id="bell_zone" data-zone="bell_zone" transform="translate(696 344)">
          <circle cx="104" cy="104" r="100" fill="#102823" stroke="#D2B472" stroke-width="5"/>
          <ellipse cx="104" cy="133" rx="74" ry="23" fill="#7B5725"/>
          <path d="M47 128 C50 75 70 48 104 48 C138 48 158 75 161 128 Z" fill="#D6B56B" stroke="#7B5725" stroke-width="6"/>
          <ellipse cx="104" cy="50" rx="26" ry="12" fill="#F3D991" stroke="#7B5725" stroke-width="5"/>
          <rect x="92" y="27" width="24" height="24" rx="8" fill="#D6B56B" stroke="#7B5725" stroke-width="5"/>
          <rect x="29" y="126" width="150" height="22" rx="11" fill="#D6B56B" stroke="#7B5725" stroke-width="5"/>
          <text x="104" y="174" text-anchor="middle" fill="#FFFDF7" font-size="18" font-weight="800">SPACE · 抢铃</text>
        </g>
        ''',
        '<g id="fruit_legend" data-zone="fruit_legend" transform="translate(492 525)"><rect width="616" height="46" rx="23" fill="#0F2B27" stroke="#527A70"/><text x="308" y="29" text-anchor="middle" fill="#DDE8E3" font-size="16" font-weight="700">图例：香蕉弯月 · 草莓籽心 · 青柠分瓣 · 李子椭圆</text></g>',
        '<g id="reaction_banner" data-zone="reaction_banner" transform="translate(525 294)"><rect width="550" height="45" rx="22" fill="#F7F2E8" stroke="#B58A4A" stroke-width="2"/><text x="275" y="29" text-anchor="middle" fill="#18211F" font-size="17" font-weight="800">教学标注：2 + 3 个香蕉 = 恰好 5 个，可抢铃</text></g>',
        '<g id="turn_banner" data-zone="turn_banner" transform="translate(602 32)"><rect width="396" height="46" rx="23" fill="#214A44" stroke="#F7D774" stroke-width="2"/><text x="198" y="29" text-anchor="middle" fill="#FFFDF7" font-size="17" font-weight="800">当前：青禾翻牌 · 桌面版本 12</text></g>',
        '<text x="72" y="858" class="subtitle" fill="#C9D8D2">原创原型 · 牌背不泄露信息 · 被覆盖牌不在实时界面展开 · 非官方美术</text>',
    ]
    return svg_document(width, height, "德国心脏病四人桌面场景原型", "四个玩家围绕中央铃，两个香蕉顶牌合计恰好五个。", "".join(parts))


def main() -> int:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    scene = json.loads(SCENE_PATH.read_text(encoding="utf-8"))
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        ASSET_DIR / "card-atlas.svg": build_card_atlas(catalog, scene),
        ASSET_DIR / "table-scene.svg": build_table_scene(catalog, scene),
    }
    for path, content in outputs.items():
        normalized = "\n".join(line.rstrip() for line in content.splitlines()) + "\n"
        path.write_text(normalized, encoding="utf-8", newline="\n")
        print(f"Generated {path.relative_to(ROOT)} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
