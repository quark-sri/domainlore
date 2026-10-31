# Changelog

## Unreleased

- `lore check` warns `unrecorded-gap` for an intended-only relation or transition on a page with `basis: actual` that no Gap page records. The exit code is unchanged, but `lore check --strict` now fails on it. To fix it, add a Gap page whose `about` lists the page and the relation target.
- `lore query` weights rare words above common ones; retrieval eval hit@5 is now 100%.
- Clearer Buyer and Four-eyes descriptions; a retrieval and agent-eval question for the inbox-link Gap.

## v0.1.0 (2026-10-30)

- OKF v0.2 Knowledge Base with seven domain types, typed relations, basis and trust tiers.
- LinkML schema with generated JSON Schemas for frontmatter validation.
- `lore init`, `build`, `check`, `query`, `explain`, `path`.
- Generated indexes, Area maps, context map, glossary, Relations blocks, and Mermaid lifecycle, journey, ER and navigation diagrams.
- `AGENTS.md` and `CLAUDE.md` pointer block, Cursor rule, `lore-use` skill, Claude Code plugin.
- Demo product `examples/order-approval` with two planted Gaps and a Spec Conflict; retrieval eval.
- Journey steps: `goto: []` ends the journey at that step, so a branch end no longer leads to the next step.
