from __future__ import annotations

import json
import random
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

from backend.app.games.plugin_api import ArcadePlayer, ArcadeRoom
from backend.app.games.plugins import _load_engine_factory


PLUGIN_DIR = Path(__file__).resolve().parents[1]
ENGINE_FACTORY = _load_engine_factory(PLUGIN_DIR, "plugin-splendor")
CATALOG = json.loads((PLUGIN_DIR / "data" / "card-catalog.json").read_text(encoding="utf-8"))
CARDS = {item["id"]: item for item in CATALOG["developmentCards"]}
NOBLES = {item["id"]: item for item in CATALOG["nobles"]}
STANDARD_COLORS = ("white", "blue", "green", "red", "black")
PIECE_COLORS = (*STANDARD_COLORS, "gold")


def make_players(count: int) -> list[ArcadePlayer]:
    return [
        ArcadePlayer(
            id=f"p{index + 1}",
            account_id=f"account-{index + 1}",
            name=f"玩家{index + 1}",
            token_hash=f"token-{index + 1}",
            seat=index,
        )
        for index in range(count)
    ]


def started_room(count: int = 4, seed: int = 731, *, first_player: str = "host"):
    game = ENGINE_FACTORY()
    game.rng = random.Random(seed)
    players = make_players(count)
    room = ArcadeRoom(
        code=f"SPL{count}",
        game_key=game.key,
        host_id=players[0].id,
        players=players,
        state=game.initial_state(),
        options={"firstPlayer": first_player, "rulesProfile": "base-2024-refresh"},
    )
    game.start(room)
    return game, room, players


def act(game: Any, room: ArcadeRoom, player: ArcadePlayer, action: str, **payload: Any) -> None:
    body = {"revision": room.state.revision, **payload}
    if action in {"reserve_face_up", "reserve_blind", "purchase_face_up"}:
        body.setdefault("marketRevision", room.state.market_revision)
    game.act(room, player, action, body)


def zero_payment() -> dict[str, int]:
    return {color: 0 for color in PIECE_COLORS}


def set_player_pieces(state: Any, player_id: str, pieces: dict[str, int]) -> None:
    board = state.players[player_id]
    for color in PIECE_COLORS:
        state.supply[color] += board.pieces[color]
        board.pieces[color] = 0
    for color in PIECE_COLORS:
        amount = pieces.get(color, 0)
        if amount > state.supply[color]:
            raise AssertionError(f"not enough {color} supply for fixture")
        state.supply[color] -= amount
        board.pieces[color] = amount


def detach_card(state: Any, card_id: str) -> None:
    for tier in state.tiers.values():
        if card_id in tier.deck:
            tier.deck.remove(card_id)
            return
        if card_id in tier.market:
            tier.market[tier.market.index(card_id)] = None
            return
    for board in state.players.values():
        if card_id in board.purchased_card_ids:
            board.purchased_card_ids.remove(card_id)
            return
        for reservation in list(board.reservations):
            if reservation.card_id == card_id:
                board.reservations.remove(reservation)
                return
    raise AssertionError(f"card not found: {card_id}")


def grant_cards(state: Any, player_id: str, card_ids: Iterable[str]) -> None:
    for card_id in card_ids:
        detach_card(state, card_id)
        state.players[player_id].purchased_card_ids.append(card_id)


def grant_bonus(state: Any, player_id: str, color: str, count: int, *, exclude: set[str] | None = None) -> list[str]:
    excluded = exclude or set()
    owned = set(state.players[player_id].purchased_card_ids)
    chosen = [
        card_id
        for card_id, item in CARDS.items()
        if item["bonusColor"] == color and card_id not in excluded and card_id not in owned
    ][:count]
    if len(chosen) != count:
        raise AssertionError(f"cannot grant {count} {color} bonuses")
    grant_cards(state, player_id, chosen)
    return chosen


