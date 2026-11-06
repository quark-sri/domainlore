from __future__ import annotations

import hashlib

import pytest

from domainlore.config import load_config
from domainlore.convert import IGNORED_DIRS, MAX_CODE_BYTES, convert, load, sections
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


def with_sources(project, path: str = "docs", basis: str = "intended") -> None:
    (project.root / "lore.toml").write_text(
        f'[knowledge]\ndir = "knowledge"\n[[sources]]\npath = "{path}"\nbasis = "{basis}"\n'
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


CODE = """# Approval limits
LIMIT = 10_000  # EUR


def needs_approval(total):
    return total > LIMIT
"""


def write(project, rel: str, data: str | bytes = "x = 1\n") -> None:
    target = project.root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data if isinstance(data, bytes) else data.encode())


def test_code_is_text_with_no_markdown_sections(project):
    with_sources(project, "src", "actual")
    write(project, "src/pkg/rules.py", CODE)
    write(project, "src/blob.py", b"\xff\xfe\x00")
    outcomes = dict(convert(load_config(project.root)))
    assert outcomes == {
        "src/pkg/rules.py": "converted",
        "src/blob.py": "skipped: not UTF-8 text",
    }
    doc = load(load_config(project.root), "src/pkg/rules.py")
    assert doc.sections == [] and doc.converter == "text" and doc.basis == "actual"
    start = doc.text.index("10_000")  # "# Approval limits" is a comment, not a heading
    assert doc.locate(start, start + 6)["lines"] == [2, 2]


@pytest.mark.parametrize("folder", sorted(IGNORED_DIRS) + [".venv", ".git"])
def test_hidden_dependency_and_build_folders_are_not_sources(project, folder):
    with_sources(project, "src", "actual")
    write(project, "src/rules.py", CODE)
    write(project, f"src/{folder}/lib.py")
    assert [rel for rel, _ in convert(load_config(project.root))] == ["src/rules.py"]


@pytest.mark.parametrize(
    "name",
    [".env", ".env.local", "config/secrets.yaml", "prod.pem", "tls.key", "credentials.json"]
    + ["db_password.txt", "main.tfvars", "id_rsa", "src/Secret.py"],
)
def test_files_that_may_hold_secrets_are_never_converted(project, name):
    with_sources(project, "src", "actual")
    write(project, f"src/{name}", "KEY = 'hunter2'\n")
    [(rel, outcome)] = convert(load_config(project.root))
    assert outcome == "skipped: the name looks like a secrets file"
    assert not (project.root / ".lore" / "cache").exists()


def test_code_is_read_only_under_an_actual_source_and_not_when_it_is_large(project):
    with_sources(project, "docs", "intended")
    write(project, "docs/notes.yaml", "limit: 5\n")
    [(rel, outcome)] = convert(load_config(project.root))
    assert outcome.startswith('skipped: code is read only under a `basis = "actual"`')
    with_sources(project, "src", "actual")
    write(project, "src/big.py", "x = 1\n" * (MAX_CODE_BYTES // 6 + 10))
    [(rel, outcome)] = convert(load_config(project.root))
    assert outcome == "skipped: larger than 200 KB"


def test_a_hidden_folder_named_as_the_source_path_still_converts(project):
    with_sources(project, ".legacy", "actual")
    write(project, ".legacy/rules.py", CODE)
    assert convert(load_config(project.root)) == [(".legacy/rules.py", "converted")]
