"""The agent extraction test's set-up and scoring, without an agent: a known good result
(the demo Proposal applied to the set-up copy) passes every check, and each defect fails its row."""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import re
import shutil
import subprocess

import pytest

from tests.conftest import EXAMPLE

SCRIPT = EXAMPLE.parents[1] / "evals" / "extract.py"


@pytest.fixture(scope="module")
def extract():
    spec = importlib.util.spec_from_file_location("eval_extract", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def prepared(extract, tmp_path_factory):
    """A set-up copy with the demo Proposal applied on a lore/ branch, as a good run leaves it."""
    for module in ("mammoth", "pypdf"):  # in CI a missing extra fails, not skips
        importlib.import_module(module) if os.environ.get("CI") else pytest.importorskip(module)
    root = tmp_path_factory.mktemp("extract") / "copy"
    extract.setup(root)
    proposal = root / ".lore" / "proposals" / "approval-documents.yaml"
    proposal.parent.mkdir(parents=True)
    shutil.copy(EXAMPLE / "proposals" / "approval-documents.yaml", proposal)
    lore = extract.lore_bin()
    for args in (["convert"], ["propose", str(proposal), "--branch", "lore/approval-documents"]):
        subprocess.run([lore, *args], cwd=root, check=True, capture_output=True)
    return root


@pytest.fixture
def run(prepared, tmp_path):
    """A fresh copy of the good result and the tool calls of a good transcript."""
    root = tmp_path / "copy"
    shutil.copytree(prepared, root)
    proposal = str(root / ".lore" / "proposals" / "approval-documents.yaml")
    uses = [
        ("Skill", {"skill": "lore-extract"}),
        ("Write", {"file_path": proposal}),
        ("Bash", {"command": f"lore propose {proposal}"}),
    ]
    return root, uses


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def score(extract, root, uses, tmp_path):
    transcript = tmp_path / "run.jsonl"
    content = [{"type": "tool_use", "name": n, "input": i} for n, i in uses]
    events = [{"type": "assistant", "message": {"content": content}}, {"type": "result"}]
    transcript.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    rows, _ = extract.checks(root, transcript)
    return {name.split(" (")[0]: ok for name, ok in rows}


def test_setup_removes_the_planted_conflict_and_the_amounts(extract, tmp_path):
    root = tmp_path / "copy"
    extract.setup(root)
    assert not (root / extract.CONFLICT).exists()
    assert not re.search(r"\d+ 000 EUR", (root / extract.THRESHOLD).read_text())
    assert (root / ".claude/skills/lore-extract/SKILL.md").is_file()


def test_a_good_run_passes_every_check(extract, run, tmp_path):
    rows = score(extract, *run, tmp_path)
    assert all(rows.values()), rows


def use_other_skill(root, uses):
    uses[0] = ("Skill", {"skill": "lore-use"})


def edit_knowledge(root, uses):
    uses.append(("Edit", {"file_path": str(root / "knowledge/questions.md")}))


def shell_write(root, uses):
    uses.append(("Bash", {"command": "cat >> knowledge/questions.md <<EOF\n- more\nEOF"}))


def leave_uncommitted(root, uses):
    with (root / "knowledge/questions.md").open("a") as file:
        file.write("\n- An extra question.\n")


def commit_by_hand(root, uses):
    leave_uncommitted(root, uses)
    git(root, "commit", "-qam", "Add a question")


def remove_a_review(root, uses):
    page = root / "knowledge/approvals/rules/four-eyes.md"
    page.write_text(re.sub(r"(?m)^verified:.*\n", "", page.read_text()))
    git(root, "commit", "-qam", "Proposal: drop the review")


def shift_a_span(root, uses):
    page = root / "knowledge" / "conflicts" / "approval-threshold-amount.md"
    text = page.read_text()
    a, b = map(int, re.search(r"#char=(\d+),(\d+)", text).groups())
    page.write_text(text.replace(f"#char={a},{b}", f"#char={a + 1},{b + 1}", 1))


def break_a_span(root, uses):
    page = root / "knowledge" / "conflicts" / "approval-threshold-amount.md"
    page.write_text(re.sub(r"#char=\d+,\d+", "#char=x", page.read_text(), count=1))


def delete_a_reviewed_page(root, uses):
    git(root, "rm", "-q", "knowledge/approvals/rules/four-eyes.md")
    git(root, "commit", "-qm", "Proposal: drop four-eyes")


def remove_the_conflict(root, uses):
    git(root, "rm", "-q", "knowledge/conflicts/approval-threshold-amount.md")
    git(root, "commit", "-qm", "Proposal: no conflict")


@pytest.mark.parametrize(
    ("defect", "row"),
    [
        (use_other_skill, "used the lore-extract skill"),
        (edit_knowledge, "wrote only in .lore/proposals/"),
        (shell_write, "wrote only in .lore/proposals/"),
        (leave_uncommitted, "knowledge/ changed only by Proposal commits on a lore/ branch"),
        (commit_by_hand, "knowledge/ changed only by Proposal commits on a lore/ branch"),
        (remove_a_review, "no review removed"),
        (shift_a_span, "document spans verified"),
        (break_a_span, "document spans verified"),
        (delete_a_reviewed_page, "no review removed"),
        (remove_the_conflict, "planted Spec Conflict found"),
    ],
    ids=lambda v: v.__name__ if callable(v) else "",
)
def test_each_defect_fails_its_check(extract, run, tmp_path, defect, row):
    root, uses = run
    defect(root, uses)
    assert score(extract, root, uses, tmp_path)[row] is False


def test_reads_and_relative_proposal_paths_are_not_writes(extract, run, tmp_path):
    root, uses = run
    uses += [
        ("Write", {"file_path": ".lore/proposals/approval-documents.yaml"}),
        ("Bash", {"command": "cp knowledge/questions.md .lore/proposals/q.md"}),
        ("Bash", {"command": "lore check > .lore/check.txt"}),
    ]
    assert score(extract, root, uses, tmp_path)["wrote only in .lore/proposals/"] is True
