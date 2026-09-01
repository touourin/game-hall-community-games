#!/usr/bin/env python3
"""Generate per-player Skull card SVG assets from the canonical JSON model."""

from __future__ import annotations

import hashlib
import html
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "model" / "player-card-models.json"
OUTPUT_DIR = ROOT / "assets" / "player-cards"
GENERATED_DIR = OUTPUT_DIR / "generated"
ATLAS_PATH = OUTPUT_DIR / "player-card-atlas.svg"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def fmt(value: float) -> str:
    rounded = round(value, 2)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def polar(cx: float, cy: float, radius: float, degrees: float) -> tuple[float, float]:
    radians = math.radians(degrees - 90)
    return cx + radius * math.cos(radians), cy + radius * math.sin(radians)


def polygon_points(
    cx: float,
    cy: float,
    radius: float,
    sides: int,
    rotation: float = 0,
) -> str:
    return " ".join(
        f"{fmt(x)},{fmt(y)}"
        for x, y in (polar(cx, cy, radius, rotation + index * 360 / sides) for index in range(sides))
    )


def star_points(
    cx: float,
    cy: float,
    outer: float,
    inner: float,
    points: int,
    rotation: float = 0,
) -> str:
    result: list[str] = []
    for index in range(points * 2):
        radius = outer if index % 2 == 0 else inner
        x, y = polar(cx, cy, radius, rotation + index * 180 / points)
        result.append(f"{fmt(x)},{fmt(y)}")
    return " ".join(result)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def svg_defs(player: dict[str, Any], prefix: str) -> str:
    palette = player["palette"]
    return f"""
    <radialGradient id="{prefix}-surface" cx="35%" cy="26%" r="76%">
      <stop offset="0" stop-color="{palette['surfaceHighlight']}"/>
      <stop offset="0.68" stop-color="{palette['surface']}"/>
      <stop offset="1" stop-color="{palette['surfaceShadow']}"/>
    </radialGradient>
    <linearGradient id="{prefix}-edge" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{palette['edge']}"/>
      <stop offset="0.48" stop-color="{palette['accent']}"/>
      <stop offset="1" stop-color="{palette['surfaceShadow']}"/>
    </linearGradient>
    <filter id="{prefix}-shadow" x="-20%" y="-20%" width="140%" height="150%">
      <feDropShadow dx="0" dy="12" stdDeviation="10" flood-color="#000000" flood-opacity="0.42"/>
    </filter>
    <filter id="{prefix}-soft" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="9"/>
    </filter>
    <clipPath id="{prefix}-clip"><circle cx="256" cy="256" r="208"/></clipPath>
    """.strip()


def center_mark(player: dict[str, Any], prefix: str) -> str:
    palette = player["palette"]
    mark = player["back"]["centerMark"]
    accent = palette["accent"]
    secondary = palette["secondary"]
    ink = palette["ink"]
    shadow = palette["surfaceShadow"]

    if mark == "ember-dot":
        return f"""
        <circle cx="256" cy="256" r="45" fill="{accent}" stroke="{secondary}" stroke-width="7"/>
        <circle cx="256" cy="256" r="18" fill="{shadow}"/>
        <circle cx="250" cy="248" r="6" fill="{ink}" opacity="0.7"/>
        """
    if mark == "tide-moon":
        return f"""
        <circle cx="256" cy="256" r="48" fill="{secondary}"/>
        <circle cx="274" cy="242" r="48" fill="{player['palette']['surface']}"/>
        <circle cx="256" cy="256" r="51" fill="none" stroke="{accent}" stroke-width="5"/>
        """
    if mark == "moss-leaf":
        return f"""
        <ellipse cx="256" cy="254" rx="31" ry="53" transform="rotate(35 256 254)" fill="{secondary}" stroke="{accent}" stroke-width="5"/>
        <path d="M228 286 Q256 253 286 220" fill="none" stroke="{shadow}" stroke-width="7" stroke-linecap="round"/>
        <path d="M244 267l-3-23M260 250l22 2" fill="none" stroke="{shadow}" stroke-width="4" stroke-linecap="round"/>
        """
    if mark == "orchid-gem":
        return f"""
        <polygon points="256,201 310,256 256,311 202,256" fill="{accent}" stroke="{secondary}" stroke-width="6"/>
        <polygon points="256,221 291,256 256,291 221,256" fill="{shadow}" stroke="{ink}" stroke-width="3" opacity="0.9"/>
        """
    if mark == "ochre-star":
        return f"""
        <polygon points="{star_points(256, 256, 58, 25, 8, 22.5)}" fill="{accent}" stroke="{secondary}" stroke-width="5"/>
        <circle cx="256" cy="256" r="13" fill="{shadow}"/>
        """
    return f"""
    <polygon points="{polygon_points(256, 256, 55, 6, 30)}" fill="{accent}" stroke="{secondary}" stroke-width="6"/>
    <polygon points="{polygon_points(256, 256, 30, 6, 0)}" fill="{shadow}" stroke="{ink}" stroke-width="3"/>
    """


