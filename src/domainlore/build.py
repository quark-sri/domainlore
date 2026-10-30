"""`lore build`: regenerate indexes, maps, the glossary and generated blocks from frontmatter."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from . import diagrams
from .bundle import CONFLICT_TYPES, Bundle, Concept, load_bundle
from .config import Config
from .graph import Graph, trust_tier

GENERATOR = "process:lore-build"
TYPE_ORDER = ["Entity", "Rule", "Actor", "Journey", "Screen", "Term", "Gap", "Spec Conflict"]
TYPE_HEADINGS = {
    "Entity": "Entities",
    "Rule": "Rules",
    "Actor": "Actors",
    "Journey": "Journeys",
    "Screen": "Screens",
    "Term": "Terms",
    "Gap": "Gaps",
    "Spec Conflict": "Spec Conflicts",
}
BLOCK = re.compile(
    r"\n*<!-- generated:start (?P<name>[a-z-]+) -->\n.*?<!-- generated:end (?P=name) -->\n?",
    re.DOTALL,
)


def block(name: str, content: str) -> str:
    return f"<!-- generated:start {name} -->\n{content.strip()}\n<!-- generated:end {name} -->\n"


def set_blocks(text: str, blocks: dict[str, str]) -> str:
    """Replace this page's generated blocks; drop stale ones; append new ones at the end."""
    existing = {m.group("name") for m in BLOCK.finditer(text)}

    def replace(match: re.Match) -> str:
        name = match.group("name")
        return "\n\n" + blocks[name] if name in blocks else "\n"

    text = BLOCK.sub(replace, text)
    for name, content in blocks.items():
        if name not in existing:
            text = text.rstrip("\n") + "\n\n" + content
    text = re.sub(r"\n{3,}(?=<!-- generated:start )", "\n\n", text)
    return text.rstrip("\n") + "\n"


def frontmatter(fields: dict[str, str]) -> str:
    lines = ["---"]
    for key, value in fields.items():
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def entry(concept: Concept, base: str) -> str:
    """An OKF index entry, linked relative to the directory `base`."""
    rel = concept.id[len(base) + 1 :] if base else concept.id
    description = concept.description or concept.type
    tier = trust_tier(concept)
    marker = "" if tier == "human-reviewed" else f" _({tier})_"
    return f"* [{concept.title}]({rel}.md) - {description}{marker}"


def relations_block(graph: Graph, concept: Concept) -> str | None:
    out = [e for e in graph.out.get(concept.id, []) if e.rel != "about"]
    into = [e for e in graph.into.get(concept.id, []) if e.rel != "about"]
    conflicts = [
        graph.concept(e.src)
        for e in graph.into.get(concept.id, [])
        if e.rel == "about" and graph.concept(e.src)
    ]
    if not (out or into or conflicts):
        return None
    lines = ["## Relations", ""]
    for e in out:
        lines.append(f"- {label(graph, e.rel)} → {link(graph, e.dst)}{tag(e)}")
    for e in into:
        lines.append(f"- {link(graph, e.src)} {label(graph, e.rel)} this{tag(e)}")
    for c in conflicts:
        if c is not None:
            state = "open" if c.is_open_conflict else "resolved"
            lines.append(f"- ⚠ {c.type} ({state}): [{c.title}]({c.link})")
    return "\n".join(lines)


def label(graph: Graph, rel: str) -> str:
    spec = graph.config.relations.get(rel)
    return spec.label if spec else rel.replace("_", " ")


def link(graph: Graph, cid: str) -> str:
    concept = graph.concept(cid)
    return f"[{concept.title}]({concept.link})" if concept else f"`{cid}` (missing)"


def tag(edge) -> str:
    return f" _({edge.basis_label})_" if edge.basis_label else ""


def concept_page(graph: Graph, concept: Concept) -> str:
    blocks: dict[str, str] = {}
    if concept.type == "Entity" and (d := diagrams.lifecycle(graph, concept)):
        blocks["lifecycle"] = block("lifecycle", "## Lifecycle\n\n" + d)
    if concept.type == "Journey" and (d := diagrams.journey(graph, concept)):
        blocks["flow"] = block("flow", "## Flow\n\n" + d)
    if r := relations_block(graph, concept):
        blocks["relations"] = block("relations", r)
    return set_blocks(concept.text, blocks)


