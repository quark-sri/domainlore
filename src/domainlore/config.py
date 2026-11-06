"""Project configuration from lore.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_FILE = "lore.toml"
AMBIGUITY_STEPS = ("sources", "code", "ask")  # the order in which an ambiguity is resolved


class ConfigError(ValueError):
    """lore.toml has a value that cannot be used."""


@dataclass(frozen=True)
class RelationSpec:
    name: str
    label: str
    sources: tuple[str, ...]  # allowed source types; empty = any
    targets: tuple[str, ...]  # allowed target types; empty = any


BUILTIN_RELATIONS: dict[str, RelationSpec] = {
    spec.name: spec
    for spec in (
        RelationSpec("has", "has", ("Entity",), ("Entity",)),
        RelationSpec("belongs_to", "belongs to", ("Entity",), ("Entity",)),
        RelationSpec("governs", "governs", ("Rule",), ("Entity",)),
        RelationSpec("performs", "performs", ("Actor",), ("Journey",)),
        RelationSpec("navigates_to", "navigates to", ("Screen",), ("Screen",)),
        RelationSpec("shows", "shows", ("Screen",), ("Entity",)),
        RelationSpec("step_of", "step of", ("Screen",), ("Journey",)),
        RelationSpec("aka", "also known as", ("Term",), ()),
    )
}


@dataclass
class Config:
    root: Path
    knowledge_dir: Path
    areas: dict[str, str] = field(default_factory=dict)
    relations: dict[str, RelationSpec] = field(default_factory=lambda: dict(BUILTIN_RELATIONS))
    max_diagram_nodes: int = 25
    sources: dict[str, str] = field(default_factory=dict)  # document path -> default basis
    ambiguity_order: tuple[str, ...] = AMBIGUITY_STEPS

    @property
    def path(self) -> Path:
        return self.root / CONFIG_FILE


def find_root(start: Path) -> Path:
    """Return the nearest directory at or above `start` that holds lore.toml, else `start`."""
    start = start.resolve()
    for candidate in (start, *start.parents):
        if (candidate / CONFIG_FILE).is_file():
            return candidate
    return start


def load_config(root: Path) -> Config:
    path = root / CONFIG_FILE
    data: dict = {}
    if path.is_file():
        data = tomllib.loads(path.read_text(encoding="utf-8"))

    knowledge = data.get("knowledge", {})
    config = Config(root=root, knowledge_dir=root / knowledge.get("dir", "knowledge"))
    config.max_diagram_nodes = int(data.get("diagrams", {}).get("max_nodes", 25))
    config.areas = {
        name: str(area.get("description", "")) for name, area in data.get("areas", {}).items()
    }
    ambiguity = data.get("ambiguity", {})
    order = ambiguity.get("order", list(AMBIGUITY_STEPS)) if isinstance(ambiguity, dict) else None
    if (
        not isinstance(order, list)
        or not order
        or not all(isinstance(step, str) for step in order)
        or len(set(order)) != len(order)
        or not set(order) <= set(AMBIGUITY_STEPS)
    ):
        raise ConfigError(
            f"lore.toml: ambiguity.order must list each of {', '.join(AMBIGUITY_STEPS)} "
            f"at most once, got {order!r}"
        )
    config.ambiguity_order = tuple(order)
    for source in data.get("sources", []):
        config.sources[str(source["path"])] = str(source.get("basis", "intended"))
    for name, spec in data.get("relations", {}).items():
        config.relations[name] = RelationSpec(
            name=name,
            label=str(spec.get("label", name.replace("_", " "))),
            sources=tuple(spec.get("from", ())),
            targets=tuple(spec.get("to", ())),
        )
    return config