def back_motif(player: dict[str, Any], prefix: str) -> str:
    palette = player["palette"]
    model = player["back"]
    motif = model["motif"]
    count = model["segmentCount"]
    rotation = model["rotation"]
    opacity = model["patternOpacity"]
    accent = palette["accent"]
    secondary = palette["secondary"]
    edge = palette["edge"]
    parts: list[str] = [f'<g clip-path="url(#{prefix}-clip)" opacity="{fmt(opacity)}">']

    if motif == "sunburst":
        for index in range(count):
            angle = rotation + index * 360 / count
            x1, y1 = polar(256, 256, 68, angle)
            x2, y2 = polar(256, 256, 190, angle)
            width = 7 if index % 2 == 0 else 3
            color = secondary if index % 2 == 0 else accent
            parts.append(
                f'<path d="M{fmt(x1)} {fmt(y1)}L{fmt(x2)} {fmt(y2)}" stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>'
            )
        for radius in (104, 154):
            parts.append(f'<circle cx="256" cy="256" r="{radius}" fill="none" stroke="{edge}" stroke-width="3" stroke-dasharray="4 10"/>')

    elif motif == "waves":
        for row, y in enumerate(range(126, 397, 45)):
            offset = 20 if row % 2 else 0
            parts.append(
                f'<path d="M54 {y} C104 {y-35+offset} 154 {y+35-offset} 204 {y} S304 {y-35+offset} 354 {y} S454 {y+35-offset} 508 {y}" fill="none" stroke="{secondary if row % 2 else accent}" stroke-width="6" stroke-linecap="round"/>'
            )
        for radius in (112, 172):
            parts.append(f'<circle cx="256" cy="256" r="{radius}" fill="none" stroke="{edge}" stroke-width="2" opacity="0.65"/>')

    elif motif == "vine":
        parts.append(f'<circle cx="256" cy="256" r="154" fill="none" stroke="{accent}" stroke-width="8" stroke-dasharray="7 10"/>')
        for index in range(count * 2):
            angle = rotation + index * 360 / (count * 2)
            x, y = polar(256, 256, 153, angle)
            parts.append(
                f'<ellipse cx="{fmt(x)}" cy="{fmt(y)}" rx="12" ry="27" transform="rotate({fmt(angle+35)} {fmt(x)} {fmt(y)})" fill="{secondary}" stroke="{edge}" stroke-width="2"/>'
            )
        parts.append(f'<circle cx="256" cy="256" r="105" fill="none" stroke="{edge}" stroke-width="3" stroke-dasharray="2 9"/>')

    elif motif == "diamonds":
        for radius, size in ((92, 28), (145, 34), (188, 38)):
            for index in range(count):
                angle = rotation + index * 360 / count
                x, y = polar(256, 256, radius, angle)
                points = f"{fmt(x)},{fmt(y-size)} {fmt(x+size)},{fmt(y)} {fmt(x)},{fmt(y+size)} {fmt(x-size)},{fmt(y)}"
                parts.append(f'<polygon points="{points}" fill="none" stroke="{secondary if index % 2 else accent}" stroke-width="4"/>')
        parts.append(f'<circle cx="256" cy="256" r="177" fill="none" stroke="{edge}" stroke-width="2"/>')

    elif motif == "compass":
        for index in range(count):
            angle = rotation + index * 360 / count
            left = polar(256, 256, 45, angle - 7)
            right = polar(256, 256, 45, angle + 7)
            tip = polar(256, 256, 188 if index % 2 == 0 else 150, angle)
            points = f"{fmt(left[0])},{fmt(left[1])} {fmt(tip[0])},{fmt(tip[1])} {fmt(right[0])},{fmt(right[1])}"
            parts.append(f'<polygon points="{points}" fill="{secondary if index % 2 == 0 else accent}" opacity="0.72"/>')
        for radius in (90, 169):
            parts.append(f'<circle cx="256" cy="256" r="{radius}" fill="none" stroke="{edge}" stroke-width="3"/>')

    else:  # hex-grid
        hex_radius = 34
        row_height = hex_radius * math.sqrt(3)
        for row in range(-4, 5):
            for col in range(-4, 5):
                x = 256 + col * hex_radius * 1.5
                y = 256 + row * row_height + (col % 2) * row_height / 2
                if math.dist((x, y), (256, 256)) < 205:
                    parts.append(
                        f'<polygon points="{polygon_points(x, y, hex_radius, 6, 30)}" fill="none" stroke="{secondary if (row+col)%2 else accent}" stroke-width="3"/>'
                    )
        parts.append(f'<circle cx="256" cy="256" r="178" fill="none" stroke="{edge}" stroke-width="4"/>')

    parts.append("</g>")
    parts.append(center_mark(player, prefix).strip())
    return "\n".join(parts)


