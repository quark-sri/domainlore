"""Write the demo product's binary source documents, byte for byte the same on every run.

Usage: uv run python scripts/gen-demo-docs.py
The documents are fictional fixtures for `lore convert` and extraction tests.
"""

from __future__ import annotations

import io
import zipfile
from datetime import datetime
from pathlib import Path

import docx
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

DOCS = Path(__file__).resolve().parents[1] / "examples" / "order-approval" / "docs"
FIXED = datetime(2025, 3, 14, 9, 0, 0)

BRD = [
    ("h1", "Purchase approval BRD"),
    ("p", "Business requirements for purchase approvals. Version 2, 2025-03-14. Owner: Finance."),
    ("h2", "Scope"),
    (
        "p",
        "Buyers place orders for their company. "
        "Approvers accept or reject orders that need approval.",
    ),
    ("h2", "Approval threshold"),
    ("p", "Every order with a total above 5 000 EUR needs approval before it is processed."),
    ("h2", "Who may approve"),
    ("p", "The approver must not be the buyer who placed the order (four-eyes principle)."),
    ("h2", "Escalation"),
    (
        "p",
        "An approval request that is not decided within 3 working days "
        "is escalated to the finance lead.",
    ),
    ("h2", "Cancelling"),
    ("p", "Cancelling a submitted order asks the buyer to confirm."),
    ("h2", "Navigation"),
    ("p", "The order details page links back to the approver's inbox."),
]


# A PDF export of the Confluence page "Approval rules", one list of lines per page.
RULES = [
    [
        "Approval rules",
        "Confluence space ORD, version 12, last edited 2026-06-01.",
        "",
        "Which orders need approval",
        "Every order with a total above 10 000 EUR needs approval.",
        "Orders at or below 10 000 EUR are processed at once.",
    ],
    [
        "Who approves",
        "A team lead or the finance lead approves.",
        "The approver must not be the buyer who placed the order.",
    ],
]


def reproducible(data: bytes) -> bytes:
    """Rewrite a zip with fixed timestamps and order, so the bytes do not depend on the clock."""
    source = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target:
        for name in sorted(source.namelist()):
            info = zipfile.ZipInfo(name, FIXED.timetuple()[:6])
            info.compress_type = zipfile.ZIP_DEFLATED
            target.writestr(info, source.read(name))
    return out.getvalue()


def brd() -> bytes:
    document = docx.Document()
    props = document.core_properties
    props.author = props.last_modified_by = "demo"
    props.created = props.modified = FIXED
    props.title = "Purchase approval BRD"
    props.revision = 2
    for kind, text in BRD:
        if kind == "p":
            document.add_paragraph(text)
        else:
            document.add_heading(text, level=int(kind[1]))
    buffer = io.BytesIO()
    document.save(buffer)
    return reproducible(buffer.getvalue())


def rules() -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4, invariant=True)
    pdf.setTitle("Approval rules")
    pdf.setAuthor("demo")
    for lines in RULES:
        y = 780
        for line in lines:
            pdf.drawString(72, y, line)
            y -= 18
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def main() -> None:
    for name, data in (("purchase-approval-brd.docx", brd()), ("approval-rules.pdf", rules())):
        target = DOCS / name
        target.write_bytes(data)
        print(f"wrote {target.relative_to(DOCS.parents[2])}")


if __name__ == "__main__":
    main()