def area_map(graph: Graph, area: str, description: str) -> str | None:
    er = diagrams.er_diagram(graph, area)
    nav = diagrams.navigation(graph, area)
    if not (er or nav):
        return None
    title = diagrams.area_title(area)
    head = frontmatter(
        {
            "type": "Area Map",
            "title": f"{title} map",
            "description": f"Entities and screen navigation in the {title} Area.",
            "generated": "{ by: " + GENERATOR + " }",
        }
    )
    body = [f"# {title} map", ""]
    if description:
        body += [description, ""]
    if er:
        body += ["## Entities", "", er, ""]
    if nav:
        body += ["## Navigation", "", nav, ""]
    return head + "\n" + "\n".join(body).rstrip("\n") + "\n"


def context_map_page(graph: Graph, areas: list[str]) -> str | None:
    diagram = diagrams.context_map(graph, areas)
    if not diagram:
        return None
    head = frontmatter(
        {
            "type": "Context Map",
            "title": "Context map",
            "description": "The Areas of the domain and how they depend on each other.",
            "generated": "{ by: " + GENERATOR + " }",
        }
    )
    return head + "\n# Context map\n\n" + diagram + "\n"


def glossary(bundle: Bundle) -> str | None:
    """Glossary in the Matt Pocock GLOSSARY.md format, grouped by Area."""
    canonical = bundle.of_type("Entity", "Actor") + [
        t for t in bundle.of_type("Term") if not (t.meta.get("relations") or {}).get("aka")
    ]
    if not canonical:
        return None
    avoid: dict[str, list[str]] = defaultdict(list)
    for c in canonical:
        avoid[c.id].extend(str(a) for a in c.meta.get("aliases") or [])
    for term in bundle.of_type("Term"):
        targets = (term.meta.get("relations") or {}).get("aka") or []
        for target in targets if isinstance(targets, list) else [targets]:
            tid = target.get("to") if isinstance(target, dict) else target
            avoid[str(tid)].append(term.title)
            avoid[str(tid)].extend(str(a) for a in term.meta.get("aliases") or [])

    head = frontmatter(
        {
            "type": "Glossary",
            "title": "Glossary",
            "description": "Canonical domain terms and the words to avoid.",
            "generated": "{ by: " + GENERATOR + " }",
        }
    )
    lines = [
        "# Glossary",
        "",
        "Generated from Entity, Actor and Term pages. Do not edit by hand.",
        "",
    ]
    groups: dict[str, list[Concept]] = defaultdict(list)
    for c in canonical:
        groups[c.area or ""].append(c)
    for area in sorted(groups):
        lines += [f"## {diagrams.area_title(area) if area else 'General'}", ""]
        for c in sorted(groups[area], key=lambda c: c.title.lower()):
            definition = str(c.meta.get("definition") or c.description or "").strip()
            lines.append(f"**[{c.title}]({c.link})**:")
            lines.append(definition or "_No definition yet._")
            words = sorted(set(avoid[c.id]), key=str.lower)
            if words:
                lines.append(f"_Avoid_: {', '.join(words)}")
            lines.append("")
    return head + "\n" + "\n".join(lines).rstrip("\n") + "\n"


def root_index(bundle: Bundle, config: Config, extras: list[tuple[str, str, str]]) -> str:
    lines = ["---", 'okf_version: "0.2"', "---", "", "# Start here", ""]
    for title, path, description in extras:
        lines.append(f"* [{title}]({path}) - {description}")
    areas = bundle.areas()
    if areas:
        lines += ["", "# Areas", ""]
        for area in areas:
            description = config.areas.get(area) or f"{len(bundle.in_area(area))} pages"
            lines.append(f"* [{diagrams.area_title(area)}]({area}/) - {description}")
    entities = bundle.of_type("Entity")
    if entities:
        lines += ["", "# Key entities", ""]
        lines += [entry(c, "") for c in entities[:60]]
    conflicts = [c for c in bundle.of_type(*CONFLICT_TYPES) if c.is_open_conflict]
    if conflicts:
        lines += ["", "# Open conflicts", ""]
        lines += [f"* [{c.title}]({c.id}.md) - {c.type}: {c.description}" for c in conflicts]
    return "\n".join(lines) + "\n"


