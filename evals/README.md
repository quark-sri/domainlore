# Evals

## Retrieval (automated, in CI)

`uv run python evals/retrieval.py --min-hit 0.96 --min-hit1 0.7` asks every question in [order-approval.yaml](order-approval.yaml) through `lore query` and reports hit@1 and hit@5 (the expected page among the top 1 or 5 results). CI fails below 96% hit@5 or 70% hit@1. The floors are a tripwire with no slack: the main set is at 30/31 and 22/31, so one more miss fails the build. A failure means fix the page (or a question's `expect` if it was wrong), not the floor. Change a floor only by owner decision, with a note here. CI also prints the held-out result, without a gate, until the held-out set has about 30 questions.

Current result: **hit@1 71%, hit@5 97%** (31 questions). The one miss is "Can a buyer approve their own order?": the Approve-an-order journey matches "approve … order" in its title. Fix misses in the pages (aliases, descriptions), not by tuning weights to this question set.

[order-approval-holdout.yaml](order-approval-holdout.yaml) holds 12 held-out questions (batch 1, 2026-11-01): **hit@1 8/12 (67%), hit@5 10/12 (83%)**. The two hit@5 misses are "Who signs off on purchases?" and "Does an order need a second person to check it?". Never edit a held-out question, and do not edit pages to fix a held-out miss. It has no CI gate. Run it with `uv run python evals/retrieval.py evals/order-approval-holdout.yaml`.

Batch 1 has been used for one decision, the removal of rarity weighting below, so it is no longer clean for ranking changes. Judge the next ranking change on a fresh batch, written before the change and added with its date. Its author had read the scoring code, and three of its questions accept two pages; a better batch has one expected page per question and comes from someone who has not read `score()`. At 12 questions, one question moves hit@1 by 8 points.

Rarity (IDF) weighting was tried on 2026-10-31 (commit `9d33d97`, `rarity()` in `src/domainlore/query.py`) and removed on 2026-11-01:

| Set | With IDF hit@1 / hit@5 | Without IDF |
|---|---|---|
| Main (31, used to choose IDF) | 23/31 / 31/31 | 22/31 / 30/31 |
| Held-out batch 1 (12) | 7/12 / 10/12 | 8/12 / 10/12 |

On each set the difference is one question, so the evidence is weak either way. IDF was removed because it gave no gain on questions it was not chosen on and it added code. On the held-out set, "Can I submit an order worth 20 euros?" lost first place to the Place-an-order journey.

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
| 2026-11-01 | 9d33d97 | Claude Code 2.1.314 / claude-opus-5-5 | 31/31 | 30/31 | 10/11 | 2.6 |

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

Notes on the 2026-11-01 run:

- Clean tree at `9d33d97`, with the command in step 1. That commit still had rarity (IDF) weighting, removed since. `lore query` was used in 3 of 31 sessions, so this run says little about ranking.
- Cited 30/31: the PO question cited the PO Term page, not the Order page, as in every run.
- Conflict-aware 10/11: "Can a buyer approve their own order?" did not mention the threshold Spec Conflict, as in the 2026-10-31 run.
- One session found that the Order page's Relations list gives the implied four-eyes `governs` link no basis label, while its diagram marks it intended.
