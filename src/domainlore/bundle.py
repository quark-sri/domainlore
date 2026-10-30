"""Read a Knowledge Base: an OKF v0.2 bundle of markdown concept pages."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

RESERVED_FILES = {"index.md", "log.md"}

# Concept types that domainlore writes itself; they need no Sources.
GENERATED_TYPES = {"Glossary", "Context Map", "Area Map"}
# Types whose pages describe the domain and therefore must cite Sources.
DOMAIN_TYPES = {"Entity", "Rule", "Actor", "Journey", "Screen", "Term"}
CONFLICT_TYPES = {"Gap", "Spec Conflict"}


@dataclass
class Concept:
    id: str  # OKF concept ID: bundle-relative path without ".md"
    path: Path
    meta: dict
    body: str
    text: str

    @property
    def type(self) -> str:
        return str(self.meta.get("type", ""))

    @property
    def title(self) -> str:
        title = self.meta.get("title")
        if title:
            return str(title)
        return self.id.rsplit("/", 1)[-1].replace("-", " ").replace("_", " ").title()

    @property
    def description(self) -> str:
        return str(self.meta.get("description") or "").strip()

    @property
    def area(self) -> str | None:
        return self.id.split("/", 1)[0] if "/" in self.id else None

    @property
    def link(self) -> str:
        """Bundle-absolute link, the form OKF recommends."""
        return f"/{self.id}.md"

    @property
    def source_ids(self) -> list[str]:
        return [
            str(s["id"])
            for s in self.meta.get("sources") or []
            if isinstance(s, dict) and s.get("id")
        ]

    @property
    def is_generated(self) -> bool:
        return self.type in GENERATED_TYPES

    @property
    def is_open_conflict(self) -> bool:
        return self.type in CONFLICT_TYPES and not self.meta.get("resolution")


@dataclass
class LoadError:
    path: Path
    message: str


@dataclass
class Bundle:
    root: Path
    concepts: dict[str, Concept] = field(default_factory=dict)
    errors: list[LoadError] = field(default_factory=list)

    def of_type(self, *types: str) -> list[Concept]:
        return sorted((c for c in self.concepts.values() if c.type in types), key=lambda c: c.id)

    def in_area(self, area: str) -> list[Concept]:
        return sorted((c for c in self.concepts.values() if c.area == area), key=lambda c: c.id)

    def areas(self) -> list[str]:
        """Top-level directories that hold at least one domain or conflict page."""
        names = {
            c.area
            for c in self.concepts.values()
            if c.area and not c.is_generated and c.area != "conflicts"
        }
        return sorted(n for n in names if n)


def split_frontmatter(text: str) -> tuple[dict | None, str, str | None]:
    """Return (frontmatter, body, error). Frontmatter is None when absent or unparseable."""
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return None, text, "no YAML frontmatter block"
    lines = text.splitlines(keepends=True)
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == "---":
            raw = "".join(lines[1:i])
            body = "".join(lines[i + 1 :])
            try:
                meta = yaml.safe_load(raw) or {}
            except yaml.YAMLError as exc:
                return None, body, f"frontmatter is not valid YAML: {exc}"
            if not isinstance(meta, dict):
                return None, body, "frontmatter is not a mapping"
            return meta, body, None
    return None, text, "frontmatter block is not closed"


def concept_id(root: Path, path: Path) -> str:
    return path.relative_to(root).with_suffix("").as_posix()


def load_bundle(root: Path) -> Bundle:
    bundle = Bundle(root=root)
    if not root.is_dir():
        return bundle
    for path in sorted(root.rglob("*.md")):
        if path.name in RESERVED_FILES:
            continue
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        text = path.read_text(encoding="utf-8")
        meta, body, error = split_frontmatter(text)
        if error or meta is None:
            bundle.errors.append(LoadError(path, error or "no frontmatter"))
            continue
        cid = concept_id(root, path)
        bundle.concepts[cid] = Concept(id=cid, path=path, meta=meta, body=body, text=text)
    return bundle
