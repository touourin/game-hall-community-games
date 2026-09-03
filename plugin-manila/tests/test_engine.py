from __future__ import annotations

import random
from typing import Any

import pytest

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError
from manila_plugin_test_backend.engine import ManilaEngine
from manila_plugin_test_backend.state import WorkerPlacement


def make_room(player_count: int, seed: int = 7) -> tuple[ManilaEngine, ArcadeRoom, list[ArcadePlayer]]:
    players = [
        ArcadePlayer(
            id=f"p{index + 1}",
            account_id=f"a{index + 1}",
            name=f"玩家{index + 1}",
            token_hash="test",
            seat=index,
        )
        for index in range(player_count)
    ]
    engine = ManilaEngine(random.Random(seed))
    room = ArcadeRoom(
        code="MNL1",
        game_key="plugin-manila",
        host_id="p1",
        players=players,
        state=engine.initial_state(),
        options={"firstPlayer": "host"},
    )
    engine.start(room)
    return engine, room, players


def act(
    engine: ManilaEngine,
    room: ArcadeRoom,
    player: ArcadePlayer,
    action: str,
    **payload: Any,
) -> None:
    engine.act(
        room,
        player,
        action,
        {"voyageNumber": room.state.voyage_number, **payload},
    )


def current_player(room: ArcadeRoom) -> ArcadePlayer:
    return room.player(room.state.current_player_id)


def win_auction(engine: ManilaEngine, room: ArcadeRoom, amount: int = 1) -> None:
    actor = current_player(room)
    act(engine, room, actor, "bid", amount=amount)
    while room.state.stage == "auction":
        act(engine, room, current_player(room), "pass_auction")


def launch_standard_voyage(engine: ManilaEngine, room: ArcadeRoom) -> None:
    master = room.player(room.state.harbor_master_id)
    act(engine, room, master, "skip_share")
    act(
        engine,
        room,
        master,
        "select_cargo",
        assignments=[
            {"puntId": "punt-1", "commodityId": "ginseng"},
            {"puntId": "punt-2", "commodityId": "nutmeg"},
            {"puntId": "punt-3", "commodityId": "jade"},
        ],
    )
    act(
        engine,
        room,
        master,
        "set_start_positions",
        assignments=[
            {"puntId": "punt-1", "laneId": "lane-1", "position": 2},
            {"puntId": "punt-2", "laneId": "lane-2", "position": 3},
            {"puntId": "punt-3", "laneId": "lane-3", "position": 4},
        ],
    )


@pytest.mark.parametrize(("player_count", "worker_count"), [(3, 4), (4, 3), (5, 3)])
def test_start_setup_and_private_projection(player_count: int, worker_count: int) -> None:
    engine, room, players = make_room(player_count)
    assert room.phase == "playing"
    assert room.state.stage == "auction"
    assert sum(len(cards) for cards in room.state.share_supply.values()) == 20 - 2 * player_count
    assert all(len(ledger.share_ids) == 2 for ledger in room.state.players.values())
    assert all(len(ledger.worker_ids) == worker_count for ledger in room.state.players.values())
    view = engine.view(room, players[0])
    assert len(view["own"]["shareCards"]) == 2
    assert "shareCards" in view["players"][0]
    assert all("shareCards" not in player for player in view["players"][1:])
    assert view["enhancedPirates"] is False


def test_auction_strict_bids_passes_no_bid_and_forced_mortgage() -> None:
    engine, room, players = make_room(3)
    with pytest.raises(GameRuleError):
        act(engine, room, players[0], "bid", amount=0)
    act(engine, room, players[0], "bid", amount=31)
    assert len(room.state.players["p1"].mortgaged_share_ids) == 0
    with pytest.raises(GameRuleError):
        act(engine, room, players[1], "bid", amount=55)
    act(engine, room, players[1], "pass_auction")
    act(engine, room, players[2], "pass_auction")
    assert room.state.harbor_master_id == "p1"
    assert room.state.players["p1"].cash == 11
    assert len(room.state.players["p1"].mortgaged_share_ids) == 1

    engine2, room2, _ = make_room(3)
    while room2.state.stage == "auction":
        act(engine2, room2, current_player(room2), "pass_auction")
    assert room2.state.harbor_master_id == "p1"
    assert room2.state.players["p1"].cash == 30


