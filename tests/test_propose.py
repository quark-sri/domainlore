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
    issues = run_check(config)
    assert [i for i in issues if i.level == "error"] == []
    open_conflicts = [i.path for i in issues if i.code == "open-conflict"]
    assert "knowledge/conflicts/approval-threshold-amount.md" in open_conflicts
