from __future__ import annotations

import pytest
from typer.testing import CliRunner

from domainlore.cli import app
from domainlore.config import AMBIGUITY_STEPS, ConfigError, load_config


def write(project, extra: str) -> None:
    (project.root / "lore.toml").write_text('[knowledge]\ndir = "knowledge"\n' + extra)


def test_the_ambiguity_order_defaults_to_sources_code_ask(project):
    assert (
        load_config(project.root).ambiguity_order == AMBIGUITY_STEPS == ("sources", "code", "ask")
    )


def test_a_team_can_set_the_ambiguity_order(project):
    write(project, '[ambiguity]\norder = ["sources", "ask", "code"]\n')
    assert load_config(project.root).ambiguity_order == ("sources", "ask", "code")


@pytest.mark.parametrize(
    "order",
    ['order = ["sources", "guess"]', "order = []", 'order = ["ask", "ask"]', 'order = "ask"']
    + ["order = [[1]]", "order = [1, 2]"],
    ids=["unknown-step", "empty", "repeated", "not-a-list", "nested-list", "numbers"],
)
def test_a_bad_ambiguity_order_is_refused_with_the_valid_steps(project, order):
    write(project, f"[ambiguity]\n{order}\n")
    with pytest.raises(ConfigError, match="sources, code, ask"):
        load_config(project.root)


def test_ambiguity_must_be_a_table(project):
    write(project, "")
    (project.root / "lore.toml").write_text("ambiguity = 1\n[knowledge]\ndir = 'knowledge'\n")
    with pytest.raises(ConfigError, match="ambiguity.order"):
        load_config(project.root)


@pytest.mark.parametrize("command", [["check"], ["build"], ["convert"], ["query", "order"]])
def test_every_command_reports_a_bad_ambiguity_order_with_exit_2(project, command):
    write(project, '[ambiguity]\norder = ["guess"]\n')
    result = CliRunner().invoke(app, [*command, "--root", str(project.root)])
    assert result.exit_code == 2
    assert "ambiguity.order" in result.output
