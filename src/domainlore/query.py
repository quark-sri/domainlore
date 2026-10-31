"""`lore query`, `lore path`, `lore explain`: small, cited answers for agents."""

from __future__ import annotations

import math
import re

from .bundle import Concept
from .graph import Edge, Graph, parse_basis, trust_tier

WORD = re.compile(r"[a-z0-9]+")
STOP = frozenset(
    [
        "a",
        "an",
        "the",
        "of",
        "to",
        "in",
        "on",
        "for",
        "and",
        "or",
        "is",
        "are",
        "what",
        "how",
        "when",
        "who",
        "does",
        "do",
        "can",
        "which",
        "with",
        "by",
        "be",
        "it",
        "this",
        "that",
        "my",
        "their",
        "there",
    ]
)
# Question words that hint at the kind of page that answers the question.
TYPE_HINTS = {
    "who": {"Actor"},
    "how": {"Journey"},
    "where": {"Screen"},
    "screen": {"Screen"},
    "page": {"Screen"},
    "can": {"Rule"},
    "allowed": {"Rule"},
    "must": {"Rule"},
    "rule": {"Rule"},
    "rules": {"Rule"},
    "bug": {"Gap"},
    "known": {"Gap", "Spec Conflict"},
    "or": {"Spec Conflict"},
}


SUFFIXES = ("ers", "ing", "ies", "er", "ed", "es", "s")


def stem(word: str) -> str:
    """Crude suffix stripping so that 'approves', 'approver' and 'approval' meet."""
    if word.endswith("al") and len(word) > 6:
        word = word[:-2]
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def words(text: str) -> list[str]:
    return [stem(w) for w in WORD.findall(text.lower()) if w not in STOP]


def hinted_types(text: str) -> set[str]:
    return set().union(*(TYPE_HINTS.get(w, set()) for w in WORD.findall(text.lower())))


def score(
    concept: Concept,
    terms: list[str],
    hints: set[str] = frozenset(),
    weight: dict[str, float] | None = None,
) -> float:
    if not terms:
        return 0.0
    title = set(words(concept.title))
    aliases = set(words(" ".join(str(a) for a in concept.meta.get("aliases") or [])))
    ident = set(words(concept.id.replace("/", " ").replace("-", " ")))
    description = set(words(concept.description))
    body = words(concept.body)
    total = 0.0
    for t in terms:
        hit = 6 * (t in title) + 4 * (t in aliases) + 3 * (t in ident) + 2 * (t in description)
        hit += min(body.count(t), 3) * 0.5
        total += hit * (weight or {}).get(t, 1.0)
    if " ".join(terms) == " ".join(words(concept.title)):
        total += 10
    if total and concept.type in hints:
        total += 4
    return total


def rarity(pages: list[Concept], terms: list[str]) -> dict[str, float]:
    """Weight each term by how few pages use it, so 'own' counts more than 'order'."""
    texts = [set(words(f"{c.title} {c.id} {c.description} {c.body}")) for c in pages]
    if not texts:
        return {}
    return {t: 1 + math.log(len(texts) / (1 + sum(t in x for x in texts))) for t in set(terms)}


def resolve(graph: Graph, name: str) -> Concept | None:
    """Find a concept by ID, title or alias (case-insensitive)."""
    key = name.strip().removesuffix(".md").lstrip("/")
    if key in graph.bundle.concepts:
        return graph.bundle.concepts[key]
    lowered = name.strip().lower()
    for c in sorted(graph.bundle.concepts.values(), key=lambda c: c.id):
        names = [c.title.lower()] + [str(a).lower() for a in c.meta.get("aliases") or []]
        if lowered in names:
            return follow_aka(graph, c)
    return None


def follow_aka(graph: Graph, concept: Concept) -> Concept:
    """A Term that is only another word for a Node resolves to that Node."""
    if concept.type == "Term":
        for e in graph.out.get(concept.id, []):
            if e.rel == "aka" and (target := graph.concept(e.dst)):
                return target
    return concept


def headline(concept: Concept) -> str:
    basis = ",".join(sorted(parse_basis(concept.meta.get("basis")))) or "-"
    return (
        f"{concept.id}  [{concept.type}; {trust_tier(concept)}; basis {basis}]\n"
        f"  {concept.description or concept.title}\n"
        f"  file: {concept.link}"
    )


def edge_line(graph: Graph, e: Edge, from_id: str) -> str:
    rel = e.rel.replace("_", " ")
    basis = f" ({e.basis_label})" if e.basis_label else ""
    if e.src == from_id:
        return f"  → {rel} {graph.label(e.dst)} ({e.dst}){basis}"
    return f"  ← {graph.label(e.src)} ({e.src}) {rel} this{basis}"


def query(graph: Graph, text: str, limit: int = 5) -> str:
    terms = words(text)
    hints = hinted_types(text)
    pages = [c for c in graph.bundle.concepts.values() if not c.is_generated]
    weight = rarity(pages, terms)
    ranked = sorted(
        ((score(c, terms, hints, weight), c) for c in pages),
        key=lambda pair: (-pair[0], pair[1].id),
    )
    hits: list[Concept] = []
    for value, concept in ranked:
        if value <= 0:
            break
        concept = follow_aka(graph, concept)
        if concept not in hits:
            hits.append(concept)
        if len(hits) == limit:
            break
    if not hits:
        return f"No match for {text!r}. Start at the root index.md and browse the Areas."
    blocks = []
    for c in hits:
        lines = [headline(c)]
        neighbours = graph.out.get(c.id, []) + graph.into.get(c.id, [])
        lines += [edge_line(graph, e, c.id) for e in neighbours[:8]]
        if len(neighbours) > 8:
            lines.append(f"  … {len(neighbours) - 8} more: lore explain {c.id}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def path(graph: Graph, start: str, goal: str) -> str:
    a, b = resolve(graph, start), resolve(graph, goal)
    if a is None or b is None:
        missing = start if a is None else goal
        return (
            f"Not found: {missing!r}. Use a concept ID such as ordering/entities/order, or a title."
        )
    edges = graph.shortest_path(a.id, b.id)
    if edges is None:
        return f"No connection between {a.id} and {b.id}."
    lines = [f"{a.title} ({a.id})"]
    node = a.id
    for e in edges:
        nxt = e.dst if e.src == node else e.src
        arrow = f"--{e.rel}-->" if e.src == node else f"<--{e.rel}--"
        lines.append(f"  {arrow} {graph.label(nxt)} ({nxt})")
        node = nxt
    return "\n".join(lines)


def explain(graph: Graph, name: str) -> str:
    c = resolve(graph, name)
    if c is None:
        return f"Not found: {name!r}."
    lines = [headline(c)]
    for source in c.meta.get("sources") or []:
        if isinstance(source, dict):
            sid = f"[{source['id']}] " if source.get("id") else ""
            lines.append(
                f"  source {sid}{source.get('title') or ''} <{source.get('resource')}>".rstrip()
            )
    states = c.meta.get("states")
    if states:
        lines.append(f"  states: {', '.join(str(s) for s in states)}")
    for e in graph.out.get(c.id, []) + graph.into.get(c.id, []):
        lines.append(edge_line(graph, e, c.id))
    return "\n".join(lines)