def test_harbor_master_share_cargo_start_and_stale_guards() -> None:
    engine, room, players = make_room(3)
    win_auction(engine, room)
    before_supply = len(room.state.share_supply["jade"])
    act(engine, room, players[0], "buy_share", commodityId="jade")
    assert len(room.state.players["p1"].share_ids) == 3
    assert len(room.state.share_supply["jade"]) == before_supply - 1
    with pytest.raises(GameRuleError):
        engine.act(room, players[0], "select_cargo", {"voyageNumber": 0, "assignments": []})
    act(
        engine,
        room,
        players[0],
        "select_cargo",
        assignments=[
            {"puntId": "punt-1", "commodityId": "ginseng"},
            {"puntId": "punt-2", "commodityId": "silk"},
            {"puntId": "punt-3", "commodityId": "jade"},
        ],
    )
    with pytest.raises(GameRuleError):
        act(
            engine,
            room,
            players[0],
            "set_start_positions",
            assignments=[
                {"puntId": "punt-1", "laneId": "lane-1", "position": 2},
                {"puntId": "punt-2", "laneId": "lane-2", "position": 2},
                {"puntId": "punt-3", "laneId": "lane-3", "position": 4},
            ],
        )


def test_placement_cost_order_insurance_and_pass_persistence() -> None:
    engine, room, players = make_room(3)
    win_auction(engine, room)
    launch_standard_voyage(engine, room)
    assert room.state.stage == "placement"
    first = current_player(room)
    cash_before = room.state.players[first.id].cash
    act(engine, room, first, "place_accomplice", targetId="punt-1")
    assert room.state.punts["punt-1"].occupants[0].slot_index == 0
    assert room.state.players[first.id].cash == cash_before - 1

    second = current_player(room)
    cash_before = room.state.players[second.id].cash
    act(engine, room, second, "place_accomplice", targetId="insurance")
    assert room.state.players[second.id].cash == cash_before + 10
    third = current_player(room)
    act(engine, room, third, "pass_placement")
    assert room.state.players[third.id].passed_placement is True
    # The three-player schedule starts a second placement round immediately.
    assert room.state.placement_round == 2
    assert room.state.current_player_id != third.id


def test_blind_passenger_uses_all_remaining_cash_and_cannot_use_insurance() -> None:
    engine, room, _ = make_room(4)
    win_auction(engine, room)
    launch_standard_voyage(engine, room)
    ledger = room.state.players[room.state.current_player_id]
    ledger.cash = 1
    ledger.mortgaged_share_ids = list(ledger.share_ids)
    # Occupy the one-cost ginseng slot so that the cheapest remaining cost is two.
    room.state.punts["punt-1"].occupants.append(
        WorkerPlacement("setup", "p2", slot_index=0)
    )
    options = engine._placement_options(room.state, ledger.player_id)
    assert all(option["targetId"] != "insurance" or not option["blindAllowed"] for option in options)
    blind = next(option for option in options if option.get("blindAllowed"))
    act(engine, room, room.player(ledger.player_id), "place_accomplice", targetId=blind["targetId"])
    assert ledger.cash == 0


def test_explicit_loan_and_redeem_costs() -> None:
    engine, room, players = make_room(3)
    ledger = room.state.players["p1"]
    card_id = ledger.share_ids[0]
    act(engine, room, players[0], "take_loan", shareId=card_id)
    assert ledger.cash == 42
    assert card_id in ledger.mortgaged_share_ids
    act(engine, room, players[0], "repay_loan", shareId=card_id)
    assert ledger.cash == 27
    assert card_id not in ledger.mortgaged_share_ids


@pytest.mark.parametrize(
    ("player_count", "expected"),
    [
        (3, ["placement", "placement", "movement", "placement", "movement", "placement", "pilots", "movement"]),
        (4, ["placement", "movement", "placement", "movement", "placement", "pilots", "movement"]),
        (5, ["placement", "movement", "placement", "movement", "placement", "pilots", "movement"]),
    ],
)
def test_player_count_schedule(player_count: int, expected: list[str]) -> None:
    engine, room, _ = make_room(player_count)
    win_auction(engine, room)
    launch_standard_voyage(engine, room)
    assert room.state.schedule == expected