def dir_index(bundle: Bundle, base: str, has_map: bool) -> str:
    """Index for a directory: every concept below it, grouped by type."""
    members = sorted(
        (
            c
            for c in bundle.concepts.values()
            if c.id.startswith(base + "/") and c.type != "Area Map"
        ),
        key=lambda c: c.id,
    )
    lines: list[str] = []
    if has_map:
        lines += [
            "# Map",
            "",
            f"* [{diagrams.area_title(base)} map](map.md) - Entities and navigation diagrams",
            "",
        ]
    by_type: dict[str, list[Concept]] = defaultdict(list)
    for c in members:
        by_type[c.type].append(c)
    for t in TYPE_ORDER + sorted(set(by_type) - set(TYPE_ORDER)):
        if by_type.get(t):
            lines += [f"# {TYPE_HEADINGS.get(t, t)}", ""]
            lines += [entry(c, base) for c in by_type[t]]
            lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def source_bundle(config: Config) -> Bundle:
    """The bundle without generated pages, which are rebuilt from scratch."""
    bundle = load_bundle(config.knowledge_dir)
    for cid in [c.id for c in bundle.concepts.values() if c.is_generated]:
        del bundle.concepts[cid]
    return bundle


def render(config: Config) -> dict[Path, str]:
    """Every file that `lore build` owns, with its expected content."""
    root = config.knowledge_dir
    bundle = source_bundle(config)
    graph = Graph.build(bundle, config)
    files: dict[Path, str] = {}

    for concept in bundle.concepts.values():
        files[concept.path] = concept_page(graph, concept)

    areas = bundle.areas()
    extras: list[tuple[str, str, str]] = []
    if page := context_map_page(graph, areas):
        files[root / "map.md"] = page
        extras.append(("Context map", "map.md", "Areas and how they depend on each other"))
    if page := glossary(bundle):
        files[root / "GLOSSARY.md"] = page
        extras.append(("Glossary", "GLOSSARY.md", "Canonical terms and the words to avoid"))
    if "questions" in bundle.concepts:
        extras.append(("Open questions", "questions.md", "Ambiguities waiting for a person"))

    maps: set[str] = set()
    for area in areas:
        if page := area_map(graph, area, config.areas.get(area, "")):
            files[root / area / "map.md"] = page
            maps.add(area)

    directories = {
        "/".join(c.id.split("/")[:i])
        for c in bundle.concepts.values()
        for i in range(1, c.id.count("/") + 1)
    }
    for base in sorted(directories):
        files[root / base / "index.md"] = dir_index(bundle, base, base in maps)
    files[root / "index.md"] = root_index(bundle, config, extras)
    return files


def stale_generated(config: Config, files: dict[Path, str]) -> list[Path]:
    """Generated pages and indexes on disk that a fresh build would no longer produce."""
    root = config.knowledge_dir
    bundle = load_bundle(root)
    stale = {c.path for c in bundle.concepts.values() if c.is_generated}
    stale |= set(root.rglob("index.md")) if root.is_dir() else set()
    return sorted(p for p in stale if p not in files)


def build(config: Config) -> tuple[list[Path], list[Path]]:
    """Write the build output. Returns (changed files, removed files)."""
    files = render(config)
    changed = []
    for path, content in sorted(files.items()):
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            changed.append(path)
    removed = stale_generated(config, files)
    for path in removed:
        path.unlink()
        parent = path.parent
        while parent != config.knowledge_dir and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent
    graph = Graph.build(source_bundle(config), config)
    out = config.root / ".lore" / "graph.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(graph.to_json(), encoding="utf-8")
    return changed, removed