def owner_ticks(player: dict[str, Any]) -> str:
    seat = player["seatIndex"] + 1
    accent = player["palette"]["accent"]
    pieces: list[str] = []
    spread = 13
    start = 180 - spread * (seat - 1) / 2
    for index in range(seat):
        angle = start + index * spread
        x1, y1 = polar(256, 256, 190, angle)
        x2, y2 = polar(256, 256, 207, angle)
        pieces.append(
            f'<path d="M{fmt(x1)} {fmt(y1)}L{fmt(x2)} {fmt(y2)}" stroke="{accent}" stroke-width="7" stroke-linecap="round"/>'
        )
    return "\n".join(pieces)


def flower_motif(player: dict[str, Any], prefix: str) -> str:
    palette = player["palette"]
    model = player["flowerFront"]
    motif = model["motif"]
    count = model["petalCount"]
    length = model["petalLength"]
    width = model["petalWidth"]
    rotation = model["rotation"]
    center_radius = model["centerRadius"]
    parts: list[str] = []

    parts.append(f'<circle cx="256" cy="256" r="183" fill="none" stroke="{palette["safe"]}" stroke-width="7" stroke-dasharray="5 9"/>')

    if motif == "geometric-bloom":
        for index in range(count):
            angle = rotation + index * 360 / count
            near_left = polar(256, 256, center_radius * 0.7, angle - 22)
            tip = polar(256, 256, length, angle)
            near_right = polar(256, 256, center_radius * 0.7, angle + 22)
            mid_right = polar(256, 256, length * 0.56, angle + 18)
            mid_left = polar(256, 256, length * 0.56, angle - 18)
            points = " ".join(
                f"{fmt(x)},{fmt(y)}"
                for x, y in (near_left, mid_left, tip, mid_right, near_right)
            )
            parts.append(f'<polygon points="{points}" fill="{palette["ink"]}" stroke="{palette["accent"]}" stroke-width="5" opacity="0.95"/>')
    else:
        for index in range(count):
            angle = rotation + index * 360 / count
            petal_length = length
            petal_width = width
            if motif == "wildflower":
                petal_length *= 0.92 + (index % 3) * 0.06
                petal_width *= 0.9 + (index % 2) * 0.12
            if motif == "orchid" and index % 2:
                petal_length *= 0.82
                petal_width *= 0.78
            center_y = 256 - petal_length / 2 + center_radius * 0.28
            fill = palette["ink"] if index % 2 == 0 else palette["secondary"]
            parts.append(
                f'<ellipse cx="256" cy="{fmt(center_y)}" rx="{fmt(petal_width/2)}" ry="{fmt(petal_length/2)}" transform="rotate({fmt(angle)} 256 256)" fill="{fill}" stroke="{palette["accent"]}" stroke-width="5" opacity="0.96"/>'
            )

    if model["secondaryRing"]:
        inner_count = count if motif != "orchid" else 6
        for index in range(inner_count):
            angle = rotation + 180 / inner_count + index * 360 / inner_count
            inner_length = length * 0.55
            center_y = 256 - inner_length / 2 + center_radius * 0.2
            parts.append(
                f'<ellipse cx="256" cy="{fmt(center_y)}" rx="{fmt(width*0.24)}" ry="{fmt(inner_length/2)}" transform="rotate({fmt(angle)} 256 256)" fill="{palette["secondary"]}" stroke="{palette["edge"]}" stroke-width="3" opacity="0.82"/>'
            )

    if motif == "lotus":
        parts.append(f'<path d="M158 318 Q256 382 354 318 Q312 354 256 337 Q200 354 158 318Z" fill="{palette["accent"]}" opacity="0.72"/>')
    elif motif == "wildflower":
        parts.append(f'<path d="M256 302 Q230 352 194 370M256 302Q283 348 322 364" fill="none" stroke="{palette["safe"]}" stroke-width="8" stroke-linecap="round"/>')
        parts.append(f'<ellipse cx="205" cy="357" rx="18" ry="35" transform="rotate(-55 205 357)" fill="{palette["secondary"]}"/>')
        parts.append(f'<ellipse cx="313" cy="352" rx="18" ry="35" transform="rotate(55 313 352)" fill="{palette["secondary"]}"/>')
    elif motif == "orchid":
        parts.append(f'<path d="M226 270 Q256 318 286 270 Q278 330 256 347 Q234 330 226 270Z" fill="{palette["accent"]}" stroke="{palette["edge"]}" stroke-width="4"/>')
    elif motif == "sunflower":
        for angle in range(0, 360, 30):
            x, y = polar(256, 256, center_radius + 12, angle)
            parts.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="7" fill="{palette["surfaceShadow"]}" opacity="0.75"/>')

    parts.append(f'<circle cx="256" cy="256" r="{center_radius+10}" fill="{palette["accent"]}" stroke="{palette["edge"]}" stroke-width="6"/>')
    parts.append(f'<circle cx="256" cy="256" r="{center_radius*0.52}" fill="{palette["surfaceShadow"]}"/>')
    parts.append(f'<circle cx="247" cy="247" r="{max(5, center_radius*0.14)}" fill="{palette["ink"]}" opacity="0.72"/>')
    return "\n".join(parts)


