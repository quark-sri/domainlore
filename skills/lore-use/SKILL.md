---
name: lore-use
description: Domain knowledge from the project's `knowledge/` Knowledge Base (domainlore). Use before writing a spec, test case or code that touches business entities, rules, journeys or screens; when asked a question about the business domain; or when recording a new domain fact or conflict.
---

# lore-use

The Knowledge Base holds **sourced** domain facts as markdown pages (OKF v0.2). Every page has a `type`, `sources`, a trust tier and a **basis**: `intended` (what the product should do, from tickets and docs) or `actual` (what it does, from the app or code).

## Read: answer from the Knowledge Base

1. Open `knowledge/index.md`, then only the Area index and pages the task needs. For a question that spans Areas, run `lore query "<question>"`, then `lore explain <page>` or `lore path <a> <b>`.
2. Before writing tests or code, open every **Gap** and **Spec Conflict** linked from the pages you use (the page's Relations block lists them).
3. Weigh each fact by trust: `human-reviewed` is settled; `machine-confirmed` was seen in the app or code; `unverified` is a hint to confirm.

Done when every domain claim in your output **cites** its page (and footnote source where the claim rests on one), and every open conflict that touches your work is named, with the side you followed.

- Test oracles come from `intended` facts. Where `intended` and `actual` disagree, that is a Gap: test the intended behaviour and expect the test to fail until the Gap is fixed.
- A Spec Conflict has no right answer yet. Ask the user which side applies, or say which side you assumed.

## Write: record a new fact or conflict

Follow [page-format.md](page-format.md) for the frontmatter fields.

1. Edit the page's frontmatter or body; add a `sources` entry with an `id` and cite it with a footnote `[^id]`.
2. Two sources disagree → create a page in `knowledge/conflicts/` with `type: Gap` (intended vs actual) or `type: Spec Conflict` (intended vs intended), `about:` the affected pages, and both sources.
3. An ambiguity the sources and the code cannot settle → add it to `knowledge/questions.md` and leave the fact without `verified`.
4. Run `lore build`, then `lore check`.

Done when `lore check` reports 0 errors. Generated blocks and files are rebuilt from frontmatter, so every change goes into frontmatter or prose outside the `generated` markers.
