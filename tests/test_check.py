from __future__ import annotations

from datetime import UTC, datetime

from domainlore.build import build
from domainlore.check import run_check

ENTITY = """
---
type: Entity
title: Invoice
description: A request for payment.
sources:
  - id: jira
    resource: https://jira.example.com/browse/BIL-1
---

# Invoice

Issued after delivery.[^jira]

[^jira]: BIL-1
"""


def codes(project, level: str = "error") -> list[str]:
    return sorted(i.code for i in run_check(project.config) if i.level == level)


def test_valid_page_passes_after_build(project):
    project.write("billing/entities/invoice.md", ENTITY)
    build(project.config)
    assert codes(project) == []


def test_page_without_frontmatter_breaks_okf(project):
    project.write("billing/notes.md", "# Just notes\n")
    assert "okf-frontmatter" in codes(project)


def test_domain_page_without_sources_is_an_error(project):
    project.write("billing/entities/invoice.md", "---\ntype: Entity\n---\n# Invoice\n")
    assert "no-source" in codes(project)


def test_footnote_must_match_a_source_id(project):
    project.write("billing/entities/invoice.md", ENTITY.replace("[^jira]:", "[^jira2]:"))
    assert "unknown-citation" in codes(project)


def test_unknown_relation_broken_target_and_wrong_type(project):
    project.write(
        "billing/entities/invoice.md",
        ENTITY.replace(
            "sources:",
            "relations:\n  pays: [billing/entities/x]\n  has: [billing/rules/late-fee]\n"
            "  shows: [billing/entities/x]\nsources:",
        ),
    )
    project.write("billing/rules/late-fee.md", ENTITY.replace("type: Entity", "type: Rule"))
    found = codes(project)
    assert "unknown-relation" in found  # pays
    assert "relation-type" in found  # has -> Rule, and shows from an Entity
    assert "broken-relation" in found  # shows -> missing page


def test_custom_relation_from_config(project):
    (project.root / "lore.toml").write_text(
        '[knowledge]\ndir = "knowledge"\n[relations.replaces]\nfrom = ["Entity"]\nto = ["Entity"]\n'
    )
    project.write(
        "billing/entities/invoice.md",
        ENTITY.replace("sources:", "relations:\n  replaces: [billing/entities/bill]\nsources:"),
    )
    project.write("billing/entities/bill.md", ENTITY.replace("Invoice", "Bill"))
    build(project.config)
    assert codes(project) == []


def test_schema_rejects_bad_basis_and_status(project):
    project.write(
        "billing/entities/invoice.md",
        ENTITY.replace("sources:", "basis: maybe\nstatus: final\nsources:"),
    )
    assert codes(project).count("schema") == 2


def test_lifecycle_transitions_must_use_declared_states(project):
    project.write(
        "billing/entities/invoice.md",
        ENTITY.replace(
            "sources:",
            "states: [draft, issued]\ntransitions:\n  - { from: draft, to: paid }\nsources:",
        ),
    )
    assert "lifecycle" in codes(project)


def test_journey_steps_must_reference_screens_and_known_steps(project):
    project.write(
        "billing/journeys/pay.md",
        """
    ---
    type: Journey
    sources: [{ id: s, resource: https://x }]
    steps:
      - { id: a, label: Start, screen: billing/screens/missing, goto: [{ to: z }] }
    ---
    # Pay
    """,
    )
    found = codes(project)
    assert "broken-reference" in found
    assert "journey" in found


def test_conflict_needs_about_and_warns_while_open(project):
    project.write("conflicts/x.md", "---\ntype: Gap\ndescription: d\n---\n# X\n")
    assert "conflict" in codes(project)
    assert "open-conflict" in codes(project, "warning")


def test_resolved_conflict_is_not_reported_as_open(project):
    project.write("billing/entities/invoice.md", ENTITY)
    project.write(
        "conflicts/x.md",
        """
    ---
    type: Gap
    about: [billing/entities/invoice]
    resolution: Fixed in BIL-9
    sources: [{ id: a, resource: https://a }, { id: b, resource: https://b }]
    ---
    # X
    """,
    )
    build(project.config)
    assert "open-conflict" not in codes(project, "warning")


def test_stale_after_in_the_past_warns(project):
    project.write(
        "billing/entities/invoice.md",
        ENTITY.replace("sources:", "stale_after: 2026-01-01T00:00:00Z\nsources:"),
    )
    build(project.config)
    issues = run_check(project.config, now=datetime(2026, 6, 1, tzinfo=UTC))
    assert [i.code for i in issues if i.level == "warning"] == ["stale"]


def test_hand_edit_inside_generated_block_is_caught(project):
    path = project.write(
        "billing/entities/invoice.md",
        ENTITY.replace(
            "sources:",
            "states: [draft, issued]\ntransitions:\n  - { from: draft, to: issued }\nsources:",
        ),
    )
    build(project.config)
    path.write_text(path.read_text().replace("draft --> issued", "draft --> paid"))
    assert "generated" in codes(project)


def test_verified_list_and_timestamps_pass_schema(project):
    project.write(
        "billing/entities/invoice.md",
        ENTITY.replace(
            "sources:",
            "verified:\n  - { by: human:ann, at: 2026-06-25T09:00:00Z }\n"
            "  - { by: process:nightly, at: 2026-06-26T02:00:00Z }\nsources:",
        ),
    )
    build(project.config)
    assert codes(project) == []
