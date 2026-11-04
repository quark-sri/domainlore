from __future__ import annotations

import hashlib

import pytest

from domainlore.config import load_config
from domainlore.convert import convert, load, sections
from tests.conftest import EXAMPLE

POLICY = """# Purchase policy

Intro line.

## Thresholds

Orders above 5 000 EUR need approval.

### Escalation

After 3 days the finance lead decides.

## Cancelling

A cancel asks the buyer to confirm.
"""


def with_sources(project, path: str = "docs") -> None:
    (project.root / "lore.toml").write_text(
        f'[knowledge]\ndir = "knowledge"\n[[sources]]\npath = "{path}"\nbasis = "intended"\n'
    )


def write_doc(project, name: str, data: bytes | str) -> None:
    target = project.root / "docs" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        target.write_text(data, encoding="utf-8")
    else:
        target.write_bytes(data)


def test_sections_nest_and_span_to_the_next_heading_of_the_same_level():
    found = {s.heading: s for s in sections(POLICY)}
    assert found["Escalation"].path == ["Purchase policy", "Thresholds", "Escalation"]
    assert POLICY[found["Thresholds"].start :].startswith("## Thresholds")
    assert POLICY[found["Thresholds"].end :].startswith("## Cancelling")  # includes the ### child
    assert found["Purchase policy"].end == len(POLICY)


def test_convert_caches_text_hash_and_spans(project):
    with_sources(project)
    write_doc(project, "policy.md", POLICY)
    assert convert(load_config(project.root)) == [("docs/policy.md", "converted")]
    doc = load(load_config(project.root), "docs/policy.md")
    assert doc.sha256 == hashlib.sha256(POLICY.encode()).hexdigest()
    assert doc.basis == "intended" and doc.converter == "text"
    start = doc.text.index("5 000 EUR")
    assert doc.locate(start, start + 9) == {
        "section": "Purchase policy > Thresholds",
        "page": None,
        "lines": [7, 7],
    }
    assert (project.root / ".lore/cache/docs/policy.md.md").read_text() == POLICY


def test_convert_does_not_rewrite_unchanged_documents(project):
    with_sources(project)
    write_doc(project, "policy.md", POLICY)
    config = load_config(project.root)
    convert(config)
    cached = project.root / ".lore/cache/docs/policy.md.json"
    before = cached.stat().st_mtime_ns
    assert convert(config) == [("docs/policy.md", "unchanged")]
    assert cached.stat().st_mtime_ns == before
    write_doc(project, "policy.md", POLICY + "\nNew rule.\n")
    assert convert(config) == [("docs/policy.md", "updated")]


def test_convert_redoes_a_document_when_its_converter_changes(project):
    with_sources(project)
    write_doc(project, "policy.md", POLICY)
    config = load_config(project.root)
    convert(config)
    cached = project.root / ".lore/cache/docs/policy.md.json"
    cached.write_text(cached.read_text().replace('"converter": "text"', '"converter": "old 1.0"'))
    assert convert(config) == [("docs/policy.md", "updated")]  # offsets depend on the converter


def test_unknown_file_types_are_skipped_with_a_reason(project):
    with_sources(project)
    write_doc(project, "logo.png", b"\x89PNG")
    [(path, outcome)] = convert(load_config(project.root))
    assert path == "docs/logo.png" and outcome.startswith("skipped")


def test_word_documents_convert_to_markdown_with_sections(project):
    docx = pytest.importorskip("docx")
    pytest.importorskip("mammoth")
    document = docx.Document()
    document.add_heading("Purchase approval BRD", level=1)
    document.add_heading("Approval threshold", level=2)
    document.add_paragraph("Every order above 5 000 EUR needs approval.")
    path = project.root / "docs" / "brd.docx"
    path.parent.mkdir(parents=True)
    document.save(str(path))
    with_sources(project)
    assert convert(load_config(project.root)) == [("docs/brd.docx", "converted")]
    doc = load(load_config(project.root), "docs/brd.docx")
    assert doc.converter.startswith("mammoth ")
    start = doc.text.index("5 000 EUR")
    assert doc.locate(start, start + 9)["section"] == "Purchase approval BRD > Approval threshold"


def test_pdf_pages_give_each_span_its_page(project):
    canvas = pytest.importorskip("reportlab.pdfgen.canvas")
    pytest.importorskip("pypdf")
    path = project.root / "docs" / "rules.pdf"
    path.parent.mkdir(parents=True)
    pdf = canvas.Canvas(str(path))
    pdf.drawString(72, 720, "Approval rules")
    pdf.showPage()
    pdf.drawString(72, 720, "Orders above 10 000 EUR need approval.")
    pdf.save()
    with_sources(project)
    assert convert(load_config(project.root)) == [("docs/rules.pdf", "converted")]
    doc = load(load_config(project.root), "docs/rules.pdf")
    assert doc.converter.startswith("pypdf ") and [p.page for p in doc.pages] == [1, 2]
    start = doc.text.index("10 000 EUR")
    assert doc.locate(start, start + 10)["page"] == 2


def test_demo_documents_match_their_generator():
    pytest.importorskip("docx")
    pytest.importorskip("reportlab")
    import importlib.util

    script = EXAMPLE.parents[1] / "scripts" / "gen-demo-docs.py"
    spec = importlib.util.spec_from_file_location("gen_demo_docs", script)
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    docs = EXAMPLE / "docs"
    assert (docs / "purchase-approval-brd.docx").read_bytes() == gen.brd()
    assert (docs / "approval-rules.pdf").read_bytes() == gen.rules()
