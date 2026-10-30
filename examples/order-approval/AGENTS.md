<!-- domainlore:start -->
## Domain knowledge

Business domain facts live in `knowledge/` (OKF v0.2 markdown, built with domainlore).

- Start at `knowledge/index.md`; open only the Area and pages you need.
- Each page cites its Sources. Prefer `human-reviewed` facts; treat `unverified` ones as hints.
- `basis: intended` = what the product should do; `basis: actual` = what it does.
- Check open Gaps and Spec Conflicts (listed in the index) before you write tests or code.
- For cross-cutting questions run `lore query "<question>"`,
  `lore explain <page>` or `lore path <a> <b>`.
- Do not edit generated blocks or files; change frontmatter and run `lore build`.
<!-- domainlore:end -->
