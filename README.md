# domainlore

**Sourced domain knowledge for AI coding agents.**

AI coding agents write specs, tests and code with almost no knowledge of your business domain. That knowledge is spread across Jira, Confluence, Word and PDF documents, the running app and the code, and it often contradicts itself.

domainlore keeps that knowledge as a **Knowledge Base**: plain markdown pages in your repo that any agent can read, one page per domain concept, each with:

- **Sources** for every fact, down to the ticket, page or line.
- A **basis**: `intended` (what the product should do) or `actual` (what it does).
- A **trust tier**: `unverified`, `machine-confirmed` or `human-reviewed`.
- **Conflicts** made explicit: a **Gap** (spec vs app: a likely bug) or a **Spec Conflict** (two specs disagree: a question for the product owner).

Pages follow Google's [Open Knowledge Format (OKF) v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md), with a small domain ontology on top: **Entity, Rule, Actor, Journey, Screen, Term**. Agents read them with progressive disclosure: root index → Area index → page → source.

> **Status: v0.1 (alpha).** Hand-written pages get validation, generated indexes, Mermaid diagrams, a glossary, query tools and agent pointers. Extraction from documents, Confluence, Jira, OpenAPI and a live-app crawler follow; see [PLAN.md](PLAN.md).

## Quick start

```bash
# Run without installing (requires uv)
uvx --from git+https://github.com/quark-sri/domainlore lore init
```

`lore init` creates `lore.toml` and `knowledge/`, adds `.lore/` to `.gitignore`, and adds a short pointer block to `AGENTS.md` (and to `CLAUDE.md` if you have one). Add `--cursor` to write a Cursor rule too.

Write a page, for example `knowledge/billing/entities/invoice.md`:

```markdown
---
type: Entity
description: A request for payment sent to a Customer after delivery.
basis: intended
sources:
  - id: bil-12
    resource: https://jira.example.com/browse/BIL-12
    title: "BIL-12: Invoicing"
relations:
  belongs_to: [billing/entities/customer]
states: [draft, issued, paid, overdue]
transitions:
  - { from: draft, to: issued, trigger: billing/actors/accountant, cites: [bil-12] }
---

# Invoice

An Invoice is issued after delivery.[^bil-12]

[^bil-12]: BIL-12: Invoicing
```

Then:

```bash
lore build    # regenerate indexes, maps, glossary, diagrams and relation lists
lore check    # validate OKF, schema, sources, relations, conflicts, generated content
```

The full field reference is in [skills/lore-use/page-format.md](skills/lore-use/page-format.md).

## Settling vague values

When a document leaves a value open ("limit to be confirmed"), the `lore-resolve` skill checks the other sources, then the production code, then asks a person. To let it read the code, add the code as a source with the basis `actual`:

```toml
[[sources]]
path = "src"
basis = "actual"

[ambiguity]
order = ["sources", "code", "ask"]   # the default; a step left out is not used
```

`lore convert` reads code files (`.py`, `.js`, `.ts`, `.java`, `.go`, `.sql`, `.yaml` and a few more) only under a source with the basis `actual`; other types (for example `.c`) are reported as "skipped: no converter". It skips hidden, dependency and build folders, files whose name looks like a secrets file (`.env`, `*secret*`, `*.pem`), code over 200 KB and files that are not UTF-8. A Source from code is titled with its lines. The optional graphify tool can help find where a value is defined; the skill asks you before it runs it.

## Commands

| Command | What it does |
|---|---|
| `lore init` | Set up a project (safe to re-run) |
| `lore build` | Regenerate everything derived from frontmatter |
| `lore check [--json] [--strict]` | Validate; exit 1 on errors (or on warnings with `--strict`) |
| `lore query "<question>"` | Find the pages that answer a domain question, with their relations |
| `lore explain <page>` | One page: trust, basis, sources, every relation |
| `lore path <a> <b>` | How two concepts connect |
| `lore convert` | Convert the source documents and code in `lore.toml` to cached text with offsets (`.lore/cache/`); Word needs `domainlore[docx]`, PDF needs `domainlore[pdf]` |
| `lore propose <file>` | Apply a Proposal: check every quote against its document, write the pages with exact source locations, build, check, commit on a new branch (`--no-branch` to skip git) |

## What gets generated

- `knowledge/index.md`: Areas, key entities and open conflicts.
- `<area>/index.md`: every page in the Area, grouped by type, with trust tier.
- `map.md` (root): a context map of the Areas. `<area>/map.md`: an ER diagram and screen navigation.
- `GLOSSARY.md`: canonical terms with the words to avoid.
- On each page: a **Relations** block (outgoing, incoming and conflicts), a **Lifecycle** state diagram for Entities, and a **Flow** diagram for Journeys.

Diagrams encode basis and trust: dashed = intended only, orange = actual only, red ⚠ = open Gap, grey = unverified.

See the demo product in [examples/order-approval/](examples/order-approval/knowledge/index.md); it has two planted Gaps and one planted Spec Conflict.

## Use it from your agent

- **Any agent**: the `AGENTS.md` block from `lore init` points to `knowledge/` and the `lore` commands.
- **Agent Skills** (Claude Code, Codex, Cursor, Copilot, Gemini CLI and others): [`skills/lore-use`](skills/lore-use/SKILL.md) to read and record facts, [`skills/lore-extract`](skills/lore-extract/SKILL.md) to extract them from documents, [`skills/lore-resolve`](skills/lore-resolve/SKILL.md) to settle a vague value from other sources, the code or a person, and [`skills/lore-review`](skills/lore-review/SKILL.md) to guide a person through reviewing a Proposal.
- **Claude Code plugin**:

  ```text
  /plugin install domainlore --marketplace quark-sri/domainlore
  ```

## Develop

```bash
uv sync
uv run pytest
uv run ruff check .
uv run lore check --root examples/order-approval
uv run python evals/retrieval.py --min-hit 0.9
./scripts/gen-schema.sh   # after changing schema/domainlore.yaml
```

Design: [PLAN.md](PLAN.md) · vocabulary: [GLOSSARY.md](GLOSSARY.md) · decisions: [docs/adr/](docs/adr/).

## License

[Apache-2.0](LICENSE)
