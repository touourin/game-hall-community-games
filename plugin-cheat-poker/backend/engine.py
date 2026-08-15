from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError


RANKS = ("3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2")
RANK_LABELS = {rank: rank for rank in RANKS}
NEXT_RANK = {rank: RANKS[(index + 1) % len(RANKS)] for index, rank in enumerate(RANKS)}
SUITS = (
    ("spades", "♠"),
    ("hearts", "♥"),
    ("diamonds", "♦"),
    ("clubs", "♣"),
)
PILE_LIMIT = 15
MAX_PLAY = 3
WINNER_SCORES_BY_PLAYER_COUNT = {
    4: (3,),
    5: (3, 1),
    6: (3, 2, 1),
}


@dataclass(frozen=True)
class Card:
    id: str
    rank: str
    suit: str
    suit_label: str
    label: str
    is_joker: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "rank": self.rank,
            "suit": self.suit,
            "suitLabel": self.suit_label,
            "label": self.label,
            "isJoker": self.is_joker,
        }


@dataclass
class LastPlay:
    player_id: str
    player_name: str
    claimed_rank: str
    cards: list[Card]


@dataclass
class CheatPokerState:
    dealer_player_id: str | None = None
    turn_order: list[str] = field(default_factory=list)
    hands: dict[str, list[Card]] = field(default_factory=dict)
    pile: list[Card] = field(default_factory=list)
    last_play: LastPlay | None = None
    current_player_id: str | None = None
    stage: str = "play"
    required_rank: str | None = None
    archived_count: int = 0
    winner_target: int = 0
    rankings: list[str] = field(default_factory=list)
    forfeited_ids: list[str] = field(default_factory=list)
    scores: dict[str, int] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)


