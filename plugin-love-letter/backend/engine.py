from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from random import SystemRandom
from typing import Any

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom, GameRuleError


MODEL_VERSION = "1.2.0"
FAVOR_TARGETS = {2: 6, 3: 5, 4: 4}
CARD_ORDER = (
    "spy", "guard", "priest", "baron", "handmaid", "prince",
    "chancellor", "king", "queen", "countess", "princess",
)
CARD_COUNTS = {
    "spy": 2,
    "guard": 6,
    "priest": 2,
    "baron": 2,
    "handmaid": 2,
    "prince": 2,
    "chancellor": 2,
    "king": 1,
    "queen": 1,
    "countess": 1,
    "princess": 1,
}
CARD_SPECS: dict[str, dict[str, Any]] = {
    "spy": {
        "value": 0, "nameZh": "间谍", "nameEn": "Spy", "symbol": "眼",
        "color": "#4B5563", "motif": "暗封",
        "effectZh": "轮末若你是唯一仍在局且处理过间谍的玩家，额外获得 1 枚好感。",
    },
    "guard": {
        "value": 1, "nameZh": "卫兵", "nameEn": "Guard", "symbol": "盾",
        "color": "#9A3412", "motif": "盘问",
        "effectZh": "猜测另一名玩家的非卫兵角色；猜中则淘汰对方。",
    },
    "priest": {
        "value": 2, "nameZh": "牧师", "nameEn": "Priest", "symbol": "烛",
        "color": "#6D28D9", "motif": "窥信",
        "effectZh": "私下查看另一名玩家当前的手牌。",
    },
    "baron": {
        "value": 3, "nameZh": "男爵", "nameEn": "Baron", "symbol": "衡",
        "color": "#1D4ED8", "motif": "比点",
        "effectZh": "与另一名玩家秘密比点，手牌点数较低者出局。",
    },
    "handmaid": {
        "value": 4, "nameZh": "侍女", "nameEn": "Handmaid", "symbol": "封",
        "color": "#0F766E", "motif": "护信",
        "effectZh": "直到你的下一回合开始前，不会成为其他玩家牌效的目标。",
    },
    "prince": {
        "value": 5, "nameZh": "王子", "nameEn": "Prince", "symbol": "诏",
        "color": "#C2410C", "motif": "重写",
        "effectZh": "令任意一名玩家弃掉手牌并补牌；可以选择自己。",
    },
    "chancellor": {
        "value": 6, "nameZh": "大臣", "nameEn": "Chancellor", "symbol": "策",
        "color": "#0369A1", "motif": "筹谋",
        "effectZh": "抽至多两张，秘密保留一张，其余按顺序压回牌底。",
    },
    "king": {
        "value": 7, "nameZh": "国王", "nameEn": "King", "symbol": "冠",
        "color": "#854D0E", "motif": "易手",
        "effectZh": "与另一名未受保护的玩家交换手牌。",
    },
    "queen": {
        "value": 7.5, "nameZh": "皇后", "nameEn": "Queen", "symbol": "后",
        "color": "#7E22CE", "motif": "御问",
        "effectZh": "与国王或伯爵夫人同手时必须打出；随后像卫兵一样猜牌。",
    },
    "countess": {
        "value": 8, "nameZh": "伯爵夫人", "nameEn": "Countess", "symbol": "扇",
        "color": "#9D174D", "motif": "缄默",
        "effectZh": "与国王或王子同手时，必须打出伯爵夫人。",
    },
    "princess": {
        "value": 9, "nameZh": "公主", "nameEn": "Princess", "symbol": "玺",
        "color": "#BE123C", "motif": "失信",
        "effectZh": "只要打出或因王子弃掉公主，你立即出局。",
    },
}


@dataclass(frozen=True)
class Card:
    id: str
    type_id: str

    @property
    def value(self) -> float:
        return float(CARD_SPECS[self.type_id]["value"])

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "typeId": self.type_id, **CARD_SPECS[self.type_id]}


@dataclass(frozen=True)
class PlayedCard:
    card: Card
    turn_number: int
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "card": self.card.as_dict(),
            "turnNumber": self.turn_number,
            "reason": self.reason,
        }


@dataclass
class PendingChoice:
    id: str
    kind: str
    actor_id: str
    source_card_id: str
    source_type_id: str
    candidate_player_ids: list[str] = field(default_factory=list)
    candidate_card_type_ids: list[str] = field(default_factory=list)
    private_card_ids: list[str] = field(default_factory=list)
    prompt_zh: str = ""


@dataclass
class Knowledge:
    viewer_ids: list[str]
    subject_id: str
    card: Card
    source: str
    acquired_turn: int
    current: bool = True


