#!/usr/bin/env python3
"""Validate generated catalogs, schemas, examples, privacy boundaries, and SVGs."""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Iterable

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:  # pragma: no cover - actionable CLI failure
    raise SystemExit("jsonschema is required; run: python -m pip install -r requirements.txt") from exc

from generate_models import expected_outputs


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "model"
EXAMPLE_DIR = ROOT / "examples"
ASSET_DIR = ROOT / "assets"

EXPECTED_SCENE_IDS = {
    "setup.ticket-selection",
    "turn.choose-action",
    "draw.train-first",
    "draw.train-second",
    "claim.route-select",
    "claim.tunnel-reveal",
    "claim.tunnel-payment",
    "draw.ticket-choice",
    "station.build",
    "round.final-turns",
    "scoring.station-allocation",
    "scoring.breakdown",
    "game.finished",
}
EXPECTED_PHASES = {
    "setup_ticket_selection",
    "turn_idle",
    "train_draw_second",
    "tunnel_payment",
    "ticket_choice",
    "final_station_assignment",
    "scoring",
    "finished",
}
PUBLIC_PLAYER_KEYS = {
    "id",
    "seatIndex",
    "status",
    "score",
    "trainsRemaining",
    "stationsRemaining",
    "trainHandCount",
    "destinationTicketCount",
    "initialTicketChoiceSubmitted",
    "finalStationAssignmentSubmitted",
}


class Audit:
    def __init__(self) -> None:
        self.checks = 0
        self.failures: list[str] = []

    def expect(self, condition: bool, message: str) -> None:
        self.checks += 1
        if not condition:
            self.failures.append(message)

    def equal(self, actual: Any, expected: Any, message: str) -> None:
        self.expect(actual == expected, f"{message}: expected {expected!r}, got {actual!r}")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def duplicate_values(values: Iterable[str]) -> set[str]:
    counts = Counter(values)
    return {value for value, count in counts.items() if count > 1}


def walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def validate_schema_instance(audit: Audit, schema_path: Path, instance_path: Path) -> None:
    schema = load_json(schema_path)
    instance = load_json(instance_path)
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:  # jsonschema exposes several specific schema exceptions
        audit.expect(False, f"invalid schema {schema_path.name}: {exc}")
        return
    errors = sorted(
        Draft202012Validator(schema).iter_errors(instance),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        for error in errors:
            location = "/".join(str(part) for part in error.absolute_path) or "<root>"
            audit.expect(False, f"{instance_path.name} schema error at {location}: {error.message}")
    else:
        audit.expect(True, f"{instance_path.name} validates")


def audit_generated_files(audit: Audit) -> None:
    outputs = expected_outputs()
    for path, expected in outputs.items():
        audit.expect(path.is_file(), f"missing generated file: {path.relative_to(ROOT)}")
        if path.is_file():
            audit.equal(
                path.read_text(encoding="utf-8"),
                expected,
                f"stale generated file {path.relative_to(ROOT)}",
            )


def audit_board(audit: Audit, board: dict[str, Any]) -> tuple[set[str], set[str]]:
    cities = board["cities"]
    routes = board["routes"]
    city_ids = {item["id"] for item in cities}
    route_ids = {item["id"] for item in routes}

    audit.equal(len(cities), 47, "city count")
    audit.equal(len(routes), 101, "route-track count")
    audit.equal(len(city_ids), 47, "unique city IDs")
    audit.equal(len(route_ids), 101, "unique route IDs")
    audit.equal(duplicate_values(item["boardLabel"] for item in cities), set(), "unique board labels")

    pair_groups: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    adjacency: defaultdict[str, set[str]] = defaultdict(set)
    kind_counts = Counter()
    route_points = {1: 1, 2: 2, 3: 4, 4: 7, 6: 15, 8: 21}

    for route in routes:
        a, b = route["fromCityId"], route["toCityId"]
        audit.expect(a in city_ids and b in city_ids, f"route references unknown city: {route['id']}")
        audit.expect(a != b, f"route must not loop to itself: {route['id']}")
        audit.equal(route["points"], route_points[route["length"]], f"route points {route['id']}")
        if route["kind"] == "ferry":
            audit.expect(route["locomotivesRequired"] >= 1, f"ferry lacks locomotive minimum: {route['id']}")
            audit.equal(route["color"], "gray", f"ferry color {route['id']}")
        else:
            audit.equal(route["locomotivesRequired"], 0, f"non-ferry locomotive minimum {route['id']}")
        pair = tuple(sorted((a, b)))
        pair_groups[pair].append(route)
        adjacency[a].add(b)
        adjacency[b].add(a)
        kind_counts[route["kind"]] += 1

    audit.equal(len(pair_groups), 90, "city-pair count")
    audit.equal(sum(len(group) == 2 for group in pair_groups.values()), 11, "double-route pair count")
    audit.expect(all(len(group) in {1, 2} for group in pair_groups.values()), "no city pair has more than two tracks")
    audit.equal(kind_counts, Counter({"standard": 70, "tunnel": 18, "ferry": 13}), "route-kind counts")
    audit.equal(sum(route["length"] for route in routes), 300, "total route spaces")

    for pair, group in pair_groups.items():
        if len(group) == 2:
            group_id = f"parallel-{pair[0]}-{pair[1]}"
            audit.expect(all(item["parallelGroupId"] == group_id for item in group), f"parallel group ID {pair}")
            audit.equal({item["trackIndex"] for item in group}, {0, 1}, f"parallel track indexes {pair}")
            audit.equal(len({item["length"] for item in group}), 1, f"parallel track lengths {pair}")
        else:
            audit.expect(group[0]["parallelGroupId"] is None, f"single track has parallel group: {group[0]['id']}")
            audit.equal(group[0]["trackIndex"], 0, f"single track index {group[0]['id']}")

    visited: set[str] = set()
    queue: deque[str] = deque([next(iter(city_ids))])
    while queue:
        city = queue.popleft()
        if city in visited:
            continue
        visited.add(city)
        queue.extend(adjacency[city] - visited)
    audit.equal(visited, city_ids, "board graph connectivity")

    audit.equal(board["summary"]["cityCount"], len(cities), "summary city count")
    audit.equal(board["summary"]["routeCount"], len(routes), "summary route count")
    return city_ids, route_ids


def audit_cards(audit: Audit, catalog: dict[str, Any], city_ids: set[str]) -> tuple[set[str], set[str]]:
    train_types = catalog["trainCardTypes"]
    tickets = catalog["destinationTickets"]
    train_type_ids = {item["id"] for item in train_types}
    ticket_ids = {item["id"] for item in tickets}

    audit.equal(len(train_types), 9, "train-card type count")
    audit.equal(len(train_type_ids), 9, "unique train-card type IDs")
    audit.equal(sum(item["copies"] for item in train_types), 110, "train-card copy count")
    audit.equal(len(tickets), 46, "destination-ticket count")
    audit.equal(len(ticket_ids), 46, "unique destination-ticket IDs")
    audit.equal(Counter(item["category"] for item in tickets), Counter({"regular": 40, "long": 6}), "ticket category counts")

    base = [item for item in train_types if item["color"] != "locomotive"]
    loco = [item for item in train_types if item["color"] == "locomotive"]
    audit.equal(len(base), 8, "base train colors")
    audit.expect(all(item["copies"] == 12 and not item["wild"] for item in base), "base colors use 12 non-wild cards")
    audit.equal(len(loco), 1, "locomotive type count")
    audit.expect(loco[0]["copies"] == 14 and loco[0]["wild"], "locomotive uses 14 wild cards")

    endpoint_pairs: list[tuple[str, str]] = []
    for ticket in tickets:
        audit.expect(ticket["fromCityId"] in city_ids and ticket["toCityId"] in city_ids, f"ticket references unknown city: {ticket['id']}")
        audit.expect(ticket["fromCityId"] != ticket["toCityId"], f"ticket endpoints must differ: {ticket['id']}")
        audit.expect(ticket["id"].startswith(f"ticket-{ticket['category']}-"), f"ticket ID/category mismatch: {ticket['id']}")
        if ticket["category"] == "long":
            audit.expect(ticket["points"] in {20, 21}, f"long-ticket points: {ticket['id']}")
        else:
            audit.expect(5 <= ticket["points"] <= 13, f"regular-ticket points: {ticket['id']}")
        endpoint_pairs.append(tuple(sorted((ticket["fromCityId"], ticket["toCityId"]))))
    audit.equal(len(set(endpoint_pairs)), 46, "unique destination endpoint pairs")
    audit.equal(catalog["summary"]["trainCardCount"], 110, "card summary count")
    audit.equal(catalog["summary"]["destinationTicketCount"], 46, "ticket summary count")
    return train_type_ids, ticket_ids


def audit_scenes(audit: Audit, catalog: dict[str, Any], machine: dict[str, Any]) -> None:
    scenes = catalog["scenes"]
    audit.equal({item["id"] for item in scenes}, EXPECTED_SCENE_IDS, "scene IDs")
    audit.equal(set(machine["phases"]), EXPECTED_PHASES, "state-machine phases")
    audit.equal(machine["initialPhase"], "setup_ticket_selection", "initial phase")
    audit.equal(machine["terminalPhase"], "finished", "terminal phase")
    for scene in scenes:
        audit.expect(scene["phase"] in EXPECTED_PHASES, f"scene phase exists: {scene['id']}")
    for transition in machine["transitions"]:
        audit.expect(transition["from"] in EXPECTED_PHASES, f"transition source phase: {transition}")
        audit.expect(transition["to"] in EXPECTED_PHASES, f"transition target phase: {transition}")


def audit_internal_example(
    audit: Audit,
    state: dict[str, Any],
    train_type_ids: set[str],
    ticket_ids: set[str],
    city_ids: set[str],
    route_ids: set[str],
) -> None:
    player_ids = {item["id"] for item in state["players"]}
    audit.equal(set(state["turnOrder"]), player_ids, "turn order contains each player")
    audit.expect(state["currentPlayerId"] in player_ids, "current player exists")
    audit.equal(state["phase"], "tunnel_payment", "tunnel fixture phase")
    audit.expect(state["pendingTunnel"] is not None, "tunnel fixture has pending tunnel")

    instances: list[dict[str, str]] = []
    instances.extend(state["trainDeck"])
    instances.extend(state["trainDiscard"])
    instances.extend(state["faceUpMarket"])
    for player in state["players"]:
        instances.extend(player["trainHand"])
        audit.expect(set(player["destinationTicketIds"]) <= ticket_ids, f"player tickets exist: {player['id']}")
    if state["pendingTunnel"]:
        instances.extend(state["pendingTunnel"]["initialCards"])
        instances.extend(state["pendingTunnel"]["revealedCards"])
        audit.expect(state["pendingTunnel"]["routeId"] in route_ids, "pending tunnel route exists")
    audit.equal(duplicate_values(item["instanceId"] for item in instances), set(), "card instances occupy one zone")
    audit.expect(all(item["typeId"] in train_type_ids for item in instances), "all card types exist")
    audit.expect(set(state["destinationDeck"]) <= ticket_ids, "destination deck IDs exist")
    audit.expect(set(state["removedDestinationTicketIds"]) <= ticket_ids, "removed destination IDs exist")
    audit.expect(all(item["routeId"] in route_ids and item["ownerPlayerId"] in player_ids for item in state["claimedRoutes"]), "claimed-route references exist")
    audit.expect(all(item["cityId"] in city_ids and item["ownerPlayerId"] in player_ids for item in state["stationPlacements"]), "station references exist")
    audit.equal(state["eventSequence"], max(item["sequence"] for item in state["history"]), "event sequence matches history")


def audit_view(
    audit: Audit,
    view: dict[str, Any],
    route_ids: set[str],
    city_ids: set[str],
    train_type_ids: set[str],
    ticket_ids: set[str],
) -> None:
    players = {item["id"]: item for item in view["players"]}
    audit.expect(all(set(item) == PUBLIC_PLAYER_KEYS for item in view["players"]), "public player summaries expose only allowed keys")
    audit.expect(all(item["typeId"] in train_type_ids for item in view["market"]), "market card types exist")
    audit.expect(all(item["routeId"] in route_ids for item in view["board"]["claimedRoutes"]), "view claimed routes exist")
    audit.expect(all(item["cityId"] in city_ids for item in view["board"]["stationPlacements"]), "view station cities exist")
    audit.expect(set(view["board"]["claimableRouteIds"]) <= route_ids, "claimable route IDs exist")

    if view["viewer"]["mode"] == "spectator":
        audit.expect(view["viewer"]["playerId"] is None, "spectator has no player ID")
        audit.expect(view["self"] is None, "spectator has no private self payload")
        audit.equal(view["actions"], [], "spectator has no actions")
        forbidden = {"trainHand", "destinationTickets", "pendingTicketChoice", "pendingTunnelPayment"}
        audit.equal(set(walk_keys(view)) & forbidden, set(), "spectator view contains no private-field names")
    else:
        self_view = view["self"]
        audit.expect(self_view is not None, "player view has private self payload")
        if self_view is not None:
            viewer_id = view["viewer"]["playerId"]
            audit.equal(self_view["playerId"], viewer_id, "private payload belongs to viewer")
            audit.equal(len(self_view["trainHand"]), players[viewer_id]["trainHandCount"], "own train hand count")
            audit.equal(len(self_view["destinationTickets"]), players[viewer_id]["destinationTicketCount"], "own ticket count")
            audit.expect(all(item["typeId"] in train_type_ids for item in self_view["trainHand"]), "private hand types exist")
            audit.expect(all(item["ticketId"] in ticket_ids for item in self_view["destinationTickets"]), "private tickets exist")


def audit_svg(audit: Audit, path: Path, expected_data_attribute: str, expected_count: int) -> None:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        audit.expect(False, f"SVG cannot be parsed: {path.name}: {exc}")
        return
    audit.expect(root.tag.endswith("svg"), f"SVG root element: {path.name}")
    audit.expect(root.get("viewBox") is not None, f"SVG has viewBox: {path.name}")
    values = [element.attrib[expected_data_attribute] for element in root.iter() if expected_data_attribute in element.attrib]
    audit.equal(len(values), expected_count, f"{path.name} {expected_data_attribute} count")
    audit.equal(len(set(values)), expected_count, f"{path.name} unique {expected_data_attribute}")


def audit_documents(audit: Audit) -> None:
    required = [
        ROOT / "README.md",
        ROOT / "SOURCES.md",
        ROOT / "docs" / "RULEBOOK.md",
        ROOT / "docs" / "IMPLEMENTATION_PLAN.md",
        ROOT / "docs" / "CARD_MODEL.md",
        ROOT / "docs" / "SCENE_MODEL.md",
    ]
    for path in required:
        audit.expect(path.is_file() and path.stat().st_size > 100, f"document exists: {path.relative_to(ROOT)}")
    sources = (ROOT / "SOURCES.md").read_text(encoding="utf-8")
    audit.expect("https://www.daysofwonder.com/game/ticket-to-ride-europe/" in sources, "official game page is cited")
    audit.expect("production-daysofwonder" in sources and ".pdf" in sources, "official rulebook PDF is cited")


def main() -> int:
    audit = Audit()
    audit_generated_files(audit)

    schema_pairs = [
        ("board-map.schema.json", "board-map.json"),
        ("card-catalog.schema.json", "card-catalog.json"),
        ("scene-catalog.schema.json", "scene-catalog.json"),
        ("game-state.schema.json", "../examples/internal-tunnel-pending.json"),
        ("view-state.schema.json", "../examples/player-view-turn.json"),
        ("view-state.schema.json", "../examples/spectator-view-turn.json"),
    ]
    for schema_name, instance_name in schema_pairs:
        validate_schema_instance(audit, MODEL_DIR / schema_name, MODEL_DIR / instance_name)

    board = load_json(MODEL_DIR / "board-map.json")
    cards = load_json(MODEL_DIR / "card-catalog.json")
    scenes = load_json(MODEL_DIR / "scene-catalog.json")
    machine = load_json(MODEL_DIR / "state-machine.json")
    internal = load_json(EXAMPLE_DIR / "internal-tunnel-pending.json")
    player_view = load_json(EXAMPLE_DIR / "player-view-turn.json")
    spectator_view = load_json(EXAMPLE_DIR / "spectator-view-turn.json")

    city_ids, route_ids = audit_board(audit, board)
    train_type_ids, ticket_ids = audit_cards(audit, cards, city_ids)
    audit_scenes(audit, scenes, machine)
    audit_internal_example(audit, internal, train_type_ids, ticket_ids, city_ids, route_ids)
    audit_view(audit, player_view, route_ids, city_ids, train_type_ids, ticket_ids)
    audit_view(audit, spectator_view, route_ids, city_ids, train_type_ids, ticket_ids)
    audit_svg(audit, ASSET_DIR / "board-wireframe.svg", "data-route-id", 101)
    audit_svg(audit, ASSET_DIR / "board-wireframe.svg", "data-city-id", 47)
    audit_svg(audit, ASSET_DIR / "card-atlas.svg", "data-card-id", 12)
    audit_documents(audit)

    if audit.failures:
        print(f"Model validation failed: {len(audit.failures)} failure(s) across {audit.checks} checks.", file=sys.stderr)
        for failure in audit.failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(f"Model validation passed: {audit.checks} checks, 47 cities, 101 routes, 156 cards, 13 scenes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
