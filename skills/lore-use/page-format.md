# Page format

A Knowledge Base is an [OKF v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) bundle. Every `.md` file except `index.md` and `log.md` is a **concept page** with YAML frontmatter and a markdown body. The concept ID is the path without `.md`, for example `ordering/entities/order`. Terms are defined in [GLOSSARY.md](https://github.com/quark-sri/domainlore/blob/main/GLOSSARY.md); the schema is [schema/domainlore.yaml](https://github.com/quark-sri/domainlore/blob/main/schema/domainlore.yaml).

## Layout

```text
knowledge/
  index.md            generated (L0)
  map.md              generated context map
  GLOSSARY.md         generated
  questions.md        Open Questions, edited by people and agents
  log.md              change log (OKF §9)
  <area>/             one folder per Area
    index.md          generated (L1)
    map.md            generated ER and navigation diagrams
    entities/ rules/ actors/ journeys/ screens/ terms/
  conflicts/          Gap and Spec Conflict pages
```

Sub-folder names inside an Area are a convention; the `type` field is what counts.

## Fields on every page

| Field | Required | Meaning |
|---|---|---|
| `type` | yes | `Entity`, `Rule`, `Actor`, `Journey`, `Screen`, `Term`, `Gap` or `Spec Conflict` |
| `title` | | Display name; defaults to the file name |
| `description` | | One sentence; shown in indexes and `lore query` |
| `sources` | yes for the six domain types | List of `{id, resource, title, author, last_modified, version, basis}`; `resource` is required |
| `basis` | | Default basis of the page's facts: `intended` or `actual` |
| `verified` | | OKF verification events `{by, at}`; `by: human:<id>` makes the page `human-reviewed`, any other actor `machine-confirmed`, none `unverified` |
| `relations` | | Map of relation name → list of targets (below) |
| `aliases` | | Other names; they appear under `_Avoid_` in the glossary |
| `status`, `stale_after`, `tags`, `generated` | | As in OKF |

Cite a source in the body with a footnote whose label is the source `id`: `…needs approval.[^policy]` and `[^policy]: Purchase approval policy v2`.

## Relations

| Relation | From → To |
|---|---|
| `has`, `belongs_to` | Entity → Entity |
| `governs` | Rule → Entity |
| `performs` | Actor → Journey |
| `navigates_to` | Screen → Screen |
| `shows` | Screen → Entity |
| `step_of` | Screen → Journey |
| `aka` | Term → any page |

A target is a concept ID, or a mapping that overrides the page's basis and names its sources:

```yaml
relations:
  navigates_to:
    - ordering/screens/order-list
    - { to: approvals/screens/approval-inbox, basis: intended, cites: [policy] }
```

Add relation types in `lore.toml` under `[relations.<name>]` with `label`, `from` and `to`.

## Type-specific fields

**Entity**: `states` (list) and `transitions`, each `{from, to, trigger, governed_by: [rules], basis, cites: [source ids]}`. Rendered as a state diagram.

**Journey**: `steps`, each `{id, label, screen, actor, goto: [{to, when}]}`; without `goto` a step leads to the next one. `diagram: sequence` renders a sequence diagram instead of a flowchart.

**Term**: `definition`, `broader`, and `relations: {aka: [page]}` when the term is another word for a page.

**Gap / Spec Conflict**: `about` (pages it concerns), at least two sources, and `resolution` once a person settles it. A Gap is intended vs actual; a Spec Conflict is intended vs intended.

## Generated content

`lore build` owns `index.md`, `map.md`, `GLOSSARY.md` and every block between `<!-- generated:start NAME -->` and `<!-- generated:end NAME -->`. `lore check` fails when they differ from a fresh build.
