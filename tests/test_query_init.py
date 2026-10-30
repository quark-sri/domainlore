from __future__ import annotations

from typer.testing import CliRunner

from domainlore.build import source_bundle
from domainlore.cli import app
from domainlore.config import load_config
from domainlore.graph import Graph
from domainlore.init import END, START, init
from domainlore.query import explain, path, query, stem
from tests.conftest import EXAMPLE


def example_graph() -> Graph:
    config = load_config(EXAMPLE)
    return Graph.build(source_bundle(config), config)


def test_stem_joins_word_forms():
    assert stem("approves") == stem("approver") == stem("approval") == "approv"


def test_query_ranks_the_matching_rule_first():
    first = query(example_graph(), "minimum order value").splitlines()[0]
    assert first.startswith("ordering/rules/minimum-order-value")


def test_term_resolves_to_its_node():
    assert explain(example_graph(), "PO").startswith("ordering/entities/order ")


def test_path_crosses_areas():
    out = path(example_graph(), "Buyer", "Approval inbox")
    assert out.splitlines()[0] == "Buyer (ordering/actors/buyer)"
    assert out.splitlines()[-1].endswith("Approval inbox (approvals/screens/approval-inbox)")


def test_init_is_idempotent_and_keeps_existing_text(tmp_path):
    (tmp_path / "AGENTS.md").write_text("# Project rules\n\nUse tabs.\n")
    (tmp_path / "CLAUDE.md").write_text("Be brief.\n")
    first = init(tmp_path)
    assert "updated AGENTS.md" in first and "updated CLAUDE.md" in first
    assert init(tmp_path) == []
    agents = (tmp_path / "AGENTS.md").read_text()
    assert agents.startswith("# Project rules\n\nUse tabs.\n")
    assert agents.count(START) == 1 and agents.count(END) == 1
    assert (tmp_path / ".gitignore").read_text() == ".lore/\n"


def test_init_does_not_create_claude_md(tmp_path):
    init(tmp_path)
    assert not (tmp_path / "CLAUDE.md").exists()


def test_cli_init_build_check(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["init", "--root", str(tmp_path), "--cursor"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".cursor" / "rules" / "domainlore.mdc").exists()
    result = runner.invoke(app, ["check", "--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    (tmp_path / "knowledge" / "bad.md").write_text("no frontmatter\n")
    result = runner.invoke(app, ["check", "--root", str(tmp_path), "--json"])
    assert result.exit_code == 1
    assert '"okf-frontmatter"' in result.output
