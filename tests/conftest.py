from __future__ import annotations

import shutil
import textwrap
from pathlib import Path

import pytest

from domainlore.config import Config, load_config

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "order-approval"


def page(text: str) -> str:
    return textwrap.dedent(text).lstrip("\n")


@pytest.fixture
def project(tmp_path: Path):
    """A writable project with lore.toml and an empty knowledge folder."""

    class Project:
        root = tmp_path

        def write(self, rel: str, text: str) -> Path:
            path = tmp_path / "knowledge" / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(page(text), encoding="utf-8")
            return path

        @property
        def config(self) -> Config:
            return load_config(tmp_path)

    (tmp_path / "lore.toml").write_text('[knowledge]\ndir = "knowledge"\n', encoding="utf-8")
    (tmp_path / "knowledge").mkdir()
    return Project()


@pytest.fixture
def example(tmp_path: Path) -> Config:
    """A writable copy of the demo product's Knowledge Base."""
    target = tmp_path / "order-approval"
    shutil.copytree(EXAMPLE, target, ignore=shutil.ignore_patterns(".lore"))
    return load_config(target)
