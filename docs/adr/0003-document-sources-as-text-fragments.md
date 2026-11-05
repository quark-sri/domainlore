# A document Source carries a text fragment, a file hash and a quote

A Fact extracted from a document cites it as an ordinary OKF `sources` entry, so no new field is needed. The `resource` is the document path relative to `knowledge/` plus an RFC 5147 fragment, `#char=<start>,<end>`. The fragment gives character offsets into the text that `lore convert` produced. The `version` is `sha256:<hash>` of the original file, and the `title` names the section path (or the PDF page). The page's footnote for that source quotes the cited text verbatim, except that Markdown emphasis characters (`*`, `` ` ``, `__`) are removed (a single `_` is kept, because it also occurs in names); the span itself is exact. Agents give only the quote; `lore propose` finds it and writes the span, because agents count characters badly. We chose this over a new `locator` object in the schema, because it keeps pages valid OKF for any reader and puts the quote where a person reads it.

## Consequences

- Offsets refer to the converted text, not to the original bytes, so they depend on the converter. `lore convert` records the converter and its version, and converts a document again when it changes.
- The quote in the footnote is what lasts: if a document or converter changes, a check can find the quote again or report the Source as stale.
- A Word or PDF file must stay at its path for its Sources to resolve; the original is never copied into the repo.