def test_move_order_assigns_ports_in_harbor_master_order() -> None:
    engine, room, _ = make_room(4)
    win_auction(engine, room)
    launch_standard_voyage(engine, room)
    while room.state.stage == "placement":
        act(engine, room, current_player(room), "pass_placement")
    state = room.state
    assert state.stage == "roll"
    for punt in state.punts.values():
        punt.position = 12
    master = room.player(state.harbor_master_id)
    act(engine, room, master, "roll_dice")
    state.die_results = {punt_id: 2 for punt_id in state.die_results}
    act(
        engine,
        room,
        master,
        "choose_move_order",
        puntIds=["punt-3", "punt-1", "punt-2"],
    )
    assert [slot.punt_id for slot in state.port_slots] == ["punt-3", "punt-1", "punt-2"]


def test_round_two_pirates_board_in_order_and_full_boat_is_not_target() -> None:
    engine, room, _ = make_room(4)
    state = room.state
    state.harbor_master_id = "p1"
    state.current_player_id = "p1"
    for index, punt in enumerate(state.punts.values()):
        punt.cargo_id = ("ginseng", "nutmeg", "jade")[index]
        punt.lane_id = f"lane-{index + 1}"
        punt.status = "sailing"
        punt.position = 13 if index < 2 else 10
    full = state.punts["punt-1"]
    full.occupants = [
        WorkerPlacement(f"full-{index}", "p3", slot_index=index)
        for index in range(3)
    ]
    captain = WorkerPlacement("captain", "p1", role="pirate-captain")
    crew = WorkerPlacement("crew", "p2", role="pirate-crew")
    state.special_workers["pirate-captain"] = captain
    state.special_workers["pirate-crew"] = crew
    state.schedule = ["movement", "placement"]
    state.schedule_index = 0
    state.movement_round = 2
    engine._begin_pirate_boarding(room, state)
    assert state.current_player_id == "p1"
    assert engine._pirate_board_targets(state) == ["punt-2"]
    act(engine, room, room.player("p1"), "pirate_board", puntId="punt-2")
    assert state.special_workers["pirate-captain"].worker_id == "crew"
    assert state.current_player_id == "p2"
    act(engine, room, room.player("p2"), "pirate_stay")
    assert state.punts["punt-2"].occupants[-1].worker_id == "captain"


def test_pilots_exact_thirteen_does_not_trigger_and_crossing_docks() -> None:
    engine, room, _ = make_room(3)
    state = room.state
    state.harbor_master_id = "p1"
    for index, punt in enumerate(state.punts.values()):
        punt.cargo_id = ("ginseng", "nutmeg", "jade")[index]
        punt.lane_id = f"lane-{index + 1}"
        punt.status = "sailing"
        punt.position = 12
    state.special_workers["pilot-small"] = WorkerPlacement("small", "p1", role="pilot-small")
    state.special_workers["pilot-large"] = WorkerPlacement("large", "p2", role="pilot-large")
    state.schedule = ["pilots", "movement"]
    state.schedule_index = 0
    state.stage = "pilot_small"
    state.current_player_id = "p1"
    act(
        engine,
        room,
        room.player("p1"),
        "pilot_move",
        moves=[{"puntId": "punt-1", "delta": 1}],
    )
    assert state.punts["punt-1"].position == 13
    assert state.punts["punt-1"].status == "sailing"
    assert state.stage == "pilot_large"
    act(
        engine,
        room,
        room.player("p2"),
        "pilot_move",
        moves=[{"puntId": "punt-1", "delta": 1}],
    )
    assert state.punts["punt-1"].status == "port"
    assert state.punts["punt-1"].destination_slot == "port-A"


def test_third_round_no_pirates_thirteen_goes_port_and_lower_goes_yard() -> None:
    engine, room, _ = make_room(3)
    state = room.state
    state.harbor_master_id = "p1"
    state.last_move_order = ["punt-2", "punt-1", "punt-3"]
    for index, punt in enumerate(state.punts.values()):
        punt.cargo_id = ("ginseng", "nutmeg", "jade")[index]
        punt.status = "sailing"
        punt.position = 13 if punt.id != "punt-3" else 12
    engine._finish_third_movement(room, state)
    assert [slot.punt_id for slot in state.port_slots[:2]] == ["punt-2", "punt-1"]
    assert state.shipyard_slots[0].punt_id == "punt-3"
    assert state.stage == "voyage_summary"