def skull_silhouette(style: str) -> tuple[str, str]:
    cranium = {
        "rounded": "M256 112C174 112 137 177 151 258C156 290 173 312 201 326L201 342H311V326C339 312 356 290 361 258C375 177 338 112 256 112Z",
        "elongated": "M256 94C187 94 151 150 153 239C154 286 174 322 205 337L205 352H307V337C338 322 358 286 359 239C361 150 325 94 256 94Z",
        "compact": "M256 128C169 128 145 191 158 261C165 299 188 318 211 329L211 344H301V329C324 318 347 299 354 261C367 191 343 128 256 128Z",
        "shielded": "M256 104L343 137L365 222C372 276 337 319 306 337L306 350H206V337C175 319 140 276 147 222L169 137Z",
        "angular": "M256 103L331 127L371 205L350 291L310 329L310 348H202V329L162 291L141 205L181 127Z",
        "faceted": "M256 101L328 125L366 189L359 274L315 329L315 348H197V329L153 274L146 189L184 125Z",
    }[style]
    jaw = {
        "rounded": "M201 316L311 316L326 377Q256 414 186 377Z",
        "elongated": "M205 327L307 327L315 399Q256 424 197 399Z",
        "compact": "M211 318L301 318L318 373Q256 401 194 373Z",
        "shielded": "M206 326L306 326L320 386L256 411L192 386Z",
        "angular": "M202 320L310 320L324 381L298 406H214L188 381Z",
        "faceted": "M197 321L315 321L327 378L296 408H216L185 378Z",
    }[style]
    return cranium, jaw


