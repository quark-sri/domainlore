"""Mermaid diagrams generated from frontmatter. Never edit their output by hand."""

from __future__ import annotations

import re
from collections import defaultdict

from .bundle import Concept
from .graph import Edge, Graph, trust_tier

FLOW_LEGEND = (
    "_Legend: dashed arrow = intended only (not seen in app or code) · "
    "orange arrow = actual only (not specified) · red ⚠ = open Gap · grey = unverified._"
)
LABEL_LEGEND = "_Labels: (intended) = specified only · (actual) = seen in app or code only._"
CLASS_DEFS = [
    "  classDef gap fill:#fde2e2,stroke:#c00,color:#900",
    "  classDef unverified color:#777,stroke:#aaa",
]
ACTUAL_STROKE = "stroke:#e67e00,stroke-width:2px"


def node_id(cid: str) -> str:
    return "n_" + re.sub(r"[^A-Za-z0-9]", "_", cid)


def quote(text: str) -> str:
    return '"' + text.replace('"', "#quot;") + '"'


def er_name(title: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_") or "Entity"


def basis_suffix(edge: Edge) -> str:
    return f" ({edge.basis_label})" if edge.basis_label else ""


def fenced(lines: list[str]) -> str:
    return "```mermaid\n" + "\n".join(lines) + "\n```"


def chunk(nodes: list[str], edges: list[Edge], limit: int) -> list[list[str]]:
    """Split nodes into parts of at most `limit`, keeping connected nodes together (BFS order)."""
    if len(nodes) <= limit:
        return [nodes]
    adjacency: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        adjacency[e.src].append(e.dst)
        adjacency[e.dst].append(e.src)
    order: list[str] = []
    seen: set[str] = set()
    for start in nodes:
        if start in seen:
            continue
        queue = [start]
        seen.add(start)
        while queue:
            node = queue.pop(0)
            order.append(node)
            for nxt in sorted(adjacency[node]):
                if nxt in nodes and nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
    return [order[i : i + limit] for i in range(0, len(order), limit)]


def flowchart(
    graph: Graph, nodes: list[str], edges: list[Edge], direction: str = "LR"
) -> list[str]:
    """One or more flowcharts with basis, trust and Gap styling, split at the node limit."""
    gaps = graph.open_gap_targets()
    parts = chunk(nodes, edges, graph.config.max_diagram_nodes)
    blocks = []
    for number, part in enumerate(parts, start=1):
        members = set(part)
        lines = [f"flowchart {direction}"]
        for cid in part:
            label = graph.label(cid)
            if cid in gaps:
                label = "⚠ " + label
            lines.append(f"  {node_id(cid)}[{quote(label)}]")
        styles = []
        index = 0
        for e in edges:
            if e.src not in members or e.dst not in members:
                continue
            arrow = "-.->" if e.basis_label == "intended" else "-->"
            lines.append(
                f"  {node_id(e.src)} {arrow}|{quote(e.rel.replace('_', ' '))}| {node_id(e.dst)}"
            )
            if e.basis_label == "actual":
                styles.append(f"  linkStyle {index} {ACTUAL_STROKE}")
            index += 1
        lines.extend(styles)
        lines.extend(CLASS_DEFS)
        gap_nodes = [node_id(c) for c in part if c in gaps]
        grey = [
            node_id(c)
            for c in part
            if c not in gaps and (k := graph.concept(c)) and trust_tier(k) == "unverified"
        ]
        if gap_nodes:
            lines.append(f"  class {','.join(gap_nodes)} gap")
        if grey:
            lines.append(f"  class {','.join(grey)} unverified")
        heading = f"_Part {number} of {len(parts)}_\n\n" if len(parts) > 1 else ""
        blocks.append(heading + fenced(lines))
    crossing = [
        e for e in edges if len(parts) > 1 and not any(e.src in p and e.dst in p for p in parts)
    ]
    text = "\n\n".join(blocks)
    if crossing:
        text += "\n\nLinks between parts:\n" + "\n".join(
            f"- {graph.label(e.src)} {e.rel.replace('_', ' ')} {graph.label(e.dst)}"
            for e in crossing
        )
    return [text, FLOW_LEGEND]


def context_map(graph: Graph, areas: list[str]) -> str | None:
    if not areas:
        return None
    pairs: set[tuple[str, str]] = set()
    for e in graph.edges:
        if e.rel in ("aka", "about"):
            continue
        a = graph.concept(e.src)
        b = graph.concept(e.dst)
        if (
            a
            and b
            and a.area
            and b.area
            and a.area != b.area
            and a.area in areas
            and b.area in areas
        ):
            pairs.add((a.area, b.area))
    lines = ["flowchart LR"]
    for area in areas:
        lines.append(f"  {node_id(area)}[{quote(area_title(area))}]")
    for a, b in sorted(pairs):
        lines.append(f"  {node_id(a)} --> {node_id(b)}")
    return fenced(lines) + "\n\n_Arrows point from an Area to an Area it depends on._"


def area_title(area: str) -> str:
    return area.replace("-", " ").replace("_", " ").title()


def er_diagram(graph: Graph, area: str) -> str | None:
    entities = [c.id for c in graph.bundle.in_area(area) if c.type == "Entity"]
    if not entities:
        return None
    members = set(entities)
    lines = ["erDiagram"]
    names: dict[str, str] = {}
    for cid in entities:
        names[cid] = er_name(graph.label(cid))
        lines.append(f"  {names[cid]}")
    has = {(e.src, e.dst) for e in graph.edges if e.rel == "has"}
    for e in graph.edges:
        if e.rel not in ("has", "belongs_to") or e.src not in members:
            continue
        if e.rel == "belongs_to" and (e.dst, e.src) in has:
            continue  # the inverse `has` already draws this line
        dst = graph.concept(e.dst)
        if dst is None or dst.type != "Entity":
            continue
        names.setdefault(e.dst, er_name(dst.title))
        shape = "||--o{" if e.rel == "has" else "}o--||"
        label = quote(e.rel.replace("_", " ") + basis_suffix(e))
        lines.append(f"  {names[e.src]} {shape} {names[e.dst]} : {label}")
    text = fenced(lines) + "\n\n" + LABEL_LEGEND
    return text + gap_notes(graph, entities)


def gap_notes(graph: Graph, cids: list[str]) -> str:
    """List open Gaps about these concepts, since ER diagrams cannot be styled."""
    notes = []
    for cid in cids:
        for e in graph.into.get(cid, []):
            gap = graph.concept(e.src)
            if e.rel == "about" and gap and gap.type == "Gap" and gap.is_open_conflict:
                notes.append(f"- ⚠ {graph.label(cid)}: [{gap.title}]({gap.link})")
    return "\n\nOpen Gaps:\n" + "\n".join(notes) if notes else ""


def navigation(graph: Graph, area: str) -> str | None:
    screens = [c.id for c in graph.bundle.in_area(area) if c.type == "Screen"]
    if not screens:
        return None
    members = set(screens)
    edges = [e for e in graph.edges if e.rel == "navigates_to" and e.src in members]
    nodes = screens + sorted({e.dst for e in edges if e.dst not in members})
    return "\n\n".join(flowchart(graph, nodes, edges))


def journey(graph: Graph, concept: Concept) -> str | None:
    steps = [s for s in concept.meta.get("steps") or [] if isinstance(s, dict) and s.get("id")]
    if not steps:
        return None
    if concept.meta.get("diagram") == "sequence":
        return journey_sequence(graph, steps)
    lines = ["flowchart TD"]
    for step in steps:
        label = str(step.get("label", step["id"]))
        if step.get("screen"):
            label += f"<br/><small>{graph.label(str(step['screen']))}</small>"
        lines.append(f"  {node_id(str(step['id']))}[{quote(label)}]")
    for i, step in enumerate(steps):
        # No `goto` leads to the next step; `goto: []` ends the journey at this step.
        if step.get("goto") is None:
            if i + 1 < len(steps):
                lines.append(f"  {node_id(str(step['id']))} --> {node_id(str(steps[i + 1]['id']))}")
            continue
        for g in step["goto"]:
            if isinstance(g, dict) and g.get("to"):
                when = f"|{quote(str(g['when']))}|" if g.get("when") else ""
                lines.append(f"  {node_id(str(step['id']))} -->{when} {node_id(str(g['to']))}")
    return fenced(lines)


def journey_sequence(graph: Graph, steps: list[dict]) -> str:
    lines = ["sequenceDiagram"]
    participants: list[str] = []
    for step in steps:
        for key, fallback in (("actor", "User"), ("screen", "System")):
            name = graph.label(str(step[key])) if step.get(key) else fallback
            if name not in participants:
                participants.append(name)
    for name in participants:
        lines.append(f"  participant {er_name(name)} as {name}")
    for step in steps:
        actor = graph.label(str(step["actor"])) if step.get("actor") else "User"
        screen = graph.label(str(step["screen"])) if step.get("screen") else "System"
        lines.append(f"  {er_name(actor)}->>{er_name(screen)}: {step.get('label', step['id'])}")
    return fenced(lines)


def lifecycle(graph: Graph, concept: Concept) -> str | None:
    states = [str(s) for s in concept.meta.get("states") or []]
    transitions = [t for t in concept.meta.get("transitions") or [] if isinstance(t, dict)]
    if not states:
        return None
    default = concept.meta.get("basis")
    lines = ["stateDiagram-v2", f"  [*] --> {states[0]}"]
    for t in transitions:
        parts = []
        if t.get("trigger"):
            parts.append(graph.label(str(t["trigger"])))
        rules = [graph.label(str(r)) for r in t.get("governed_by") or []]
        if rules:
            parts.append("[" + ", ".join(rules) + "]")
        basis = t.get("basis", default)
        if basis in ("intended", "actual"):
            parts.append(f"({basis})")
        label = " ".join(parts).replace(":", " ")
        lines.append(f"  {t.get('from')} --> {t.get('to')}" + (f" : {label}" if label else ""))
    return fenced(lines) + "\n\n" + LABEL_LEGEND
