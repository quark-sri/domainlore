# Markdown is the source of truth; the graph is derived

The Knowledge Base lives as markdown pages with typed YAML frontmatter in the product's own git repo. The graph (JSON) and any search index are build outputs, rebuilt from those pages and never edited by hand. We chose this over a graph database (Neo4j, Kuzu) as the source of truth because AI agents read markdown directly, people review knowledge changes in normal pull requests, and teams need no server or licence to adopt the tool.

## Consequences

- Graph queries are only as fresh as the last build, so the build must be cheap and run in CI and git hooks.
- A graph database can still be added as an optional, disposable index, but nothing may write to it except the build.