def put_market_card(state: Any, card_id: str, slot: int = 0) -> None:
    level = CARDS[card_id]["level"]
    tier = state.tiers[level]
    current = tier.market[slot]
    if current == card_id:
        return
    if card_id in tier.deck:
        index = tier.deck.index(card_id)
        tier.deck[index] = current
        tier.market[slot] = card_id
        return
    if card_id in tier.market:
        other = tier.market.index(card_id)
        tier.market[other], tier.market[slot] = current, card_id
        return
    raise AssertionError("fixture only swaps cards already in their original tier")


def set_available_nobles(state: Any, identifiers: list[str]) -> None:
    acquired = {item for board in state.players.values() for item in board.noble_ids}
    state.available_noble_ids = list(identifiers)
    state.unused_noble_ids = [item for item in NOBLES if item not in acquired and item not in identifiers]


def force_turn(state: Any, player_id: str) -> None:
    state.current_player_index = state.turn_order.index(player_id)
    state.turn.active_player_id = player_id
    state.phase = "turn_action"
    state.turn.pending_return_count = 0
    state.turn.eligible_noble_ids = []


def relocate_deck_to_player(state: Any, level: int, player_id: str) -> list[str]:
    moved = list(state.tiers[level].deck)
    state.tiers[level].deck.clear()
    state.players[player_id].purchased_card_ids.extend(moved)
    return moved


def disjoint_card_sets_with_score(score: int, count: int, groups: int = 2) -> list[list[str]]:
    candidates = [identifier for identifier, item in CARDS.items() if item["prestige"] > 0]
    found: list[list[str]] = []
    used: set[str] = set()
    for combo in combinations(candidates, count):
        if any(identifier in used for identifier in combo):
            continue
        if sum(CARDS[identifier]["prestige"] for identifier in combo) == score:
            found.append(list(combo))
            used.update(combo)
            if len(found) == groups:
                return found
    raise AssertionError(f"cannot find {groups} disjoint {count}-card sets scoring {score}")


def card_set_with_score(score: int, count: int, exclude: set[str] | None = None) -> list[str]:
    excluded = exclude or set()
    candidates = [identifier for identifier, item in CARDS.items() if item["prestige"] > 0 and identifier not in excluded]
    for combo in combinations(candidates, count):
        if sum(CARDS[identifier]["prestige"] for identifier in combo) == score:
            return list(combo)
    raise AssertionError(f"cannot find {count} cards scoring {score}")


def all_located_card_ids(state: Any) -> list[str]:
    result: list[str] = []
    for tier in state.tiers.values():
        result.extend(tier.deck)
        result.extend(card_id for card_id in tier.market if card_id is not None)
    for board in state.players.values():
        result.extend(board.purchased_card_ids)
        result.extend(item.card_id for item in board.reservations)
    return result


def _target_cards(view: dict[str, Any], player_id: str) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for tier in view["tiers"]:
        for slot in tier["slots"]:
            if slot["card"] is not None:
                targets.append({"source": "market", "card": slot["card"]})
    self_view = next(item for item in view["players"] if item["id"] == player_id)
    for reservation in self_view["reservations"]:
        if reservation["card"] is not None:
            targets.append({
                "source": "reservation",
                "reservationId": reservation["reservationId"],
                "card": reservation["card"],
            })
    return targets


