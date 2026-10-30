from __future__ import annotations

from domainlore.build import build, set_blocks
from domainlore.bundle import load_bundle
from domainlore.config import load_config
from domainlore.graph import Graph, trust_tier

SCREEN = """
---
type: Screen
title: {title}
description: {title} page.
basis: {basis}
sources: [{{ id: s, resource: https://app/{slug} }}]
relations:
  navigates_to: [{targets}]
---
# {title}
"""


def screen(project, slug: str, targets: str = "", basis: str = "actual") -> None:
    project.write(
        f"shop/screens/{slug}.md",
        SCREEN.format(title=slug.title(), slug=slug, basis=basis, targets=targets),
    )


def test_set_blocks_inserts_replaces_and_drops():
    text = "# Page\n"
    once = set_blocks(text, {"a": "<!-- generated:start a -->\nA\n<!-- generated:end a -->\n"})
    assert once.endswith("<!-- generated:end a -->\n")
    twice = set_blocks(once, {"a": "<!-- generated:start a -->\nB\n<!-- generated:end a -->\n"})
    assert "\nB\n" in twice and "\nA\n" not in twice
    assert set_blocks(twice, {}) == "# Page\n"


def test_indexes_and_area_map_are_generated(project):
    screen(project, "cart", "shop/screens/checkout")
    screen(project, "checkout", "", basis="intended")
    build(project.config)
    root = project.root / "knowledge"
    assert (root / "index.md").read_text().startswith('---\nokf_version: "0.2"\n---')
    area_index = (root / "shop" / "index.md").read_text()
    assert "* [Cart](screens/cart.md) - Cart page. _(unverified)_" in area_index
    assert "# Map" in area_index
    nav = (root / "shop" / "map.md").read_text()
    assert "linkStyle 0 stroke:#e67e00" in nav  # actual-only edge is orange
    assert "class n_shop_screens_cart,n_shop_screens_checkout unverified" in nav


def test_intended_only_edge_is_dashed(project):
    screen(project, "cart", "shop/screens/checkout", basis="intended")
    screen(project, "checkout")
    build(project.config)
    nav = (project.root / "knowledge" / "shop" / "map.md").read_text()
    assert "n_shop_screens_cart -.->" in nav


def test_large_navigation_is_split_into_parts(project):
    (project.root / "lore.toml").write_text(
        '[knowledge]\ndir = "knowledge"\n[diagrams]\nmax_nodes = 3\n'
    )
    for i in range(5):
        screen(project, f"s{i}", f"shop/screens/s{i + 1}" if i < 4 else "")
    build(project.config)
    nav = (project.root / "knowledge" / "shop" / "map.md").read_text()
    assert "_Part 1 of 2_" in nav and "_Part 2 of 2_" in nav
    assert "Links between parts:" in nav


def test_generated_pages_are_removed_when_no_longer_needed(project):
    screen(project, "cart")
    build(project.config)
    (project.root / "knowledge" / "shop" / "screens" / "cart.md").unlink()
    _, removed = build(project.config)
    names = sorted(p.relative_to(project.root).as_posix() for p in removed)
    assert names == [
        "knowledge/map.md",
        "knowledge/shop/index.md",
        "knowledge/shop/map.md",
        "knowledge/shop/screens/index.md",
    ]
    assert not (project.root / "knowledge" / "shop").exists()


def test_trust_tier_follows_okf():
    class C:
        def __init__(self, verified):
            self.meta = {"verified": verified} if verified is not None else {}

    assert trust_tier(C(None)) == "unverified"
    assert trust_tier(C({"by": "process:crawl"})) == "machine-confirmed"
    assert trust_tier(C([{"by": "process:x"}, {"by": "human:ann"}])) == "human-reviewed"


def test_declared_edge_wins_over_implied(project):
    project.write(
        "shop/rules/limit.md",
        """
    ---
    type: Rule
    sources: [{ id: s, resource: https://x }]
    relations:
      governs: [{ to: shop/entities/order, basis: intended }]
    ---
    # Limit
    """,
    )
    project.write(
        "shop/entities/order.md",
        """
    ---
    type: Entity
    sources: [{ id: s, resource: https://x }]
    states: [a, b]
    transitions: [{ from: a, to: b, governed_by: [shop/rules/limit] }]
    ---
    # Order
    """,
    )
    config = load_config(project.root)
    graph = Graph.build(load_bundle(config.knowledge_dir), config)
    [edge] = [e for e in graph.edges if e.rel == "governs"]
    assert not edge.implied and edge.basis_label == "intended"


def test_journey_step_with_empty_goto_ends_the_flow(project):
    project.write(
        "shop/journeys/buy.md",
        """
    ---
    type: Journey
    sources: [{ id: s, resource: https://x }]
    steps:
      - { id: pay, label: Pay, goto: [{ to: failed, when: card declined }, { to: done }] }
      - { id: failed, label: See error, goto: [] }
      - { id: done, label: See receipt }
    ---
    # Buy
    """,
    )
    build(project.config)
    flow = (project.root / "knowledge" / "shop" / "journeys" / "buy.md").read_text()
    assert 'n_pay -->|"card declined"| n_failed' in flow and "n_pay --> n_done" in flow
    assert "n_failed -->" not in flow
