from __future__ import annotations

import shutil
import subprocess

import pytest
import yaml

from domainlore.bundle import load_bundle
from domainlore.check import run_check
from domainlore.config import load_config
from domainlore.convert import convert, load
from domainlore.propose import ProposalError, find, propose
from tests.conftest import EXAMPLE

POLICY = """# Purchase policy

## Thresholds

Every order with a total above
5 000 EUR needs approval.

## Escalation

Undecided requests go to the finance lead.
Undecided requests go to the finance lead.
"""

RULE = {
    "id": "shop/rules/threshold",
    "type": "Rule",
    "title": "Approval threshold",
    "description": "Orders above a total amount need approval.",
    "basis": "intended",
    "body": "# Approval threshold\n\nOrders above 5 000 EUR need approval.[^policy]\n",
    "cites": {
        "policy": {
            "doc": "docs/policy.md",
            "quote": "Every order with a total above 5 000 EUR needs approval.",
        }
    },
}


@pytest.fixture
def converted(project):
    (project.root / "lore.toml").write_text(
        '[knowledge]\ndir = "knowledge"\n[[sources]]\npath = "docs"\nbasis = "intended"\n'
    )
    (project.root / "docs").mkdir()
    (project.root / "docs" / "policy.md").write_text(POLICY)
    convert(load_config(project.root))
    return project


def proposal(project, *pages: dict, title: str = "Facts from the policy"):
    path = project.root / "proposal.yaml"
    path.write_text(yaml.safe_dump({"title": title, "pages": list(pages)}, sort_keys=False))
    return path


def test_find_ignores_line_breaks_and_needs_nth_when_a_quote_repeats():
    start, end = find(POLICY, "total above 5 000 EUR")
    assert POLICY[start:end] == "total above\n5 000 EUR"
    with pytest.raises(ProposalError, match="found 2 times"):
        find(POLICY, "go to the finance lead.")
    second = find(POLICY, "go to the finance lead.", nth=2)
    assert second[0] > find(POLICY, "go to the finance lead.", nth=1)[0]


def test_propose_writes_the_page_with_an_exact_checked_citation(converted):
    config = load_config(converted.root)
    summary = propose(config, proposal(converted, RULE), branch=None)
    page = load_bundle(config.knowledge_dir).concepts["shop/rules/threshold"]
    [source] = page.meta["sources"]
    resource, span = source["resource"].split("#char=")
    start, end = (int(n) for n in span.split(","))
    doc = load(config, "docs/policy.md")
    assert resource == "../docs/policy.md"
    assert " ".join(doc.text[start:end].split()) == RULE["cites"]["policy"]["quote"]
    assert source["version"] == f"sha256:{doc.sha256}"
    assert source["title"] == "policy.md, Purchase policy > Thresholds"
    assert source["basis"] == "intended"
    assert '[^policy]: policy.md, Purchase policy > Thresholds: "Every order' in page.body
    assert "new: `knowledge/shop/rules/threshold.md`" in summary
    assert [i for i in run_check(config) if i.level == "error"] == []


@pytest.mark.parametrize(
    ("cite", "message"),
    [
        ({"doc": "docs/policy.md", "quote": "Orders below 5 EUR are free."}, "quote not found"),
        ({"doc": "notes/other.md", "quote": "x"}, "not under a"),
    ],
    ids=["quote-not-in-document", "document-not-a-source"],
)
def test_a_bad_citation_stops_the_proposal_before_anything_is_written(converted, cite, message):
    page = {**RULE, "cites": {"policy": cite}}
    with pytest.raises(ProposalError, match=message):
        propose(load_config(converted.root), proposal(converted, page), branch=None)
    assert not (converted.root / "knowledge/shop/rules/threshold.md").exists()


def test_a_document_changed_since_convert_cannot_be_cited(converted):
    (converted.root / "docs/policy.md").write_text(POLICY + "\nNew rule.\n")
    with pytest.raises(ProposalError, match="changed since `lore convert`"):
        propose(load_config(converted.root), proposal(converted, RULE), branch=None)


def test_a_proposal_that_breaks_lore_check_is_rolled_back(converted):
    page = {**RULE, "relations": {"governs": ["shop/entities/missing"]}}
    with pytest.raises(ProposalError, match="nothing was kept"):
        propose(load_config(converted.root), proposal(converted, page), branch=None)
    assert not (converted.root / "knowledge/shop/rules/threshold.md").exists()
    assert not (converted.root / "knowledge/shop").exists()


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)


def test_propose_commits_on_a_new_branch(converted):
    root = converted.root
    git(root, "init", "-q", "-b", "main")
    git(
        root,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "start",
    )
    git(root, "config", "user.name", "t")
    git(root, "config", "user.email", "t@t")
    propose(load_config(root), proposal(converted, RULE), branch="lore/policy")
    assert git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "lore/policy"
    assert git(root, "log", "-1", "--format=%s").stdout.strip() == "Proposal: Facts from the policy"
    changed = git(root, "show", "--name-only", "--format=").stdout.split()
    assert "knowledge/shop/rules/threshold.md" in changed


