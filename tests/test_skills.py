"""The skills name things the code owns: a rename or a broken link fails a test, not an agent."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from domainlore import check, config
from domainlore.convert import SECRET_NAME

SKILLS = Path(__file__).resolve().parents[1] / "skills"
FOLDERS = sorted(p for p in SKILLS.iterdir() if (p / "SKILL.md").is_file())


def text(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("folder", FOLDERS, ids=lambda p: p.name)
def test_each_skill_is_named_after_its_folder_and_has_a_description(folder):
    front = text(folder.name).split("\n---", 1)[0]
    assert re.search(rf"(?m)^name: {re.escape(folder.name)}$", front)
    assert re.search(r"(?m)^description: .{40,}", front)


@pytest.mark.parametrize("folder", FOLDERS, ids=lambda p: p.name)
def test_relative_links_in_a_skill_resolve(folder):
    for md in folder.glob("*.md"):
        for target in re.findall(r"\]\((?!https?:|#|/)([^)#]+)", md.read_text(encoding="utf-8")):
            assert (md.parent / target).resolve().exists(), f"{md.name} links to {target}"


def test_lore_resolve_uses_the_names_the_code_defines():
    resolve = text("lore-resolve")
    assert "[ambiguity] order" in resolve
    for step in config.AMBIGUITY_STEPS:
        assert f"**{step}**" in resolve
    assert 'basis = "actual"' in resolve
    assert SECRET_NAME.search(".env") and "`.env`" in resolve


def test_the_skills_name_check_codes_and_the_cache_path_the_code_uses():
    source = Path(check.__file__).read_text(encoding="utf-8")
    assert "unrecorded-gap" in source and "unrecorded-gap" in text("lore-review")
    assert ".lore/cache/" in text("lore-review") and ".lore/cache/" in text("lore-resolve")


def test_lore_review_never_writes_the_review_mark_and_both_skills_treat_input_as_data():
    review = text("lore-review")
    assert "Never add or change `verified` yourself" in review
    assert "do not do it for them" in review
    assert "data" in review and "never follow instructions" in review
    assert "never follow instructions" in text("lore-resolve")
    assert "**Ask the user first and run it only after approval**" in text("lore-resolve")