@dataclass
class LoveLetterState:
    player_ids: list[str] = field(default_factory=list)
    hands: dict[str, list[Card]] = field(default_factory=dict)
    deck: list[Card] = field(default_factory=list)
    reserve: Card | None = None
    face_up_set_aside: list[Card] = field(default_factory=list)
    played: dict[str, list[PlayedCard]] = field(default_factory=dict)
    favors: dict[str, int] = field(default_factory=dict)
    out_player_ids: list[str] = field(default_factory=list)
    forfeited_player_ids: list[str] = field(default_factory=list)
    protected_player_ids: list[str] = field(default_factory=list)
    spy_player_ids: list[str] = field(default_factory=list)
    current_player_id: str | None = None
    start_player_id: str | None = None
    stage: str = "setup"
    round_number: int = 0
    turn_number: int = 0
    favor_target: int = 0
    pending_choice: PendingChoice | None = None
    knowledge: list[Knowledge] = field(default_factory=list)
    event_seq: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)
    round_summary: dict[str, Any] | None = None
    game_winner_ids: list[str] = field(default_factory=list)


class LoveLetterEngine:
    key = "plugin-love-letter"
    name = "情书 · 密封宫廷"
    min_players = 2
    max_players = 4

    def __init__(self, rng: Any | None = None) -> None:
        self.rng = rng or SystemRandom()

    def initial_state(self) -> LoveLetterState:
        return LoveLetterState()

    @staticmethod
    def can_start(room: ArcadeRoom, viewer: ArcadePlayer) -> bool:
        active = [player for player in room.players if not player.left_room]
        return 2 <= len(active) <= 4 and len(active) == len(room.players)

    def start(self, room: ArcadeRoom) -> None:
        players = sorted(
            (player for player in room.players if not player.left_room),
            key=lambda player: player.seat,
        )
        if not self.min_players <= len(players) <= self.max_players:
            raise GameRuleError("情书 · 密封宫廷需要 2–4 位玩家")
        if len(players) != len(room.players):
            raise GameRuleError("请先移除已经离开房间的玩家")

        if room.options.get("firstPlayer") == "host":
            starter = next((player for player in players if player.id == room.host_id), players[0])
        else:
            starter = self.rng.choice(players)
        player_ids = [player.id for player in players]
        state = LoveLetterState(
            player_ids=player_ids,
            favors={player_id: 0 for player_id in player_ids},
            hands={player_id: [] for player_id in player_ids},
            played={player_id: [] for player_id in player_ids},
            favor_target=FAVOR_TARGETS[len(player_ids)],
        )
        room.state = state
        room.phase = "playing"
        room.winner = None
        room.winner_player_ids = []
        room.win_reason = None
        self._deal_round(room, starter.id)

    def act(
        self,
        room: ArcadeRoom,
        player: ArcadePlayer,
        action: str,
        payload: dict[str, Any],
    ) -> None:
        self._member(room, player)
        if room.phase != "playing":
            raise GameRuleError("当前牌局尚未开始或已经结束")
        state: LoveLetterState = room.state
        if action == "resign":
            self.manual_forfeit(room, player)
            return
        if player.id in state.forfeited_player_ids:
            raise GameRuleError("退出整局后不能继续操作")
        if action == "draw_card":
            self._draw_card(room, state, player, payload)
        elif action == "play_card":
            self._play_card(room, state, player, payload)
        elif action == "resolve_choice":
            self._resolve_choice(room, state, player, payload)
        elif action == "next_round":
            self._next_round(room, state, player, payload)
        else:
            raise GameRuleError("不支持这个情书操作")

    def _draw_card(
        self,
        room: ArcadeRoom,
        state: LoveLetterState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_turn(state, player, "draw", payload)
        if len(state.deck) <= 1:
            raise GameRuleError("最后一张牌已封存，不能抽取")
        card = state.deck.pop()
        self._mark_hand_changed(state, player.id)
        state.hands[player.id].append(card)
        state.stage = "play"
        self._emit(
            state, "draw_card", player.id, [],
            f"{self._name(room, player.id)} 从牌堆抽了一张牌",
            {"deckCount": len(state.deck)},
        )

    def _play_card(
        self,
        room: ArcadeRoom,
        state: LoveLetterState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        self._require_turn(state, player, "play", payload)
        card_id = payload.get("cardId")
        if not isinstance(card_id, str):
            raise GameRuleError("请选择要打出的手牌")
        hand = state.hands[player.id]
        card = next((item for item in hand if item.id == card_id), None)
        if card is None:
            raise GameRuleError("这张牌不在你的手牌中")
        if card.id not in self._legal_card_ids(hand):
            raise GameRuleError("这张牌受皇后或伯爵夫人的强制出牌规则限制")

        self._mark_hand_changed(state, player.id)
        hand.remove(card)
        self._record_discard(state, player.id, card, "played")
        self._emit(
            state, "play_card", player.id, [],
            f"{self._name(room, player.id)} 打出{CARD_SPECS[card.type_id]['nameZh']}",
            {"card": card.as_dict()},
        )
        if card.type_id == "spy":
            self._record_spy(state, player.id)
            self._complete_effect(room, state, "spy_mark", player.id, [], "间谍留下了一枚暗记")
        elif card.type_id == "guard" or card.type_id == "queen":
            self._begin_guess(room, state, player.id, card)
        elif card.type_id in {"priest", "baron", "king"}:
            self._begin_target(room, state, player.id, card)
        elif card.type_id == "handmaid":
            if player.id not in state.protected_player_ids:
                state.protected_player_ids.append(player.id)
            self._complete_effect(
                room, state, "gain_protection", player.id, [player.id],
                f"{self._name(room, player.id)} 获得侍女保护",
            )
        elif card.type_id == "prince":
            self._begin_target(room, state, player.id, card)
        elif card.type_id == "chancellor":
            self._begin_chancellor(room, state, player.id, card)
        elif card.type_id == "princess":
            self._eliminate(state, player.id)
            self._complete_effect(
                room, state, "princess_discard", player.id, [player.id],
                f"{self._name(room, player.id)} 弃掉公主，本轮出局",
            )
        else:
            self._complete_effect(
                room, state, "effect_complete", player.id, [],
                f"{CARD_SPECS[card.type_id]['nameZh']}没有即时效果",
            )

    def _begin_guess(
        self,
        room: ArcadeRoom,
        state: LoveLetterState,
        actor_id: str,
        card: Card,
    ) -> None:
        targets = self._other_targets(state, actor_id)
        if not targets:
            self._complete_effect(
                room, state, "no_legal_target", actor_id, [],
                f"{CARD_SPECS[card.type_id]['nameZh']}没有合法目标，效果略过",
            )
            return
        state.pending_choice = PendingChoice(
            id=self._choice_id(state),
            kind="guess",
            actor_id=actor_id,
            source_card_id=card.id,
            source_type_id=card.type_id,
            candidate_player_ids=targets,
            candidate_card_type_ids=[type_id for type_id in CARD_ORDER if type_id != "guard"],
            prompt_zh="选择一名对手并猜测其角色（不能猜卫兵）",
        )
        state.stage = "choice"

    def _begin_target(
        self,
        room: ArcadeRoom,
        state: LoveLetterState,
        actor_id: str,
        card: Card,
    ) -> None:
        targets = self._other_targets(state, actor_id)
        if card.type_id == "prince":
            targets = [actor_id, *targets]
        if not targets:
            self._complete_effect(
                room, state, "no_legal_target", actor_id, [],
                f"{CARD_SPECS[card.type_id]['nameZh']}没有合法目标，效果略过",
            )
            return
        prompts = {
            "priest": "选择一名玩家，私下查看其手牌",
            "baron": "选择一名玩家，秘密比较手牌点数",
            "prince": "选择一名玩家令其弃牌并补牌（可以选自己）",
            "king": "选择一名玩家交换手牌",
        }
        state.pending_choice = PendingChoice(
            id=self._choice_id(state),
            kind="target",
            actor_id=actor_id,
            source_card_id=card.id,
            source_type_id=card.type_id,
            candidate_player_ids=targets,
            prompt_zh=prompts[card.type_id],
        )
        state.stage = "choice"

    def _begin_chancellor(
        self,
        room: ArcadeRoom,
        state: LoveLetterState,
        actor_id: str,
        card: Card,
    ) -> None:
        draw_count = min(2, max(0, len(state.deck) - 1))
        if draw_count == 0:
            self._complete_effect(
                room, state, "chancellor_no_draw", actor_id, [],
                "大臣没有可抽取的牌；最后一张继续封存",
            )
            return
        self._mark_hand_changed(state, actor_id)
        for _ in range(draw_count):
            state.hands[actor_id].append(state.deck.pop())
        state.pending_choice = PendingChoice(
            id=self._choice_id(state),
            kind="chancellor",
            actor_id=actor_id,
            source_card_id=card.id,
            source_type_id=card.type_id,
            private_card_ids=[item.id for item in state.hands[actor_id]],
            prompt_zh="秘密保留一张；其余按从最底到最上的顺序压回牌底",
        )
        state.stage = "choice"
        self._emit(
            state, "chancellor_draw", actor_id, [],
            f"{self._name(room, actor_id)} 用大臣查看了 {len(state.hands[actor_id])} 张候选牌",
            {"candidateCount": len(state.hands[actor_id]), "deckCount": len(state.deck)},
        )

    def _resolve_choice(
        self,
        room: ArcadeRoom,
        state: LoveLetterState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        pending = state.pending_choice
        if state.stage != "choice" or pending is None:
            raise GameRuleError("当前没有待完成的牌效选择")
        if pending.actor_id != player.id:
            raise GameRuleError("只有牌效行动者可以完成这个选择")
        if payload.get("choiceId") != pending.id:
            raise GameRuleError("选择已过期，请按最新桌面重新操作")
        if payload.get("turnNumber") != state.turn_number:
            raise GameRuleError("回合已更新，请重新选择")

        if pending.kind == "guess":
            self._resolve_guess(room, state, pending, payload)
        elif pending.kind == "target":
            self._resolve_target(room, state, pending, payload)
        elif pending.kind == "chancellor":
            self._resolve_chancellor(room, state, pending, payload)
        else:  # pragma: no cover - defensive state corruption guard
            raise GameRuleError("未知的牌效选择")

    def _resolve_guess(
        self,
        room: ArcadeRoom,
        state: LoveLetterState,
        pending: PendingChoice,
        payload: dict[str, Any],
    ) -> None:
        target_id = payload.get("targetPlayerId")
        guess_id = payload.get("cardTypeId")
        if target_id not in pending.candidate_player_ids:
            raise GameRuleError("目标不是当前合法目标")
        if guess_id not in pending.candidate_card_type_ids:
            raise GameRuleError("猜测角色无效；卫兵不能被猜测")
        self._validate_live_target(state, pending.actor_id, target_id, allow_self=False)
        state.pending_choice = None
        target_hand = state.hands[target_id]
        matched = bool(target_hand and target_hand[0].type_id == guess_id)
        source_name = CARD_SPECS[pending.source_type_id]["nameZh"]
        guessed_name = CARD_SPECS[guess_id]["nameZh"]
        if not matched:
            self._complete_effect(
                room, state, "guess_miss", pending.actor_id, [target_id],
                f"{source_name}猜测{self._name(room, target_id)}持有{guessed_name}：未命中",
                {"guessTypeId": guess_id, "matched": False},
            )
            return

        if pending.source_type_id == "guard" and guess_id == "queen":
            queen = target_hand[0]
            self._mark_hand_changed(state, target_id)
            state.hands[target_id] = []
            self._record_discard(state, target_id, queen, "guard-hit")
            replacement_source = self._give_replacement(state, target_id)
            self._complete_effect(
                room, state, "queen_escape", pending.actor_id, [target_id],
                f"卫兵猜中皇后；{self._name(room, target_id)} 弃掉皇后并从{replacement_source}补牌，未被淘汰",
                {"guessTypeId": guess_id, "matched": True, "replacementSource": replacement_source},
            )
            return

        self._eliminate(state, target_id)
        self._complete_effect(
            room, state, "guess_hit", pending.actor_id, [target_id],
            f"{source_name}猜中{self._name(room, target_id)}持有{guessed_name}，目标出局",
            {"guessTypeId": guess_id, "matched": True},
        )

    def _resolve_target(
        self,
        room: ArcadeRoom,
        state: LoveLetterState,
        pending: PendingChoice,
        payload: dict[str, Any],
    ) -> None:
        target_id = payload.get("targetPlayerId")
        if target_id not in pending.candidate_player_ids:
            raise GameRuleError("目标不是当前合法目标")
        allow_self = pending.source_type_id == "prince"
        self._validate_live_target(state, pending.actor_id, target_id, allow_self=allow_self)
        state.pending_choice = None
        actor_id = pending.actor_id
        source = pending.source_type_id
        if source == "priest":
            card = state.hands[target_id][0]
            self._add_knowledge(state, [actor_id], target_id, card, "priest")
            self._complete_effect(
                room, state, "peek_hand", actor_id, [target_id],
                f"{self._name(room, actor_id)} 私下查看了{self._name(room, target_id)}的手牌",
            )
        elif source == "baron":
            actor_card = state.hands[actor_id][0]
            target_card = state.hands[target_id][0]
            self._add_knowledge(state, [actor_id], target_id, target_card, "baron")
            self._add_knowledge(state, [target_id], actor_id, actor_card, "baron")
            if actor_card.value < target_card.value:
                loser_id = actor_id
            elif target_card.value < actor_card.value:
                loser_id = target_id
            else:
                loser_id = None
            if loser_id:
                self._eliminate(state, loser_id)
            outcome = "平手，无人出局" if loser_id is None else f"{self._name(room, loser_id)} 点数较低，本轮出局"
            self._complete_effect(
                room, state, "compare_hands", actor_id, [target_id],
                f"{self._name(room, actor_id)} 与{self._name(room, target_id)}秘密比点：{outcome}",
                {"outcome": "tie" if loser_id is None else "eliminated", "eliminatedPlayerId": loser_id},
            )
        elif source == "king":
            actor_hand = state.hands[actor_id]
            target_hand = state.hands[target_id]
            self._mark_hand_changed(state, actor_id)
            self._mark_hand_changed(state, target_id)
            state.hands[actor_id], state.hands[target_id] = target_hand, actor_hand
            self._complete_effect(
                room, state, "trade_hands", actor_id, [target_id],
                f"{self._name(room, actor_id)} 与{self._name(room, target_id)}交换了手牌",
            )
        elif source == "prince":
            discarded = state.hands[target_id][0]
            self._mark_hand_changed(state, target_id)
            state.hands[target_id] = []
            self._record_discard(state, target_id, discarded, "prince")
            if discarded.type_id == "spy":
                self._record_spy(state, target_id)
            if discarded.type_id == "princess":
                self._eliminate(state, target_id)
                self._complete_effect(
                    room, state, "prince_princess", actor_id, [target_id],
                    f"{self._name(room, target_id)} 被迫弃掉公主，本轮出局",
                    {"discardedCard": discarded.as_dict()},
                )
            else:
                replacement_source = self._give_replacement(state, target_id)
                self._complete_effect(
                    room, state, "force_redraw", actor_id, [target_id],
                    f"{self._name(room, target_id)} 弃掉{CARD_SPECS[discarded.type_id]['nameZh']}并从{replacement_source}补牌",
                    {"discardedCard": discarded.as_dict(), "replacementSource": replacement_source},
                )
        else:  # pragma: no cover
            raise GameRuleError("目标牌效类型无效")

    def _resolve_chancellor(
        self,
        room: ArcadeRoom,
        state: LoveLetterState,
        pending: PendingChoice,
        payload: dict[str, Any],
    ) -> None:
        keep_id = payload.get("keepCardId")
        bottom_ids = payload.get("bottomCardIds")
        if not isinstance(keep_id, str) or not isinstance(bottom_ids, list) or not all(
            isinstance(card_id, str) for card_id in bottom_ids
        ):
            raise GameRuleError("必须选择保留牌并提交牌底顺序")
        expected = set(pending.private_card_ids)
        submitted = [keep_id, *bottom_ids]
        if len(submitted) != len(expected) or set(submitted) != expected:
            raise GameRuleError("保留牌与牌底顺序必须恰好覆盖全部候选牌")
        cards = {card.id: card for card in state.hands[pending.actor_id]}
        if set(cards) != expected:
            raise GameRuleError("大臣候选牌已变化，请刷新桌面")
        state.pending_choice = None
        self._mark_hand_changed(state, pending.actor_id)
        state.hands[pending.actor_id] = [cards[keep_id]]
        # deck[0] is the deepest card and deck[-1] is the next draw.
        state.deck = [cards[card_id] for card_id in bottom_ids] + state.deck
        self._complete_effect(
            room, state, "bottom_cards", pending.actor_id, [],
            f"{self._name(room, pending.actor_id)} 秘密保留一张，并将 {len(bottom_ids)} 张牌压回牌底",
            {"bottomCount": len(bottom_ids), "deckCount": len(state.deck)},
        )

    def _complete_effect(
        self,
        room: ArcadeRoom,
        state: LoveLetterState,
        kind: str,
        actor_id: str | None,
        target_ids: list[str],
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        state.stage = "resolving"
        self._emit(state, kind, actor_id, target_ids, message, data or {})
        self._advance_or_finish_round(room, state)

    def _advance_or_finish_round(self, room: ArcadeRoom, state: LoveLetterState) -> None:
        active = self._active_ids(state)
        if len(active) <= 1:
            self._finish_round(room, state, "last-player")
            return
        if len(state.deck) <= 1:
            self._finish_round(room, state, "one-card-left")
            return
        assert state.current_player_id is not None
        next_id = self._next_active_id(state, state.current_player_id)
        state.current_player_id = next_id
        state.turn_number += 1
        state.stage = "draw"
        if next_id in state.protected_player_ids:
            state.protected_player_ids.remove(next_id)
            self._emit(
                state, "protection_expired", next_id, [next_id],
                f"{self._name(room, next_id)} 的侍女保护在回合开始时消退",
            )

    def _finish_round(self, room: ArcadeRoom, state: LoveLetterState, reason: str) -> None:
        active = self._active_ids(state)
        if not active:
            # Only possible through simultaneous external forfeits; preserve a total result.
            winners: list[str] = []
        elif reason == "last-player":
            winners = [active[0]]
        else:
            highest = max(state.hands[player_id][0].value for player_id in active)
            winners = [player_id for player_id in active if state.hands[player_id][0].value == highest]

        revealed_hands: list[dict[str, Any]] = []
        for player_id in active:
            if not state.hands[player_id]:
                continue
            card = state.hands[player_id][0]
            revealed_hands.append({"playerId": player_id, "card": card.as_dict()})
            state.hands[player_id] = []
            self._record_discard(state, player_id, card, "round-reveal")
            self._mark_hand_changed(state, player_id)

        spy_eligible = [player_id for player_id in active if player_id in state.spy_player_ids]
        spy_bonus_id = spy_eligible[0] if len(spy_eligible) == 1 else None
        rewards = {player_id: 1 for player_id in winners}
        if spy_bonus_id is not None:
            rewards[spy_bonus_id] = rewards.get(spy_bonus_id, 0) + 1
        for player_id, amount in rewards.items():
            state.favors[player_id] += amount

        state.round_summary = {
            "roundNumber": state.round_number,
            "endReason": reason,
            "roundWinnerIds": winners,
            "revealedHands": revealed_hands,
            "spyBonusPlayerId": spy_bonus_id,
            "rewardDeltas": rewards,
            "deckCountAtEnd": len(state.deck),
            "sealedCardCount": 1 if len(state.deck) == 1 else 0,
            "sealedCardRevealed": False,
            "reserveRevealed": False,
        }
        state.current_player_id = None
        state.pending_choice = None
        state.protected_player_ids = []
        state.game_winner_ids = [
            player_id for player_id in self._match_player_ids(state)
            if state.favors[player_id] >= state.favor_target
        ]
        winner_names = "、".join(self._name(room, player_id) for player_id in winners) or "无人"
        self._emit(
            state, "round_end", None, winners,
            f"第 {state.round_number} 轮结束：{winner_names} 赢得本轮；最后一张牌保持封存",
            {
                "endReason": reason,
                "winnerPlayerIds": winners,
                "rewardDeltas": rewards,
                "sealedCardCount": 1 if len(state.deck) == 1 else 0,
                "sealedCardRevealed": False,
            },
        )
        if state.game_winner_ids:
            state.stage = "finished"
            names = "、".join(self._name(room, player_id) for player_id in state.game_winner_ids)
            room.finish(
                "favor",
                list(state.game_winner_ids),
                f"{names} 达到 {state.favor_target} 枚好感标记，赢得密封宫廷",
            )
        else:
            state.stage = "round_summary"

    def _next_round(
        self,
        room: ArcadeRoom,
        state: LoveLetterState,
        player: ArcadePlayer,
        payload: dict[str, Any],
    ) -> None:
        if state.stage != "round_summary" or state.round_summary is None:
            raise GameRuleError("当前不是轮间结算阶段")
        if payload.get("roundNumber") != state.round_number:
            raise GameRuleError("轮次已更新，请刷新桌面")
        candidates = [
            player_id for player_id in state.round_summary["roundWinnerIds"]
            if player_id not in state.forfeited_player_ids
        ]
        if not candidates:
            candidates = self._match_player_ids(state)
        self._deal_round(room, self.rng.choice(candidates))

    def _deal_round(self, room: ArcadeRoom, starter_id: str) -> None:
        state: LoveLetterState = room.state
        match_ids = self._match_player_ids(state)
        if starter_id not in match_ids:
            starter_id = match_ids[0]
        deck = self._new_deck()
        self.rng.shuffle(deck)
        state.deck = deck
        state.reserve = state.deck.pop()
        state.face_up_set_aside = []
        if len(match_ids) == 2:
            state.face_up_set_aside = [state.deck.pop() for _ in range(3)]
        state.hands = {player_id: [] for player_id in state.player_ids}
        state.played = {player_id: [] for player_id in state.player_ids}
        for player_id in match_ids:
            state.hands[player_id].append(state.deck.pop())
        state.out_player_ids = list(state.forfeited_player_ids)
        state.protected_player_ids = []
        state.spy_player_ids = []
        state.knowledge = []
        state.pending_choice = None
        state.round_summary = None
        state.round_number += 1
        state.turn_number = 1
        state.start_player_id = starter_id
        state.current_player_id = starter_id
        state.stage = "draw"
        room.round_number = state.round_number
        self._emit(
            state, "round_deal", starter_id, match_ids,
            f"第 {state.round_number} 轮完成密封发牌，{self._name(room, starter_id)} 先手",
            {
                "playerCount": len(match_ids),
                "deckCount": len(state.deck),
                "faceUpSetAsideCount": len(state.face_up_set_aside),
                "reserveCount": 1,
            },
        )

    def manual_forfeit(self, room: ArcadeRoom, player: ArcadePlayer) -> bool:
        state: LoveLetterState = room.state
        if room.phase != "playing" or player.id not in state.player_ids:
            return False
        if player.id in state.forfeited_player_ids:
            return False
        was_current = state.current_player_id == player.id
        state.forfeited_player_ids.append(player.id)
        self._eliminate(state, player.id)
        if state.pending_choice and state.pending_choice.actor_id == player.id:
            state.pending_choice = None
        self._emit(
            state, "forfeit", player.id, [player.id],
            f"{self._name(room, player.id)} 退出整局",
        )
        remaining = self._match_player_ids(state)
        if len(remaining) == 1:
            winner_id = remaining[0]
            state.game_winner_ids = [winner_id]
            state.stage = "finished"
            room.finish(
                "last-player", [winner_id],
                f"{self._name(room, winner_id)} 是最后留在整局的玩家",
            )
            return True
        if len(self._active_ids(state)) <= 1:
            self._finish_round(room, state, "forfeit")
        elif was_current:
            next_id = self._next_active_id(state, player.id)
            state.current_player_id = next_id
            state.turn_number += 1
            state.stage = "draw"
            if next_id in state.protected_player_ids:
                state.protected_player_ids.remove(next_id)
        return True

    disconnect_timeout = manual_forfeit

    def view(self, room: ArcadeRoom, viewer: ArcadePlayer) -> dict[str, Any]:
        state: LoveLetterState = room.state
        viewer_id = viewer.id if viewer.id in state.player_ids else None
        actions: list[str] = []
        if room.phase == "playing" and viewer_id not in state.forfeited_player_ids:
            if state.stage == "draw" and viewer_id == state.current_player_id:
                actions.append("draw_card")
            elif state.stage == "play" and viewer_id == state.current_player_id:
                actions.append("play_card")
            elif (
                state.stage == "choice" and state.pending_choice is not None
                and viewer_id == state.pending_choice.actor_id
            ):
                actions.append("resolve_choice")
            elif state.stage == "round_summary" and viewer_id in self._match_player_ids(state):
                actions.append("next_round")
            actions.append("resign")

        players = []
        for player_id in state.player_ids:
            player = room.player(player_id)
            if player_id in state.forfeited_player_ids:
                status = "forfeited"
            elif player_id in state.out_player_ids:
                status = "out"
            else:
                status = "active"
            players.append({
                "id": player_id,
                "name": player.name,
                "seat": player.seat,
                "favorTokens": state.favors.get(player_id, 0),
                "favorTarget": state.favor_target,
                "roundStatus": status,
                "protected": player_id in state.protected_player_ids,
                "handCount": len(state.hands.get(player_id, [])),
                "visibleHand": [
                    card.as_dict() for card in state.hands.get(player_id, [])
                ] if player_id == viewer_id else [],
                "played": [entry.as_dict() for entry in state.played.get(player_id, [])],
                "isCurrent": player_id == state.current_player_id,
            })

        pending_view = None
        pending = state.pending_choice
        if pending is not None:
            is_actor = viewer_id == pending.actor_id
            pending_view = {
                "kind": pending.kind,
                "sourceTypeId": pending.source_type_id,
                "actorPlayerId": pending.actor_id,
                "isActor": is_actor,
                "choiceId": pending.id if is_actor else None,
                "promptZh": pending.prompt_zh,
                "candidatePlayerIds": list(pending.candidate_player_ids) if is_actor else [],
                "candidateCardTypeIds": list(pending.candidate_card_type_ids) if is_actor else [],
                "privateCards": [
                    card.as_dict()
                    for card in state.hands.get(pending.actor_id, [])
                    if card.id in pending.private_card_ids
                ] if is_actor else [],
            }

        knowledge = []
        if viewer_id is not None:
            for item in state.knowledge:
                if viewer_id in item.viewer_ids:
                    knowledge.append({
                        "subjectPlayerId": item.subject_id,
                        "card": item.card.as_dict(),
                        "source": item.source,
                        "acquiredTurn": item.acquired_turn,
                        "current": item.current,
                    })

        legal_card_ids = []
        if "play_card" in actions and viewer_id is not None:
            legal_card_ids = self._legal_card_ids(state.hands[viewer_id])
        return {
            "schemaVersion": 1,
            "modelVersion": MODEL_VERSION,
            "profileId": "queen_22",
            "sceneId": self._scene_id(state),
            "stage": state.stage,
            "roundNumber": state.round_number,
            "turnNumber": state.turn_number,
            "currentPlayerId": state.current_player_id,
            "startPlayerId": state.start_player_id,
            "deckCount": len(state.deck),
            "sealedCardCount": 1 if len(state.deck) == 1 else 0,
            "reserveAvailable": state.reserve is not None,
            "faceUpSetAside": [card.as_dict() for card in state.face_up_set_aside],
            "players": players,
            "cardCatalog": [
                {"typeId": type_id, "count": CARD_COUNTS[type_id], **CARD_SPECS[type_id]}
                for type_id in CARD_ORDER
            ],
            "rules": {
                "playerMin": 2,
                "playerMax": 4,
                "deckSize": 22,
                "favorTarget": state.favor_target,
                "finalCardSealed": True,
                "roundEndsAtDeckCount": 1,
                "queenValue": 7.5,
            },
            "actions": actions,
            "legalCardIds": legal_card_ids,
            "pendingChoice": pending_view,
            "privateInfo": {"knownHands": knowledge},
            "events": deepcopy(state.events[-24:]),
            "latestEvent": deepcopy(state.events[-1]) if state.events else None,
            "roundSummary": deepcopy(state.round_summary),
            "gameWinnerIds": list(state.game_winner_ids),
        }

    def player_result(
        self, room: ArcadeRoom, player: ArcadePlayer,
    ) -> tuple[str, str, bool]:
        state: LoveLetterState = room.state
        favor = state.favors.get(player.id, 0)
        won = player.id in room.winner_player_ids
        label = f"{favor} / {state.favor_target} 枚好感"
        return label, "courtier", won

    def record_state(self, room: ArcadeRoom) -> dict[str, Any]:
        state: LoveLetterState = room.state
        # Deliberately excludes deck/reserve identities and all private knowledge.
        return {
            "modelVersion": MODEL_VERSION,
            "profileId": "queen_22",
            "roundNumber": state.round_number,
            "turnNumber": state.turn_number,
            "stage": state.stage,
            "favors": dict(state.favors),
            "favorTarget": state.favor_target,
            "players": [
                {
                    "id": player_id,
                    "played": [entry.as_dict() for entry in state.played.get(player_id, [])],
                    "forfeited": player_id in state.forfeited_player_ids,
                }
                for player_id in state.player_ids
            ],
            "faceUpSetAside": [card.as_dict() for card in state.face_up_set_aside],
            "deckCount": len(state.deck),
            "sealedCardRevealed": False,
            "roundSummary": deepcopy(state.round_summary),
            "winnerPlayerIds": list(room.winner_player_ids),
            "events": deepcopy(state.events),
        }

    @staticmethod
    def _member(room: ArcadeRoom, player: ArcadePlayer) -> None:
        if not any(member.id == player.id for member in room.players):
            raise GameRuleError("只有本局玩家可以操作")

    @staticmethod
    def _require_turn(
        state: LoveLetterState,
        player: ArcadePlayer,
        stage: str,
        payload: dict[str, Any],
    ) -> None:
        if state.stage != stage:
            raise GameRuleError("当前不是这个操作阶段")
        if state.current_player_id != player.id:
            raise GameRuleError("还没有轮到你")
        if payload.get("turnNumber") != state.turn_number:
            raise GameRuleError("回合已更新，请刷新桌面")

    @staticmethod
    def _new_deck() -> list[Card]:
        return [
            Card(f"{type_id}-{index:02d}", type_id)
            for type_id in CARD_ORDER
            for index in range(1, CARD_COUNTS[type_id] + 1)
        ]

    @staticmethod
    def _legal_card_ids(hand: list[Card]) -> list[str]:
        types = {card.type_id for card in hand}
        if "queen" in types and types.intersection({"king", "countess"}):
            return [card.id for card in hand if card.type_id == "queen"]
        if "countess" in types and types.intersection({"king", "prince"}):
            return [card.id for card in hand if card.type_id == "countess"]
        return [card.id for card in hand]

    @staticmethod
    def _match_player_ids(state: LoveLetterState) -> list[str]:
        return [
            player_id for player_id in state.player_ids
            if player_id not in state.forfeited_player_ids
        ]

    def _active_ids(self, state: LoveLetterState) -> list[str]:
        return [
            player_id for player_id in self._match_player_ids(state)
            if player_id not in state.out_player_ids
        ]

    def _other_targets(self, state: LoveLetterState, actor_id: str) -> list[str]:
        return [
            player_id for player_id in self._active_ids(state)
            if player_id != actor_id and player_id not in state.protected_player_ids
        ]

    def _validate_live_target(
        self,
        state: LoveLetterState,
        actor_id: str,
        target_id: str,
        *,
        allow_self: bool,
    ) -> None:
        if target_id not in self._active_ids(state):
            raise GameRuleError("目标已不在本轮")
        if target_id == actor_id:
            if not allow_self:
                raise GameRuleError("这个效果不能选择自己")
            return
        if target_id in state.protected_player_ids:
            raise GameRuleError("目标正受到侍女保护")

    def _next_active_id(self, state: LoveLetterState, player_id: str) -> str:
        start = state.player_ids.index(player_id)
        active = set(self._active_ids(state))
        for offset in range(1, len(state.player_ids) + 1):
            candidate = state.player_ids[(start + offset) % len(state.player_ids)]
            if candidate in active:
                return candidate
        raise RuntimeError("no active Love Letter player")

    @staticmethod
    def _choice_id(state: LoveLetterState) -> str:
        return f"choice-{state.round_number}-{state.turn_number}-{state.event_seq + 1}"

    @staticmethod
    def _record_discard(
        state: LoveLetterState,
        player_id: str,
        card: Card,
        reason: str,
    ) -> None:
        state.played[player_id].append(PlayedCard(card, state.turn_number, reason))

    @staticmethod
    def _record_spy(state: LoveLetterState, player_id: str) -> None:
        if player_id not in state.spy_player_ids:
            state.spy_player_ids.append(player_id)

    @staticmethod
    def _mark_hand_changed(state: LoveLetterState, player_id: str) -> None:
        for item in state.knowledge:
            if item.subject_id == player_id:
                item.current = False

    @staticmethod
    def _add_knowledge(
        state: LoveLetterState,
        viewer_ids: list[str],
        subject_id: str,
        card: Card,
        source: str,
    ) -> None:
        state.knowledge.append(Knowledge(
            viewer_ids=list(viewer_ids),
            subject_id=subject_id,
            card=card,
            source=source,
            acquired_turn=state.turn_number,
        ))

    def _eliminate(self, state: LoveLetterState, player_id: str) -> None:
        if player_id in state.out_player_ids:
            return
        self._mark_hand_changed(state, player_id)
        for card in list(state.hands.get(player_id, [])):
            self._record_discard(state, player_id, card, "eliminated")
        state.hands[player_id] = []
        state.out_player_ids.append(player_id)
        if player_id in state.protected_player_ids:
            state.protected_player_ids.remove(player_id)

    def _give_replacement(self, state: LoveLetterState, player_id: str) -> str:
        if len(state.deck) > 1:
            card = state.deck.pop()
            source = "牌堆"
        elif state.reserve is not None:
            card = state.reserve
            state.reserve = None
            source = "暗置牌"
        else:  # defensive fallback for externally corrupted fixtures
            raise GameRuleError("没有可用的补牌；最后一张封存牌不能抽取")
        state.hands[player_id] = [card]
        return source

    @staticmethod
    def _emit(
        state: LoveLetterState,
        kind: str,
        actor_id: str | None,
        target_ids: list[str],
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        state.event_seq += 1
        state.events.append({
            "seq": state.event_seq,
            "kind": kind,
            "actorPlayerId": actor_id,
            "targetPlayerIds": list(target_ids),
            "messageZh": message,
            "data": deepcopy(data or {}),
        })

    @staticmethod
    def _name(room: ArcadeRoom, player_id: str) -> str:
        return room.player(player_id).name

    @staticmethod
    def _scene_id(state: LoveLetterState) -> str:
        if state.stage == "draw":
            return "turn_draw"
        if state.stage == "play":
            return "turn_play"
        if state.stage == "choice" and state.pending_choice:
            if state.pending_choice.kind == "guess":
                return "guard_choice"
            if state.pending_choice.kind == "chancellor":
                return "chancellor_choice"
            return "target_choice"
        if state.stage == "round_summary":
            return "round_result"
        if state.stage == "finished":
            return "game_result"
        return "round_setup"
