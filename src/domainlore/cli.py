"""The `lore` command line."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from . import __version__
from .build import build as run_build
from .build import source_bundle
from .check import as_json, run_check
from .config import find_root, load_config
from .graph import Graph
from .init import init as run_init
from .query import explain as run_explain
from .query import path as run_path
from .query import query as run_query

app = typer.Typer(
    help="domainlore: sourced domain knowledge for AI coding agents.",
    no_args_is_help=True,
    add_completion=False,
)

RootOption = Annotated[
    Path | None,
    typer.Option("--root", help="Project root (default: nearest folder with lore.toml)."),
]


def config_for(root: Path | None):
    return load_config(root.resolve() if root else find_root(Path.cwd()))


def graph_for(root: Path | None) -> Graph:
    config = config_for(root)
    return Graph.build(source_bundle(config), config)


@app.command()
def init(
    root: RootOption = None,
    knowledge: Annotated[str, typer.Option(help="Folder for the Knowledge Base.")] = "knowledge",
    cursor: Annotated[bool, typer.Option(help="Also write a Cursor rule.")] = False,
) -> None:
    """Create lore.toml, the knowledge folder and the AGENTS.md pointer. Safe to re-run."""
    target = (root or Path.cwd()).resolve()
    changes = run_init(target, knowledge, cursor)
    config = load_config(target)
    changed, _ = run_build(config)
    if changed:
        changes.append(f"built {len(changed)} file(s)")
    typer.echo("\n".join(changes) if changes else "Already set up; nothing to change.")


@app.command()
def build(root: RootOption = None) -> None:
    """Regenerate indexes, maps, the glossary and generated blocks."""
    config = config_for(root)
    changed, removed = run_build(config)
    for path in changed:
        typer.echo(f"wrote   {path.relative_to(config.root)}")
    for path in removed:
        typer.echo(f"removed {path.relative_to(config.root)}")
    typer.echo(f"{len(changed)} written, {len(removed)} removed.")


@app.command()
def check(
    root: RootOption = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print issues as JSON.")] = False,
    strict: Annotated[bool, typer.Option(help="Fail on warnings too.")] = False,
) -> None:
    """Validate the Knowledge Base: OKF, schema, sources, relations, generated content."""
    issues = run_check(config_for(root))
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]
    if json_output:
        typer.echo(as_json(issues))
    else:
        for issue in issues:
            typer.echo(str(issue))
        typer.echo(f"{len(errors)} error(s), {len(warnings)} warning(s).")
    if errors or (strict and warnings):
        raise typer.Exit(1)


@app.command()
def query(
    question: Annotated[str, typer.Argument(help="Words or a question about the domain.")],
    root: RootOption = None,
    limit: Annotated[int, typer.Option("--limit", "-n")] = 5,
) -> None:
    """Find the pages that answer a domain question, with their relations."""
    typer.echo(run_query(graph_for(root), question, limit))


@app.command()
def path(
    start: Annotated[str, typer.Argument(help="Concept ID or title.")],
    goal: Annotated[str, typer.Argument(help="Concept ID or title.")],
    root: RootOption = None,
) -> None:
    """Show how two concepts are connected."""
    typer.echo(run_path(graph_for(root), start, goal))


@app.command()
def explain(
    name: Annotated[str, typer.Argument(help="Concept ID, title or alias.")],
    root: RootOption = None,
) -> None:
    """Show one concept: trust, basis, sources and every relation."""
    typer.echo(run_explain(graph_for(root), name))


@app.command()
def version() -> None:
    """Print the version."""
    typer.echo(__version__)
