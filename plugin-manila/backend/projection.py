from __future__ import annotations

from copy import deepcopy
from typing import Any

from backend.app.games.plugin_api import ArcadeRoom

from .catalog import (
    COMMODITIES,
    DESTINATION_COSTS,
    DESTINATION_PAYOUTS,
    LANE_IDS,
    MARKET_TRACK,
    PLAYER_COLORS,
    PUNT_IDS,
    RULESET_ID,
    SCENE_IDS,
    SPECIAL_POSITIONS,
    STAGE_LABELS,
    share_commodity,
)
from .state import ManilaState, WorkerPlacement


def _worker_view(
    state: ManilaState,
    placement: WorkerPlacement | None,
) -> dict[str, Any] | None:
    if placement is None:
        return None
    owner = state.players[placement.player_id]
    color = PLAYER_COLORS[owner.color_index]
    return {
        "workerId": placement.worker_id,
        "playerId": placement.player_id,
        "role": placement.role,
        "slotIndex": placement.slot_index,
        "colorId": color["id"],
        "color": color["fill"],
        "ink": color["ink"],
    }


def _share_view(
    state: ManilaState,
    card_id: str,
    mortgaged: bool,
) -> dict[str, Any]:
    commodity_id = share_commodity(card_id)
    commodity = COMMODITIES[commodity_id]
    return {
        "id": card_id,
        "commodityId": commodity_id,
        "label": commodity["label"],
        "labelEn": commodity["labelEn"],
        "code": commodity["code"],
        "color": commodity["color"],
        "pattern": commodity["pattern"],
        "marketValue": state.market_values[commodity_id],
        "mortgaged": mortgaged,
    }


def _rank_for(state: ManilaState, player_id: str) -> int | None:
    ledger = state.players[player_id]
    if ledger.final_wealth is None:
        return None
    return 1 + sum(
        1
        for other in state.players.values()
        if not other.forfeited
        and other.final_wealth is not None
        and other.final_wealth > ledger.final_wealth
    )


