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

## Extraction (manual)

Measures whether an agent turns the demo documents into a correct Proposal with the `lore-extract` skill and finds the planted Spec Conflict without help.

1. `uv run python evals/extract.py <empty dir> --run` makes a copy of the demo (`--runs N` for N copies). Each copy has no threshold Spec Conflict page, a neutral threshold page (no amount), and only the `lore-extract` and `lore-use` skills, committed in a new git repository. The script runs one headless Claude Code session in each copy (model `claude-opus-5-5`, at most 3 USD and 30 minutes each; it prints the maximum cost first) with the prompt "Extract the domain facts from the documents in docs/ into the knowledge base." and writes each transcript next to its copy. The agent may write only in `.lore/proposals/`.
2. The script scores eight checks for each run: the `lore-extract` skill was used; the agent wrote files only in `.lore/proposals/` (no `Edit` or `Write` elsewhere; a pattern scan for shell writes to `knowledge/`); `knowledge/` changed only through Proposal commits on a `lore/` branch, with nothing left uncommitted; a new Spec Conflict has both amounts (5 000 and 10 000 EUR) and cites the PDF; every document Source has the right hash and its footnote quotes its span; no reviewed page lost its review or was deleted; the questions page keeps its old text and has a new Open Question about the new-buyer period, which the policy leaves open ("to be confirmed"); `lore check` has no errors. A run passes when all eight pass. It also prints the repository commit, the hash of the skill text the agent used, and the cost.
3. The session cannot open a pull request (the copy has no remote), so that step is not scored.
4. When to run it. The unit tests cover the code and the scoring for free; an agent run is needed only to see how an agent follows the skill text:
   - A wording change to the skill, or a change to `lore propose` or the eval: no run.
   - A skill change that alters what the agent must do: 1 run before the merge.
   - Before a release tag: `--runs 3` on the final skill text; at least 2 must pass, with the failure reasons noted. The script exits 0 at 1 of 1 or 2 of 3.
   
   Record each run in the table below, with the commit and skill hash that the script prints. The transcripts are not kept in the repository.
5. Other agents: without `--run`, the script sets up one copy and prints the Claude Code command. The first two checks read Claude Code tool calls; the other six read only the copy's git and file state, so they apply to any agent. `uv run python evals/extract.py <copy> --score <transcript>` scores a finished run. `tests/test_eval_extract.py` tests the set-up and each check without an agent.

| Date | Commit | Agent / model | Result | Spans verified | Pages changed | Cost / turns |
|---|---|---|---|---|---|---|
| 2026-11-04 | 93138d8 | Claude Code 2.1.316 / claude-opus-5-5 | pass (scored by hand, before the script) | 11/11 | 10 | $0.58 / 35 |
| 2026-11-05 | before 4bc2bad: earlier skill text (sha256:93b988acc532) | Claude Code 2.1.316 / claude-opus-5-5 | fail: direct edit to the questions page | 25/25 | 17 | $0.71 / 24 |
| 2026-11-05 | 4bc2bad skill text (sha256:b67acea38e58) and `lore propose` | Claude Code 2.1.316 / claude-opus-5-5 | pass | 24/24 | 19 | $0.65 / 39 |
| 2026-11-05 | 1cd3a38 skill text (sha256:c941ff6d1f67); the script had an uncommitted `--model` option | Claude Code 2.1.316 / claude-sonnet-5-5 | pass (1 run, 7 of 7 checks) | 7/7 | 6 | $0.15 / 13 |

Notes on the 2026-11-04 run:

- The agent found the Spec Conflict (the BRD and the policy say 5 000 EUR, the PDF says 10 000 EUR), added an escalation Rule and three Open Questions.
- It did not add the documents as Sources to reviewed pages, because a Proposal page replaced the whole page and removed its review. Since then, a page given with only cites adds Sources and keeps the review.
- Two defects, fixed since: a page with no cites got an empty `sources` list, and footnotes kept Markdown emphasis from the quote.

Notes on the 2026-11-05 runs:

- Both runs added the documents as Sources to existing pages with the new mode (9 and 10 cites); all five reviewed pages kept their review.
- In the first run the agent added Open Questions to the questions page with a direct edit after `lore propose`, because the skill said "add an Open Question to `knowledge/questions.md`". The skill now says to put the questions page in the Proposal.
- Each run had three shell commands denied (loops and `find`, not on the allowed list); the agent used `Read` instead.
- A single run per skill text is weak evidence: the pages changed (10 to 19) and the cost vary from run to run.
- Both runs were scored again with the stricter checks (writes only in `.lore/proposals/`, only Proposal commits): the results did not change. The second run used the skill text committed in 4bc2bad; one sentence was added to the `lore-use` page format reference after it.

Notes on the 2026-11-05 Sonnet run (first run on the current skill text, after PR 10):

- Run with `uv run python evals/extract.py <dir> --run --model claude-sonnet-5-5`. The `--model` option was added for this run; the default stays `claude-opus-5-5`, so earlier rows stay comparable.
- The agent used the sources-only mode on three existing pages (two were reviewed and kept their review) and wrote the Spec Conflict with both amounts and both documents cited. It wrote only in `.lore/proposals/`.
- It did less than the Opus runs: it added no escalation rule and no Open Questions (6 pages changed, against 17 to 19). The seven checks do not require them, so this run did not exercise the Open Questions step that PR 10 rewrote. Since 2026-11-06 the policy document plants a vague value ("how long a buyer counts as new is to be confirmed") and an eighth check requires an Open Question for it, so a run now covers that step. Rows before that date have seven checks.
- One run on one model: weak evidence, as before.
