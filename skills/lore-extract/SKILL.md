---
name: lore-extract
description: Extract sourced domain facts from the project's documents (Markdown, Word, PDF) into a domainlore Proposal, each with an exact source location. Use when asked to add, import or update domain knowledge from a document, a BRD, a policy or a spec, or after new files appear under a `[[sources]]` path in lore.toml. Not for answering domain questions (use lore-use).
---

# lore-extract

You turn documents into a **Proposal**: new or changed Knowledge Base pages where every fact cites a verbatim quote. `lore propose` checks each quote against the document, writes the exact span and commits the pages on a branch. A person reviews the pull request. You never edit `knowledge/` directly for extracted facts.

## Steps

1. Run `lore convert`. Read the converted text in `.lore/cache/<document path>.md`, not the original file.
2. Read `knowledge/index.md` and the pages your facts touch. Reuse their concept IDs. Add a new page only for a thing that has no page yet.
3. For each fact, copy the sentence that states it **exactly as it appears** in the converted text. Do not paraphrase the quote and do not compute offsets.
4. Compare with the existing pages and the other documents:
   - Two `intended` sources disagree → a `Spec Conflict` page in `knowledge/conflicts/`, citing both.
   - An `intended` source disagrees with an `actual` page (the app or the code) → a `Gap` page, citing both.
   - Record both sides. Never pick a winner.
   - The documents do not settle a vague value → add an Open Question to `knowledge/questions.md`; do not guess.
5. Write the Proposal to `.lore/proposals/<short-name>.yaml` (format below). Field names follow [page-format.md](../lore-use/page-format.md).
6. Run `lore propose .lore/proposals/<short-name>.yaml`. If it reports a quote that is not found, fix the quote, not the document.
7. Open a pull request from the branch it names, with the summary it prints as the description.

Done when `lore propose` succeeds and the pull request is open. Facts stay `unverified` until a person merges the pull request.

## Proposal format

```yaml
title: Approval threshold from the purchase approval BRD
pages:
  - id: approvals/rules/approval-threshold   # the concept ID: path under knowledge/, no .md
    type: Rule
    title: Approval threshold
    description: Orders above a total amount need approval.
    basis: intended
    relations:
      governs: [ordering/entities/order]
    body: |
      # Approval threshold

      Orders above 5 000 EUR need approval before they are processed.[^brd]
    cites:
      brd:                                   # the footnote label in the body
        doc: docs/purchase-approval-brd.docx # a file under a [[sources]] path
        quote: Every order with a total above 5 000 EUR needs approval before it is processed.
```

- Every key except `id`, `body` and `cites` is frontmatter. A page in the Proposal replaces the whole page, so copy the fields you keep from the existing page (except `verified` and generated blocks).
- Cite each fact with a footnote `[^label]` in the body; `lore propose` writes the footnote text and the `sources` entry.
- If a quote appears more than once in a document, add `nth: 2` (1-based) to the cite.
- Keep non-document sources (a ticket URL) under `sources:` as usual.
