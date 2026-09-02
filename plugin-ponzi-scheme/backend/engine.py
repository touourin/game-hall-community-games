from __future__ import annotations

import random
from typing import Any

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError

from .catalog import card_view, fund_cards, industries, luxuries
from .state import (
    GameEvent,
    PendingTrade,
    PlayerLedger,
    PonziSchemeState,
    FundHolding,
)


MARKET_SIZE = 9
EVENT_LIMIT = 80
RULESET_ID = "bright-eye-standard"
STAGE_LABELS = {
    "funding": "募集资金",
    "trade": "暗盘交易",
    "trade_response": "回应暗盘报价",
    "market_prune": "移除资金牌",
    "crash_discard": "市场崩盘",
    "settlement": "转轮付息",
    "finished": "破产结算",
}


class PonziSchemeEngine:
    key = "plugin-ponzi-scheme"
    name = "庞氏骗局"
    min_players = 3
    max_players = 5
    action_phases = {"playing"}

    def __init__(self, rng: random.Random | random.SystemRandom | None = None) -> None:
        self.rng = rng or random.SystemRandom()

    def initial_state(self) -> PonziSchemeState:
        return PonziSchemeState()

    def start(self, room: ArcadeRoom) -> None:
        players = [player for player in room.players if not player.left_room]
        if not self.min_players <= len(players) <= self.max_players:
            raise GameRuleError("庞氏骗局需要 3–5 位玩家")

        if room.options.get("firstPlayer") == "host":
            starter = next(
                (player for player in players if player.id == room.host_id),
                players[0],
            )
        else:
            starter = self.rng.choice(players)
        starter_index = players.index(starter)
        ordered = players[starter_index:] + players[:starter_index]
        deck = [f"F{amount:03d}" for amount in range(18, 81)]
        self.rng.shuffle(deck)
        state = PonziSchemeState(
            round_number=1,
            stage="funding",
            turn_order=[player.id for player in ordered],
            starter_index=0,
            current_player_id=starter.id,
            phase_cursor=0,
            market=[f"F{amount:03d}" for amount in range(9, 18)],
            fund_deck=deck,
            luxury_market=list(luxuries()),
            ledgers={player.id: PlayerLedger() for player in ordered},
        )
        room.state = state
        room.phase = "playing"
        self._emit(
            state,
            "game_start",
            f"{starter.name} 持有起始玩家标记，九张起始资金牌进入市场",
            {"starterId": starter.id, "playerCount": len(ordered)},
        )

    def act(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        action: str,
        payload: dict[str, Any],
    ) -> None:
        if room.phase != "playing":
            raise GameRuleError("当前对局不能继续操作")
        state: PonziSchemeState = room.state
        ledger = state.ledgers.get(player.id)
        if action == "resign":
            if ledger is None or ledger.bankrupt or ledger.forfeited:
                raise GameRuleError("你已不在本局的行动序列中")
            self.manual_forfeit(room, player)
            return
        if ledger is None or ledger.bankrupt or ledger.forfeited:
            raise GameRuleError("你已不在本局的行动序列中")

        handlers = {
            "fund": self._fund,
            "pass_funding": self._pass_funding,
            "make_offer": self._make_offer,
            "accept_offer": self._accept_offer,
            "counter_offer": self._counter_offer,
            "pass_trade": self._pass_trade,
            "buy_luxury": self._buy_luxury,
            "discard_market_card": self._discard_market_card,
            "discard_industry": self._discard_industry,
        }
        handler = handlers.get(action)
        if handler is None:
            raise GameRuleError("不支持这个庞氏骗局操作")
        handler(room, state, player, payload)

    def manual_forfeit(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        if room.phase != "playing":
            return False
        state: PonziSchemeState = room.state
        ledger = state.ledgers.get(player.id)
        if ledger is None or ledger.bankrupt or ledger.forfeited:
            return False
        ledger.bankrupt = True
        ledger.forfeited = True
        state.bankrupt_ids = [player.id]
        self._emit(
            state,
            "bankruptcy",
            f"{player.name} 退出并被视为破产",
            {"playerIds": [player.id], "forfeited": True},
        )
        self._finish(room, state)
        return True

    def disconnect_timeout(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        return self.manual_forfeit(room, player)

    def request_voter_ids(self, room: ArcadeRoom, kind: str) -> set[str]:
        state: PonziSchemeState = room.state
        return {
            player_id
            for player_id, ledger in state.ledgers.items()
            if not ledger.bankrupt and not ledger.forfeited
        }

    def _fund(
        self,
        room: ArcadeRoom,
        state: PonziSchemeState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_turn(state, player.id, "funding", "还没有轮到你募集资金")
        industry_id = payload.get("industryId")
        card_id = payload.get("cardId")
        if industry_id not in industries():
            raise GameRuleError("请选择有效产业")
        if not isinstance(card_id, str) or card_id not in state.market:
            raise GameRuleError("请选择市场中的资金牌")
        ledger = state.ledgers[player.id]
        next_count = ledger.industries[industry_id] + 1
        if next_count > 3:
            raise GameRuleError("募集阶段不能取得同产业的第 4 枚产业牌")
        if state.industry_supply[industry_id] <= 0:
            raise GameRuleError("该产业牌已经取完")
        allowed = self._market_rows(state)[next_count - 1]
        if card_id not in allowed:
            raise GameRuleError(f"取得该产业的第 {next_count} 枚时必须选择第 {next_count} 排")

        card = fund_cards()[card_id]
        ledger.industries[industry_id] = next_count
        state.industry_supply[industry_id] -= 1
        ledger.cash += card["amount"]
        ledger.funds.append(FundHolding(card_id=card_id, due_in=card["period"]))
        state.market.remove(card_id)
        self._restock_market(state)
        self._emit(
            state,
            "fund",
            f"{player.name} 募集 {card['amount']}，取得一枚{industries()[industry_id]['name']}产业",
            {
                "playerId": player.id,
                "industryId": industry_id,
                "cardId": card_id,
                "amount": card["amount"],
            },
        )
        self._advance_funding(room, state)

    def _pass_funding(
        self,
        room: ArcadeRoom,
        state: PonziSchemeState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_turn(state, player.id, "funding", "还没有轮到你募集资金")
        self._emit(
            state,
            "fund_pass",
            f"{player.name} 放弃本轮募集",
            {"playerId": player.id},
        )
        self._advance_funding(room, state)

    def _advance_funding(self, room: ArcadeRoom, state: PonziSchemeState) -> None:
        state.phase_cursor += 1
        order = self._round_order(state)
        if state.phase_cursor < len(order):
            state.current_player_id = order[state.phase_cursor]
            return
        if state.round_number == 1 and room.options.get("skipFirstTrade", True):
            self._emit(state, "trade_skipped", "首轮按新版流程跳过暗盘交易")
            self._begin_marker_pass(state)
            return
        state.stage = "trade"
        state.phase_cursor = 0
        state.current_player_id = order[0]
        self._emit(state, "trade_start", "暗盘交易开始；报价金额仅交易双方可见")

    def _make_offer(
        self,
        room: ArcadeRoom,
        state: PonziSchemeState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_turn(state, player.id, "trade", "还没有轮到你发起暗盘交易")
        target_id = payload.get("targetId")
        industry_id = payload.get("industryId")
        offer = payload.get("offer")
        if target_id == player.id or target_id not in state.ledgers:
            raise GameRuleError("请选择另一位有效玩家")
        if industry_id not in industries():
            raise GameRuleError("请选择有效产业")
        if isinstance(offer, bool) or not isinstance(offer, int) or offer < 0:
            raise GameRuleError("报价必须是非负整数")
        proposer = state.ledgers[player.id]
        target = state.ledgers[target_id]
        if proposer.industries[industry_id] < 1 or target.industries[industry_id] < 1:
            raise GameRuleError("双方必须至少共有一种产业")
        if proposer.cash < offer:
            raise GameRuleError("挡板后的现金不足以装入该报价")
        state.pending_trade = PendingTrade(
            proposer_id=player.id,
            target_id=target_id,
            industry_id=industry_id,
            offer=offer,
        )
        state.stage = "trade_response"
        state.current_player_id = target_id
        self._emit(
            state,
            "trade_offer",
            f"{player.name} 向 {self._player_name(room, target_id)} 递出一只密封信封，交易{industries()[industry_id]['name']}",
            {"proposerId": player.id, "targetId": target_id, "industryId": industry_id},
        )

    def _accept_offer(
        self,
        room: ArcadeRoom,
        state: PonziSchemeState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        trade = self._require_trade_response(state, player.id)
        proposer = state.ledgers[trade.proposer_id]
        target = state.ledgers[trade.target_id]
        if proposer.cash < trade.offer or target.industries[trade.industry_id] < 1:
            raise GameRuleError("交易状态已经失效")
        proposer.cash -= trade.offer
        target.cash += trade.offer
        target.industries[trade.industry_id] -= 1
        proposer.industries[trade.industry_id] += 1
        self._emit(
            state,
            "trade_accept",
            f"{player.name} 收下信封并出售一枚{industries()[trade.industry_id]['name']}产业",
            {
                "proposerId": trade.proposer_id,
                "targetId": trade.target_id,
                "industryId": trade.industry_id,
                "direction": "target_to_proposer",
            },
        )
        self._complete_trade_turn(room, state)

    def _counter_offer(
        self,
        room: ArcadeRoom,
        state: PonziSchemeState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        trade = self._require_trade_response(state, player.id)
        proposer = state.ledgers[trade.proposer_id]
        target = state.ledgers[trade.target_id]
        if target.cash < trade.offer:
            raise GameRuleError("现金不足，无法以相同金额反向收购")
        if proposer.industries[trade.industry_id] < 1:
            raise GameRuleError("交易状态已经失效")
        target.cash -= trade.offer
        proposer.cash += trade.offer
        proposer.industries[trade.industry_id] -= 1
        target.industries[trade.industry_id] += 1
        self._emit(
            state,
            "trade_counter",
            f"{player.name} 补入等额现金并反向收购一枚{industries()[trade.industry_id]['name']}产业",
            {
                "proposerId": trade.proposer_id,
                "targetId": trade.target_id,
                "industryId": trade.industry_id,
                "direction": "proposer_to_target",
            },
        )
        self._complete_trade_turn(room, state)

    def _pass_trade(
        self,
        room: ArcadeRoom,
        state: PonziSchemeState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_turn(state, player.id, "trade", "还没有轮到你决定暗盘交易")
        self._emit(
            state,
            "trade_pass",
            f"{player.name} 本轮不进行暗盘交易",
            {"playerId": player.id},
        )
        self._complete_trade_turn(room, state)

    def _buy_luxury(
        self,
        room: ArcadeRoom,
        state: PonziSchemeState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_turn(state, player.id, "trade", "还没有轮到你决定暗盘交易")
        if not room.options.get("luxuries", True):
            raise GameRuleError("本局未启用奢侈品规则")
        luxury_id = payload.get("luxuryId")
        if not isinstance(luxury_id, str) or luxury_id not in state.luxury_market:
            raise GameRuleError("请选择市场中可用的奢侈品")
        luxury = luxuries()[luxury_id]
        ledger = state.ledgers[player.id]
        if ledger.cash < luxury["cost"]:
            raise GameRuleError("现金不足以购买该奢侈品")
        ledger.cash -= luxury["cost"]
        ledger.luxuries.append(luxury_id)
        state.luxury_market.remove(luxury_id)
        self._emit(
            state,
            "luxury",
            f"{player.name} 购入{luxury['name']}，它在终局价值 {luxury['points']} 分",
            {"playerId": player.id, "luxuryId": luxury_id},
        )
        self._complete_trade_turn(room, state)

    def _complete_trade_turn(self, room: ArcadeRoom, state: PonziSchemeState) -> None:
        state.pending_trade = None
        state.stage = "trade"
        state.phase_cursor += 1
        order = self._round_order(state)
        if state.phase_cursor < len(order):
            state.current_player_id = order[state.phase_cursor]
            return
        self._begin_marker_pass(state)

    def _begin_marker_pass(self, state: PonziSchemeState) -> None:
        state.starter_index = (state.starter_index + 1) % len(state.turn_order)
        state.stage = "market_prune"
        state.phase_cursor = 0
        state.current_player_id = state.turn_order[state.starter_index]
        self._emit(
            state,
            "marker_pass",
            "起始玩家标记顺时针传递；新起始玩家必须移除一张市场资金牌",
            {"starterId": state.current_player_id},
        )

    def _discard_market_card(
        self,
        room: ArcadeRoom,
        state: PonziSchemeState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_turn(state, player.id, "market_prune", "只有新起始玩家可以移除资金牌")
        card_id = payload.get("cardId")
        if not isinstance(card_id, str) or card_id not in state.market:
            raise GameRuleError("请选择市场中的资金牌")
        state.market.remove(card_id)
        card = fund_cards()[card_id]
        if card["kind"] == "starting":
            state.removed_starting_cards.append(card_id)
        else:
            state.fund_discard.append(card_id)
        self._emit(
            state,
            "market_discard",
            f"{player.name} 从市场移除资金牌 {card['amount']}",
            {"playerId": player.id, "cardId": card_id},
        )
        self._restock_market(state)
        bear_count = self._bear_count(state)
        if bear_count >= len(state.turn_order):
            self._begin_crash(room, state)
        else:
            state.crash_occurred = False
            self._settle_interest(room, state, 1)

    def _begin_crash(self, room: ArcadeRoom, state: PonziSchemeState) -> None:
        state.crash_occurred = True
        bears = [card_id for card_id in state.market if fund_cards()[card_id]["kind"] == "bear"]
        state.market = [card_id for card_id in state.market if card_id not in set(bears)]
        state.fund_deck.extend(state.fund_discard)
        state.fund_deck.extend(bears)
        state.fund_discard.clear()
        self.rng.shuffle(state.fund_deck)
        self._restock_market(state)
        state.stage = "crash_discard"
        state.crash_queue = self._round_order(state)
        self._emit(
            state,
            "market_crash",
            f"市场出现 {len(bears)} 张熊市牌：所有人弃置最大产业，时间轮推进两格",
            {"bearCount": len(bears)},
        )
        self._advance_crash_queue(room, state)

    def _discard_industry(
        self,
        room: ArcadeRoom,
        state: PonziSchemeState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_turn(state, player.id, "crash_discard", "还没有轮到你处理市场崩盘")
        industry_id = payload.get("industryId")
        legal = self._largest_industries(state.ledgers[player.id])
        if industry_id not in legal:
            raise GameRuleError("必须从自己数量最多的产业中弃置一枚")
        state.ledgers[player.id].industries[industry_id] -= 1
        state.industry_supply[industry_id] += 1
        self._emit(
            state,
            "crash_discard",
            f"{player.name} 在崩盘中失去一枚{industries()[industry_id]['name']}产业",
            {"playerId": player.id, "industryId": industry_id},
        )
        if state.crash_queue and state.crash_queue[0] == player.id:
            state.crash_queue.pop(0)
        self._advance_crash_queue(room, state)

    def _advance_crash_queue(self, room: ArcadeRoom, state: PonziSchemeState) -> None:
        while state.crash_queue:
            player_id = state.crash_queue[0]
            if self._largest_industries(state.ledgers[player_id]):
                state.current_player_id = player_id
                return
            state.crash_queue.pop(0)
            self._emit(
                state,
                "crash_skip",
                f"{self._player_name(room, player_id)} 没有产业可弃置",
                {"playerId": player_id},
            )
        self._settle_interest(room, state, 2)

    def _settle_interest(
        self,
        room: ArcadeRoom,
        state: PonziSchemeState,
        wheel_steps: int,
    ) -> None:
        state.stage = "settlement"
        state.current_player_id = None
        state.wheel_position = (state.wheel_position + wheel_steps) % 5
        due_by_player: dict[str, int] = {}
        for player_id, ledger in state.ledgers.items():
            due = 0
            for holding in ledger.funds:
                holding.due_in -= wheel_steps
                if holding.due_in <= 0:
                    card = fund_cards()[holding.card_id]
                    due += card["interest"]
                    holding.due_in = card["period"]
            due_by_player[player_id] = due

        bankrupt_ids = [
            player_id
            for player_id, due in due_by_player.items()
            if state.ledgers[player_id].cash < due
        ]
        for player_id, due in due_by_player.items():
            if player_id in bankrupt_ids:
                state.ledgers[player_id].bankrupt = True
                continue
            state.ledgers[player_id].cash -= due
            if due:
                self._emit(
                    state,
                    "interest_paid",
                    f"{self._player_name(room, player_id)} 支付到期利息 {due}",
                    {"playerId": player_id, "amount": due},
                )
        if bankrupt_ids:
            state.bankrupt_ids = bankrupt_ids
            names = "、".join(self._player_name(room, player_id) for player_id in bankrupt_ids)
            self._emit(
                state,
                "bankruptcy",
                f"{names} 无法支付全部到期利息，骗局崩解",
                {"playerIds": bankrupt_ids},
            )
            self._finish(room, state)
            return

        self._emit(
            state,
            "wheel",
            f"全部时间轮推进 {wheel_steps} 格并完成付息",
            {"steps": wheel_steps, "crash": wheel_steps == 2},
        )
        state.round_number += 1
        state.stage = "funding"
        state.phase_cursor = 0
        state.current_player_id = state.turn_order[state.starter_index]
        state.crash_occurred = False
        self._emit(
            state,
            "round_start",
            f"第 {state.round_number} 轮开始",
            {"round": state.round_number, "starterId": state.current_player_id},
        )

    def _finish(self, room: ArcadeRoom, state: PonziSchemeState) -> None:
        luxury_mode = bool(room.options.get("luxuries", True))
        survivors: list[str] = []
        for player_id, ledger in state.ledgers.items():
            if ledger.bankrupt or ledger.forfeited:
                ledger.final_score = None
                continue
            ledger.final_score = self._score_breakdown(ledger, luxury_mode)["total"]
            survivors.append(player_id)

        state.rankings = sorted(
            survivors,
            key=lambda player_id: (
                -(state.ledgers[player_id].final_score or 0),
                -self._highest_fund(state.ledgers[player_id]),
                state.turn_order.index(player_id),
            ),
        )
        if state.rankings:
            first = state.rankings[0]
            top_score = state.ledgers[first].final_score
            top_fund = self._highest_fund(state.ledgers[first])
            winners = [
                player_id
                for player_id in state.rankings
                if state.ledgers[player_id].final_score == top_score
                and self._highest_fund(state.ledgers[player_id]) == top_fund
            ]
            tied_on_score = sum(
                state.ledgers[player_id].final_score == top_score
                for player_id in state.rankings
            ) > 1
            if len(winners) > 1:
                reason = f"骗局崩解；{len(winners)} 位玩家同获 {top_score} 分且最高资金牌同为 {top_fund}"
            elif tied_on_score:
                reason = f"骗局崩解；同为 {top_score} 分，最高资金牌 {top_fund} 决胜"
            elif len(state.rankings) > 1:
                reason = f"骗局崩解；最高资本分为 {top_score}"
            else:
                reason = f"唯一未破产玩家以 {top_score} 分胜出"
        else:
            winners = []
            reason = "所有玩家同时破产，本局无人获胜"
        state.stage = "finished"
        state.current_player_id = None
        room.finish("capital", winners, reason)

    def view(self, room: ArcadeRoom, viewer: ArcadePlayer) -> dict[str, Any]:
        return self._view(room, viewer.id)

    def _view(self, room: ArcadeRoom, viewer_id: str | None) -> dict[str, Any]:
        state: PonziSchemeState = room.state
        reveal_cash = room.phase == "finished"
        ledger_views = []
        for player_id in state.turn_order:
            ledger = state.ledgers[player_id]
            cash_visible = reveal_cash or viewer_id == player_id
            fund_views = [
                {**card_view(holding.card_id), "dueIn": holding.due_in}
                for holding in sorted(
                    ledger.funds,
                    key=lambda item: (item.due_in, fund_cards()[item.card_id]["amount"]),
                )
            ]
            ledger_views.append(
                {
                    "playerId": player_id,
                    "cash": ledger.cash if cash_visible else None,
                    "cashHidden": not cash_visible,
                    "industries": dict(ledger.industries),
                    "industryTotal": sum(ledger.industries.values()),
                    "funds": fund_views,
                    "fundCount": len(fund_views),
                    "luxuries": [dict(luxuries()[luxury_id]) for luxury_id in ledger.luxuries],
                    "interestDueNext": sum(
                        fund_cards()[holding.card_id]["interest"]
                        for holding in ledger.funds
                        if holding.due_in <= 1
                    ),
                    "cycleInterest": sum(
                        fund_cards()[holding.card_id]["interest"] for holding in ledger.funds
                    ),
                    "bankrupt": ledger.bankrupt,
                    "forfeited": ledger.forfeited,
                    "finalScore": ledger.final_score,
                }
            )
        trade = state.pending_trade
        trade_participant = bool(
            trade and viewer_id in {trade.proposer_id, trade.target_id}
        )
        settlement = None
        if room.phase == "finished":
            winner_ids = set(room.winner_player_ids)
            rank_by_player: dict[str, int] = {}
            previous_key: tuple[int, int] | None = None
            previous_rank = 0
            for index, player_id in enumerate(state.rankings):
                ledger = state.ledgers[player_id]
                rank_key = (ledger.final_score or 0, self._highest_fund(ledger))
                if rank_key != previous_key:
                    previous_rank = index + 1
                    previous_key = rank_key
                rank_by_player[player_id] = previous_rank
            settlement = {
                "mode": (
                    "industry_and_luxury" if room.options.get("luxuries", True)
                    else "industry_and_wealth"
                ),
                "winnerPlayerIds": list(room.winner_player_ids),
                "bankruptPlayerIds": list(state.bankrupt_ids),
                "reason": room.win_reason,
                "rows": [
                    {
                        "playerId": player_id,
                        "rank": rank_by_player.get(player_id),
                        "winner": player_id in winner_ids,
                        "bankrupt": state.ledgers[player_id].bankrupt,
                        **self._score_breakdown(
                            state.ledgers[player_id],
                            bool(room.options.get("luxuries", True)),
                        ),
                    }
                    for player_id in state.turn_order
                ],
            }
        return {
            "version": "1.1.0",
            "ruleset": RULESET_ID,
            "round": state.round_number,
            "stage": state.stage,
            "stageLabel": STAGE_LABELS.get(state.stage, state.stage),
            "currentPlayerId": state.current_player_id,
            "starterPlayerId": (
                state.turn_order[state.starter_index] if state.turn_order else None
            ),
            "turnOrder": list(state.turn_order),
            "marketRows": [
                [card_view(card_id) for card_id in row]
                for row in self._market_rows(state)
            ],
            "bearCount": self._bear_count(state),
            "playerCount": len(state.turn_order),
            "deckCounts": {
                "draw": len(state.fund_deck),
                "discard": len(state.fund_discard),
                "removedStarting": len(state.removed_starting_cards),
            },
            "industryCatalog": [
                {**dict(definition), "remaining": state.industry_supply[industry_id]}
                for industry_id, definition in industries().items()
            ],
            "luxuryMarket": [dict(luxuries()[luxury_id]) for luxury_id in state.luxury_market],
            "luxuriesEnabled": bool(room.options.get("luxuries", True)),
            "scoringMode": "industry_and_luxury" if room.options.get("luxuries", True) else "industry_and_wealth",
            "wheelPosition": state.wheel_position,
            "wheelAdvance": 2 if state.crash_occurred else 1,
            "ledgers": ledger_views,
            "pendingTrade": (
                {
                    "proposerId": trade.proposer_id,
                    "targetId": trade.target_id,
                    "industryId": trade.industry_id,
                    "industryName": industries()[trade.industry_id]["name"],
                    "offer": trade.offer if trade_participant else None,
                    "offerKnown": trade_participant,
                }
                if trade
                else None
            ),
            "legalActions": self._legal_actions(room, state, viewer_id),
            "events": [self._event_dict(event) for event in state.events[-40:]],
            "bankruptPlayerIds": list(state.bankrupt_ids),
            "rankings": list(state.rankings),
            "settlement": settlement,
            "privacy": {
                "cash": "self-only" if not reveal_cash else "revealed-at-finish",
                "tradeOffer": "participants-only",
                "fundsAndIndustries": "public",
            },
        }

    def player_result(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
    ) -> tuple[str, str, bool]:
        state: PonziSchemeState = room.state
        ledger = state.ledgers.get(player.id)
        if ledger is None:
            return "旁观者", "observer", False
        if ledger.bankrupt:
            role = "破产操盘手"
            team = "bankrupt"
        else:
            role = f"资本分 {ledger.final_score or 0}"
            team = "survivor"
        return role, team, player.id in room.winner_player_ids

    def record_state(self, room: ArcadeRoom) -> dict[str, Any]:
        return self._view(room, None)

    def _legal_actions(
        self,
        room: ArcadeRoom,
        state: PonziSchemeState,
        player_id: str | None,
    ) -> dict[str, Any]:
        if player_id is None:
            return {}
        ledger = state.ledgers.get(player_id)
        if ledger is None or ledger.bankrupt or ledger.forfeited or room.phase != "playing":
            return {}
        result: dict[str, Any] = {"canResign": True}
        if state.current_player_id != player_id:
            return result
        if state.stage == "funding":
            rows = self._market_rows(state)
            options = []
            for industry_id, definition in industries().items():
                next_count = ledger.industries[industry_id] + 1
                if next_count <= 3 and state.industry_supply[industry_id] > 0:
                    options.append(
                        {
                            "industryId": industry_id,
                            "industryName": definition["name"],
                            "row": next_count,
                            "cardIds": list(rows[next_count - 1]),
                        }
                    )
            result["fundingOptions"] = options
            result["canPassFunding"] = True
        elif state.stage == "trade":
            targets = []
            for target_id, target_ledger in state.ledgers.items():
                if target_id == player_id or target_ledger.bankrupt:
                    continue
                shared = [
                    industry_id
                    for industry_id in industries()
                    if ledger.industries[industry_id] > 0
                    and target_ledger.industries[industry_id] > 0
                ]
                if shared:
                    targets.append({"targetId": target_id, "industryIds": shared})
            result["tradeTargets"] = targets
            result["maxOffer"] = ledger.cash
            result["canPassTrade"] = True
            if room.options.get("luxuries", True):
                result["luxuryIds"] = [
                    luxury_id
                    for luxury_id in state.luxury_market
                    if luxuries()[luxury_id]["cost"] <= ledger.cash
                ]
        elif state.stage == "trade_response" and state.pending_trade:
            trade = state.pending_trade
            if trade.target_id == player_id:
                result["canAcceptOffer"] = True
                result["canCounterOffer"] = ledger.cash >= trade.offer
        elif state.stage == "market_prune":
            result["discardMarketCardIds"] = list(state.market)
        elif state.stage == "crash_discard":
            result["discardIndustryIds"] = self._largest_industries(ledger)
        return result

    def _market_rows(self, state: PonziSchemeState) -> list[list[str]]:
        ordered = sorted(state.market, key=lambda card_id: fund_cards()[card_id]["amount"])
        return [ordered[index:index + 3] for index in range(0, MARKET_SIZE, 3)]

    def _restock_market(self, state: PonziSchemeState) -> None:
        while len(state.market) < MARKET_SIZE:
            if not state.fund_deck:
                if not state.fund_discard:
                    break
                state.fund_deck = list(state.fund_discard)
                state.fund_discard.clear()
                self.rng.shuffle(state.fund_deck)
            state.market.append(state.fund_deck.pop())
        state.market.sort(key=lambda card_id: fund_cards()[card_id]["amount"])

    def _round_order(self, state: PonziSchemeState) -> list[str]:
        return (
            state.turn_order[state.starter_index:]
            + state.turn_order[:state.starter_index]
        )

    def _require_turn(
        self,
        state: PonziSchemeState,
        player_id: str,
        stage: str,
        message: str,
    ) -> None:
        if state.stage != stage or state.current_player_id != player_id:
            raise GameRuleError(message)

    def _require_trade_response(
        self,
        state: PonziSchemeState,
        player_id: str,
    ) -> PendingTrade:
        trade = state.pending_trade
        if (
            state.stage != "trade_response"
            or trade is None
            or state.current_player_id != player_id
            or trade.target_id != player_id
        ):
            raise GameRuleError("只有收到信封的玩家可以回应报价")
        return trade

    @staticmethod
    def _largest_industries(ledger: PlayerLedger) -> list[str]:
        largest = max(ledger.industries.values(), default=0)
        if largest <= 0:
            return []
        return [
            industry_id
            for industry_id, count in ledger.industries.items()
            if count == largest
        ]

    @staticmethod
    def _wealth_points(cash: int) -> int:
        if cash >= 96:
            return 4
        if cash >= 78:
            return 3
        if cash >= 56:
            return 2
        if cash >= 30:
            return 1
        return 0

    @staticmethod
    def _highest_fund(ledger: PlayerLedger) -> int:
        return max(
            (fund_cards()[holding.card_id]["amount"] for holding in ledger.funds),
            default=0,
        )

    def _score_breakdown(
        self,
        ledger: PlayerLedger,
        luxury_mode: bool,
    ) -> dict[str, int | None]:
        industry_score = sum(
            count * (count + 1) // 2 for count in ledger.industries.values()
        )
        luxury_score = sum(
            luxuries()[luxury_id]["points"] for luxury_id in ledger.luxuries
        )
        wealth_score = self._wealth_points(ledger.cash)
        extra_score = luxury_score if luxury_mode else wealth_score
        return {
            "industryScore": industry_score,
            "luxuryScore": luxury_score if luxury_mode else None,
            "wealthScore": wealth_score if not luxury_mode else None,
            "highestFund": self._highest_fund(ledger),
            "total": industry_score + extra_score,
        }

    @staticmethod
    def _bear_count(state: PonziSchemeState) -> int:
        return sum(
            fund_cards()[card_id]["kind"] == "bear" for card_id in state.market
        )

    @staticmethod
    def _player_name(room: ArcadeRoom, player_id: str) -> str:
        return room.player(player_id).name

    @staticmethod
    def _event_dict(event: GameEvent) -> dict[str, Any]:
        return {
            "seq": event.seq,
            "type": event.type,
            "message": event.message,
            "data": dict(event.data),
        }

    @staticmethod
    def _emit(
        state: PonziSchemeState,
        event_type: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        state.event_sequence += 1
        state.events.append(
            GameEvent(
                seq=state.event_sequence,
                type=event_type,
                message=message,
                data=data or {},
            )
        )
        if len(state.events) > EVENT_LIMIT:
            del state.events[:-EVENT_LIMIT]