def eye_shapes(shape: str, fill: str) -> str:
    if shape == "oval":
        return f'<ellipse cx="218" cy="245" rx="29" ry="38" fill="{fill}"/><ellipse cx="294" cy="245" rx="29" ry="38" fill="{fill}"/>'
    if shape == "round":
        return f'<circle cx="218" cy="248" r="31" fill="{fill}"/><circle cx="294" cy="248" r="31" fill="{fill}"/>'
    if shape == "slit":
        return f'<path d="M184 246Q218 222 246 246Q218 266 184 246Z" fill="{fill}"/><path d="M266 246Q294 222 328 246Q294 266 266 246Z" fill="{fill}"/>'
    if shape == "diamond":
        return f'<polygon points="218,211 249,246 218,281 187,246" fill="{fill}"/><polygon points="294,211 325,246 294,281 263,246" fill="{fill}"/>'
    if shape == "teardrop":
        return f'<path d="M218 207C250 244 244 281 218 281C192 281 186 244 218 207Z" fill="{fill}"/><path d="M294 207C326 244 320 281 294 281C268 281 262 244 294 207Z" fill="{fill}"/>'
    return f'<polygon points="{polygon_points(218, 246, 34, 6, 30)}" fill="{fill}"/><polygon points="{polygon_points(294, 246, 34, 6, 30)}" fill="{fill}"/>'


def skull_ornament(player: dict[str, Any]) -> str:
    palette = player["palette"]
    ornament = player["skullFront"]["ornament"]
    accent = palette["accent"]
    secondary = palette["secondary"]
    danger = palette["danger"]
    surface = palette["surfaceShadow"]
    if ornament == "crack":
        return f'<path d="M268 126L239 177L268 192L239 234" fill="none" stroke="{danger}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>'
    if ornament == "waves":
        return f'<path d="M186 167Q221 142 256 167T326 167M176 192Q216 166 256 192T336 192" fill="none" stroke="{accent}" stroke-width="8" stroke-linecap="round" opacity="0.85"/>'
    if ornament == "sprout":
        return f'<path d="M256 139Q250 91 269 67" fill="none" stroke="{accent}" stroke-width="10" stroke-linecap="round"/><ellipse cx="238" cy="85" rx="20" ry="38" transform="rotate(-48 238 85)" fill="{secondary}"/><ellipse cx="283" cy="73" rx="18" ry="36" transform="rotate(42 283 73)" fill="{secondary}"/>'
    if ornament == "halo":
        return f'<circle cx="256" cy="210" r="126" fill="none" stroke="{secondary}" stroke-width="12" opacity="0.74"/><circle cx="256" cy="210" r="145" fill="none" stroke="{accent}" stroke-width="4" stroke-dasharray="5 10"/>'
    if ornament == "compass":
        return f'<polygon points="{star_points(256, 177, 48, 18, 8, 22.5)}" fill="{accent}" stroke="{secondary}" stroke-width="4"/><circle cx="256" cy="177" r="9" fill="{surface}"/>'
    return f'<path d="M256 111L226 184L256 214L286 184ZM154 226L218 245L196 310M358 226L294 245L316 310M201 326L256 286L311 326" fill="none" stroke="{accent}" stroke-width="7" stroke-linejoin="round" opacity="0.88"/>'


