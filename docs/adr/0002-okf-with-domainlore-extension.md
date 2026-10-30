# OKF v0.2 with a domainlore extension

Knowledge Base pages are Open Knowledge Format v0.2 concepts, so any OKF reader can consume them, and we add only optional keys (`basis`, `relations`, `states`, `transitions`, `steps`, `about`, `resolution`, `definition`, `broader`, `aliases`). We follow OKF where it already answers a question, even where our first design differed: the concept ID is the file path (no `id` field); trust is derived from the `verified` event list (`human:` actor ⇒ human-reviewed), not stored as a value; sources are inline `sources` entries cited by footnote `[^id]`, so Source is a glossary concept without its own pages; `index.md` stays a pure listing, so Area diagrams live in a generated `map.md` concept.

## Consequences

- Relations are typed in frontmatter because OKF links are untyped; the generated Relations block also writes them as plain markdown links, so OKF graph readers still see the edges.
- Every generated file except `index.md` is an OKF concept with its own `type` (`Glossary`, `Context Map`, `Area Map`) and `generated: { by: process:lore-build }`.
- Conflicts are concepts too (`Gap`, `Spec Conflict`) in `knowledge/conflicts/`.
- If OKF changes, the mapping is isolated in the schema and the bundle reader.