def test_pirate_plunder_profit_split_and_captain_route() -> None:
    engine, room, _ = make_room(4)
    state = room.state
    state.harbor_master_id = "p1"
    state.last_move_order = ["punt-1", "punt-2", "punt-3"]
    for index, punt in enumerate(state.punts.values()):
        punt.cargo_id = ("jade", "silk", "ginseng")[index]
        punt.status = "sailing"
        punt.position = 13 if index == 0 else 10
    state.punts["punt-1"].occupants = [WorkerPlacement("victim", "p3", slot_index=0)]
    state.special_workers["pirate-captain"] = WorkerPlacement("cap", "p1", role="pirate-captain")
    state.special_workers["pirate-crew"] = WorkerPlacement("crew", "p2", role="pirate-crew")
    engine._finish_third_movement(room, state)
    assert state.stage == "pirate_route"
    assert state.punts["punt-1"].occupants == []
    act(
        engine,
        room,
        room.player("p1"),
        "route_plundered_punt",
        puntId="punt-1",
        destination="port",
    )
    pirate_entries = [
        entry for entry in state.last_settlement["entries"]
        if entry["reason"] == "pirate_profit"
    ]
    assert [entry["amount"] for entry in pirate_entries] == [18, 18]
    assert state.players["p3"].cash == 30
    assert "jade" in state.last_settlement["deliveredCommodityIds"]


def test_atomic_settlement_covers_cargo_port_insurance_shortfall_and_unclaimed_repairs() -> None:
    engine, room, _ = make_room(3)
    state = room.state
    state.harbor_master_id = "p1"
    # Normal ginseng delivery: p1 and p2 receive 9 each.
    punt1 = state.punts["punt-1"]
    punt1.cargo_id = "ginseng"
    punt1.status = "port"
    punt1.destination_slot = "port-A"
    punt1.occupants = [
        WorkerPlacement("w1", "p1", slot_index=0),
        WorkerPlacement("w2", "p2", slot_index=1),
    ]
    state.port_slots[0].punt_id = "punt-1"
    state.port_slots[0].bettor = WorkerPlacement("bet", "p3")
    # Two damaged boats create 6 + 8 liability. The insurer first receives 6,
    # pays it to p2, then has no shares/cash and the bank covers the final 8.
    for index, commodity in enumerate(("nutmeg", "jade"), start=1):
        punt = state.punts[f"punt-{index + 1}"]
        punt.cargo_id = commodity
        punt.status = "shipyard"
        punt.destination_slot = f"shipyard-{'AB'[index - 1]}"
        state.shipyard_slots[index - 1].punt_id = punt.id
    state.shipyard_slots[0].bettor = WorkerPlacement("yard-bet", "p2")
    state.special_workers["insurance"] = WorkerPlacement("insurer", "p3", role="insurance")
    state.players["p3"].cash = 0
    state.players["p3"].share_ids = []
    state.players["p3"].mortgaged_share_ids = []

    engine._settle_voyage(room, state)
    assert state.players["p1"].cash == 39
    assert state.players["p2"].cash == 45
    assert state.players["p3"].cash == 0
    repair_entries = [
        entry for entry in state.last_settlement["entries"]
        if entry["reason"] == "insured_repair"
    ]
    assert repair_entries[0]["payerAmount"] == 6
    assert repair_entries[0]["bankCoverage"] == 0
    assert repair_entries[1]["payerAmount"] == 0
    assert repair_entries[1]["bankCoverage"] == 8


