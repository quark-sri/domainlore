"""`lore propose`: apply a Proposal file, with every quote checked against its source document.

A Proposal is YAML written by an agent (or a person) after reading converted documents:

    title: Facts from the purchase approval BRD
    pages:
      - id: approvals/rules/approval-threshold
        type: Rule
        description: Orders above a total amount need approval.
        body: |
          # Approval threshold
          Orders above 5 000 EUR need approval.[^brd]
        cites:
          brd: {doc: docs/purchase-approval-brd.docx, quote: "Every order with a total above"}

Every key of a page except `id`, `body` and `cites` is frontmatter. Each cite names a converted
document and a verbatim quote; `lore propose` finds the quote and records its exact span
(ADR 0003). The agent never computes offsets.

A page with a `body` replaces the page; it is unverified until a person reviews it again. A page
with only `id` and `cites` adds Sources to an existing page and keeps its body and review: each
cite then gives `after`, the page text the quote supports, and the footnote goes after it.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import textwrap
from dataclasses import dataclass
from os.path import relpath
from pathlib import Path

import yaml

from .build import build
from .bundle import split_frontmatter
from .check import run_check
from .config import Config
from .convert import Document, documents, load

FRONT_ORDER = ("type", "title", "description", "aliases", "basis", "about")
GENERATED = "<!-- generated:start "


class ProposalError(Exception):
    """The Proposal cannot be applied as written."""


@dataclass
class Quote:
    id: str
    doc: Document
    start: int
    end: int
    quote: str

    def source(self, config: Config) -> dict:
        where = self.doc.locate(self.start, self.end)
        place = f"p. {where['page']}" if where["page"] else where["section"]
        name = Path(self.doc.path).name
        resource = relpath(config.root / self.doc.path, config.knowledge_dir)
        return {
            "id": self.id,
            "resource": f"{Path(resource).as_posix()}#char={self.start},{self.end}",
            "title": f"{name}, {place}" if place else name,
            "version": f"sha256:{self.doc.sha256}",
            "basis": self.doc.basis,
        }

    @property
    def plain(self) -> str:
        """The quote without Markdown emphasis, for footnotes and the summary."""
        return re.sub(r"[*`]|__", "", self.quote)

    def footnote(self, config: Config) -> str:
        return f'[^{self.id}]: {self.source(config)["title"]}: "{self.plain}"'


def find(text: str, quote: str, nth: int | None = None) -> tuple[int, int]:
    """The span of a quote in the text; whitespace may differ (PDF line breaks)."""
    words = quote.split()
    if not words:
        raise ProposalError("empty quote")
    pattern = r"\s+".join(re.escape(w) for w in words)
    matches = list(re.finditer(pattern, text))
    if not matches:
        raise ProposalError(f"quote not found: {quote!r}")
    if nth is None and len(matches) > 1:
        raise ProposalError(f"quote found {len(matches)} times; add `nth` (1-based): {quote!r}")
    if (nth or 1) > len(matches):
        raise ProposalError(f"quote found {len(matches)} times, not {nth}: {quote!r}")
    match = matches[(nth or 1) - 1]
    return match.start(), match.end()


def cite(config: Config, cid: str, spec: dict) -> Quote:
    rel = str(spec.get("doc", ""))
    if rel not in {p.relative_to(config.root).as_posix() for p, _ in documents(config)}:
        raise ProposalError(f"cite {cid}: `{rel}` is not under a [[sources]] path in lore.toml")
    doc = load(config, rel)
    if doc is None:
        raise ProposalError(f"cite {cid}: `{rel}` is not converted; run `lore convert`")
    current = hashlib.sha256((config.root / rel).read_bytes()).hexdigest()
    if current != doc.sha256:
        raise ProposalError(f"cite {cid}: `{rel}` changed since `lore convert`; run it again")
    quote = " ".join(str(spec.get("quote", "")).split())
    nth = spec.get("nth")
    start, end = find(doc.text, quote, int(nth) if nth is not None else None)
    return Quote(cid, doc, start, end, quote)


def dump(data: object) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000)


def with_notes(body: str, notes: list[str]) -> str:
    """Append footnote definitions, after the existing ones if the body ends with them."""
    body = body.rstrip() + "\n"
    if not notes:
        return body
    gap = "" if body.splitlines()[-1].startswith("[^") else "\n"
    return body + gap + "\n".join(notes) + "\n"


def append_sources(front: str, meta: dict, new: list[dict]) -> str:
    """Add Source entries to the frontmatter text and keep the rest as written."""
    entries = textwrap.indent(dump(new), "  ")
    lines = front.splitlines(keepends=True)
    result = ""
    if "sources:\n" in lines:
        i = lines.index("sources:\n") + 1
        while i < len(lines) and lines[i].startswith((" ", "-")):
            i += 1
        result = "".join(lines[:i]) + entries + "".join(lines[i:])
    elif not any(line.startswith("sources:") for line in lines):
        result = front + "sources:\n" + entries
    want = (meta.get("sources") or []) + new
    if result and (yaml.safe_load(result) or {}).get("sources") == want:
        return result
    return dump({**meta, "sources": want})  # unusual layout: write the frontmatter again


def add_sources(config: Config, pid: str, page: dict, target: Path) -> tuple[str, list[Quote]]:
    """Cite new quotes on an existing page; its body and review stay as they are."""
    meta, body, error = split_frontmatter(target.read_text(encoding="utf-8"))
    if meta is None:
        raise ProposalError(f"page `{pid}`: {error}")
    known = {s.get("id") for s in meta.get("sources") or [] if isinstance(s, dict)}
    own, generated = (body.split(GENERATED, 1) + [""])[:2]
    quotes = []
    for cid, spec in (page.get("cites") or {}).items():
        if cid in known:
            raise ProposalError(f"cite {cid}: page `{pid}` already has a source `{cid}`")
        after = " ".join(str(spec.get("after", "")).split())
        if not after:
            raise ProposalError(
                f"cite {cid}: page `{pid}` has no `body` in the Proposal, so the cite needs "
                "`after`: the page text the quote supports"
            )
        quote = cite(config, cid, spec)
        try:
            _, end = find(own, after)
        except ProposalError as err:
            raise ProposalError(f"cite {cid}: `after` in page `{pid}`: {err}") from err
        end += re.match(r"(\[\^[^\]\s]+\])*", own[end:]).end()  # after any footnotes there
        own = f"{own[:end]}[^{cid}]{own[end:]}"
        quotes.append(quote)
    own = with_notes(own, [q.footnote(config) for q in quotes])
    if generated:
        own += "\n" + GENERATED + generated
    front = append_sources(
        target.read_text("utf-8").split("\n---", 1)[0][4:] + "\n",
        meta,
        [q.source(config) for q in quotes],
    )
    return f"---\n{front}---\n{own}", quotes


def render(config: Config, page: dict) -> tuple[Path, str, list[Quote], str]:
    """The page file, its new text, its quotes and what changes (for the summary)."""
    pid = str(page.get("id", "")).strip("/")
    if not pid or ".." in pid.split("/"):
        raise ProposalError(f"page id `{pid}` is not a concept ID such as `area/rules/name`")
    target = config.knowledge_dir / f"{pid}.md"
    if "body" not in page and set(page) <= {"id", "cites"}:
        if not target.is_file():
            raise ProposalError(f"page `{pid}` does not exist; a new page needs a `body`")
        text, quotes = add_sources(config, pid, page, target)
        return target, text, quotes, "sources added"
    quotes = [cite(config, cid, spec) for cid, spec in (page.get("cites") or {}).items()]
    meta = {k: v for k, v in page.items() if k not in ("id", "body", "cites", "verified")}
    sources = [s for s in meta.pop("sources", []) or [] if s.get("id") not in page.get("cites", {})]
    sources += [c.source(config) for c in quotes]
    if sources:
        meta["sources"] = sources
    ordered = {k: meta.pop(k) for k in FRONT_ORDER if k in meta}
    ordered.update(meta)
    body = str(page.get("body", ""))
    body = with_notes(body, [c.footnote(config) for c in quotes if f"[^{c.id}]:" not in body])
    kind = "new"
    if target.is_file():
        old, _, _ = split_frontmatter(target.read_text(encoding="utf-8"))
        kind = "changed, review removed" if old and old.get("verified") else "changed"
    return target, f"---\n{dump(ordered)}---\n\n{body.lstrip()}", quotes, kind


def load_proposal(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as err:
        raise ProposalError(f"cannot read {path}: {err}") from err
    if not isinstance(data, dict) or not data.get("title") or not data.get("pages"):
        raise ProposalError("a Proposal needs a `title` and a list of `pages`")
    return data


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50] or "proposal"


def git(config: Config, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=config.root, capture_output=True, text=True)
    if done.returncode:
        raise ProposalError(f"git {' '.join(args)}: {done.stderr.strip()}")
    return done.stdout


def summary(config: Config, title: str, written: list[tuple[Path, str, list[Quote]]]) -> str:
    lines = [f"# Proposal: {title}", "", "Pages:"]
    for path, kind, _ in written:
        lines.append(f"- {kind}: `{path.relative_to(config.root).as_posix()}`")
    lines += ["", "Sources (exact spans, each quote checked against its document):"]
    for _, _, quotes in written:
        for c in quotes:
            lines.append(
                f'- `{c.source(config)["resource"]}` {c.source(config)["title"]}: "{c.plain}"'
            )
    lines += ["", "Review each fact against its quote. Merging marks these facts as reviewed."]
    return "\n".join(lines) + "\n"


def propose(config: Config, path: Path, branch: str | None) -> str:
    """Apply a Proposal. With `branch`, commit it there; returns the PR summary."""
    proposal = load_proposal(path)
    rendered = [render(config, page) for page in proposal["pages"]]  # all checks before any write
    if branch:
        if git(config, "status", "--porcelain", "--", config.knowledge_dir.as_posix()):
            raise ProposalError("the Knowledge Base has uncommitted changes; commit or stash them")
        previous = git(config, "rev-parse", "--abbrev-ref", "HEAD").strip()
        git(config, "switch", "-c", branch)
    before = {
        target: target.read_text("utf-8") if target.exists() else None for target, *_ in rendered
    }
    written = []
    for target, text, quotes, kind in rendered:
        written.append((target, kind, quotes))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    build(config)
    errors = [str(i) for i in run_check(config) if i.level == "error"]
    if errors:
        for target, old in before.items():  # leave the Knowledge Base as it was
            if old is None:
                target.unlink()
            else:
                target.write_text(old, encoding="utf-8")
        build(config)
        if branch:
            git(config, "switch", previous)
            git(config, "branch", "-D", branch)
        raise ProposalError(
            "lore check fails after the Proposal; nothing was kept:\n" + "\n".join(errors)
        )
    if branch:
        git(config, "add", "--", config.knowledge_dir.as_posix())
        git(config, "commit", "-m", f"Proposal: {proposal['title']}")
    return summary(config, str(proposal["title"]), written)