def build_view(
    state: ManilaState,
    room: ArcadeRoom,
    viewer_id: str,
    legal_actions: dict[str, Any],
) -> dict[str, Any]:
    reveal_all = room.phase == "finished"
    players: list[dict[str, Any]] = []
    for player_id in state.turn_order:
        ledger = state.players[player_id]
        member = room.player(player_id)
        color = PLAYER_COLORS[ledger.color_index]
        player_view: dict[str, Any] = {
            "id": player_id,
            "name": member.name,
            "seat": member.seat,
            "avatarUrl": member.avatar_url,
            "connected": member.connected,
            "forfeited": ledger.forfeited,
            "cash": ledger.cash,
            "colorId": color["id"],
            "color": color["fill"],
            "ink": color["ink"],
            "workerCount": len(ledger.worker_ids),
            "availableWorkerCount": len(ledger.available_worker_ids),
            "shareCount": len(ledger.share_ids),
            "mortgagedShareCount": len(ledger.mortgaged_share_ids),
            "passedPlacement": ledger.passed_placement,
            "isHarborMaster": player_id == state.harbor_master_id,
            "isCurrent": player_id == state.current_player_id,
            "finalWealth": ledger.final_wealth,
            "rank": _rank_for(state, player_id),
        }
        if reveal_all or player_id == viewer_id:
            player_view["shareCards"] = [
                _share_view(
                    state,
                    card_id,
                    card_id in ledger.mortgaged_share_ids,
                )
                for card_id in ledger.share_ids
            ]
        players.append(player_view)

    punts: list[dict[str, Any]] = []
    for punt_id in PUNT_IDS:
        punt = state.punts[punt_id]
        commodity = COMMODITIES.get(punt.cargo_id or "")
        costs = list(commodity["costs"]) if commodity else []
        occupants = [_worker_view(state, occupant) for occupant in punt.occupants]
        punts.append(
            {
                "id": punt.id,
                "number": PUNT_IDS.index(punt.id) + 1,
                "cargoId": punt.cargo_id,
                "cargo": dict(commodity) if commodity else None,
                "laneId": punt.lane_id,
                "position": punt.position,
                "status": punt.status,
                "lastDie": punt.last_die,
                "destinationSlot": punt.destination_slot,
                "plundered": punt.plundered,
                "displacedPlayerIds": list(punt.displaced_player_ids),
                "occupants": occupants,
                "cargoSlots": [
                    {
                        "index": index,
                        "cost": cost,
                        "occupant": occupants[index] if index < len(occupants) else None,
                    }
                    for index, cost in enumerate(costs)
                ],
            }
        )

    def destination_views(kind: str) -> list[dict[str, Any]]:
        slots = state.port_slots if kind == "port" else state.shipyard_slots
        return [
            {
                "id": f"{kind}-{slot.id}",
                "slot": slot.id,
                "kind": kind,
                "cost": slot.cost,
                "payout": slot.payout,
                "bettor": _worker_view(state, slot.bettor),
                "puntId": slot.punt_id,
            }
            for slot in slots
        ]

    special_positions = []
    for special_id, definition in SPECIAL_POSITIONS.items():
        special_positions.append(
            {
                **dict(definition),
                "occupant": _worker_view(state, state.special_workers[special_id]),
            }
        )

    auction = None
    if state.auction is not None:
        auction = {
            "openerId": state.auction.opener_id,
            "currentPlayerId": state.auction.current_player_id,
            "activePlayerIds": [
                player_id
                for player_id in state.auction.active_player_ids
                if player_id not in state.auction.passed_player_ids
                and not state.players[player_id].forfeited
            ],
            "passedPlayerIds": list(state.auction.passed_player_ids),
            "leaderId": state.auction.leader_id,
            "currentBid": state.auction.current_bid,
        }

    own = state.players.get(viewer_id)
    settlement = deepcopy(state.last_settlement)
    return {
        "schemaVersion": state.schema_version,
        "modelVersion": state.model_version,
        "ruleset": RULESET_ID,
        "rulesVariant": "base",
        "enhancedPirates": False,
        "sceneId": SCENE_IDS.get(state.stage, "game.table"),
        "stage": state.stage,
        "stageLabel": STAGE_LABELS.get(state.stage, state.stage),
        "voyageNumber": state.voyage_number,
        "roomPhase": room.phase,
        "currentPlayerId": state.current_player_id,
        "harborMasterId": state.harbor_master_id,
        "turnOrder": list(state.turn_order),
        "players": players,
        "market": [
            {
                **dict(definition),
                "value": state.market_values[commodity_id],
                "trackIndex": MARKET_TRACK.index(state.market_values[commodity_id]),
                "supplyCount": len(state.share_supply[commodity_id]),
            }
            for commodity_id, definition in COMMODITIES.items()
        ],
        "marketTrack": list(MARKET_TRACK),
        "lanes": [
            {
                "id": lane_id,
                "number": index + 1,
                "marks": list(range(14)),
                "puntId": next(
                    (punt.id for punt in state.punts.values() if punt.lane_id == lane_id),
                    None,
                ),
            }
            for index, lane_id in enumerate(LANE_IDS)
        ],
        "punts": punts,
        "destinations": {
            "port": destination_views("port"),
            "shipyard": destination_views("shipyard"),
        },
        "specialPositions": special_positions,
        "auction": auction,
        "schedule": [
            {
                "index": index,
                "token": token,
                "state": (
                    "done" if index < state.schedule_index
                    else "current" if index == state.schedule_index
                    else "upcoming"
                ),
            }
            for index, token in enumerate(state.schedule)
        ],
        "placementRound": state.placement_round,
        "movementRound": state.movement_round,
        "dice": dict(state.die_results),
        "lastMoveOrder": list(state.last_move_order),
        "pirateBoardQueue": list(state.pirate_board_queue),
        "pirateRouteQueue": list(state.pirate_route_queue),
        "legalActions": legal_actions,
        "animation": deepcopy(state.animation),
        "events": deepcopy(state.events[-24:]),
        "settlement": settlement,
        "rankings": list(state.rankings),
        "winnerPlayerIds": list(room.winner_player_ids),
        "winReason": room.win_reason,
        "own": (
            {
                "playerId": viewer_id,
                "cash": own.cash,
                "availableWorkerIds": list(own.available_worker_ids),
                "shareCards": [
                    _share_view(
                        state,
                        card_id,
                        card_id in own.mortgaged_share_ids,
                    )
                    for card_id in own.share_ids
                ],
            }
            if own is not None
            else None
        ),
        "rules": {
            "playerRange": [3, 5],
            "marketTrack": list(MARKET_TRACK),
            "startPositionTotal": 9,
            "arrivalThreshold": 13,
            "loanAmount": 12,
            "redeemCost": 15,
            "destinationCosts": dict(DESTINATION_COSTS),
            "destinationPayouts": dict(DESTINATION_PAYOUTS),
            "privacy": "仅本人可见持股份额种类；现金、数量、抵押数量与版图公开",
        },
    }

