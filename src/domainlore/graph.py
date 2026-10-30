"""The derived graph: typed edges between concepts, plus trust and basis per edge."""

from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass, field

from .bundle import Bundle, Concept
from .config import Config

BASES = ("intended", "actual")


@dataclass(frozen=True)
class Edge:
    src: str
    rel: str
    dst: str
    basis: frozenset[str] = frozenset()
    cites: tuple[str, ...] = ()
    implied: bool = False  # derived from transitions or journey steps, not declared

    @property
    def basis_label(self) -> str:
        """'intended' or 'actual' when only one basis backs the edge, else ''."""
        return next(iter(self.basis)) if len(self.basis) == 1 else ""


def parse_basis(value: object, default: frozenset[str] = frozenset()) -> frozenset[str]:
    if value is None:
        return default
    values = value if isinstance(value, list) else [value]
    return frozenset(str(v) for v in values if str(v) in BASES)


def trust_tier(concept: Concept) -> str:
    """OKF §5.3: derive the trust tier from `verified` events."""
    verified = concept.meta.get("verified")
    if not verified:
        return "unverified"
    events = verified if isinstance(verified, list) else [verified]
    actors = [str(e.get("by", "")) for e in events if isinstance(e, dict)]
    if any(a.startswith("human:") for a in actors):
        return "human-reviewed"
    return "machine-confirmed" if actors else "unverified"


def relation_targets(concept: Concept) -> list[tuple[str, object]]:
    """Yield (relation, raw target) pairs from the `relations` frontmatter field."""
    relations = concept.meta.get("relations") or {}
    if not isinstance(relations, dict):
        return []
    pairs = []
    for rel, targets in relations.items():
        for target in targets if isinstance(targets, list) else [targets]:
            pairs.append((str(rel), target))
    return pairs


def declared_edges(concept: Concept) -> list[Edge]:
    default = parse_basis(concept.meta.get("basis"))
    edges = []
    for rel, target in relation_targets(concept):
        if isinstance(target, dict):
            dst = str(target.get("to", ""))
            basis = parse_basis(target.get("basis"), default)
            cites = tuple(str(c) for c in target.get("cites") or [])
        else:
            dst, basis, cites = str(target), default, ()
        if dst:
            edges.append(Edge(concept.id, rel, dst, basis, cites))
    return edges


def implied_edges(concept: Concept) -> list[Edge]:
    edges = []
    if concept.type == "Entity":
        for t in concept.meta.get("transitions") or []:
            if not isinstance(t, dict):
                continue
            for rule in t.get("governed_by") or []:
                edges.append(Edge(str(rule), "governs", concept.id, implied=True))
    if concept.type == "Journey":
        for step in concept.meta.get("steps") or []:
            if not isinstance(step, dict):
                continue
            if step.get("screen"):
                edges.append(Edge(str(step["screen"]), "step_of", concept.id, implied=True))
            if step.get("actor"):
                edges.append(Edge(str(step["actor"]), "performs", concept.id, implied=True))
    if concept.type in ("Gap", "Spec Conflict"):
        for target in concept.meta.get("about") or []:
            edges.append(Edge(concept.id, "about", str(target), implied=True))
    return edges


@dataclass
class Graph:
    bundle: Bundle
    config: Config
    edges: list[Edge] = field(default_factory=list)
    out: dict[str, list[Edge]] = field(default_factory=lambda: defaultdict(list))
    into: dict[str, list[Edge]] = field(default_factory=lambda: defaultdict(list))

    @classmethod
    def build(cls, bundle: Bundle, config: Config) -> Graph:
        graph = cls(bundle, config)
        seen: set[tuple[str, str, str]] = set()
        concepts = sorted(bundle.concepts.values(), key=lambda c: c.id)
        declared = [e for c in concepts for e in declared_edges(c)]
        implied = [e for c in concepts for e in implied_edges(c)]
        for edge in declared + implied:
            key = (edge.src, edge.rel, edge.dst)
            if key in seen:  # a declared edge wins over the same implied one
                continue
            seen.add(key)
            graph.edges.append(edge)
            graph.out[edge.src].append(edge)
            graph.into[edge.dst].append(edge)
        return graph

    def concept(self, cid: str) -> Concept | None:
        return self.bundle.concepts.get(cid)

    def open_gap_targets(self) -> set[str]:
        """Concept IDs that an open Gap is about."""
        return {
            e.dst
            for e in self.edges
            if e.rel == "about"
            and (c := self.concept(e.src)) is not None
            and c.type == "Gap"
            and c.is_open_conflict
        }

    def label(self, cid: str) -> str:
        concept = self.concept(cid)
        return concept.title if concept else cid

    def shortest_path(self, start: str, goal: str) -> list[Edge] | None:
        """Breadth-first search over edges in both directions."""
        if start == goal:
            return []
        previous: dict[str, tuple[str, Edge]] = {}
        queue = deque([start])
        visited = {start}
        while queue:
            node = queue.popleft()
            for edge in self.out.get(node, []) + self.into.get(node, []):
                nxt = edge.dst if edge.src == node else edge.src
                if nxt in visited:
                    continue
                visited.add(nxt)
                previous[nxt] = (node, edge)
                if nxt == goal:
                    path = []
                    while nxt != start:
                        nxt, e = previous[nxt]
                        path.append(e)
                    return list(reversed(path))
                queue.append(nxt)
        return None

    def to_json(self) -> str:
        nodes = [
            {
                "id": c.id,
                "type": c.type,
                "title": c.title,
                "description": c.description,
                "area": c.area,
                "trust": trust_tier(c),
                "basis": sorted(parse_basis(c.meta.get("basis"))),
                "path": c.link,
            }
            for c in sorted(self.bundle.concepts.values(), key=lambda c: c.id)
        ]
        edges = [
            {
                "src": e.src,
                "rel": e.rel,
                "dst": e.dst,
                "basis": sorted(e.basis),
                "cites": list(e.cites),
                "implied": e.implied,
            }
            for e in self.edges
        ]
        return json.dumps({"okf_version": "0.2", "nodes": nodes, "edges": edges}, indent=2) + "\n"
