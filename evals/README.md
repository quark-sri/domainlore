# Evals

## Retrieval (automated, in CI)

`uv run python evals/retrieval.py --min-hit 0.9` asks every question in [order-approval.yaml](order-approval.yaml) through `lore query` and reports hit@1 and hit@5 (the expected page among the top 1 or 5 results). CI fails below 90% hit@5.

Current result on v0.1: **hit@1 70%, hit@5 93%**. The two misses are vocabulary gaps ("Who places orders?" where the Buyer page says "creates and submits"; "approve their own order" where the rule says "placed it"). Fix such misses in the pages (aliases, descriptions), not by tuning weights to this question set.

## Agent (manual)

Measures whether an agent answers correctly, with citations, reading only the Knowledge Base.

1. Open a fresh agent session in `examples/order-approval/` (it has the `AGENTS.md` pointer).
2. Ask each question from `order-approval.yaml`, one session per question.
3. Score: **correct** (matches the expected page), **cited** (names the page), **conflict-aware** (for questions touching the threshold or cancel, mentions the open Spec Conflict or Gap), and the number of files the agent read.
4. Record agent, model, date and the four scores in a table below.

| Date | Agent / model | Correct | Cited | Conflict-aware | Avg files read |
|---|---|---|---|---|---|
| 2026-10-30 | Claude Code 2.1.314 / claude-opus-5-5 | 30/30 | 29/30 | 10/10 | 2.9 |

Notes on the 2026-10-30 run:

- Headless sessions (`claude -p`), one per question, with read-only tools: `Read`, `Grep`, `Glob` and `lore`. Every session started at `knowledge/index.md` and read 1 to 6 files.
- Cited 29/30: for "What does PO mean?" the agent cited the PO Term page, not the Order page. The answer was correct.
- Conflict-aware counts the 10 questions about the threshold or cancel; all 10 named the open Spec Conflict or Gap.
- The agents found two defects in the demo, fixed since: a journey branch end led on to the next step, and a missing inbox link on Order details had no Gap page.
- `lore query` was not used: the agents called it through `uv run`, which the session did not allow, so they read the files instead.
