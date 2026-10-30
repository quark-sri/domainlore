# Working on domainlore

- Vocabulary: [GLOSSARY.md](GLOSSARY.md). Use its terms in code, docs and commit messages; the `_Avoid_` words are banned synonyms.
- Design and roadmap: [PLAN.md](PLAN.md). Decisions: `docs/adr/`. Add an ADR only for a choice that is hard to reverse, surprising, and a real trade-off.
- The on-disk format is OKF v0.2 plus our extension ([ADR 0002](docs/adr/0002-okf-with-domainlore-extension.md)). Readers must accept any valid OKF bundle.
- Markdown frontmatter is the source of truth; everything `lore build` writes is derived ([ADR 0001](docs/adr/0001-markdown-is-the-source-of-truth.md)).
- The core stays agent-agnostic: CLI + files + `AGENTS.md`. Per-agent packaging lives in `.claude-plugin/`, `skills/` and `src/domainlore/adapters/`, with no logic.
- Dependencies: permissive licences only (MIT, Apache-2.0, BSD). No AGPL or GPL.

## Changes

- Schema change: edit `schema/domainlore.yaml`, run `./scripts/gen-schema.sh`, commit both.
- Output change: run `uv run lore build --root examples/order-approval` and review the diff; the demo is the golden fixture.
- Before a commit: `uv run ruff check . && uv run ruff format --check . && uv run pytest`.