def skull_motif(player: dict[str, Any], prefix: str) -> str:
    palette = player["palette"]
    model = player["skullFront"]
    cranium, jaw = skull_silhouette(model["silhouette"])
    teeth = model["jawTeeth"]
    parts = [
        f'<circle cx="256" cy="256" r="183" fill="none" stroke="{palette["danger"]}" stroke-width="7" stroke-dasharray="5 9"/>',
    ]
    if model["ornament"] == "halo":
        parts.append(skull_ornament(player))
    parts.extend(
        [
            f'<path d="{cranium}" fill="{palette["ink"]}" stroke="{palette["edge"]}" stroke-width="7" stroke-linejoin="round"/>',
            f'<path d="{jaw}" fill="{palette["ink"]}" stroke="{palette["edge"]}" stroke-width="7" stroke-linejoin="round"/>',
            eye_shapes(model["eyeShape"], palette["surfaceShadow"]),
            f'<path d="M256 270L238 303H274Z" fill="{palette["surfaceShadow"]}"/>',
        ]
    )
    if model["ornament"] != "halo":
        parts.append(skull_ornament(player))

    left = 214
    right = 298
    step = (right - left) / max(1, teeth - 1)
    parts.append(f'<path d="M204 350H308" stroke="{palette["surfaceShadow"]}" stroke-width="7" stroke-linecap="round"/>')
    for index in range(teeth):
        x = left + index * step
        parts.append(f'<path d="M{fmt(x)} 344V389" stroke="{palette["surfaceShadow"]}" stroke-width="6" stroke-linecap="round"/>')
    return "\n".join(parts)


def card_body(player: dict[str, Any], face: str, prefix: str) -> str:
    palette = player["palette"]
    semantic = palette["accent"] if face == "back" else palette["safe"] if face == "flower" else palette["danger"]
    motif = back_motif(player, prefix) if face == "back" else flower_motif(player, prefix) if face == "flower" else skull_motif(player, prefix)
    return f"""
    <g id="{prefix}-disc" data-player="{esc(player['id'])}" data-face="{face}">
      <circle cx="256" cy="267" r="224" fill="#000000" opacity="0.28" filter="url(#{prefix}-soft)"/>
      <circle cx="256" cy="256" r="232" fill="url(#{prefix}-edge)" filter="url(#{prefix}-shadow)"/>
      <circle cx="256" cy="256" r="216" fill="url(#{prefix}-surface)" stroke="{palette['edge']}" stroke-width="4"/>
      <circle cx="256" cy="256" r="202" fill="none" stroke="{semantic}" stroke-width="3" opacity="0.7"/>
      {motif}
      {owner_ticks(player)}
      <path d="M126 154A166 166 0 0 1 235 92" fill="none" stroke="{palette['ink']}" stroke-width="8" stroke-linecap="round" opacity="0.16"/>
    </g>
    """.strip()


