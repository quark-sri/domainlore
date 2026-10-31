# Evals

## Retrieval (automated, in CI)

`uv run python evals/retrieval.py --min-hit 0.96 --min-hit1 0.7` asks every question in [order-approval.yaml](order-approval.yaml) through `lore query` and reports hit@1 and hit@5 (the expected page among the top 1 or 5 results). CI fails below 96% hit@5 or 70% hit@1, just under the current result. Raise the floors when the result improves.

Current result: **hit@1 74%, hit@5 100%** (31 questions). `lore query` weights rare words above common ones, so "own" counts more than "order". Fix a new miss in the pages first (aliases, descriptions), not by tuning weights to this question set.

## Agent (manual)

Measures whether an agent answers correctly, with citations, reading only the Knowledge Base.

1. Start from a clean tree at a commit (`git status --porcelain` is empty); record the commit. Open a fresh agent session in `examples/order-approval/` (it has the `AGENTS.md` pointer). For Claude Code, one headless session per question:

   ```bash
   cd examples/order-approval
   claude -p "<question>" --setting-sources project,local --output-format stream-json --verbose \
     --allowedTools "Read" "Grep" "Glob" "Bash(lore:*)" "Bash(uv run lore:*)" \
     --disallowedTools "Edit" "Write" "WebFetch" "WebSearch" "Agent" < /dev/null
   ```

2. Ask each question from `order-approval.yaml`, one session per question.
3. Score: **correct** (matches the expected page), **cited** (names the page), **conflict-aware** (for questions touching the threshold or cancel, mentions the open Spec Conflict or Gap), and the number of files the agent read.
4. Record date, commit, agent, model and the four scores in the table below. Count files read from `Read` calls and `cat` commands.

| Date | Commit | Agent / model | Correct | Cited | Conflict-aware | Avg files read |
|---|---|---|---|---|---|---|
| 2026-10-30 | 834efc5 | Claude Code 2.1.314 / claude-opus-5-5 | 30/30 | 29/30 | 10/10 | 2.9 |
| 2026-10-31 | a00183a + uncommitted edits (not comparable) | Claude Code 2.1.314 / claude-opus-5-5 | 31/31 | 29/31 | 10/11 | 2.1 |

Notes on the 2026-10-30 run:

- Headless sessions (`claude -p`), one per question, with read-only tools: `Read`, `Grep`, `Glob` and `lore`. Every session started at `knowledge/index.md` and read 1 to 6 files.
- Cited 29/30: for "What does PO mean?" the agent cited the PO Term page, not the Order page. The answer was correct.
- Conflict-aware counts the 10 questions about the threshold or cancel; all 10 named the open Spec Conflict or Gap.
- The agents found two defects in the demo, fixed since: a journey branch end led on to the next step, and a missing inbox link on Order details had no Gap page.
- `lore query` was not used: the agents called it through `uv run`, which the session did not allow, so they read the files instead.

Notes on the 2026-10-31 run:

- **Not comparable with the 2026-10-30 run:** the tree had uncommitted page edits, the tools differed, and files read also counts `cat`. Re-run on a clean commit.
- Same set-up with user settings off (`--setting-sources project,local`); `lore` and `uv run lore` allowed. Files read counts `Read` and `cat`.
- `lore query` was used in 2 of 31 sessions. The agents preferred `Grep` and reading the index, and still answered correctly.
- Cited 29/31: the PO question cited the PO Term page again; "Who approves orders?" gave no page path for the Approver.
- Conflict-aware 10/11: the 11 include the new inbox-link Gap question. "Can a buyer approve their own order?" did not mention the threshold Spec Conflict.
- Three sessions ran `git diff` and saw uncommitted page edits. Run the eval on a clean tree.
