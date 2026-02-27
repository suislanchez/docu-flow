"""
Step 2 — Adaptive text extraction.

Strategy:
  - For TEXT pdfs:    pure PyMuPDF text extraction.
  - For SCANNED pdfs: render each page → Tesseract OCR.
  - For HYBRID pdfs:  per-page decision — use native text if chars >= threshold,
                      else fall back to OCR for that page.
  - For ENCRYPTED:    raise ExtractionError immediately.
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

from docu_flow.config import settings
from docu_flow.logging import log
from docu_flow.schemas.pdf import PDFType, PageText, ParsedDocument


class ExtractionError(RuntimeError):
    """Raised when a PDF cannot be extracted at all."""


def extract_text(pdf_path: Path, pdf_type: PDFType | None = None) -> ParsedDocument:
    """Extract text from *pdf_path*, using OCR as needed."""
    if pdf_type is None:
        from docu_flow.pipeline.classifier import classify_pdf
        pdf_type = classify_pdf(pdf_path)

    if pdf_type == PDFType.ENCRYPTED:
        raise ExtractionError(f"PDF is encrypted and cannot be read: {pdf_path}")

    try:
        doc = fitz.open(str(pdf_path))
    except fitz.FileDataError as exc:
        raise ExtractionError(f"Cannot open PDF: {pdf_path}") from exc

    pages: list[PageText] = []
    warnings: list[str] = []
    threshold = settings.ocr_quality_threshold

    for page_index in range(len(doc)):
        page = doc[page_index]
        native_text = page.get_text("text").strip()
        page_number = page_index + 1

        if len(native_text) >= threshold:
            pages.append(PageText(
                page_number=page_number,
                text=native_text,
                char_count=len(native_text),
                ocr_used=False,
                confidence=1.0,
            ))
        else:
            # Fall back to OCR for this page
            log.debug("extractor.ocr_fallback", page=page_number, native_chars=len(native_text))
            ocr_result = _ocr_page(page, page_number)
            if ocr_result is None:
                warnings.append(f"Page {page_number}: OCR produced no usable text.")
                pages.append(PageText(
                    page_number=page_number,
                    text="",
                    char_count=0,
                    ocr_used=True,
                    confidence=0.0,
                ))
            else:
                pages.append(ocr_result)

    doc.close()

    parsed = ParsedDocument(
        source_filename=pdf_path.name,
        pdf_type=pdf_type,
        total_pages=len(pages),
        pages=pages,
        extraction_warnings=warnings,
    )
    log.info(
        "extractor.done",
        filename=pdf_path.name,
        total_pages=parsed.total_pages,
        ocr_pages=sum(1 for p in pages if p.ocr_used),
        warnings=len(warnings),
    )
    return parsed


def _ocr_page(page: fitz.Page, page_number: int) -> PageText | None:
    """Render *page* to an image and run Tesseract OCR."""
    try:
        import pytesseract
        from PIL import Image
        import io

        if settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

        # Render at 300 DPI for acceptable OCR quality
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        img_bytes = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_bytes))

        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        words = [w for w in data["text"] if w.strip()]
        confidences = [c for c, w in zip(data["conf"], data["text"]) if w.strip() and c != -1]
        text = " ".join(words)
        avg_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0

        return PageText(
            page_number=page_number,
            text=text,
            char_count=len(text),
            ocr_used=True,
            confidence=avg_conf,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("extractor.ocr_error", page=page_number, error=str(exc))
        return None