def autoplay_step(game: Any, room: ArcadeRoom, player: ArcadePlayer) -> str:
    view = game.view(room, player)
    legal = view["actions"]
    if legal["canReturnTokens"]:
        board = next(item for item in view["players"] if item["id"] == player.id)
        targets = _target_cards(view, player.id)
        target = min(
            targets,
            key=lambda item: (
                item["card"]["payment"]["minimumGold"],
                -item["card"]["prestige"],
                item["card"]["totalCost"],
            ),
            default=None,
        )
        need = target["card"]["payment"]["effectiveCost"] if target else {color: 0 for color in STANDARD_COLORS}
        order = sorted(
            STANDARD_COLORS,
            key=lambda color: (
                board["pieces"][color] <= need[color],
                need[color],
                -board["pieces"][color],
            ),
        ) + ["gold"]
        returned = zero_payment()
        remaining = legal["returnCount"]
        for color in order:
            while remaining and returned[color] < board["pieces"][color]:
                returned[color] += 1
                remaining -= 1
        if remaining:
            raise RuntimeError("autoplayer could not compose exact token return")
        act(game, room, player, "return_tokens", pieces=returned)
        return "return_tokens"
    if legal["canChooseNoble"]:
        act(game, room, player, "choose_noble", nobleId=legal["eligibleNobleIds"][0])
        return "choose_noble"
    if not legal["canAct"]:
        raise RuntimeError(f"{player.id} cannot act in phase {view['phase']}")

    targets = _target_cards(view, player.id)
    affordable = [item for item in targets if item["card"]["payment"]["affordable"]]
    if affordable:
        chosen = max(
            affordable,
            key=lambda item: (
                item["card"]["prestige"],
                item["card"]["level"],
                -sum(item["card"]["payment"]["recommendedPayment"].values()),
            ),
        )
        card_view = chosen["card"]
        if chosen["source"] == "market":
            act(
                game, room, player, "purchase_face_up",
                cardId=card_view["id"], payment=card_view["payment"]["recommendedPayment"],
            )
            return "purchase_face_up"
        act(
            game, room, player, "purchase_reserved",
            reservationId=chosen["reservationId"], payment=card_view["payment"]["recommendedPayment"],
        )
        return "purchase_reserved"

    target = min(
        targets,
        key=lambda item: (
            sum(
                max(item["card"]["payment"]["effectiveCost"][color]
                    - next(row for row in view["players"] if row["id"] == player.id)["pieces"][color], 0)
                for color in STANDARD_COLORS
            ),
            -item["card"]["prestige"],
            item["card"]["level"],
        ),
        default=None,
    )
    own = next(row for row in view["players"] if row["id"] == player.id)
    if target:
        effective = target["card"]["payment"]["effectiveCost"]
        deficits = {
            color: max(effective[color] - own["pieces"][color], 0)
            for color in STANDARD_COLORS
        }
        same = [color for color in legal["sameColors"] if deficits[color] >= 2]
        if same:
            color = max(same, key=lambda item: deficits[item])
            act(game, room, player, "take_same", color=color)
            return "take_same"

        if (
            legal["canReserve"]
            and room.state.supply["gold"] > 0
            and len(own["reservations"]) < 2
            and target["source"] == "market"
            and target["card"]["prestige"] >= 2
        ):
            act(game, room, player, "reserve_face_up", cardId=target["card"]["id"])
            return "reserve_face_up"

        if legal["canTakeDifferent"]:
            chosen_colors = sorted(
                legal["differentColors"],
                key=lambda color: (deficits[color], room.state.supply[color]),
                reverse=True,
            )[: legal["requiredDistinctCount"]]
            act(game, room, player, "take_different", colors=chosen_colors)
            return "take_different"

    if legal["blindReserveLevels"]:
        act(game, room, player, "reserve_blind", level=legal["blindReserveLevels"][-1])
        return "reserve_blind"
    if legal["canTakeDifferent"]:
        act(
            game, room, player, "take_different",
            colors=legal["differentColors"][: legal["requiredDistinctCount"]],
        )
        return "take_different"
    if legal["sameColors"]:
        act(game, room, player, "take_same", color=legal["sameColors"][0])
        return "take_same"
    raise RuntimeError("autoplayer found no legal action")


def autoplay_game(count: int, seed: int, max_steps: int = 1_200):
    game, room, players = started_room(count, seed)
    trace: list[str] = []
    for _ in range(max_steps):
        if room.phase == "finished":
            break
        active_id = room.state.turn.active_player_id
        player = room.player(active_id)
        trace.append(f"{active_id}:{room.state.phase}:{autoplay_step(game, room, player)}")
    else:
        raise RuntimeError(f"{count}-player game exceeded {max_steps} actions")
    if room.phase != "finished":
        raise RuntimeError(f"{count}-player game did not finish")
    return game, room, players, trace
