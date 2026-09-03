from __future__ import annotations

from typing import Final


RULESET_ID: Final = "zoch-2005-base"
MODEL_VERSION: Final = "1.0.0"
MARKET_TRACK: Final = (0, 5, 10, 20, 30)
PUNT_IDS: Final = ("punt-1", "punt-2", "punt-3")
LANE_IDS: Final = ("lane-1", "lane-2", "lane-3")
DESTINATION_SLOT_IDS: Final = ("A", "B", "C")
DESTINATION_COSTS: Final = {"A": 4, "B": 3, "C": 2}
DESTINATION_PAYOUTS: Final = {"A": 6, "B": 8, "C": 15}
PLAYER_COLORS: Final = (
    {"id": "amber", "fill": "#d6a341", "ink": "#332817"},
    {"id": "coral", "fill": "#cb6252", "ink": "#321b18"},
    {"id": "teal", "fill": "#4c9a91", "ink": "#132b29"},
    {"id": "indigo", "fill": "#6b79b8", "ink": "#191d35"},
    {"id": "ivory", "fill": "#e8dfc8", "ink": "#2d2a22"},
)

COMMODITIES: Final = {
    "ginseng": {
        "id": "ginseng",
        "label": "人参",
        "labelEn": "Ginseng",
        "code": "GS",
        "profit": 18,
        "costs": (1, 2, 3),
        "color": "#B4862C",
        "pattern": "diagonal-root",
    },
    "nutmeg": {
        "id": "nutmeg",
        "label": "肉豆蔻",
        "labelEn": "Nutmeg",
        "code": "NM",
        "profit": 24,
        "costs": (2, 3, 4),
        "color": "#9A5C3A",
        "pattern": "seed-dots",
    },
    "silk": {
        "id": "silk",
        "label": "丝绸",
        "labelEn": "Silk",
        "code": "SK",
        "profit": 30,
        "costs": (3, 4, 5),
        "color": "#456F9E",
        "pattern": "woven-lines",
    },
    "jade": {
        "id": "jade",
        "label": "玉石",
        "labelEn": "Jade",
        "code": "JD",
        "profit": 36,
        "costs": (3, 4, 5, 5),
        "color": "#3F806E",
        "pattern": "faceted-diamonds",
    },
}

SPECIAL_POSITIONS: Final = {
    "pirate-captain": {
        "id": "pirate-captain", "kind": "pirate", "label": "海盗船长", "cost": 5,
    },
    "pirate-crew": {
        "id": "pirate-crew", "kind": "pirate", "label": "海盗船员", "cost": 5,
    },
    "pilot-small": {
        "id": "pilot-small", "kind": "pilot", "label": "小引航员", "cost": 2,
    },
    "pilot-large": {
        "id": "pilot-large", "kind": "pilot", "label": "大引航员", "cost": 5,
    },
    "insurance": {
        "id": "insurance", "kind": "insurance", "label": "保险代理", "cost": 0,
    },
}

STAGE_LABELS: Final = {
    "auction": "港务长拍卖",
    "harbor_share": "购买份额",
    "harbor_load": "选择装船货物",
    "harbor_launch": "设置起航位置",
    "placement": "部署助手",
    "roll": "掷骰航行",
    "move_order": "决定移动顺序",
    "pirate_board": "海盗登船",
    "pilot_small": "小引航员",
    "pilot_large": "大引航员",
    "pirate_route": "海盗决定去向",
    "voyage_summary": "航行结算",
    "finished": "最终财富",
}

SCENE_IDS: Final = {
    "auction": "auction.bid",
    "harbor_share": "harbor.share",
    "harbor_load": "harbor.load",
    "harbor_launch": "harbor.launch",
    "placement": "placement.choose",
    "roll": "movement.roll",
    "move_order": "movement.order",
    "pirate_board": "pirates.board",
    "pilot_small": "pilot.small",
    "pilot_large": "pilot.large",
    "pirate_route": "pirates.route",
    "voyage_summary": "voyage.summary",
    "finished": "game.finished",
}


def placement_schedule(player_count: int) -> tuple[str, ...]:
    if player_count == 3:
        return (
            "placement", "placement", "movement", "placement",
            "movement", "placement", "pilots", "movement",
        )
    return (
        "placement", "movement", "placement", "movement",
        "placement", "pilots", "movement",
    )


def share_id(commodity_id: str, copy_index: int) -> str:
    return f"share-{commodity_id}-{copy_index:02d}"


def share_commodity(share_card_id: str) -> str:
    parts = share_card_id.split("-")
    if len(parts) != 3 or parts[0] != "share" or parts[1] not in COMMODITIES:
        raise ValueError("invalid Manila share id")
    return parts[1]


def market_advance(value: int) -> int:
    try:
        index = MARKET_TRACK.index(value)
    except ValueError as error:
        raise ValueError("market value is not on the Manila track") from error
    return MARKET_TRACK[min(index + 1, len(MARKET_TRACK) - 1)]
