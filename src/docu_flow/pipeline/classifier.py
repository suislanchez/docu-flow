"""
Step 1 — Classify the PDF type (text / scanned / hybrid / encrypted).

Decision logic:
  - Try to open with PyMuPDF.
  - For each page sample the text character count.
  - If avg chars/page < OCR_QUALITY_THRESHOLD  → scanned
  - If some pages are good and some are bad     → hybrid
  - If all pages have good text                 → text
  - If PyMuPDF raises a permissions error       → encrypted
"""

from pathlib import Path

import fitz  # PyMuPDF

from docu_flow.config import settings
from docu_flow.logging import log
from docu_flow.schemas.pdf import PDFType


def classify_pdf(pdf_path: Path) -> PDFType:
    """Return the PDFType for *pdf_path*."""
    try:
        doc = fitz.open(str(pdf_path))
    except fitz.FileDataError:
        log.warning("classify_pdf.open_failed", path=str(pdf_path))
        return PDFType.UNKNOWN

    if doc.is_encrypted:
        log.info("classify_pdf.encrypted", path=str(pdf_path))
        return PDFType.ENCRYPTED

    total_pages = len(doc)
    if total_pages == 0:
        return PDFType.UNKNOWN

    # Sample up to 10 evenly-spaced pages to keep this fast.
    sample_indices = _sample_indices(total_pages, n=10)
    char_counts = []
    for i in sample_indices:
        page = doc[i]
        text = page.get_text("text")
        char_counts.append(len(text))

    doc.close()

    threshold = settings.ocr_quality_threshold
    good = sum(1 for c in char_counts if c >= threshold)
    bad = sum(1 for c in char_counts if c < threshold)

    if bad == 0:
        pdf_type = PDFType.TEXT
    elif good == 0:
        pdf_type = PDFType.SCANNED
    else:
        pdf_type = PDFType.HYBRID

    log.info(
        "classify_pdf.result",
        path=str(pdf_path),
        pdf_type=pdf_type,
        sampled_pages=len(sample_indices),
        good_pages=good,
        bad_pages=bad,
    )
    return pdf_type


def _sample_indices(total: int, n: int) -> list[int]:
    if total <= n:
        return list(range(total))
    step = total / n
    return [int(i * step) for i in range(n)]
