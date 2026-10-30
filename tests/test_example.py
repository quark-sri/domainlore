"""The demo product is the golden fixture: its committed output must equal a fresh build."""

from __future__ import annotations

from domainlore.build import build, render
from domainlore.check import run_check
from domainlore.config import load_config
from tests.conftest import EXAMPLE


def test_committed_example_is_current_and_valid():
    issues = run_check(load_config(EXAMPLE))
    errors = [str(i) for i in issues if i.level == "error"]
    assert errors == []


def test_planted_conflicts_are_reported():
    issues = run_check(load_config(EXAMPLE))
    open_conflicts = sorted(i.path for i in issues if i.code == "open-conflict")
    assert open_conflicts == [
        "knowledge/conflicts/approval-threshold-amount.md",
        "knowledge/conflicts/cancel-without-confirmation.md",
        "knowledge/conflicts/no-inbox-link-on-order-details.md",
    ]


def test_build_is_idempotent(example):
    build(example)
    changed, removed = build(example)
    assert (changed, removed) == ([], [])


def test_render_matches_committed_files():
    config = load_config(EXAMPLE)
    for path, content in render(config).items():
        assert path.read_text(encoding="utf-8") == content, path
