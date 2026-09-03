#!/usr/bin/env python3
"""Generate deterministic Ticket to Ride: Europe model catalogs and SVG wireframes."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "model"
EXAMPLE_DIR = ROOT / "examples"
ASSET_DIR = ROOT / "assets"

GAME_KEY = "ticket-to-ride-europe-base"
MODEL_VERSION = "1.0.0"
CANVAS_WIDTH = 1360
CANVAS_HEIGHT = 880

BASE_COLORS = (
    "purple",
    "blue",
    "orange",
    "white",
    "green",
    "yellow",
    "black",
    "red",
)

COLOR_VISUALS = {
    "purple": {"hex": "#79589F", "pattern": "dots", "code": "PU", "labelZh": "紫色"},
    "blue": {"hex": "#3479B8", "pattern": "horizontal", "code": "BL", "labelZh": "蓝色"},
    "orange": {"hex": "#D47A2C", "pattern": "diagonal", "code": "OR", "labelZh": "橙色"},
    "white": {"hex": "#EEECE4", "pattern": "cross", "code": "WH", "labelZh": "白色"},
    "green": {"hex": "#4C8758", "pattern": "diamonds", "code": "GR", "labelZh": "绿色"},
    "yellow": {"hex": "#D0A92C", "pattern": "waves", "code": "YE", "labelZh": "黄色"},
    "black": {"hex": "#30343A", "pattern": "grid", "code": "BK", "labelZh": "黑色"},
    "red": {"hex": "#B84C46", "pattern": "triangles", "code": "RD", "labelZh": "红色"},
    "gray": {"hex": "#8A8E93", "pattern": "neutral", "code": "GY", "labelZh": "灰色"},
    "locomotive": {"hex": "#8A607F", "pattern": "spectrum", "code": "LO", "labelZh": "彩虹"},
}

ROUTE_POINTS = {1: 1, 2: 2, 3: 4, 4: 7, 6: 15, 8: 21}


# Layout coordinates are a schematic interaction canvas, not geographic coordinates.
CITY_SPECS = [
    ("amsterdam", "AMSTERDAM", "阿姆斯特丹", "Amsterdam", 419, 249),
    ("angora", "ANGORA", "安哥拉", "Ankara", 1186, 812),
    ("athina", "ATHÍNA", "雅典", "Athens", 906, 812),
    ("barcelona", "BARCELONA", "巴塞罗那", "Barcelona", 267, 763),
    ("berlin", "BERLIN", "柏林", "Berlin", 664, 280),
    ("brest", "BREST", "布雷斯特", "Brest", 147, 406),
    ("brindisi", "BRINDISI", "布林迪西", "Brindisi", 738, 706),
    ("bruxelles", "BRUXELLES", "布鲁塞尔", "Brussels", 386, 310),
    ("bucuresti", "BUCURESTI", "布加勒斯特", "Bucharest", 1015, 570),
    ("budapest", "BUDAPEST", "布达佩斯", "Budapest", 809, 474),
    ("cadiz", "CÁDIZ", "加的斯", "Cádiz", 116, 850),
    ("constantinople", "CONSTANTINOPLE", "君士坦丁堡", "Istanbul", 1085, 740),
    ("danzig", "DANZIG", "但泽", "Gdańsk", 818, 172),
    ("dieppe", "DIEPPE", "迪耶普", "Dieppe", 271, 368),
    ("edinburgh", "EDINBURGH", "爱丁堡", "Edinburgh", 197, 39),
    ("erzurum", "ERZURUM", "埃尔祖鲁姆", "Erzurum", 1299, 780),
    ("essen", "ESSEN", "埃森", "Essen", 528, 260),
    ("frankfurt", "FRANKFURT", "法兰克福", "Frankfurt", 507, 357),
    ("kharkiv", "KHARKIV", "哈尔科夫", "Kharkiv", 1273, 414),
    ("kobenhavn", "KØBENHAVN", "哥本哈根", "Copenhagen", 627, 116),
    ("kyiv", "KYÏV", "基辅", "Kyiv", 1092, 342),
    ("lisboa", "LISBOA", "里斯本", "Lisbon", 24, 778),
    ("london", "LONDON", "伦敦", "London", 286, 243),
    ("madrid", "MADRID", "马德里", "Madrid", 118, 750),
    ("marseille", "MARSEILLE", "马赛", "Marseille", 458, 630),
    ("moskva", "MOSKVA", "莫斯科", "Moscow", 1296, 208),
    ("munchen", "MÜNCHEN", "慕尼黑", "Munich", 584, 417),
    ("palermo", "PALERMO", "巴勒莫", "Palermo", 671, 851),
    ("pamplona", "PAMPLONA", "潘普洛纳", "Pamplona", 251, 637),
    ("paris", "PARIS", "巴黎", "Paris", 339, 428),
    ("petrograd", "PETROGRAD", "彼得格勒", "Saint Petersburg", 1164, 43),
    ("riga", "RIGA", "里加", "Riga", 931, 51),
    ("roma", "ROMA", "罗马", "Rome", 620, 672),
    ("rostov", "ROSTOV", "罗斯托夫", "Rostov-on-Don", 1331, 487),
    ("sarajevo", "SARAJEVO", "萨拉热窝", "Sarajevo", 841, 645),
    ("sevastopol", "SEVASTOPOL", "塞瓦斯托波尔", "Sevastopol", 1202, 589),
    ("smolensk", "SMOLENSK", "斯摩棱斯克", "Smolensk", 1177, 242),
    ("smyrna", "SMYRNA", "士麦那", "İzmir", 1023, 848),
    ("sochi", "SOCHI", "索契", "Sochi", 1323, 609),
    ("sofia", "SOFIA", "索非亚", "Sofia", 931, 658),
    ("stockholm", "STOCKHOLM", "斯德哥尔摩", "Stockholm", 767, 11),
    ("venezia", "VENEZIA", "威尼斯", "Venice", 610, 549),
    ("warszawa", "WARSZAWA", "华沙", "Warsaw", 887, 270),
    ("wien", "WIEN", "维也纳", "Vienna", 743, 441),
    ("wilno", "WILNO", "维尔诺", "Vilnius", 1039, 235),
    ("zagrab", "ZÁGRÁB", "萨格勒布", "Zagreb", 726, 565),
    ("zurich", "ZÜRICH", "苏黎世", "Zürich", 495, 503),
]

ALIASES = {
    "Amsterdam": "amsterdam",
    "Angora": "angora",
    "Athina": "athina",
    "Barcelona": "barcelona",
    "Berlin": "berlin",
    "Brest": "brest",
    "Brindisi": "brindisi",
    "Bruxelles": "bruxelles",
    "Bucuresti": "bucuresti",
    "Budapest": "budapest",
    "Cadiz": "cadiz",
    "Constantinople": "constantinople",
    "Danzig": "danzig",
    "Dieppe": "dieppe",
    "Edinburgh": "edinburgh",
    "Erzurum": "erzurum",
    "Essen": "essen",
    "Frankfurt": "frankfurt",
    "Kharkov": "kharkiv",
    "Kharkiv": "kharkiv",
    "Kobenhavn": "kobenhavn",
    "Kyiv": "kyiv",
    "Lisbon": "lisboa",
    "Lisboa": "lisboa",
    "London": "london",
    "Madrid": "madrid",
    "Marseille": "marseille",
    "Moskva": "moskva",
    "Munchen": "munchen",
    "Palermo": "palermo",
    "Pamplona": "pamplona",
    "Paris": "paris",
    "Petrograd": "petrograd",
    "Riga": "riga",
    "Roma": "roma",
    "Rostov": "rostov",
    "Sarajevo": "sarajevo",
    "Sevastopol": "sevastopol",
    "Smolensk": "smolensk",
    "Smyrna": "smyrna",
    "Sochi": "sochi",
    "Sofia": "sofia",
    "Stockholm": "stockholm",
    "Venezia": "venezia",
    "Warszawa": "warszawa",
    "Wien": "wien",
    "Wilno": "wilno",
    "Zagreb": "zagrab",
    "Zagrab": "zagrab",
    "Zurich": "zurich",
}


# Each tuple is (city A, city B, length, color, kind, minimum locomotives).
# It is normalized from multiple public data transcriptions and manually checked.
ROUTE_SPECS = [
    ("Amsterdam", "Bruxelles", 1, "black", "standard", 0),
    ("Amsterdam", "Essen", 3, "yellow", "standard", 0),
    ("Amsterdam", "Frankfurt", 2, "white", "standard", 0),
    ("Amsterdam", "London", 2, "gray", "ferry", 2),
    ("Angora", "Constantinople", 2, "gray", "tunnel", 0),
    ("Angora", "Erzurum", 3, "black", "standard", 0),
    ("Angora", "Smyrna", 3, "orange", "tunnel", 0),
    ("Athina", "Brindisi", 4, "gray", "ferry", 1),
    ("Athina", "Sarajevo", 4, "green", "standard", 0),
    ("Athina", "Smyrna", 2, "gray", "ferry", 1),
    ("Athina", "Sofia", 3, "purple", "standard", 0),
    ("Barcelona", "Madrid", 2, "yellow", "standard", 0),
    ("Barcelona", "Marseille", 4, "gray", "standard", 0),
    ("Barcelona", "Pamplona", 2, "gray", "tunnel", 0),
    ("Berlin", "Danzig", 4, "gray", "standard", 0),
    ("Berlin", "Essen", 2, "blue", "standard", 0),
    ("Berlin", "Frankfurt", 3, "black", "standard", 0),
    ("Berlin", "Frankfurt", 3, "red", "standard", 0),
    ("Berlin", "Warszawa", 4, "purple", "standard", 0),
    ("Berlin", "Warszawa", 4, "yellow", "standard", 0),
    ("Berlin", "Wien", 3, "green", "standard", 0),
    ("Brest", "Dieppe", 2, "orange", "standard", 0),
    ("Brest", "Pamplona", 4, "purple", "standard", 0),
    ("Brest", "Paris", 3, "black", "standard", 0),
    ("Brindisi", "Palermo", 3, "gray", "ferry", 1),
    ("Brindisi", "Roma", 2, "white", "standard", 0),
    ("Bruxelles", "Dieppe", 2, "green", "standard", 0),
    ("Bruxelles", "Frankfurt", 2, "blue", "standard", 0),
    ("Bruxelles", "Paris", 2, "yellow", "standard", 0),
    ("Bruxelles", "Paris", 2, "red", "standard", 0),
    ("Bucuresti", "Budapest", 4, "gray", "tunnel", 0),
    ("Bucuresti", "Constantinople", 3, "yellow", "standard", 0),
    ("Bucuresti", "Kyiv", 4, "gray", "standard", 0),
    ("Bucuresti", "Sevastopol", 4, "white", "standard", 0),
    ("Bucuresti", "Sofia", 2, "gray", "tunnel", 0),
    ("Budapest", "Kyiv", 6, "gray", "tunnel", 0),
    ("Budapest", "Sarajevo", 3, "purple", "standard", 0),
    ("Budapest", "Wien", 1, "red", "standard", 0),
    ("Budapest", "Wien", 1, "white", "standard", 0),
    ("Budapest", "Zagreb", 2, "orange", "standard", 0),
    ("Cadiz", "Lisbon", 2, "blue", "standard", 0),
    ("Cadiz", "Madrid", 3, "orange", "standard", 0),
    ("Constantinople", "Sevastopol", 4, "gray", "ferry", 2),
    ("Constantinople", "Smyrna", 2, "gray", "tunnel", 0),
    ("Constantinople", "Sofia", 3, "blue", "standard", 0),
    ("Danzig", "Riga", 3, "black", "standard", 0),
    ("Danzig", "Warszawa", 2, "white", "standard", 0),
    ("Dieppe", "London", 2, "gray", "ferry", 1),
    ("Dieppe", "London", 2, "gray", "ferry", 1),
    ("Dieppe", "Paris", 1, "purple", "standard", 0),
    ("Edinburgh", "London", 4, "orange", "standard", 0),
    ("Edinburgh", "London", 4, "black", "standard", 0),
    ("Erzurum", "Sevastopol", 4, "gray", "ferry", 2),
    ("Erzurum", "Sochi", 3, "red", "tunnel", 0),
    ("Essen", "Frankfurt", 2, "green", "standard", 0),
    ("Essen", "Kobenhavn", 3, "gray", "ferry", 1),
    ("Essen", "Kobenhavn", 3, "gray", "ferry", 1),
    ("Frankfurt", "Munchen", 2, "purple", "standard", 0),
    ("Frankfurt", "Paris", 3, "white", "standard", 0),
    ("Frankfurt", "Paris", 3, "orange", "standard", 0),
    ("Kharkov", "Kyiv", 4, "gray", "standard", 0),
    ("Kharkov", "Moskva", 4, "gray", "standard", 0),
    ("Kharkov", "Rostov", 2, "green", "standard", 0),
    ("Kobenhavn", "Stockholm", 3, "yellow", "standard", 0),
    ("Kobenhavn", "Stockholm", 3, "white", "standard", 0),
    ("Kyiv", "Smolensk", 3, "red", "standard", 0),
    ("Kyiv", "Warszawa", 4, "gray", "standard", 0),
    ("Kyiv", "Wilno", 2, "gray", "standard", 0),
    ("Lisbon", "Madrid", 3, "purple", "standard", 0),
    ("Madrid", "Pamplona", 3, "black", "tunnel", 0),
    ("Madrid", "Pamplona", 3, "white", "tunnel", 0),
    ("Marseille", "Pamplona", 4, "red", "standard", 0),
    ("Marseille", "Paris", 4, "gray", "standard", 0),
    ("Marseille", "Roma", 4, "gray", "tunnel", 0),
    ("Marseille", "Zurich", 2, "purple", "tunnel", 0),
    ("Moskva", "Petrograd", 4, "white", "standard", 0),
    ("Moskva", "Smolensk", 2, "orange", "standard", 0),
    ("Munchen", "Venezia", 2, "blue", "tunnel", 0),
    ("Munchen", "Wien", 3, "orange", "standard", 0),
    ("Munchen", "Zurich", 2, "yellow", "tunnel", 0),
    ("Palermo", "Roma", 4, "gray", "ferry", 1),
    ("Palermo", "Smyrna", 6, "gray", "ferry", 2),
    ("Pamplona", "Paris", 4, "blue", "standard", 0),
    ("Pamplona", "Paris", 4, "green", "standard", 0),
    ("Paris", "Zurich", 3, "gray", "tunnel", 0),
    ("Petrograd", "Riga", 4, "gray", "standard", 0),
    ("Petrograd", "Stockholm", 8, "gray", "tunnel", 0),
    ("Petrograd", "Wilno", 4, "blue", "standard", 0),
    ("Riga", "Wilno", 4, "green", "standard", 0),
    ("Roma", "Venezia", 2, "black", "standard", 0),
    ("Rostov", "Sevastopol", 4, "gray", "standard", 0),
    ("Rostov", "Sochi", 2, "gray", "standard", 0),
    ("Sarajevo", "Sofia", 2, "gray", "tunnel", 0),
    ("Sarajevo", "Zagreb", 3, "red", "standard", 0),
    ("Sevastopol", "Sochi", 2, "gray", "ferry", 1),
    ("Smolensk", "Wilno", 3, "yellow", "standard", 0),
    ("Venezia", "Zagreb", 2, "gray", "standard", 0),
    ("Venezia", "Zurich", 2, "green", "tunnel", 0),
    ("Warszawa", "Wien", 4, "blue", "standard", 0),
    ("Warszawa", "Wilno", 3, "red", "standard", 0),
    ("Wien", "Zagreb", 2, "gray", "standard", 0),
]


LONG_TICKETS = [
    ("Brest", "Petrograd", 20),
    ("Lisboa", "Danzig", 20),
    ("Palermo", "Moskva", 20),
    ("Cadiz", "Stockholm", 21),
    ("Edinburgh", "Athina", 21),
    ("Kobenhavn", "Erzurum", 21),
]

REGULAR_TICKETS = [
    ("Athina", "Angora", 5),
    ("Budapest", "Sofia", 5),
    ("Frankfurt", "Kobenhavn", 5),
    ("Rostov", "Erzurum", 5),
    ("Sofia", "Smyrna", 5),
    ("Kyiv", "Petrograd", 6),
    ("Warszawa", "Smolensk", 6),
    ("Zagrab", "Brindisi", 6),
    ("Zurich", "Brindisi", 6),
    ("Zurich", "Budapest", 6),
    ("Amsterdam", "Pamplona", 7),
    ("Brest", "Marseille", 7),
    ("Edinburgh", "Paris", 7),
    ("London", "Berlin", 7),
    ("Paris", "Zagrab", 7),
    ("Barcelona", "Bruxelles", 8),
    ("Barcelona", "Munchen", 8),
    ("Berlin", "Bucuresti", 8),
    ("Brest", "Venezia", 8),
    ("Kyiv", "Sochi", 8),
    ("Madrid", "Dieppe", 8),
    ("Madrid", "Zurich", 8),
    ("Marseille", "Essen", 8),
    ("Palermo", "Constantinople", 8),
    ("Paris", "Wien", 8),
    ("Roma", "Smyrna", 8),
    ("Sarajevo", "Sevastopol", 8),
    ("Smolensk", "Rostov", 8),
    ("Berlin", "Roma", 9),
    ("Bruxelles", "Danzig", 9),
    ("Angora", "Kharkiv", 10),
    ("Essen", "Kyiv", 10),
    ("London", "Wien", 10),
    ("Riga", "Bucuresti", 10),
    ("Venezia", "Constantinople", 10),
    ("Athina", "Wilno", 11),
    ("Stockholm", "Wien", 11),
    ("Amsterdam", "Wilno", 12),
    ("Berlin", "Moskva", 12),
    ("Frankfurt", "Smolensk", 13),
]


def city_id(name: str) -> str:
    try:
        return ALIASES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown city alias: {name}") from exc


def city_records() -> list[dict[str, Any]]:
    return [
        {
            "id": item[0],
            "boardLabel": item[1],
            "labelZhCN": item[2],
            "modernName": item[3],
            "position": {"x": item[4], "y": item[5]},
        }
        for item in CITY_SPECS
    ]


def route_records() -> list[dict[str, Any]]:
    pairs = [tuple(sorted((city_id(a), city_id(b)))) for a, b, *_ in ROUTE_SPECS]
    counts = Counter(pairs)
    seen: defaultdict[tuple[str, str], int] = defaultdict(int)
    records: list[dict[str, Any]] = []
    for source_a, source_b, length, color, kind, locomotives in ROUTE_SPECS:
        pair = tuple(sorted((city_id(source_a), city_id(source_b))))
        index = seen[pair]
        seen[pair] += 1
        suffix = f"-{chr(97 + index)}" if counts[pair] > 1 else ""
        pair_slug = f"{pair[0]}-{pair[1]}"
        records.append(
            {
                "id": f"route-{pair_slug}{suffix}",
                "fromCityId": city_id(source_a),
                "toCityId": city_id(source_b),
                "length": length,
                "points": ROUTE_POINTS[length],
                "color": color,
                "kind": kind,
                "locomotivesRequired": locomotives,
                "parallelGroupId": f"parallel-{pair_slug}" if counts[pair] > 1 else None,
                "trackIndex": index,
            }
        )
    return records


def board_map() -> dict[str, Any]:
    routes = route_records()
    pair_counts = Counter(
        tuple(sorted((route["fromCityId"], route["toCityId"]))) for route in routes
    )
    kind_counts = Counter(route["kind"] for route in routes)
    return {
        "$schema": "./board-map.schema.json",
        "schemaVersion": 1,
        "modelVersion": MODEL_VERSION,
        "gameKey": GAME_KEY,
        "coordinateSystem": {
            "kind": "schematic",
            "width": CANVAS_WIDTH,
            "height": CANVAS_HEIGHT,
            "origin": "top-left",
            "units": "logical-px",
        },
        "routeColors": [*BASE_COLORS, "gray"],
        "routeKinds": ["standard", "tunnel", "ferry"],
        "routeScoring": {str(key): value for key, value in ROUTE_POINTS.items()},
        "cities": city_records(),
        "routes": routes,
        "summary": {
            "cityCount": len(CITY_SPECS),
            "routeCount": len(routes),
            "cityPairCount": len(pair_counts),
            "doubleRoutePairCount": sum(value == 2 for value in pair_counts.values()),
            "routeKindCounts": dict(sorted(kind_counts.items())),
            "totalTrackSpaces": sum(route["length"] for route in routes),
        },
        "copyrightBoundary": (
            "Schematic coordinates and rule facts only; no official board art, logo, "
            "illustration, or print-ready reproduction is included."
        ),
    }


def ticket_records() -> list[dict[str, Any]]:
    labels = {item[0]: item[2] for item in CITY_SPECS}
    records: list[dict[str, Any]] = []
    for category, specs in (("long", LONG_TICKETS), ("regular", REGULAR_TICKETS)):
        for index, (source, target, points) in enumerate(specs, start=1):
            from_id = city_id(source)
            to_id = city_id(target)
            records.append(
                {
                    "id": f"ticket-{category}-{index:03d}",
                    "category": category,
                    "fromCityId": from_id,
                    "toCityId": to_id,
                    "points": points,
                    "labelZhCN": f"{labels[from_id]} - {labels[to_id]}",
                }
            )
    return records


def card_catalog() -> dict[str, Any]:
    train_types = []
    for color in BASE_COLORS:
        visual = COLOR_VISUALS[color]
        train_types.append(
            {
                "id": f"train-{color}",
                "color": color,
                "labelZhCN": f"{visual['labelZh']}车票",
                "copies": 12,
                "wild": False,
                "visual": {
                    "accent": visual["hex"],
                    "pattern": visual["pattern"],
                    "accessibilityCode": visual["code"],
                },
            }
        )
    loco = COLOR_VISUALS["locomotive"]
    train_types.append(
        {
            "id": "train-locomotive",
            "color": "locomotive",
            "labelZhCN": "彩虹车票",
            "copies": 14,
            "wild": True,
            "visual": {
                "accent": loco["hex"],
                "pattern": loco["pattern"],
                "accessibilityCode": loco["code"],
            },
        }
    )
    tickets = ticket_records()
    return {
        "$schema": "./card-catalog.schema.json",
        "schemaVersion": 1,
        "modelVersion": MODEL_VERSION,
        "gameKey": GAME_KEY,
        "trainCardTypes": train_types,
        "destinationTickets": tickets,
        "bonusCards": [
            {
                "id": "bonus-european-express",
                "labelZhCN": "欧洲快车",
                "points": 10,
                "condition": "longest-continuous-path",
                "sharedOnTie": True,
            }
        ],
        "visualModel": {
            "trainCard": {
                "width": 440,
                "height": 680,
                "cornerRadius": 28,
                "safeInset": 36,
                "sharedBackId": "train-card-back",
            },
            "destinationTicket": {
                "width": 680,
                "height": 440,
                "cornerRadius": 28,
                "safeInset": 36,
                "sharedBackId": "destination-ticket-back",
            },
        },
        "summary": {
            "trainCardCount": sum(item["copies"] for item in train_types),
            "trainTypeCount": len(train_types),
            "regularDestinationTicketCount": sum(
                item["category"] == "regular" for item in tickets
            ),
            "longDestinationTicketCount": sum(
                item["category"] == "long" for item in tickets
            ),
            "destinationTicketCount": len(tickets),
        },
        "copyrightBoundary": (
            "Facts and original neutral visual tokens only; official card illustrations, "
            "logos, typography, and printable layouts are excluded."
        ),
    }


SCENE_SPECS = [
    {
        "id": "setup.ticket-selection",
        "phase": "setup_ticket_selection",
        "title": "秘密选择初始任务",
        "purpose": "每名玩家从一张长程与三张短程任务中至少保留两张。",
        "entry": ["本人收到四张私有候选", "尚未提交初始选择"],
        "actions": ["keep_initial_tickets"],
        "focusZones": ["private-ticket-drawer", "selection-counter", "player-ready-strip"],
        "privacy": "private",
        "exit": "所有有效玩家提交后进入首个回合",
        "transient": False,
    },
    {
        "id": "turn.choose-action",
        "phase": "turn_idle",
        "title": "选择本回合行动",
        "purpose": "在抽车票、占轨、抽任务和建站四种行动中选择一个。",
        "entry": ["轮到当前玩家", "不存在待决子流程"],
        "actions": [
            "draw_train_card",
            "claim_route",
            "draw_destination_tickets",
            "build_station",
        ],
        "focusZones": ["europe-map", "train-market", "turn-actions", "self-hand"],
        "privacy": "mixed",
        "exit": "主行动完成或进入一个待决子流程",
        "transient": False,
    },
    {
        "id": "draw.train-first",
        "phase": "turn_idle",
        "title": "抽取第一张车票",
        "purpose": "从五张明牌或牌库顶选择第一张。",
        "entry": ["当前玩家在本地打开抽牌模式", "尚未提交主行动"],
        "actions": ["draw_train_card"],
        "focusZones": ["train-market", "train-deck", "draw-rule-hint"],
        "privacy": "public",
        "exit": "拿公共彩虹后结束回合，否则可能进入第二次抽牌",
        "transient": True,
    },
    {
        "id": "draw.train-second",
        "phase": "train_draw_second",
        "title": "抽取第二张车票",
        "purpose": "选择第二张合法车票；公共彩虹不可作为第二张。",
        "entry": ["第一张未以公共彩虹结束回合", "仍有可抽牌"],
        "actions": ["draw_train_card"],
        "focusZones": ["train-market", "train-deck", "locomotive-lock-hint"],
        "privacy": "public",
        "exit": "第二张结算后结束回合",
        "transient": False,
    },
    {
        "id": "claim.route-select",
        "phase": "turn_idle",
        "title": "选择轨道与支付",
        "purpose": "选择开放轨道，声明灰色支付颜色并提交具体手牌。",
        "entry": ["当前玩家在本地打开占轨模式"],
        "actions": ["claim_route"],
        "focusZones": ["claimable-routes", "self-hand", "payment-preview"],
        "privacy": "mixed",
        "exit": "普通或渡轮立即完成；隧道可能进入补付",
        "transient": True,
    },
    {
        "id": "claim.tunnel-reveal",
        "phase": "tunnel_payment",
        "title": "揭示隧道风险",
        "purpose": "表现服务端已固定的风险牌和额外费用。",
        "entry": ["最新事件为 tunnel_cards_revealed", "本地尚未完成揭示表现"],
        "actions": [],
        "focusZones": ["focused-tunnel", "revealed-risk-cards", "extra-cost-meter"],
        "privacy": "public",
        "exit": "动画完成后显示补付或放弃操作",
        "transient": True,
    },
    {
        "id": "claim.tunnel-payment",
        "phase": "tunnel_payment",
        "title": "补付或放弃隧道",
        "purpose": "隧道发起者支付额外同色/彩虹牌，或收回初始牌结束回合。",
        "entry": ["pendingTunnel.status 为 awaiting_payment"],
        "actions": ["pay_tunnel_extra", "decline_tunnel"],
        "focusZones": ["locked-initial-payment", "self-hand", "tunnel-decision"],
        "privacy": "mixed",
        "exit": "成功占轨或放弃后结束回合",
        "transient": False,
    },
    {
        "id": "draw.ticket-choice",
        "phase": "ticket_choice",
        "title": "选择新任务",
        "purpose": "从最多三张私有候选中至少保留一张。",
        "entry": ["本人存在 pendingTicketChoice"],
        "actions": ["keep_destination_tickets"],
        "focusZones": ["private-ticket-drawer", "keep-counter", "commit-warning"],
        "privacy": "private",
        "exit": "保留牌入手，其余稳定置于任务牌库底部",
        "transient": False,
    },
    {
        "id": "station.build",
        "phase": "turn_idle",
        "title": "建造火车站",
        "purpose": "选择无站城市，并按本局第几个车站支付一至三张牌。",
        "entry": ["当前玩家在本地打开建站模式", "仍有火车站"],
        "actions": ["build_station"],
        "focusZones": ["station-eligible-cities", "self-hand", "station-cost"],
        "privacy": "mixed",
        "exit": "车站落位并结束回合",
        "transient": True,
    },
    {
        "id": "round.final-turns",
        "phase": "turn_idle",
        "title": "最后一轮",
        "purpose": "持续显示触发者和尚未完成最终回合的玩家顺序。",
        "entry": ["finalRound 已触发", "remainingPlayerIds 非空"],
        "actions": [
            "draw_train_card",
            "claim_route",
            "draw_destination_tickets",
            "build_station",
        ],
        "focusZones": ["final-round-banner", "remaining-turn-order", "turn-actions"],
        "privacy": "public",
        "exit": "所有剩余最终回合完成",
        "transient": False,
    },
    {
        "id": "scoring.station-allocation",
        "phase": "final_station_assignment",
        "title": "选择火车站借线",
        "purpose": "每位建站玩家为每座站选择至多一条相邻对手轨道。",
        "entry": ["最后一轮结束", "本人仍有未确认站点分配"],
        "actions": ["assign_station_routes"],
        "focusZones": ["owned-stations", "borrowable-routes", "private-ticket-preview"],
        "privacy": "private",
        "exit": "所有有效玩家确认或超时自动分配",
        "transient": False,
    },
    {
        "id": "scoring.breakdown",
        "phase": "scoring",
        "title": "终局计分",
        "purpose": "展示线路、任务、未建站与最长路线的逐项结果。",
        "entry": ["站点分配全部完成"],
        "actions": [],
        "focusZones": ["score-breakdown", "revealed-tickets", "longest-path-highlight"],
        "privacy": "public",
        "exit": "服务端生成最终排名",
        "transient": True,
    },
    {
        "id": "game.finished",
        "phase": "finished",
        "title": "游戏结束",
        "purpose": "展示并列安全的名次、胜者、同分依据与再来一局入口。",
        "entry": ["result 已生成"],
        "actions": [],
        "focusZones": ["winners", "ranking", "score-breakdown", "restart"],
        "privacy": "public",
        "exit": "宿主再来一局流程",
        "transient": False,
    },
]


def scene_catalog() -> dict[str, Any]:
    return {
        "$schema": "./scene-catalog.schema.json",
        "schemaVersion": 1,
        "modelVersion": MODEL_VERSION,
        "gameKey": GAME_KEY,
        "layout": {
            "desktop": {
                "mode": "immersive",
                "mapMinShare": 0.64,
                "sidePanelMaxWidth": 420,
                "privateHandPlacement": "bottom",
            },
            "mobile": {
                "mapViewport": "pan-zoom",
                "privateControls": "bottom-sheet",
                "minimumTouchTarget": 44,
            },
        },
        "mapLayers": [
            "terrain-layer",
            "route-base-layer",
            "route-owner-layer",
            "city-layer",
            "station-layer",
            "interaction-layer",
            "effect-layer",
        ],
        "scenes": SCENE_SPECS,
    }


def state_machine() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "modelVersion": MODEL_VERSION,
        "gameKey": GAME_KEY,
        "initialPhase": "setup_ticket_selection",
        "terminalPhase": "finished",
        "phases": [
            "setup_ticket_selection",
            "turn_idle",
            "train_draw_second",
            "tunnel_payment",
            "ticket_choice",
            "final_station_assignment",
            "scoring",
            "finished",
        ],
        "transitions": [
            {
                "from": "setup_ticket_selection",
                "action": "keep_initial_tickets",
                "to": "turn_idle",
                "guard": "all active players submitted",
            },
            {
                "from": "turn_idle",
                "action": "draw_train_card",
                "to": "train_draw_second",
                "guard": "first draw permits a second draw",
            },
            {
                "from": "turn_idle",
                "action": "draw_train_card",
                "to": "turn_idle",
                "guard": "face-up locomotive or no second card ends turn",
            },
            {
                "from": "train_draw_second",
                "action": "draw_train_card",
                "to": "turn_idle",
                "guard": "second card resolves and turn advances",
            },
            {
                "from": "turn_idle",
                "action": "claim_route",
                "to": "turn_idle",
                "guard": "standard/ferry or zero-extra tunnel resolves",
            },
            {
                "from": "turn_idle",
                "action": "claim_route",
                "to": "tunnel_payment",
                "guard": "tunnel reveals a positive extra cost",
            },
            {
                "from": "tunnel_payment",
                "action": "pay_tunnel_extra",
                "to": "turn_idle",
                "guard": "payment is legal; route is claimed and turn advances",
            },
            {
                "from": "tunnel_payment",
                "action": "decline_tunnel",
                "to": "turn_idle",
                "guard": "initial cards return and turn advances",
            },
            {
                "from": "turn_idle",
                "action": "draw_destination_tickets",
                "to": "ticket_choice",
                "guard": "at least one destination ticket is available",
            },
            {
                "from": "ticket_choice",
                "action": "keep_destination_tickets",
                "to": "turn_idle",
                "guard": "at least one offered ticket is kept",
            },
            {
                "from": "turn_idle",
                "action": "build_station",
                "to": "turn_idle",
                "guard": "city and payment are legal; turn advances",
            },
            {
                "from": "turn_idle",
                "action": "end_final_turn",
                "to": "final_station_assignment",
                "guard": "finalRound.remainingPlayerIds becomes empty",
            },
            {
                "from": "final_station_assignment",
                "action": "assign_station_routes",
                "to": "scoring",
                "guard": "all active players confirmed or were auto-assigned",
            },
            {
                "from": "scoring",
                "action": "calculate_result",
                "to": "finished",
                "guard": "score audit and ranking are complete",
            },
        ],
        "globalGuards": [
            "actor is active and authorized for the current phase",
            "expectedRevision equals authoritative revision",
            "payload references only catalog IDs and card instances that exist",
            "a rejected transition is side-effect free",
        ],
    }


def card(instance_id: str, type_id: str) -> dict[str, str]:
    return {"instanceId": instance_id, "typeId": type_id}


def internal_tunnel_example() -> dict[str, Any]:
    return {
        "$schema": "../model/game-state.schema.json",
        "schemaVersion": 1,
        "fixtureScope": "transition",
        "gameKey": GAME_KEY,
        "phase": "tunnel_payment",
        "revision": 18,
        "turnOrder": ["p1", "p2"],
        "currentPlayerId": "p1",
        "players": [
            {
                "id": "p1",
                "seatIndex": 0,
                "status": "active",
                "score": 12,
                "trainsRemaining": 38,
                "stationsRemaining": 3,
                "trainHand": [
                    card("train-green-04", "train-green"),
                    card("train-green-05", "train-green"),
                    card("train-locomotive-03", "train-locomotive"),
                ],
                "destinationTicketIds": ["ticket-regular-011", "ticket-regular-021"],
                "initialTicketChoiceSubmitted": True,
                "finalStationAssignmentSubmitted": False,
            },
            {
                "id": "p2",
                "seatIndex": 1,
                "status": "active",
                "score": 9,
                "trainsRemaining": 40,
                "stationsRemaining": 2,
                "trainHand": [
                    card("train-red-02", "train-red"),
                    card("train-blue-06", "train-blue"),
                ],
                "destinationTicketIds": ["ticket-long-002", "ticket-regular-013"],
                "initialTicketChoiceSubmitted": True,
                "finalStationAssignmentSubmitted": False,
            },
        ],
        "trainDeck": [
            card("train-yellow-08", "train-yellow"),
            card("train-white-09", "train-white"),
        ],
        "trainDiscard": [card("train-orange-01", "train-orange")],
        "faceUpMarket": [
            card("train-red-07", "train-red"),
            card("train-black-11", "train-black"),
            card("train-blue-03", "train-blue"),
            card("train-yellow-02", "train-yellow"),
            card("train-locomotive-05", "train-locomotive"),
        ],
        "destinationDeck": ["ticket-regular-001", "ticket-regular-002"],
        "removedDestinationTicketIds": ["ticket-long-006"],
        "claimedRoutes": [
            {"routeId": "route-bruxelles-paris-a", "ownerPlayerId": "p1"},
            {"routeId": "route-bruxelles-frankfurt", "ownerPlayerId": "p2"},
        ],
        "stationPlacements": [
            {"cityId": "bruxelles", "ownerPlayerId": "p2", "borrowedRouteId": None}
        ],
        "pendingTicketChoice": None,
        "pendingTunnel": {
            "actorPlayerId": "p1",
            "routeId": "route-paris-zurich",
            "declaredColor": "green",
            "initialCards": [
                card("train-green-01", "train-green"),
                card("train-green-02", "train-green"),
                card("train-locomotive-01", "train-locomotive"),
            ],
            "revealedCards": [
                card("train-green-09", "train-green"),
                card("train-red-08", "train-red"),
                card("train-locomotive-08", "train-locomotive"),
            ],
            "extraCost": 2,
            "paymentMode": "declared-color",
            "status": "awaiting_payment",
        },
        "finalRound": None,
        "result": None,
        "eventSequence": 27,
        "history": [
            {
                "sequence": 27,
                "type": "tunnel_cards_revealed",
                "actorPlayerId": "p1",
                "publicMessage": "玩家 1 的隧道额外费用为 2 张。",
            }
        ],
    }


def player_view_example() -> dict[str, Any]:
    return {
        "$schema": "../model/view-state.schema.json",
        "schemaVersion": 1,
        "gameKey": GAME_KEY,
        "viewer": {"mode": "player", "playerId": "p1"},
        "phase": "turn_idle",
        "revision": 19,
        "currentPlayerId": "p1",
        "players": [
            {
                "id": "p1",
                "seatIndex": 0,
                "status": "active",
                "score": 16,
                "trainsRemaining": 35,
                "stationsRemaining": 3,
                "trainHandCount": 3,
                "destinationTicketCount": 2,
                "initialTicketChoiceSubmitted": True,
                "finalStationAssignmentSubmitted": False,
            },
            {
                "id": "p2",
                "seatIndex": 1,
                "status": "active",
                "score": 9,
                "trainsRemaining": 40,
                "stationsRemaining": 2,
                "trainHandCount": 2,
                "destinationTicketCount": 2,
                "initialTicketChoiceSubmitted": True,
                "finalStationAssignmentSubmitted": False,
            },
        ],
        "market": [
            card("train-red-07", "train-red"),
            card("train-black-11", "train-black"),
            card("train-blue-03", "train-blue"),
            card("train-yellow-02", "train-yellow"),
            card("train-locomotive-05", "train-locomotive"),
        ],
        "trainDeckCount": 61,
        "trainDiscardCount": 14,
        "destinationDeckCount": 22,
        "board": {
            "claimedRoutes": [
                {"routeId": "route-bruxelles-paris-a", "ownerPlayerId": "p1"},
                {"routeId": "route-bruxelles-frankfurt", "ownerPlayerId": "p2"},
                {"routeId": "route-paris-zurich", "ownerPlayerId": "p1"},
            ],
            "stationPlacements": [
                {"cityId": "bruxelles", "ownerPlayerId": "p2"}
            ],
            "claimableRouteIds": [
                "route-amsterdam-bruxelles",
                "route-bruxelles-paris-b",
                "route-frankfurt-paris-a",
            ],
        },
        "self": {
            "playerId": "p1",
            "trainHand": [
                card("train-green-04", "train-green"),
                card("train-green-05", "train-green"),
                card("train-locomotive-03", "train-locomotive"),
            ],
            "destinationTickets": [
                {
                    "ticketId": "ticket-regular-011",
                    "fromCityId": "amsterdam",
                    "toCityId": "pamplona",
                    "points": 7,
                    "category": "regular",
                    "completionPreview": False,
                },
                {
                    "ticketId": "ticket-regular-021",
                    "fromCityId": "paris",
                    "toCityId": "wien",
                    "points": 8,
                    "category": "regular",
                    "completionPreview": False,
                },
            ],
            "pendingTicketChoice": None,
            "pendingTunnelPayment": None,
        },
        "publicPendingTunnel": None,
        "finalRound": None,
        "actions": [
            "draw_train_card",
            "claim_route",
            "draw_destination_tickets",
            "build_station",
        ],
        "latestEvent": {
            "sequence": 28,
            "type": "route_claimed",
            "publicMessage": "玩家 1 占用了巴黎与苏黎世之间的轨道。",
        },
        "result": None,
    }


def spectator_view_example() -> dict[str, Any]:
    data = player_view_example()
    data["viewer"] = {"mode": "spectator", "playerId": None}
    data["self"] = None
    data["actions"] = []
    return data


def board_svg(board: dict[str, Any]) -> str:
    cities = {item["id"]: item for item in board["cities"]}
    routes = board["routes"]
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}" viewBox="0 0 {CANVAS_WIDTH} {CANVAS_HEIGHT}" role="img" aria-labelledby="title desc">',
        '<title id="title">欧洲铁路网络中性线框</title>',
        '<desc id="desc">由四十七个城市节点与一百零一条轨道组成的原创结构图，不含官方版图美术。</desc>',
        '<rect width="1360" height="880" rx="32" fill="#171C22"/>',
        '<path d="M34 178 C220 82 420 126 552 70 C738 -6 954 16 1114 98 C1240 164 1332 302 1324 474 C1318 652 1184 820 976 846 C758 872 608 790 466 824 C292 866 92 820 42 688 C-8 558 82 444 52 332 C30 252 4 214 34 178Z" fill="#242B31" stroke="#3B454E" stroke-width="3"/>',
        '<g id="routes" fill="none" stroke-linecap="round">',
    ]

    for route in routes:
        a = cities[route["fromCityId"]]["position"]
        b = cities[route["toCityId"]]["position"]
        x1, y1, x2, y2 = a["x"], a["y"], b["x"], b["y"]
        if route["parallelGroupId"]:
            dx, dy = x2 - x1, y2 - y1
            magnitude = math.hypot(dx, dy) or 1
            direction = -1 if route["trackIndex"] == 0 else 1
            offset = 5 * direction
            ox, oy = -dy / magnitude * offset, dx / magnitude * offset
            x1, y1, x2, y2 = x1 + ox, y1 + oy, x2 + ox, y2 + oy
        dash = ""
        if route["kind"] == "tunnel":
            dash = ' stroke-dasharray="10 7"'
        elif route["kind"] == "ferry":
            dash = ' stroke-dasharray="3 8"'
        color = COLOR_VISUALS[route["color"]]["hex"]
        label = (
            f"{cities[route['fromCityId']]['boardLabel']} - "
            f"{cities[route['toCityId']]['boardLabel']}, "
            f"{route['length']} spaces, {route['color']} {route['kind']}"
        )
        lines.append(
            f'<g data-route-id="{route["id"]}" data-kind="{route["kind"]}"><title>{escape(label)}</title>'
            f'<path d="M{x1:.1f} {y1:.1f} L{x2:.1f} {y2:.1f}" stroke="#11161B" stroke-width="9"/>'
            f'<path d="M{x1:.1f} {y1:.1f} L{x2:.1f} {y2:.1f}" stroke="{color}" stroke-width="5"{dash}/></g>'
        )
    lines.append("</g>")

    lines.append('<g id="cities" font-family="Arial, sans-serif">')
    for city in board["cities"]:
        x, y = city["position"]["x"], city["position"]["y"]
        anchor = "start" if x < CANVAS_WIDTH * 0.72 else "end"
        tx = x + 9 if anchor == "start" else x - 9
        ty = y - 8 if y > 55 else y + 22
        lines.append(
            f'<g data-city-id="{city["id"]}"><title>{escape(city["boardLabel"])} / {escape(city["labelZhCN"])}</title>'
            f'<circle cx="{x}" cy="{y}" r="6.5" fill="#F0D8A6" stroke="#0E1318" stroke-width="3"/>'
            f'<text x="{tx}" y="{ty}" text-anchor="{anchor}" font-size="10" font-weight="700" fill="#E8E2D7">{escape(city["boardLabel"])}</text></g>'
        )
    lines.append("</g>")
    lines.extend(
        [
            '<g transform="translate(36 36)" font-family="Arial, sans-serif">',
            '<rect width="300" height="78" rx="14" fill="#11161BCC" stroke="#58636D"/>',
            '<text x="18" y="25" font-size="15" font-weight="700" fill="#F0EAE0">EUROPE RAIL NETWORK / WIREFRAME</text>',
            '<path d="M18 47 H72" stroke="#8A8E93" stroke-width="5"/><text x="82" y="51" font-size="11" fill="#CCD2D7">standard</text>',
            '<path d="M156 47 H210" stroke="#8A8E93" stroke-width="5" stroke-dasharray="10 7"/><text x="220" y="51" font-size="11" fill="#CCD2D7">tunnel</text>',
            '<path d="M18 66 H72" stroke="#8A8E93" stroke-width="5" stroke-dasharray="3 8"/><text x="82" y="70" font-size="11" fill="#CCD2D7">ferry</text>',
            '<text x="156" y="70" font-size="10" fill="#89939D">original neutral diagram</text>',
            "</g>",
            "</svg>",
        ]
    )
    return "\n".join(lines) + "\n"


def pattern_marks(pattern: str, x: int, y: int, width: int, height: int) -> str:
    color = "#FFFFFF66"
    if pattern == "dots":
        return "".join(
            f'<circle cx="{x + 45 + col * 55}" cy="{y + 130 + row * 65}" r="7" fill="{color}"/>'
            for row in range(3)
            for col in range(3)
        )
    if pattern == "horizontal":
        return "".join(
            f'<path d="M{x + 34} {y + 135 + row * 52} H{x + width - 34}" stroke="{color}" stroke-width="7"/>'
            for row in range(4)
        )
    if pattern == "diagonal":
        return "".join(
            f'<path d="M{x + 26 + row * 48} {y + 300} L{x + 112 + row * 48} {y + 120}" stroke="{color}" stroke-width="7"/>'
            for row in range(3)
        )
    if pattern == "cross":
        return "".join(
            f'<path d="M{cx - 10} {cy} H{cx + 10} M{cx} {cy - 10} V{cy + 10}" stroke="#30343A88" stroke-width="5"/>'
            for cx in (x + 62, x + 120, x + 178)
            for cy in (y + 160, y + 225, y + 290)
        )
    if pattern == "diamonds":
        return "".join(
            f'<path d="M{cx} {cy - 12} L{cx + 12} {cy} L{cx} {cy + 12} L{cx - 12} {cy}Z" fill="none" stroke="{color}" stroke-width="5"/>'
            for cx in (x + 62, x + 120, x + 178)
            for cy in (y + 165, y + 235, y + 305)
        )
    if pattern == "waves":
        return "".join(
            f'<path d="M{x + 30} {y + 150 + row * 55} Q{x + 75} {y + 125 + row * 55} {x + 120} {y + 150 + row * 55} T{x + 210} {y + 150 + row * 55}" fill="none" stroke="#44390F88" stroke-width="6"/>'
            for row in range(4)
        )
    if pattern == "grid":
        return (
            "".join(
                f'<path d="M{x + 42 + col * 50} {y + 125} V{y + 315}" stroke="{color}" stroke-width="4"/>'
                for col in range(4)
            )
            + "".join(
                f'<path d="M{x + 28} {y + 140 + row * 52} H{x + 212}" stroke="{color}" stroke-width="4"/>'
                for row in range(4)
            )
        )
    if pattern == "triangles":
        return "".join(
            f'<path d="M{cx} {cy - 12} L{cx + 13} {cy + 10} H{cx - 13}Z" fill="none" stroke="{color}" stroke-width="5"/>'
            for cx in (x + 62, x + 120, x + 178)
            for cy in (y + 165, y + 235, y + 305)
        )
    return ""


def vertical_card_svg(
    x: int,
    y: int,
    card_id: str,
    label: str,
    accent: str,
    code: str,
    pattern: str,
    dark_text: bool = False,
) -> str:
    text = "#242930" if dark_text else "#F8F5EE"
    marks = pattern_marks(pattern, x, y, 240, 340)
    if pattern == "spectrum":
        stripe_colors = ["#79589F", "#3479B8", "#4C8758", "#D0A92C", "#D47A2C", "#B84C46"]
        marks = "".join(
            f'<path d="M{x + 34 + index * 30} {y + 310} L{x + 116 + index * 18} {y + 126}" stroke="{color}" stroke-width="19" opacity="0.8"/>'
            for index, color in enumerate(stripe_colors)
        )
    return (
        f'<g data-card-id="{card_id}"><title>{escape(label)}</title>'
        f'<rect x="{x}" y="{y}" width="240" height="340" rx="24" fill="#11161B" stroke="#66717C" stroke-width="3"/>'
        f'<rect x="{x + 12}" y="{y + 12}" width="216" height="316" rx="18" fill="{accent}"/>'
        f'{marks}'
        f'<path d="M{x + 48} {y + 252} H{x + 192} L{x + 174} {y + 278} H{x + 66}Z" fill="#11161BCC" stroke="{text}" stroke-width="3"/>'
        f'<circle cx="{x + 78}" cy="{y + 286}" r="14" fill="#11161B" stroke="{text}" stroke-width="4"/>'
        f'<circle cx="{x + 162}" cy="{y + 286}" r="14" fill="#11161B" stroke="{text}" stroke-width="4"/>'
        f'<text x="{x + 22}" y="{y + 45}" font-family="Arial, sans-serif" font-size="23" font-weight="700" fill="{text}">{escape(code)}</text>'
        f'<text x="{x + 120}" y="{y + 320}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="{text}">{escape(label)}</text>'
        "</g>"
    )


def card_atlas_svg(catalog: dict[str, Any]) -> str:
    width, height = 1100, 1220
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">原创中性卡牌模型总览</title>',
        '<desc id="desc">八种基础车票、彩虹车票、统一卡背和任务牌正反面的结构示意。</desc>',
        f'<rect width="{width}" height="{height}" rx="28" fill="#1A2026"/>',
        '<text x="50" y="54" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#F1ECE2">CARD MODEL ATLAS</text>',
        '<text x="50" y="81" font-family="Arial, sans-serif" font-size="12" fill="#9CA6AF">ORIGINAL NEUTRAL PLACEHOLDERS / NOT OFFICIAL ART</text>',
    ]
    card_types = catalog["trainCardTypes"]
    for index, item in enumerate(card_types):
        row, col = divmod(index, 4)
        x, y = 50 + col * 260, 110 + row * 360
        parts.append(
            vertical_card_svg(
                x,
                y,
                item["id"],
                item["labelZhCN"],
                item["visual"]["accent"],
                item["visual"]["accessibilityCode"],
                item["visual"]["pattern"],
                item["color"] in {"white", "yellow"},
            )
        )

    # Shared train-card back.
    x, y = 310, 830
    parts.append(
        f'<g data-card-id="train-card-back"><title>统一车票卡背</title>'
        f'<rect x="{x}" y="{y}" width="240" height="280" rx="24" fill="#11161B" stroke="#66717C" stroke-width="3"/>'
        f'<rect x="{x + 12}" y="{y + 12}" width="216" height="256" rx="18" fill="#27343C" stroke="#B7945B" stroke-width="3"/>'
        f'<circle cx="{x + 120}" cy="{y + 122}" r="68" fill="none" stroke="#B7945B" stroke-width="5"/>'
        f'<path d="M{x + 55} {y + 122} H{x + 185} M{x + 76} {y + 84} L{x + 164} {y + 160} M{x + 76} {y + 160} L{x + 164} {y + 84}" stroke="#B7945B88" stroke-width="5"/>'
        f'<text x="{x + 120}" y="{y + 232}" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" font-weight="700" fill="#EFE8DC">SHARED TRAIN BACK</text></g>'
    )

    # Destination ticket face and back, landscape.
    for offset, face in enumerate(("destination-ticket-front", "destination-ticket-back")):
        x, y = 580, 830 + offset * 140
        fill = "#E9DFCB" if offset == 0 else "#263139"
        text = "#283038" if offset == 0 else "#EFE8DC"
        parts.append(
            f'<g data-card-id="{face}"><title>{"任务牌正面结构" if offset == 0 else "统一任务牌卡背"}</title>'
            f'<rect x="{x}" y="{y}" width="470" height="122" rx="20" fill="#11161B" stroke="#66717C" stroke-width="3"/>'
            f'<rect x="{x + 10}" y="{y + 10}" width="450" height="102" rx="14" fill="{fill}"/>'
            + (
                f'<circle cx="{x + 64}" cy="{y + 61}" r="15" fill="#B84C46"/><circle cx="{x + 326}" cy="{y + 61}" r="15" fill="#3479B8"/>'
                f'<path d="M{x + 82} {y + 61} H{x + 308}" stroke="#65717B" stroke-width="5" stroke-dasharray="9 7"/>'
                f'<text x="{x + 350}" y="{y + 71}" font-family="Arial, sans-serif" font-size="30" font-weight="700" fill="{text}">+8</text>'
                if offset == 0
                else f'<path d="M{x + 40} {y + 61} H{x + 410}" stroke="#B7945B" stroke-width="4"/><text x="{x + 225}" y="{y + 70}" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" font-weight="700" fill="{text}">SHARED DESTINATION BACK</text>'
            )
            + "</g>"
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def expected_outputs() -> dict[Path, str]:
    board = board_map()
    cards = card_catalog()
    return {
        MODEL_DIR / "board-map.json": json_text(board),
        MODEL_DIR / "card-catalog.json": json_text(cards),
        MODEL_DIR / "scene-catalog.json": json_text(scene_catalog()),
        MODEL_DIR / "state-machine.json": json_text(state_machine()),
        EXAMPLE_DIR / "internal-tunnel-pending.json": json_text(internal_tunnel_example()),
        EXAMPLE_DIR / "player-view-turn.json": json_text(player_view_example()),
        EXAMPLE_DIR / "spectator-view-turn.json": json_text(spectator_view_example()),
        ASSET_DIR / "board-wireframe.svg": board_svg(board),
        ASSET_DIR / "card-atlas.svg": card_atlas_svg(cards),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if committed generated files differ from deterministic output.",
    )
    args = parser.parse_args()

    outputs = expected_outputs()
    stale: list[str] = []
    for path, content in outputs.items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                stale.append(str(path.relative_to(ROOT)))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")

    if stale:
        print("Generated model files are stale:", file=sys.stderr)
        for item in stale:
            print(f"- {item}", file=sys.stderr)
        return 1

    if args.check:
        print(f"Generated models are current: {len(outputs)} deterministic files.")
    else:
        print(f"Generated {len(outputs)} model, example, and SVG files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
