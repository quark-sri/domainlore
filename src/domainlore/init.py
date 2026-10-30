"""`lore init`: set up a project to hold a Knowledge Base. Safe to run again."""

from __future__ import annotations

import re
from importlib import resources
from pathlib import Path

from .config import CONFIG_FILE

START = "<!-- domainlore:start -->"
END = "<!-- domainlore:end -->"

DEFAULT_CONFIG = """\
# domainlore configuration. See https://github.com/quark-sri/domainlore
[knowledge]
dir = "knowledge"

[diagrams]
max_nodes = 25

# Describe each Area (a bounded context); the folder name is the key.
# [areas.ordering]
# description = "Placing and tracking customer orders"

# Extra relation types, beyond the built-in ones.
# [relations.replaces]
# label = "replaces"
# from = ["Entity"]
# to = ["Entity"]
"""

QUESTIONS = """\
---
type: Open Questions
title: Open questions
description: Ambiguities that neither the Sources nor the code settle, waiting for a person.
---

# Open questions

Add one item per question. Link the pages it affects and say who can answer it.
When it is answered, update the pages, cite the answer as a Source and remove the item.
"""

LOG = """\
# Knowledge Base update log
"""


def pointer_block(knowledge_dir: str) -> str:
    return f"""{START}
## Domain knowledge

Business domain facts live in `{knowledge_dir}/` (OKF v0.2 markdown, built with domainlore).

- Start at `{knowledge_dir}/index.md`; open only the Area and pages you need.
- Each page cites its Sources. Prefer `human-reviewed` facts; treat `unverified` ones as hints.
- `basis: intended` = what the product should do; `basis: actual` = what it does.
- Check open Gaps and Spec Conflicts (listed in the index) before you write tests or code.
- For cross-cutting questions run `lore query "<question>"`,
  `lore explain <page>` or `lore path <a> <b>`.
- Do not edit generated blocks or files; change frontmatter and run `lore build`.
{END}
"""


def upsert_block(path: Path, block: str, create: bool) -> bool:
    """Insert or replace the domainlore block. Returns True if the file changed."""
    if not path.exists():
        if not create:
            return False
        path.write_text(block, encoding="utf-8")
        return True
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\n?", re.DOTALL)
    updated = (
        pattern.sub(lambda _: block, text)
        if pattern.search(text)
        else text.rstrip("\n") + "\n\n" + block
    )
    if updated != text:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def ensure_gitignore(root: Path) -> bool:
    path = root / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if any(line.strip() in (".lore/", ".lore") for line in text.splitlines()):
        return False
    path.write_text(
        text + ("" if text.endswith("\n") or not text else "\n") + ".lore/\n", encoding="utf-8"
    )
    return True


def init(root: Path, knowledge: str = "knowledge", cursor: bool = False) -> list[str]:
    """Create config, folders and agent pointers. Returns a list of what changed."""
    changes: list[str] = []
    config = DEFAULT_CONFIG.replace('dir = "knowledge"', f'dir = "{knowledge}"')
    if write_if_missing(root / CONFIG_FILE, config):
        changes.append(f"created {CONFIG_FILE}")
    kdir = root / knowledge
    if write_if_missing(kdir / "questions.md", QUESTIONS):
        changes.append(f"created {knowledge}/questions.md")
    if write_if_missing(kdir / "log.md", LOG):
        changes.append(f"created {knowledge}/log.md")
    if ensure_gitignore(root):
        changes.append("added .lore/ to .gitignore")
    block = pointer_block(knowledge)
    if upsert_block(root / "AGENTS.md", block, create=True):
        changes.append("updated AGENTS.md")
    if upsert_block(root / "CLAUDE.md", block, create=False):
        changes.append("updated CLAUDE.md")
    if cursor:
        rule = (
            resources.files("domainlore")
            .joinpath("adapters/cursor.mdc")
            .read_text(encoding="utf-8")
        )
        target = root / ".cursor" / "rules" / "domainlore.mdc"
        if not target.exists() or target.read_text(encoding="utf-8") != rule:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rule, encoding="utf-8")
            changes.append("wrote .cursor/rules/domainlore.mdc")
    return changes
