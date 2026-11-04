"""`lore convert`: turn source documents into cached text with offsets, so Sources name exact spans.

Each document becomes `.lore/cache/<path>.json` (metadata, sections, pages, the text) and
`<path>.md` (the same text, for agents to read). Offsets are character positions in that text.
The cache is derived and git-ignored; the original document stays where it is.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from importlib import metadata
from pathlib import Path

from .config import Config

HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t#]*$", re.MULTILINE)
TEXT_SUFFIXES = (".md", ".markdown", ".txt")
EXTRA = {".docx": "docx", ".pdf": "pdf"}


class MissingConverter(Exception):
    """The optional package that converts this file type is not installed."""


@dataclass
class Section:
    heading: str
    level: int
    path: list[str]  # headings from the top level down to this one
    start: int
    end: int


@dataclass
class Page:
    page: int  # 1-based
    start: int
    end: int


@dataclass
class Document:
    path: str  # relative to the project root
    sha256: str
    basis: str
    converter: str
    sections: list[Section] = field(default_factory=list)
    pages: list[Page] = field(default_factory=list)  # PDF only
    text: str = ""

    def locate(self, start: int, end: int) -> dict:
        """Where a span sits: its section path, PDF page and 1-based line numbers."""
        section = next((s for s in reversed(self.sections) if s.start <= start < s.end), None)
        page = next((p.page for p in self.pages if p.start <= start < p.end), None)
        return {
            "section": " > ".join(section.path) if section else None,
            "page": page,
            "lines": [self.text.count("\n", 0, start) + 1, self.text.count("\n", 0, end) + 1],
        }


def sections(text: str) -> list[Section]:
    """Markdown headings, each spanning to the next heading of the same or a higher level."""
    found = [(m.start(), len(m.group(1)), m.group(2).strip()) for m in HEADING.finditer(text)]
    result: list[Section] = []
    trail: list[tuple[int, str]] = []
    for i, (start, level, heading) in enumerate(found):
        trail = [t for t in trail if t[0] < level] + [(level, heading)]
        end = next((s for s, lv, _ in found[i + 1 :] if lv <= level), len(text))
        result.append(Section(heading, level, [h for _, h in trail], start, end))
    return result


PACKAGES = {".docx": ("mammoth", "markdownify"), ".pdf": ("pypdf",)}


def converter(suffix: str) -> str:
    """The converter and its versions for a file type; offsets depend on it, so it is cached."""
    if suffix in TEXT_SUFFIXES:
        return "text"
    try:
        return " + ".join(f"{name} {metadata.version(name)}" for name in PACKAGES[suffix])
    except metadata.PackageNotFoundError as err:
        raise MissingConverter(EXTRA[suffix]) from err


def to_text(path: Path) -> tuple[str, list[Page]]:
    """Return (text, pages) for one document."""
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8"), []
    if suffix == ".docx":
        import mammoth
        from markdownify import markdownify

        with path.open("rb") as file:
            html = mammoth.convert_to_html(file).value
        text = markdownify(html, heading_style="ATX").strip() + "\n"
        return re.sub(r"\n{3,}", "\n\n", text), []
    from pypdf import PdfReader

    text, pages = "", []
    for number, page in enumerate(PdfReader(path).pages, 1):
        start = len(text)
        text += (page.extract_text() or "").strip() + "\n\n"
        pages.append(Page(number, start, len(text)))
    return text, pages


def cache_dir(config: Config) -> Path:
    return config.root / ".lore" / "cache"


def cache_path(config: Config, rel: str) -> Path:
    return cache_dir(config) / f"{rel}.json"


def load(config: Config, rel: str) -> Document | None:
    path = cache_path(config, rel)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    data["sections"] = [Section(**s) for s in data.get("sections", [])]
    data["pages"] = [Page(**p) for p in data.get("pages", [])]
    return Document(**data)


def documents(config: Config) -> list[tuple[Path, str]]:
    """Every file under the configured source folders, with its default basis."""
    found = []
    for folder, basis in config.sources.items():
        base = config.root / folder
        if base.is_file():
            found.append((base, basis))
        elif base.is_dir():
            found += [(p, basis) for p in sorted(base.rglob("*")) if p.is_file()]
    return found


def convert(config: Config) -> list[tuple[str, str]]:
    """Convert every source document. Returns (path, outcome) pairs; unchanged files are kept."""
    outcomes = []
    for path, basis in documents(config):
        rel = path.relative_to(config.root).as_posix()
        if path.suffix.lower() not in (*TEXT_SUFFIXES, *EXTRA):
            outcomes.append((rel, "skipped: no converter for this file type"))
            continue
        try:
            used = converter(path.suffix.lower())
        except MissingConverter as err:
            outcomes.append((rel, f"skipped: install the `{err}` extra (domainlore[{err}])"))
            continue
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        cached = load(config, rel)
        if cached and (cached.sha256, cached.basis, cached.converter) == (sha, basis, used):
            outcomes.append((rel, "unchanged"))
            continue
        text, pages = to_text(path)
        doc = Document(rel, sha, basis, used, sections(text), pages, text)
        target = cache_path(config, rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(asdict(doc), indent=2, ensure_ascii=False) + "\n", "utf-8")
        target.with_suffix(".md").write_text(text, encoding="utf-8")
        outcomes.append((rel, "converted" if cached is None else "updated"))
    return outcomes
