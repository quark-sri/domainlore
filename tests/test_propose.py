from __future__ import annotations

import re
import shutil
import subprocess

import pytest
import yaml

from domainlore.bundle import load_bundle, split_frontmatter
from domainlore.check import run_check
from domainlore.config import load_config
from domainlore.convert import convert, load
from domainlore.propose import ProposalError, find, propose, render
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
    summary = propose(config, root / "proposals" / "approval-documents.yaml", branch=None)
    assert "New and changed pages are unverified" in summary  # a new conflict page
    assert "keep their review" in summary  # four-eyes: sources added
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
REVIEWED_AT = yaml.safe_load("at: 2026-10-01T09:00:00Z")["at"]


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
    assert "keep their review: check that each new quote supports" in summary
    assert "New and changed pages are unverified" not in summary
    assert [i for i in run_check(config) if i.level == "error"] == []


@pytest.mark.parametrize(
    ("cite", "message"),
    [
        ({}, "needs `after`"),
        ({"after": "Orders below 5 EUR are free."}, "`after` is not in the page text"),
        ({"after": "Approval wiki"}, "`after` is not in the page text"),  # only in a footnote
        ({"after": "need approva"}, "`after` is not in the page text"),  # not a whole word
        ({"id": "wiki", "after": "need approval."}, "already has a source `wiki`"),
    ],
    ids=["no-after", "after-not-in-page", "after-only-in-footnotes", "part-word", "label-taken"],
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
    assert "changed, review removed, `verified` in the Proposal ignored: `knowledge/" in summary
    assert "New and changed pages are unverified" in summary


def test_verified_in_a_proposal_is_ignored_on_a_new_page(converted):
    config = load_config(converted.root)
    page = {**RULE, "verified": {"by": "human:someone", "at": "2026-11-01T00:00:00Z"}}
    summary = propose(config, proposal(converted, page), branch=None)
    assert "verified" not in load_bundle(config.knowledge_dir).concepts["shop/rules/threshold"].meta
    assert "new, `verified` in the Proposal ignored: `knowledge/shop/rules/threshold.md`" in summary


def test_after_that_appears_twice_is_refused(reviewed):
    target = reviewed.root / "knowledge/shop/rules/threshold.md"
    twice = REVIEWED.replace("requests escalate.", "requests escalate. Orders need approval.")
    target.write_text(twice)
    cites = {**RULE["cites"]["policy"], "after": "need approval."}
    page = {"id": "shop/rules/threshold", "cites": {"policy": cites}}
    with pytest.raises(ProposalError, match="`after` appears 2 times; make it longer"):
        propose(load_config(reviewed.root), proposal(reviewed, page), branch=None)
    assert target.read_text() == twice


@pytest.mark.parametrize(
    "extra",
    [{"description": "New text."}, {"cites": {}}, {"cites": None}],
    ids=["other-field", "no-cites", "empty-cites"],
)
def test_a_page_without_a_body_needs_only_id_and_cites(reviewed, extra):
    cites = {**RULE["cites"]["policy"], "after": "need approval."}
    page = {"id": "shop/rules/threshold", "cites": {"policy": cites}, **extra}
    if extra.get("cites", 1) is None:
        del page["cites"]
    with pytest.raises(ProposalError, match="give a `body` to write the page, or only `id`"):
        propose(load_config(reviewed.root), proposal(reviewed, page), branch=None)
    assert (reviewed.root / "knowledge/shop/rules/threshold.md").read_text() == REVIEWED


def test_cites_alone_need_an_existing_page(converted):
    cites = {**RULE["cites"]["policy"], "after": "need approval."}
    page = {"id": "shop/rules/missing", "cites": {"policy": cites}}
    with pytest.raises(ProposalError, match="does not exist; a new page needs a `body`"):
        propose(load_config(converted.root), proposal(converted, page), branch=None)


WIKI = "sources:\n  - id: wiki\n    resource: https://wiki.example.com/approvals\n"
NO_WIKI = (
    REVIEWED.replace(WIKI, "").replace(".[^wiki]", ".").replace("\n[^wiki]: Approval wiki\n", "")
)
GENERATED = (
    "\n<!-- generated:start relations -->\n## Relations\n\n- x\n<!-- generated:end relations -->\n"
)


def without_policy(body: str) -> str:
    """The body with the added footnote removed, blank lines collapsed."""
    kept = [line for line in body.splitlines() if not line.startswith("[^policy]:")]
    body = "\n".join(kept).replace("[^policy]", "")
    return re.sub(r"\n{3,}", "\n\n", body).strip()


@pytest.mark.parametrize(
    "text",
    [
        NO_WIKI,
        NO_WIKI.replace("basis: intended\n", "basis: intended\nsources: []\n"),
        REVIEWED.replace(
            WIKI, "sources: [{id: wiki, resource: 'https://wiki.example.com/approvals'}]\n"
        ),
        REVIEWED + GENERATED,
    ],
    ids=["no-sources-key", "empty-flow-list", "flow-list", "generated-block"],
)
def test_adding_sources_keeps_the_review_and_the_text_in_any_layout(reviewed, text):
    target = reviewed.root / "knowledge/shop/rules/threshold.md"
    target.write_text(text)
    config = load_config(reviewed.root)
    cites = {**RULE["cites"]["policy"], "after": "need approval."}
    page = {"id": "shop/rules/threshold", "cites": {"policy": cites}}
    _, new, _, kind = render(config, page)
    meta, body, _ = split_frontmatter(new)
    old_meta, old_body, _ = split_frontmatter(text)
    assert kind == "sources added"
    assert meta["verified"] == old_meta["verified"]
    added = meta["sources"][-1]
    assert added["id"] == "policy" and added["resource"].startswith("../docs/policy.md#char=")
    assert meta == {**old_meta, "sources": (old_meta.get("sources") or []) + [added]}
    assert "need approval.[^policy]" in body or "need approval.[^wiki][^policy]" in body
    assert without_policy(body) == without_policy(old_body)
    if GENERATED in text:  # footnotes stay above the generated block
        assert body.index("[^policy]: ") < body.index("<!-- generated:start relations -->")
    propose(config, proposal(reviewed, page), branch=None)
    assert [i for i in run_check(config) if i.level == "error"] == []


def test_two_cites_after_the_same_text_keep_their_order(reviewed):
    escalation = {"doc": "docs/policy.md", "quote": "Undecided requests go to the finance lead."}
    cites = {
        "policy": {**RULE["cites"]["policy"], "after": "need approval."},
        "esc": {**escalation, "nth": 1, "after": "need approval."},
    }
    config = load_config(reviewed.root)
    propose(config, proposal(reviewed, {"id": "shop/rules/threshold", "cites": cites}), branch=None)
    body = load_bundle(config.knowledge_dir).concepts["shop/rules/threshold"].body
    assert "need approval.[^wiki][^policy][^esc] Undecided" in body


def test_a_quote_from_code_is_cited_by_its_lines_with_the_actual_basis(project):
    (project.root / "lore.toml").write_text(
        '[knowledge]\ndir = "knowledge"\n[[sources]]\npath = "src"\nbasis = "actual"\n'
    )
    (project.root / "src").mkdir()
    (project.root / "src" / "rules.py").write_text("# Limits\nLIMIT = 10_000  # EUR\n\nOTHER = 1\n")
    config = load_config(project.root)
    convert(config)
    page = {
        **RULE,
        "id": "shop/rules/code-limit",
        "basis": "actual",
        "body": "# Limit in the code\n\nThe code sets the limit to 10 000.[^code]\n",
        "cites": {"code": {"doc": "src/rules.py", "quote": "LIMIT = 10_000  # EUR"}},
    }
    propose(config, proposal(project, page), branch=None)
    concept = load_bundle(config.knowledge_dir).concepts["shop/rules/code-limit"]
    [source] = concept.meta["sources"]
    assert source["title"] == "rules.py, line 2" and source["basis"] == "actual"
    assert source["resource"].startswith("../src/rules.py#char=")
    assert '[^code]: rules.py, line 2: "LIMIT = 10_000 # EUR"' in concept.body  # spaces collapse
    assert [i for i in run_check(config) if i.level == "error"] == []


def source_title(project, doc: str, text: str, quote: str, basis: str = "intended") -> str:
    folder = doc.split("/")[0]
    (project.root / "lore.toml").write_text(
        f'[knowledge]\ndir = "knowledge"\n[[sources]]\npath = "{folder}"\nbasis = "{basis}"\n'
    )
    (project.root / folder).mkdir(exist_ok=True)
    (project.root / doc).write_text(text)
    config = load_config(project.root)
    convert(config)
    page = {**RULE, "cites": {"policy": {"doc": doc, "quote": quote}}}
    propose(config, proposal(project, page), branch=None)
    concept = load_bundle(config.knowledge_dir).concepts["shop/rules/threshold"]
    return concept.meta["sources"][0]["title"]


@pytest.mark.parametrize(
    ("doc", "text", "quote", "title"),
    [
        (
            "src/rules.py",
            "# Limits\nLIMIT = 10_000\nLOW = 1\nOTHER = 2\n",
            "LIMIT = 10_000 LOW = 1",
            "rules.py, lines 2-3",
        ),
        (
            "docs/p.md",
            "Intro line.\n\n# Rules\n\nOrders above 5 000 EUR need approval.\n",
            "above 5 000 EUR",
            "p.md, Rules",
        ),
        (
            "docs/p.md",
            "Orders above 5 000 EUR need approval.\n\n# Rules\n",
            "above 5 000 EUR",
            "p.md, line 1",
        ),
    ],
    ids=["code-two-lines", "section-wins", "before-any-heading"],
)
def test_the_source_title_names_the_section_else_the_lines(project, doc, text, quote, title):
    basis = "actual" if doc.startswith("src") else "intended"
    assert source_title(project, doc, text, quote, basis) == title
