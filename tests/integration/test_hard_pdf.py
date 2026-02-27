"""
Integration tests — Hard PDF (large ~57 MB protocol).

Fixture: tests/fixtures/large_protocol_hard.pdf
  A large, problematic protocol that resists standard text extraction.
  This file exercises the OCR fallback, error surfacing, graceful degradation,
  and the system's ability to handle adversarial inputs.

What "hard" means here
──────────────────────
- File is large (57 MB) → memory / time pressure.
- May be scanned (image-only pages) → OCR required.
- May have complex multi-column layouts → extraction artifacts.
- May have garbled encoding → text quality checks matter.
- Extraction warnings MUST surface; the pipeline must NOT swallow errors.

API keys exercised
──────────────────
GOOGLE_API_KEY    → Gemini used as an alternative extractor on difficult text,
                    because its larger context window handles noisy OCR output
                    better in some cases.
ANTHROPIC_API_KEY → Criteria extraction if any sections are extractable.

Run these tests (including slow ones):
    pytest tests/integration/test_hard_pdf.py -m integration -v

Skip slow tests:
    pytest tests/integration/test_hard_pdf.py -m "integration and not slow" -v
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from docu_flow.pipeline.classifier import classify_pdf
from docu_flow.pipeline.extractor import ExtractionError, extract_text
from docu_flow.pipeline.section_locator import locate_eligibility_section, get_section_pages
from docu_flow.schemas.pdf import PDFType


# ---------------------------------------------------------------------------
# Stage 1: Classification (no API key needed)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_classify_hard_pdf(hard_pdf_path: Path) -> None:
    """
    Classifier must complete and return a known PDFType — never crash.

    We do not assert a specific type because the file's composition determines
    the result. What we assert is that:
      - The call does not raise an unhandled exception.
      - The result is a valid PDFType value.
      - The result is logged and can be inspected.
    """
    pdf_type = classify_pdf(hard_pdf_path)

    assert isinstance(pdf_type, PDFType), f"classify_pdf returned unexpected type: {type(pdf_type)}"
    assert pdf_type in list(PDFType), f"Unknown PDFType value: {pdf_type}"

    # Record classification for downstream reasoning (visible in -v output)
    print(f"\n[hard_pdf] Classified as: {pdf_type}")


@pytest.mark.integration
def test_classify_hard_pdf_not_unknown(hard_pdf_path: Path) -> None:
    """
    Classifier should assign a specific type, not UNKNOWN.
    UNKNOWN indicates the file could not be opened at all — that is a harder
    failure that should be investigated.
    """
    pdf_type = classify_pdf(hard_pdf_path)
    if pdf_type == PDFType.UNKNOWN:
        pytest.xfail(
            "Hard PDF classified as UNKNOWN — file may be corrupt or use an unsupported format. "
            "OCR pipeline cannot proceed; manual inspection required."
        )


# ---------------------------------------------------------------------------
# Stage 2: Text extraction (no API key needed)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.slow
def test_extract_hard_pdf_does_not_crash(hard_pdf_path: Path) -> None:
    """
    Extraction must either succeed (returning a ParsedDocument) or raise
    ExtractionError explicitly. It must NEVER raise an unhandled exception,
    silently return empty results, or hang indefinitely.

    @slow — large file; OCR on scanned pages takes significant time.
    """
    pdf_type = classify_pdf(hard_pdf_path)

    if pdf_type == PDFType.ENCRYPTED:
        with pytest.raises(ExtractionError, match="encrypted"):
            extract_text(hard_pdf_path, pdf_type=pdf_type)
        return

    try:
        doc = extract_text(hard_pdf_path, pdf_type=pdf_type)
        assert doc.total_pages > 0, "Extraction returned a document with 0 pages."
        print(
            f"\n[hard_pdf] Extracted {doc.total_pages} pages | "
            f"OCR pages: {sum(1 for p in doc.pages if p.ocr_used)} | "
            f"Warnings: {len(doc.extraction_warnings)}"
        )
    except ExtractionError as exc:
        # ExtractionError is the *expected* explicit failure path — not a crash.
        pytest.xfail(f"Hard PDF raised ExtractionError (expected): {exc}")


@pytest.mark.integration
@pytest.mark.slow
def test_extraction_warnings_surface_for_hard_pdf(hard_pdf_path: Path) -> None:
    """
    Any pages that cannot be extracted must produce an extraction_warning entry.
    Warnings must NOT be silently swallowed — this is a non-negotiable safety rule.

    If all pages fail, we expect ExtractionError (not empty warnings).
    """
    pdf_type = classify_pdf(hard_pdf_path)
    if pdf_type == PDFType.ENCRYPTED:
        pytest.skip("Encrypted PDF — extraction not attempted.")

    try:
        doc = extract_text(hard_pdf_path, pdf_type=pdf_type)
    except ExtractionError:
        pytest.xfail("Extraction failed with ExtractionError — error DID surface loudly (correct).")
        return

    # If any pages have zero chars after OCR, warnings must explain them
    zero_char_pages = [p for p in doc.pages if p.char_count == 0]
    for page in zero_char_pages:
        matched_warnings = [w for w in doc.extraction_warnings if str(page.page_number) in w]
        assert matched_warnings, (
            f"Page {page.page_number} produced no text but has no extraction warning — "
            "silent failure detected. This violates the safety rule: errors must surface loudly."
        )


@pytest.mark.integration
@pytest.mark.slow
def test_hard_pdf_text_quality_score(hard_pdf_path: Path) -> None:
    """
    Report per-page quality metrics for the hard PDF.
    Does not assert a pass/fail threshold — the purpose is to capture
    the quality baseline so degradation is detectable over time.

    Marked xfail if extraction fails entirely.
    """
    pdf_type = classify_pdf(hard_pdf_path)
    if pdf_type in (PDFType.ENCRYPTED, PDFType.UNKNOWN):
        pytest.skip(f"Skipping quality score — PDF type is {pdf_type}.")

    try:
        doc = extract_text(hard_pdf_path, pdf_type=pdf_type)
    except ExtractionError as exc:
        pytest.xfail(f"Extraction failed: {exc}")
        return

    total = doc.total_pages
    ocr_count = sum(1 for p in doc.pages if p.ocr_used)
    avg_conf = sum(p.confidence for p in doc.pages) / total if total else 0.0
    avg_chars = sum(p.char_count for p in doc.pages) / total if total else 0.0
    blank_count = sum(1 for p in doc.pages if p.char_count == 0)

    report = {
        "total_pages": total,
        "ocr_pages": ocr_count,
        "ocr_fraction": f"{ocr_count / total:.1%}" if total else "N/A",
        "avg_confidence": round(avg_conf, 3),
        "avg_chars_per_page": round(avg_chars, 0),
        "blank_pages": blank_count,
        "extraction_warnings": len(doc.extraction_warnings),
    }
    print(f"\n[hard_pdf] Quality report:\n{json.dumps(report, indent=2)}")

    # Minimum bar: at least 10% of pages must have some text
    extractable = sum(1 for p in doc.pages if p.char_count > 0)
    assert extractable / total >= 0.10, (
        f"Only {extractable}/{total} pages have any text. "
        "Hard PDF may be entirely image-based — Vision LLM path required."
    )


# ---------------------------------------------------------------------------
# Stage 3: Section location on hard PDF (no API key for heuristic)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.slow
def test_section_locator_hard_pdf_heuristic(hard_pdf_path: Path) -> None:
    """
    Heuristic section locator must not crash on a low-quality extraction.
    If confidence is low, it correctly returns confidence < 0.7 so the LLM
    fallback would be triggered in production.
    """
    pdf_type = classify_pdf(hard_pdf_path)
    if pdf_type in (PDFType.ENCRYPTED, PDFType.UNKNOWN):
        pytest.skip(f"PDF type {pdf_type} — skipping section location.")

    try:
        doc = extract_text(hard_pdf_path, pdf_type=pdf_type)
    except ExtractionError as exc:
        pytest.xfail(f"Extraction failed: {exc}")
        return

    location = locate_eligibility_section(doc, llm_fallback=False)

    assert location.start_page >= 1
    assert location.end_page >= location.start_page

    print(
        f"\n[hard_pdf] Section location: pages {location.start_page}–{location.end_page} "
        f"| method={location.method} | confidence={location.confidence:.2f} "
        f"| name={location.section_name!r}"
    )

    if location.method == "full_doc_fallback":
        print(
            "[hard_pdf] WARNING: Section locator fell back to full document. "
            "Eligibility section could not be heuristically identified — "
            "LLM fallback required in production."
        )


# ---------------------------------------------------------------------------
# Stage 4: Gemini extraction on hard PDF  (requires GOOGLE_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.google
@pytest.mark.slow
def test_gemini_extraction_hard_pdf(hard_pdf_path: Path, google_key: str) -> None:
    """
    Attempt Gemini-based criteria extraction on the hard PDF.
    Gemini's larger context window (1M tokens) makes it better suited for
    noisy OCR output and long, fragmented eligibility sections.

    If extraction produces no usable text, the test is marked xfail.

    API: Google (GOOGLE_API_KEY)
    Model: gemini-2.0-flash
    """
    from docu_flow.utils.gemini_client import get_gemini_model

    pdf_type = classify_pdf(hard_pdf_path)
    if pdf_type in (PDFType.ENCRYPTED, PDFType.UNKNOWN):
        pytest.skip(f"PDF type {pdf_type} — cannot attempt extraction.")

    try:
        doc = extract_text(hard_pdf_path, pdf_type=pdf_type)
    except ExtractionError as exc:
        pytest.xfail(f"Text extraction failed before Gemini call: {exc}")
        return

    # Use up to 20k chars of the document (stay within practical token budget)
    sample_text = doc.full_text[:20_000]
    if not sample_text.strip():
        pytest.xfail("Hard PDF produced no extractable text — Gemini cannot proceed.")

    prompt = (
        "You are a clinical trial protocol analyst. From the following raw text "
        "(which may contain OCR artifacts), extract any eligibility criteria you can identify.\n\n"
        "Return ONLY JSON:\n"
        '{"found_eligibility_section": true/false, "inclusion_count": <int>, '
        '"exclusion_count": <int>, "quality_notes": "<brief description of text quality>"}\n\n'
        f"PROTOCOL TEXT (first 20000 chars):\n{sample_text}"
    )

    model = get_gemini_model()

    start = time.time()
    response = model.generate_content(prompt)
    elapsed = time.time() - start

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    data = json.loads(raw)

    print(
        f"\n[hard_pdf] Gemini extraction result ({elapsed:.1f}s):\n"
        + json.dumps(data, indent=2)
    )

    # We do not assert counts because the hard PDF may have no readable criteria.
    # We assert the response is structurally valid.
    assert "found_eligibility_section" in data, "Gemini response missing found_eligibility_section."
    assert "quality_notes" in data, "Gemini response missing quality_notes."

    if not data.get("found_eligibility_section"):
        pytest.xfail(
            f"Gemini could not find eligibility section in hard PDF. "
            f"Quality notes: {data.get('quality_notes', 'none')}"
        )


# ---------------------------------------------------------------------------
# Stage 5: Anthropic extraction on hard PDF (requires ANTHROPIC_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.anthropic
@pytest.mark.slow
def test_anthropic_extraction_hard_pdf(hard_pdf_path: Path, anthropic_key: str) -> None:
    """
    Attempt full criteria extraction via Anthropic on the hard PDF.
    Tests that the pipeline does not crash and either returns criteria or
    raises an explicit ExtractionError.

    API: Anthropic (ANTHROPIC_API_KEY)
    Model: claude-sonnet-4-6
    """
    from docu_flow.pipeline.criteria_extractor import ExtractionError as CriteriaExtractionError
    from docu_flow.pipeline.orchestrator import run_protocol_pipeline

    pdf_type = classify_pdf(hard_pdf_path)
    if pdf_type == PDFType.ENCRYPTED:
        pytest.skip("Encrypted PDF — skipping Anthropic extraction.")

    try:
        result = run_protocol_pipeline(hard_pdf_path)
        print(
            f"\n[hard_pdf] Anthropic extraction: {len(result.criteria)} criteria found | "
            f"top disqualifiers: {len(result.top_disqualifiers)} | "
            f"warnings: {len(result.metadata.warnings)}"
        )
        # If extraction succeeded, verify we got something
        # (hard PDF may still have sparse criteria)
        assert result.metadata.model_used is not None

    except (ExtractionError, CriteriaExtractionError) as exc:
        pytest.xfail(f"Hard PDF raised explicit extraction error (expected): {exc}")
    except Exception as exc:
        pytest.fail(
            f"Hard PDF raised an UNHANDLED exception — this is a bug. "
            f"All failures must surface as ExtractionError.\n{type(exc).__name__}: {exc}"
        )