class CheatPokerEngine:
    key = "plugin-cheat-poker"
    name = "欺诈者"
    min_players = 4
    max_players = 6

    def __init__(self, rng: random.Random | random.SystemRandom | None = None) -> None:
        self.rng = rng or random.SystemRandom()

    def initial_state(self) -> CheatPokerState:
        return CheatPokerState()

    def start(self, room: ArcadeRoom) -> None:
        players = [player for player in room.players if not player.left_room]
        if not self.min_players <= len(players) <= self.max_players:
            raise GameRuleError("欺诈者需要 4–6 位玩家")

        if room.options.get("firstPlayer") == "host":
            dealer = next(
                (player for player in players if player.id == room.host_id),
                players[0],
            )
        else:
            dealer = self.rng.choice(players)
        dealer_index = players.index(dealer)
        ordered_players = players[dealer_index:] + players[:dealer_index]
        turn_order = [player.id for player in ordered_players]
        hands = {player.id: [] for player in ordered_players}
        deck = self._new_deck()
        self.rng.shuffle(deck)
        for index, card in enumerate(deck):
            hands[turn_order[index % len(turn_order)]].append(card)
        for player_id in turn_order:
            hands[player_id] = self._sort_cards(hands[player_id])

        room.state = CheatPokerState(
            dealer_player_id=dealer.id,
            turn_order=turn_order,
            hands=hands,
            current_player_id=dealer.id,
            winner_target=len(WINNER_SCORES_BY_PLAYER_COUNT[len(players)]),
            history=[{
                "type": "start",
                "message": f"{dealer.name} 担任庄家并首先开牌",
            }],
        )
        room.phase = "playing"

    def act(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        action: str,
        payload: dict[str, Any],
    ) -> None:
        if room.phase != "playing":
            raise GameRuleError("当前对局不能继续操作")
        state: CheatPokerState = room.state
        if action == "resign":
            self._resign(room, state, player)
            return
        if not self._is_active(state, player.id):
            raise GameRuleError("你已不在本局的行动序列中")
        if action == "play":
            self._play(room, state, player, payload)
        elif action == "challenge":
            self._challenge(room, state, player)
        elif action == "accept":
            self._accept(room, state, player)
        else:
            raise GameRuleError("不支持这个欺诈者操作")

    def manual_forfeit(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        state: CheatPokerState = room.state
        if room.phase != "playing" or not self._is_active(state, player.id):
            return False
        self._resign(room, state, player)
        return True

    def view(self, room: ArcadeRoom, viewer: ArcadePlayer) -> dict[str, Any]:
        state: CheatPokerState = room.state
        last_play = state.last_play
        viewer_active = self._is_active(state, viewer.id)
        can_challenge = (
            room.phase == "playing"
            and state.stage == "challenge"
            and last_play is not None
            and viewer_active
            and viewer.id != last_play.player_id
        )
        return {
            "dealerPlayerId": state.dealer_player_id,
            "currentPlayerId": state.current_player_id,
            "stage": state.stage,
            "requiredRank": state.required_rank,
            "requiredRankLabel": (
                RANK_LABELS[state.required_rank] if state.required_rank else None
            ),
            "rankOptions": [
                {"rank": rank, "label": RANK_LABELS[rank]} for rank in RANKS
            ],
            "hand": [
                card.as_dict() for card in state.hands.get(viewer.id, [])
            ],
            "cardCounts": {
                player_id: len(state.hands.get(player_id, []))
                for player_id in state.turn_order
            },
            "activePlayerIds": self._active_ids(state),
            "forfeitedPlayerIds": list(state.forfeited_ids),
            "pileCount": len(state.pile),
            "pileLimit": PILE_LIMIT,
            "pileLocked": len(state.pile) >= PILE_LIMIT,
            "archivedCount": state.archived_count,
            "lastPlay": (
                {
                    "playerId": last_play.player_id,
                    "playerName": last_play.player_name,
                    "claimedRank": last_play.claimed_rank,
                    "claimedLabel": RANK_LABELS[last_play.claimed_rank],
                    "count": len(last_play.cards),
                }
                if last_play
                else None
            ),
            "winnerTarget": state.winner_target,
            "rankings": list(state.rankings),
            "scores": dict(state.scores),
            "history": list(state.history[-14:]),
            "canPlay": (
                room.phase == "playing"
                and state.stage == "play"
                and state.current_player_id == viewer.id
                and viewer_active
            ),
            "canAccept": (
                room.phase == "playing"
                and state.stage == "challenge"
                and state.current_player_id == viewer.id
                and viewer_active
            ),
            "canChallenge": can_challenge,
            "isOpening": state.stage == "play" and state.required_rank is None,
            "myRank": (
                state.rankings.index(viewer.id) + 1
                if viewer.id in state.rankings
                else None
            ),
        }

    def player_result(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
    ) -> tuple[str, str, bool]:
        state: CheatPokerState = room.state
        role = (
            f"第 {state.rankings.index(player.id) + 1} 名"
            if player.id in state.rankings
            else "未晋级"
        )
        return role, "ranking", player.id in room.winner_player_ids

    def record_state(self, room: ArcadeRoom) -> dict[str, Any]:
        state: CheatPokerState = room.state
        return {
            "dealerPlayerId": state.dealer_player_id,
            "turnOrder": list(state.turn_order),
            "cardCounts": {
                player_id: len(state.hands.get(player_id, []))
                for player_id in state.turn_order
            },
            "pileCount": len(state.pile),
            "archivedCount": state.archived_count,
            "winnerTarget": state.winner_target,
            "rankings": list(state.rankings),
            "forfeitedPlayerIds": list(state.forfeited_ids),
            "scores": dict(state.scores),
            "history": list(state.history),
        }

    def _play(
        self,
        room: ArcadeRoom,
        state: CheatPokerState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        if state.stage != "play" or state.current_player_id != player.id:
            raise GameRuleError("还没有轮到你出牌")
        if len(state.pile) >= PILE_LIMIT:
            raise GameRuleError("牌堆已达到 15 张，请先决定是否质疑")
        card_ids = payload.get("cardIds")
        if (
            not isinstance(card_ids, list)
            or not 1 <= len(card_ids) <= MAX_PLAY
            or not all(isinstance(card_id, str) for card_id in card_ids)
            or len(set(card_ids)) != len(card_ids)
        ):
            raise GameRuleError("每次必须选择 1–3 张不同的手牌")
        claimed_rank = payload.get("claimedRank")
        if claimed_rank not in RANKS:
            raise GameRuleError("请选择有效的声明点数")
        if state.required_rank is not None and claimed_rank != state.required_rank:
            raise GameRuleError(f"本轮必须声明 {RANK_LABELS[state.required_rank]}")

        hand_by_id = {card.id: card for card in state.hands[player.id]}
        if any(card_id not in hand_by_id for card_id in card_ids):
            raise GameRuleError("选择的牌不在你的手牌中")
        selected_ids = set(card_ids)
        cards = self._sort_cards([hand_by_id[card_id] for card_id in card_ids])
        state.hands[player.id] = [
            card for card in state.hands[player.id] if card.id not in selected_ids
        ]
        state.pile.extend(cards)
        state.last_play = LastPlay(
            player_id=player.id,
            player_name=player.name,
            claimed_rank=claimed_rank,
            cards=cards,
        )
        state.required_rank = NEXT_RANK[claimed_rank]
        state.stage = "challenge"
        state.current_player_id = self._next_active_id(state, player.id)
        count = len(cards)
        state.history.append({
            "type": "play",
            "playerId": player.id,
            "claimedRank": claimed_rank,
            "count": count,
            "message": f"{player.name} 暗扣 {count} 张牌，声明 {count} 张 {RANK_LABELS[claimed_rank]}",
        })

    def _accept(
        self,
        room: ArcadeRoom,
        state: CheatPokerState,
        player: ArcadePlayer,
    ) -> None:
        last_play = state.last_play
        if (
            state.stage != "challenge"
            or last_play is None
            or state.current_player_id != player.id
        ):
            raise GameRuleError("只有下一位玩家可以选择相信")

        claimant_id = last_play.player_id
        claimed_rank = last_play.claimed_rank
        pile_locked = len(state.pile) >= PILE_LIMIT
        self._qualify_if_empty(room, state, claimant_id)
        state.last_play = None
        state.stage = "play"
        if pile_locked:
            sealed_count = len(state.pile)
            state.archived_count += sealed_count
            state.pile.clear()
            state.required_rank = None
            state.current_player_id = (
                claimant_id
                if self._is_active(state, claimant_id)
                else self._next_active_id(state, claimant_id)
            )
            state.history.append({
                "type": "sealed",
                "count": sealed_count,
                "message": f"无人质疑，{sealed_count} 张牌被封存并重新开牌",
            })
        else:
            state.required_rank = NEXT_RANK[claimed_rank]
            state.current_player_id = player.id

        self._finish_if_ready(room, state)

    def _challenge(
        self,
        room: ArcadeRoom,
        state: CheatPokerState,
        challenger: ArcadePlayer,
    ) -> None:
        last_play = state.last_play
        if state.stage != "challenge" or last_play is None:
            raise GameRuleError("当前没有可以质疑的出牌")
        if challenger.id == last_play.player_id:
            raise GameRuleError("不能质疑自己出的牌")

        truthful = all(
            card.is_joker or card.rank == last_play.claimed_rank
            for card in last_play.cards
        )
        pile_count = len(state.pile)
        collector_id = challenger.id if truthful else last_play.player_id
        state.hands[collector_id].extend(state.pile)
        state.hands[collector_id] = self._sort_cards(state.hands[collector_id])
        state.pile.clear()
        revealed_cards = [card.as_dict() for card in last_play.cards]
        claimant_id = last_play.player_id
        claimant_name = last_play.player_name
        state.last_play = None
        state.required_rank = None
        state.stage = "play"

        if truthful:
            state.history.append({
                "type": "challenge",
                "truthful": True,
                "challengerId": challenger.id,
                "claimantId": claimant_id,
                "revealedCards": revealed_cards,
                "message": f"{challenger.name} 质疑失败：{claimant_name} 说了实话，收走 {pile_count} 张牌",
            })
            self._qualify_if_empty(room, state, claimant_id)
            state.current_player_id = (
                claimant_id
                if self._is_active(state, claimant_id)
                else self._next_active_id(state, claimant_id)
            )
        else:
            state.history.append({
                "type": "challenge",
                "truthful": False,
                "challengerId": challenger.id,
                "claimantId": claimant_id,
                "revealedCards": revealed_cards,
                "message": f"{challenger.name} 揭穿 {claimant_name}，出牌人收走 {pile_count} 张牌",
            })
            state.current_player_id = challenger.id

        self._finish_if_ready(room, state)

    def _resign(
        self,
        room: ArcadeRoom,
        state: CheatPokerState,
        player: ArcadePlayer,
    ) -> None:
        if not self._is_active(state, player.id):
            return
        state.forfeited_ids.append(player.id)
        state.hands[player.id] = []
        state.history.append({
            "type": "resign",
            "playerId": player.id,
            "message": f"{player.name} 认输退出，本局记为 -1 分",
        })

        if state.last_play is not None and state.last_play.player_id == player.id:
            state.pile.clear()
            state.last_play = None
            state.required_rank = None
            state.stage = "play"
        if state.current_player_id == player.id:
            state.current_player_id = self._next_active_id(state, player.id)

        remaining_slots = state.winner_target - len(state.rankings)
        active_ids = self._active_ids(state)
        if active_ids and len(active_ids) <= remaining_slots:
            ordered = sorted(
                active_ids,
                key=lambda player_id: (
                    len(state.hands.get(player_id, [])),
                    state.turn_order.index(player_id),
                ),
            )
            state.rankings.extend(ordered[:remaining_slots])
        self._finish_if_ready(room, state)

    def _qualify_if_empty(
        self,
        room: ArcadeRoom,
        state: CheatPokerState,
        player_id: str,
    ) -> None:
        if self._is_active(state, player_id) and not state.hands.get(player_id):
            state.rankings.append(player_id)
            player = room.player(player_id)
            rank = len(state.rankings)
            state.history.append({
                "type": "rank",
                "playerId": player_id,
                "rank": rank,
                "message": f"{player.name} 的最后一手通过，获得第 {rank} 名",
            })

    def _finish_if_ready(self, room: ArcadeRoom, state: CheatPokerState) -> None:
        if len(state.rankings) < state.winner_target:
            return
        winners = list(state.rankings[:state.winner_target])
        scores = {player.id: -1 for player in room.players}
        for index, player_id in enumerate(winners):
            scores[player_id] = WINNER_SCORES_BY_PLAYER_COUNT[
                len(state.turn_order)
            ][index]
        state.scores = scores
        state.current_player_id = None
        names = [room.player(player_id).name for player_id in winners]
        room.finish(
            "ranking",
            winners,
            f"{', '.join(names)} 依次安全出完手牌",
        )

    @staticmethod
    def _new_deck() -> list[Card]:
        deck = [
            Card(
                id=f"{suit}-{rank}",
                rank=rank,
                suit=suit,
                suit_label=suit_label,
                label=rank,
            )
            for rank in RANKS
            for suit, suit_label in SUITS
        ]
        deck.extend((
            Card("joker-small", "joker", "joker", "★", "小王", True),
            Card("joker-big", "joker", "joker", "★", "大王", True),
        ))
        return deck

    @staticmethod
    def _sort_cards(cards: list[Card]) -> list[Card]:
        rank_order = {rank: index for index, rank in enumerate(RANKS)}
        suit_order = {suit: index for index, (suit, _) in enumerate(SUITS)}
        return sorted(
            cards,
            key=lambda card: (
                len(RANKS) + (1 if card.id == "joker-big" else 0)
                if card.is_joker
                else rank_order[card.rank],
                suit_order.get(card.suit, 0),
            ),
        )

    @staticmethod
    def _active_ids(state: CheatPokerState) -> list[str]:
        unavailable = set(state.rankings) | set(state.forfeited_ids)
        return [
            player_id for player_id in state.turn_order
            if player_id not in unavailable
        ]

    @classmethod
    def _is_active(cls, state: CheatPokerState, player_id: str) -> bool:
        return player_id in cls._active_ids(state)

    @classmethod
    def _next_active_id(
        cls,
        state: CheatPokerState,
        after_player_id: str,
    ) -> str | None:
        if after_player_id not in state.turn_order:
            return None
        start = state.turn_order.index(after_player_id)
        for offset in range(1, len(state.turn_order) + 1):
            candidate = state.turn_order[(start + offset) % len(state.turn_order)]
            if cls._is_active(state, candidate):
                return candidate
        return None