def card_svg(player: dict[str, Any], face: str, model_version: str) -> str:
    prefix = f"{player['slug']}-{face}"
    labels = player["accessibility"]
    label_key = "backLabel" if face == "back" else "flowerLabel" if face == "flower" else "skullLabel"
    description = (
        "同一玩家所有个人牌共用的隐藏牌背。"
        if face == "back"
        else "翻开后表示安全的花牌正面。"
        if face == "flower"
        else "翻开后令挑战立即失败的骷髅牌正面。"
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512" role="img" aria-labelledby="title desc" data-model-version="{esc(model_version)}">
  <title id="title">{esc(labels[label_key])}</title>
  <desc id="desc">{esc(labels['ownerLabel'])}。{description}原创中性占位设计，不含官方美术。</desc>
  <defs>
    {svg_defs(player, prefix)}
  </defs>
  {card_body(player, face, prefix)}
</svg>
"""


def atlas_svg(model: dict[str, Any]) -> str:
    width = 1900
    height = 1090
    card_scale = 0.43
    card_size = 512 * card_scale
    start_x = 160
    col_step = 286
    row_y = {"back": 182, "flower": 475, "skull": 768}
    faces = ("back", "flower", "skull")
    face_labels = {"back": "统一牌背", "flower": "花牌正面", "skull": "骷髅牌正面"}
    all_defs: list[str] = []
    all_cards: list[str] = []

    for player in model["players"]:
        col = player["seatIndex"]
        x = start_x + col * col_step
        all_cards.append(
            f'<text x="{fmt(x + card_size/2)}" y="128" text-anchor="middle" fill="#F3EFE8" font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif" font-size="27" font-weight="700">玩家 {col+1} · {esc(player["label"])}</text>'
        )
        all_cards.append(
            f'<text x="{fmt(x + card_size/2)}" y="158" text-anchor="middle" fill="{player["palette"]["accent"]}" font-family="Arial, sans-serif" font-size="17" font-weight="700">{esc(player["accessibility"]["patternCode"])} · {esc(player["slug"])}</text>'
        )
        for face in faces:
            prefix = f"atlas-{player['slug']}-{face}"
            all_defs.append(svg_defs(player, prefix))
            y = row_y[face]
            all_cards.append(
                f'<g transform="translate({fmt(x)} {fmt(y)}) scale({fmt(card_scale)})">{card_body(player, face, prefix)}</g>'
            )
            all_cards.append(
                f'<text x="{fmt(x + card_size/2)}" y="{fmt(y + card_size + 29)}" text-anchor="middle" fill="#AEB5BC" font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif" font-size="17">{face_labels[face]}</text>'
            )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc" data-model-version="{esc(model['modelVersion'])}">
  <title id="title">骷髅牌六套玩家卡牌正反面模型总览</title>
  <desc id="desc">从左到右为六名玩家；从上到下为每套统一牌背、花牌正面和骷髅牌正面。</desc>
  <defs>
    <linearGradient id="atlas-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#111419"/><stop offset="1" stop-color="#272C33"/></linearGradient>
    {''.join(all_defs)}
  </defs>
  <rect width="{width}" height="{height}" rx="38" fill="url(#atlas-bg)"/>
  <text x="70" y="58" fill="#F4EFE8" font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif" font-size="34" font-weight="700">玩家卡牌正反面生成模型</text>
  <text x="70" y="94" fill="#9FA8B0" font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif" font-size="18">JSON 模型 v{esc(model['modelVersion'])} · 每名玩家的花牌与骷髅牌共用同一牌背 · 512 x 512 SVG</text>
  <path d="M58 438H1842M58 731H1842" stroke="#FFFFFF" stroke-opacity="0.08"/>
  {''.join(all_cards)}
</svg>
"""


def write_generated_assets(model: dict[str, Any]) -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    expected_names: set[str] = set()
    manifest_players: list[dict[str, Any]] = []
    for player in model["players"]:
        seat = player["seatIndex"] + 1
        player_assets: dict[str, Any] = {
            "id": player["id"],
            "seatIndex": player["seatIndex"],
            "label": player["label"],
            "slug": player["slug"],
            "patternCode": player["accessibility"]["patternCode"],
            "assets": {},
        }
        for face in ("back", "flower", "skull"):
            filename = f"seat-{seat}-{player['slug']}-{face}.svg"
            expected_names.add(filename)
            content = card_svg(player, face, model["modelVersion"])
            path = GENERATED_DIR / filename
            path.write_text(content, encoding="utf-8", newline="\n")
            player_assets["assets"][face] = {
                "path": f"generated/{filename}",
                "sha256": sha256_text(content),
                "width": 512,
                "height": 512,
            }
        manifest_players.append(player_assets)

    for stale in GENERATED_DIR.glob("seat-*-*.svg"):
        if stale.name not in expected_names:
            stale.unlink()

    atlas = atlas_svg(model)
    ATLAS_PATH.write_text(atlas, encoding="utf-8", newline="\n")

    model_text = MODEL_PATH.read_text(encoding="utf-8")
    manifest = {
        "schemaVersion": 1,
        "gameKey": "skull",
        "modelVersion": model["modelVersion"],
        "generatorVersion": model["renderer"]["generatorVersion"],
        "source": "../../model/player-card-models.json",
        "sourceSha256": sha256_text(model_text),
        "assetCount": len(expected_names),
        "atlas": {
            "path": "player-card-atlas.svg",
            "sha256": sha256_text(atlas),
            "width": 1900,
            "height": 1090,
        },
        "players": manifest_players,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def main() -> int:
    try:
        model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
        manifest = write_generated_assets(model)
    except Exception as exc:  # noqa: BLE001 - command-line generator reports all failures.
        print(f"Failed to generate player cards: {exc}", file=sys.stderr)
        return 1
    print(
        f"Generated {manifest['assetCount']} player card SVGs, "
        f"1 atlas, and {MANIFEST_PATH.relative_to(ROOT)} from model {manifest['modelVersion']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