def test_the_demo_proposal_cites_the_planted_spec_conflict_in_both_documents(tmp_path):
    pytest.importorskip("mammoth")
    pytest.importorskip("pypdf")
    root = tmp_path / "demo"
    shutil.copytree(EXAMPLE, root, ignore=shutil.ignore_patterns(".lore"))
    config = load_config(root)
    convert(config)
    propose(config, root / "proposals" / "approval-documents.yaml", branch=None)
    conflict = load_bundle(config.knowledge_dir).concepts["conflicts/approval-threshold-amount"]
    titles = {s["id"]: s["title"] for s in conflict.meta["sources"]}
    assert titles == {
        "rules": "approval-rules.pdf, p. 1",
        "brd": "purchase-approval-brd.docx, Purchase approval BRD > Approval threshold",
    }
    four_eyes = load_bundle(config.knowledge_dir).concepts["approvals/rules/four-eyes"]
    assert four_eyes.meta["verified"]["by"] == "human:demo-reviewer"  # sources added, review kept
    assert [s["id"] for s in four_eyes.meta["sources"]] == ["policy", "brd", "rules"]
    issues = run_check(config)
    assert [i for i in issues if i.level == "error"] == []
    open_conflicts = [i.path for i in issues if i.code == "open-conflict"]
    assert "knowledge/conflicts/approval-threshold-amount.md" in open_conflicts


def test_a_page_with_no_cites_gets_no_empty_sources(converted):
    page = {
        "id": "questions",
        "type": "Open Questions",
        "title": "Open questions",
        "description": "Ambiguities waiting for a person.",
        "body": "# Open questions\n\n- Who decides after 3 days?\n",
    }
    config = load_config(converted.root)
    propose(config, proposal(converted, page), branch=None)
    assert "sources" not in load_bundle(config.knowledge_dir).concepts["questions"].meta


def test_footnotes_quote_the_text_without_markdown_emphasis(converted):
    (converted.root / "docs/policy.md").write_text(POLICY.replace("5 000 EUR", "**5 000 EUR**"))
    config = load_config(converted.root)
    convert(config)
    quote = "Every order with a total above **5 000 EUR** needs approval."
    page = {**RULE, "cites": {"policy": {"doc": "docs/policy.md", "quote": quote}}}
    summary = propose(config, proposal(converted, page), branch=None)
    body = load_bundle(config.knowledge_dir).concepts["shop/rules/threshold"].body
    assert 'Thresholds: "Every order with a total above 5 000 EUR needs approval."' in body
    assert "**" not in summary


REVIEWED = """---
type: Rule
title: Approval threshold
description: Orders above a total amount need approval.
basis: intended
sources:
  - id: wiki
    resource: https://wiki.example.com/approvals
verified: { by: human:reviewer, at: 2026-10-01T09:00:00Z }
---

# Approval threshold

Orders above 5 000 EUR need approval.[^wiki] Undecided requests escalate.

[^wiki]: Approval wiki
"""


@pytest.fixture
def reviewed(converted):
    target = converted.root / "knowledge/shop/rules/threshold.md"
    target.parent.mkdir(parents=True)
    target.write_text(REVIEWED)
    return converted


def test_cites_alone_add_sources_and_keep_the_body_and_the_review(reviewed):
    config = load_config(reviewed.root)
    cites = {**RULE["cites"]["policy"], "after": "Orders above 5 000 EUR need approval."}
    page = {"id": "shop/rules/threshold", "cites": {"policy": cites}}
    summary = propose(config, proposal(reviewed, page), branch=None)
    concept = load_bundle(config.knowledge_dir).concepts["shop/rules/threshold"]
    assert concept.meta["verified"] == {"by": "human:reviewer", "at": REVIEWED_AT}
    assert [s["id"] for s in concept.meta["sources"]] == ["wiki", "policy"]
    assert "need approval.[^wiki][^policy] Undecided" in concept.body
    assert "[^wiki]: Approval wiki\n[^policy]: policy.md" in concept.body
    assert "verified: { by: human:reviewer" in concept.text  # the frontmatter is kept as written
    assert "sources added: `knowledge/shop/rules/threshold.md`" in summary
    assert [i for i in run_check(config) if i.level == "error"] == []


REVIEWED_AT = yaml.safe_load("at: 2026-10-01T09:00:00Z")["at"]


@pytest.mark.parametrize(
    ("cite", "message"),
    [
        ({}, "needs `after`"),
        ({"after": "Orders below 5 EUR are free."}, "`after` in page"),
        ({"id": "wiki", "after": "need approval."}, "already has a source `wiki`"),
    ],
    ids=["no-after", "after-not-in-page", "label-taken"],
)
def test_adding_sources_needs_a_place_in_the_page_and_a_new_label(reviewed, cite, message):
    label = cite.pop("id", "policy")
    page = {"id": "shop/rules/threshold", "cites": {label: {**RULE["cites"]["policy"], **cite}}}
    with pytest.raises(ProposalError, match=message):
        propose(load_config(reviewed.root), proposal(reviewed, page), branch=None)
    assert (reviewed.root / "knowledge/shop/rules/threshold.md").read_text() == REVIEWED


def test_a_proposal_that_replaces_a_reviewed_page_removes_the_review(reviewed):
    config = load_config(reviewed.root)
    page = {**RULE, "verified": {"by": "human:someone", "at": "2026-11-01T00:00:00Z"}}
    summary = propose(config, proposal(reviewed, page), branch=None)
    concept = load_bundle(config.knowledge_dir).concepts["shop/rules/threshold"]
    assert "verified" not in concept.meta
    assert "changed, review removed: `knowledge/shop/rules/threshold.md`" in summary