def test_insurer_self_payment_is_net_zero_and_forced_mortgage_is_bounded() -> None:
    engine, room, _ = make_room(3)
    state = room.state
    state.harbor_master_id = "p1"
    state.players["p1"].cash = 0
    state.special_workers["insurance"] = WorkerPlacement("ins", "p1", role="insurance")
    punt = state.punts["punt-1"]
    punt.cargo_id = "ginseng"
    punt.status = "shipyard"
    state.shipyard_slots[0].punt_id = punt.id
    state.shipyard_slots[0].bettor = WorkerPlacement("self", "p1")
    engine._settle_voyage(room, state)
    assert state.players["p1"].cash == 0
    self_entry = next(
        entry for entry in state.last_settlement["entries"]
        if entry["reason"] == "self_insurance"
    )
    assert self_entry["selfInsurance"] is True
    assert self_entry["payerAmount"] == 0
    assert state.players["p1"].mortgaged_share_ids == []


def test_bank_pays_shipyard_when_no_insurer() -> None:
    engine, room, _ = make_room(3)
    state = room.state
    state.harbor_master_id = "p1"
    punt = state.punts["punt-1"]
    punt.cargo_id = "nutmeg"
    punt.status = "shipyard"
    state.shipyard_slots[0].punt_id = punt.id
    state.shipyard_slots[0].bettor = WorkerPlacement("yard", "p2")
    engine._settle_voyage(room, state)
    assert state.players["p2"].cash == 36
    payment = next(
        entry for entry in state.last_settlement["entries"]
        if entry["reason"] == "shipyard_bet"
    )
    assert payment["fromId"] == "bank"
    assert payment["amount"] == 6


def test_terminal_market_and_shared_win_include_mortgaged_penalty() -> None:
    engine, room, _ = make_room(3)
    state = room.state
    state.harbor_master_id = "p1"
    for ledger in state.players.values():
        ledger.share_ids = []
        ledger.mortgaged_share_ids = []
        ledger.cash = 30
    state.market_values["ginseng"] = 20
    punt = state.punts["punt-1"]
    punt.cargo_id = "ginseng"
    punt.status = "port"
    state.port_slots[0].punt_id = punt.id
    engine._settle_voyage(room, state)
    assert room.phase == "finished"
    assert state.market_values["ginseng"] == 30
    assert room.winner_player_ids == ["p1", "p2", "p3"]
    assert all(ledger.final_wealth == 30 for ledger in state.players.values())


@pytest.mark.parametrize("player_count", [3, 4, 5])
def test_complete_autoplay_reaches_audited_finish_for_every_player_count(player_count: int) -> None:
    engine, room, _ = make_room(player_count, seed=player_count * 17)
    actions = 0
    while room.phase == "playing" and actions < 800:
        state = room.state
        actor = current_player(room)
        if state.stage == "auction":
            act(engine, room, actor, "pass_auction")
        elif state.stage == "harbor_share":
            act(engine, room, actor, "skip_share")
        elif state.stage == "harbor_load":
            act(
                engine,
                room,
                actor,
                "select_cargo",
                assignments=[
                    {"puntId": "punt-1", "commodityId": "ginseng"},
                    {"puntId": "punt-2", "commodityId": "nutmeg"},
                    {"puntId": "punt-3", "commodityId": "silk"},
                ],
            )
        elif state.stage == "harbor_launch":
            act(
                engine,
                room,
                actor,
                "set_start_positions",
                assignments=[
                    {"puntId": "punt-1", "laneId": "lane-1", "position": 2},
                    {"puntId": "punt-2", "laneId": "lane-2", "position": 3},
                    {"puntId": "punt-3", "laneId": "lane-3", "position": 4},
                ],
            )
        elif state.stage == "placement":
            act(engine, room, actor, "pass_placement")
        elif state.stage == "roll":
            act(engine, room, actor, "roll_dice")
        elif state.stage == "move_order":
            act(
                engine,
                room,
                actor,
                "choose_move_order",
                puntIds=[
                    punt_id for punt_id in ("punt-1", "punt-2", "punt-3")
                    if state.punts[punt_id].status == "sailing"
                ],
            )
        elif state.stage == "voyage_summary":
            act(engine, room, actor, "next_voyage")
        else:
            raise AssertionError(f"autoplay encountered unexpected stage {state.stage}")
        actions += 1
    assert actions < 800
    assert room.phase == "finished"
    assert room.winner_player_ids
    assert any(value == 30 for value in room.state.market_values.values())
    assert all(
        ledger.final_wealth is not None
        for ledger in room.state.players.values()
        if not ledger.forfeited
    )
