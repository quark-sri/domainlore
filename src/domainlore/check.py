"""`lore check`: validate the Knowledge Base. Exit non-zero on any error."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from functools import cache
from importlib import resources
from pathlib import Path

from jsonschema import Draft202012Validator

from .build import render
from .bundle import CONFLICT_TYPES, DOMAIN_TYPES, Bundle, Concept, load_bundle
from .config import Config
from .graph import BASES, Graph, declared_edges, parse_basis

KNOWN_TYPES = (
    DOMAIN_TYPES | CONFLICT_TYPES | {"Glossary", "Context Map", "Area Map", "Open Questions"}
)
SCHEMA_FILES = {t: t.replace(" ", "") + ".json" for t in DOMAIN_TYPES | CONFLICT_TYPES}
FOOTNOTE = re.compile(r"\[\^([^\]\s]+)\]")
BODY_LINK = re.compile(r"\]\((/[^)\s#]+\.md)")


@dataclass
class Issue:
    level: str  # "error" or "warning"
    code: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.level.upper():7} {self.path}: {self.message} [{self.code}]"


@cache
def validator(concept_type: str) -> Draft202012Validator | None:
    name = SCHEMA_FILES.get(concept_type)
    if not name:
        return None
    text = resources.files("domainlore.schemas").joinpath(name).read_text(encoding="utf-8")
    return Draft202012Validator(json.loads(text))


def plain(value: object) -> object:
    """YAML parses timestamps into datetime objects; the schema expects strings."""
    return json.loads(json.dumps(value, default=lambda v: v.isoformat()))


class Checker:
    def __init__(self, config: Config, now: datetime | None = None):
        self.config = config
        self.now = now or datetime.now(UTC)
        self.bundle: Bundle = load_bundle(config.knowledge_dir)
        self.graph = Graph.build(self.bundle, config)
        self.issues: list[Issue] = []

    def rel(self, path: Path) -> str:
        try:
            return path.relative_to(self.config.root).as_posix()
        except ValueError:
            return path.as_posix()

    def add(self, level: str, code: str, path: Path, message: str) -> None:
        self.issues.append(Issue(level, code, self.rel(path), message))

    def run(self) -> list[Issue]:
        if not self.config.knowledge_dir.is_dir():
            self.add(
                "error",
                "no-knowledge-dir",
                self.config.knowledge_dir,
                "folder not found; run `lore init`",
            )
            return self.issues
        for error in self.bundle.errors:
            self.add("error", "okf-frontmatter", error.path, error.message)
        for concept in sorted(self.bundle.concepts.values(), key=lambda c: c.id):
            self.check_concept(concept)
        self.check_generated()
        return self.issues

    def check_concept(self, c: Concept) -> None:
        if not c.type.strip():
            self.add("error", "okf-type", c.path, "frontmatter has no `type` (OKF requires it)")
            return
        if c.type not in KNOWN_TYPES:
            self.add("warning", "unknown-type", c.path, f"type `{c.type}` is not a domainlore type")
        if v := validator(c.type):
            for err in sorted(v.iter_errors(plain(c.meta)), key=lambda e: list(e.path)):
                where = ".".join(str(p) for p in err.path) or "frontmatter"
                self.add("error", "schema", c.path, f"{where}: {err.message}")
        if c.type in DOMAIN_TYPES and not c.meta.get("sources"):
            self.add("error", "no-source", c.path, "every Fact needs a Source; add `sources`")
        self.check_citations(c)
        self.check_relations(c)
        if c.type == "Entity":
            self.check_lifecycle(c)
        if c.type == "Journey":
            self.check_steps(c)
        if c.type in CONFLICT_TYPES:
            self.check_conflict(c)
        self.check_unrecorded_gap(c)
        self.check_stale(c)
        self.check_body_links(c)

    def check_citations(self, c: Concept) -> None:
        ids = c.source_ids
        for dup in sorted({i for i in ids if ids.count(i) > 1}):
            self.add("error", "duplicate-source", c.path, f"source id `{dup}` is used twice")
        known = set(ids)
        for label in sorted(set(FOOTNOTE.findall(c.body))):
            if label not in known:
                self.add(
                    "error",
                    "unknown-citation",
                    c.path,
                    f"footnote [^{label}] has no `sources` entry",
                )
        cited = [cite for e in declared_edges(c) for cite in e.cites]
        cited += [
            str(x)
            for t in c.meta.get("transitions") or []
            if isinstance(t, dict)
            for x in t.get("cites") or []
        ]
        for cite in sorted(set(cited) - known):
            self.add("error", "unknown-citation", c.path, f"`cites: {cite}` has no `sources` entry")

    def check_relations(self, c: Concept) -> None:
        relations = c.meta.get("relations")
        if relations is not None and not isinstance(relations, dict):
            self.add("error", "relations", c.path, "`relations` must map relation names to targets")
            return
        for e in declared_edges(c):
            spec = self.config.relations.get(e.rel)
            if spec is None:
                self.add(
                    "error",
                    "unknown-relation",
                    c.path,
                    f"relation `{e.rel}` is not defined (add it to lore.toml)",
                )
                continue
            target = self.bundle.concepts.get(e.dst)
            if target is None:
                self.add("error", "broken-relation", c.path, f"{e.rel} → `{e.dst}` does not exist")
                continue
            if spec.sources and c.type not in spec.sources:
                self.add(
                    "error",
                    "relation-type",
                    c.path,
                    f"`{e.rel}` must start from {'/'.join(spec.sources)}, not {c.type}",
                )
            if spec.targets and target.type not in spec.targets:
                self.add(
                    "error",
                    "relation-type",
                    c.path,
                    f"`{e.rel}` must point to {'/'.join(spec.targets)}, `{e.dst}` is {target.type}",
                )
        for rel, raw in (relations or {}).items():
            for target in raw if isinstance(raw, list) else [raw]:
                if (
                    isinstance(target, dict)
                    and target.get("basis") not in (None, *BASES)
                    and not isinstance(target.get("basis"), list)
                ):
                    self.add("error", "basis", c.path, f"{rel}: basis must be intended or actual")

    def check_lifecycle(self, c: Concept) -> None:
        states = {str(s) for s in c.meta.get("states") or []}
        for t in c.meta.get("transitions") or []:
            if not isinstance(t, dict):
                continue
            for end in ("from", "to"):
                if t.get(end) is not None and str(t[end]) not in states:
                    self.add(
                        "error",
                        "lifecycle",
                        c.path,
                        f"transition {end} `{t[end]}` is not in `states`",
                    )
            for rule in t.get("governed_by") or []:
                self.expect(c, str(rule), "Rule", "governed_by")
            if t.get("trigger"):
                trigger = str(t["trigger"])
                if "/" in trigger:
                    self.expect(c, trigger, "Actor", "trigger")

    def check_steps(self, c: Concept) -> None:
        steps = [s for s in c.meta.get("steps") or [] if isinstance(s, dict)]
        ids = [str(s.get("id")) for s in steps]
        for dup in sorted({i for i in ids if ids.count(i) > 1}):
            self.add("error", "journey", c.path, f"step id `{dup}` is used twice")
        for s in steps:
            if s.get("screen"):
                self.expect(c, str(s["screen"]), "Screen", f"step {s.get('id')} screen")
            if s.get("actor"):
                self.expect(c, str(s["actor"]), "Actor", f"step {s.get('id')} actor")
            for g in s.get("goto") or []:
                if isinstance(g, dict) and str(g.get("to")) not in ids:
                    self.add(
                        "error",
                        "journey",
                        c.path,
                        f"step {s.get('id')} goes to unknown step `{g.get('to')}`",
                    )

    def check_conflict(self, c: Concept) -> None:
        about = [str(a) for a in c.meta.get("about") or []]
        if not about:
            self.add("error", "conflict", c.path, f"a {c.type} must say what it is `about`")
        for target in about:
            if target not in self.bundle.concepts:
                self.add("error", "conflict", c.path, f"about `{target}` does not exist")
        if len(c.source_ids) < 2:
            self.add(
                "warning", "conflict", c.path, f"a {c.type} should cite both disagreeing Sources"
            )
        if c.is_open_conflict:
            self.add(
                "warning", "open-conflict", c.path, f"open {c.type}: {c.description or c.title}"
            )

    def check_unrecorded_gap(self, c: Concept) -> None:
        """An intended-only Fact on a page observed as actual is a Gap; it needs a Gap page."""
        if parse_basis(c.meta.get("basis")) != {"actual"}:
            return
        gaps = [
            {str(a) for a in g.meta.get("about") or []}
            for e in self.graph.into.get(c.id, [])
            if e.rel == "about" and (g := self.graph.concept(e.src)) is not None and g.type == "Gap"
        ]
        # A relation is recorded by a Gap about both its ends; a transition by any Gap on the page.
        facts = [
            (f"{e.rel} → `{e.dst}`", f"[{c.id}, {e.dst}]")
            for e in declared_edges(c)
            if e.basis == {"intended"} and not any(e.dst in about for about in gaps)
        ]
        if not gaps:
            facts += [
                (f"transition {t.get('from')} → {t.get('to')}", f"[{c.id}]")
                for t in c.meta.get("transitions") or []
                if isinstance(t, dict) and parse_basis(t.get("basis")) == {"intended"}
            ]
        for fact, about in facts:
            self.add(
                "warning",
                "unrecorded-gap",
                c.path,
                f"{fact} is intended only on an actual page; "
                f"add a Gap page in conflicts/ with `about: {about}`",
            )

    def check_stale(self, c: Concept) -> None:
        value = c.meta.get("stale_after")
        if value is None:
            return
        try:
            if isinstance(value, datetime):
                instant = value
            elif isinstance(value, date):
                instant = datetime(value.year, value.month, value.day, tzinfo=UTC)
            else:
                instant = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if instant.tzinfo is None:
                instant = instant.replace(tzinfo=UTC)
        except ValueError:
            self.add(
                "error", "stale-after", c.path, f"stale_after `{value}` is not an ISO 8601 instant"
            )
            return
        if self.now >= instant:
            self.add(
                "warning",
                "stale",
                c.path,
                f"stale since {instant.date().isoformat()}; re-check its Sources",
            )

    def check_body_links(self, c: Concept) -> None:
        for target in sorted(set(BODY_LINK.findall(c.body))):
            if not (self.config.knowledge_dir / target.lstrip("/")).is_file():
                self.add("warning", "broken-link", c.path, f"link {target} does not resolve")

    def expect(self, c: Concept, cid: str, expected: str, where: str) -> None:
        target = self.bundle.concepts.get(cid)
        if target is None:
            self.add("error", "broken-reference", c.path, f"{where}: `{cid}` does not exist")
        elif target.type != expected:
            self.add(
                "error",
                "broken-reference",
                c.path,
                f"{where}: `{cid}` is {target.type}, expected {expected}",
            )

    def check_generated(self) -> None:
        if self.bundle.errors:
            return  # a page that does not parse makes the build output meaningless
        files = render(self.config)
        for path, content in sorted(files.items()):
            current = path.read_text(encoding="utf-8") if path.exists() else None
            if current != content:
                what = "missing" if current is None else "out of date or edited by hand"
                self.add(
                    "error", "generated", path, f"generated content is {what}; run `lore build`"
                )


def run_check(config: Config, now: datetime | None = None) -> list[Issue]:
    return Checker(config, now).run()


def as_json(issues: list[Issue]) -> str:
    return json.dumps([asdict(i) for i in issues], indent=2)
