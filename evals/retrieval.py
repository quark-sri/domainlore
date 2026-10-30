"""Retrieval eval: does `lore query` put the answering page in its top results?

Usage: uv run python evals/retrieval.py [evals/order-approval.yaml] [--k 5] [--min-hit 0.9]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from domainlore.build import source_bundle
from domainlore.config import load_config
from domainlore.graph import Graph
from domainlore.query import query

REPO = Path(__file__).resolve().parents[1]


def hits(graph: Graph, question: str, k: int) -> list[str]:
    out = query(graph, question, limit=k)
    return [line.split()[0] for line in out.splitlines() if line and not line.startswith(" ")]


def evaluate(spec_path: Path, k: int) -> tuple[float, float, list[str]]:
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    config = load_config(REPO / spec["knowledge"])
    graph = Graph.build(source_bundle(config), config)
    at_1 = at_k = 0
    misses = []
    for item in spec["questions"]:
        found = hits(graph, item["q"], k)
        expect = item["expect"] if isinstance(item["expect"], list) else [item["expect"]]
        at_1 += bool(found) and found[0] in expect
        if set(expect) & set(found):
            at_k += 1
        else:
            misses.append(f"{item['q']!r}: expected {expect}, got {found}")
    total = len(spec["questions"])
    return at_1 / total, at_k / total, misses


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", nargs="?", default=str(REPO / "evals" / "order-approval.yaml"))
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--min-hit", type=float, default=0.0, help="Fail below this hit@k.")
    args = parser.parse_args()
    at_1, at_k, misses = evaluate(Path(args.spec), args.k)
    print(f"hit@1 {at_1:.0%}  hit@{args.k} {at_k:.0%}")
    for miss in misses:
        print(f"  miss: {miss}")
    return 0 if at_k >= args.min_hit else 1


if __name__ == "__main__":
    sys.exit(main())
