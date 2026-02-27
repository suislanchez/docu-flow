"""
Integration tests — Easy PDF (J3R-MC-YDAO protocol, ~1.8 MB).

Fixture: tests/fixtures/ydao_protocol_easy.pdf
  A standard clinical trial protocol with a native text layer.
  Expected to extract cleanly without OCR.

API keys exercised
──────────────────
ANTHROPIC_API_KEY  → criteria extraction (claude-sonnet-4-6),
                     section location LLM fallback (claude-haiku-4-5),
                     patient screening.
GOOGLE_API_KEY     → Gemini cross-validation of extracted criteria.

Run these tests:
    pytest tests/integration/test_easy_pdf.py -m integration -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from docu_flow.pipeline.classifier import classify_pdf
from docu_flow.pipeline.extractor import extract_text
from docu_flow.pipeline.section_locator import locate_eligibility_section, get_section_pages
from docu_flow.pipeline.criteria_extractor import extract_criteria
from docu_flow.pipeline.orchestrator import run_protocol_pipeline, run_screening_pipeline
from docu_flow.schemas.criteria import (
    CriterionType,
    ScreeningDecision,
    ScreeningRequest,
)
from docu_flow.schemas.pdf import PDFType


# ---------------------------------------------------------------------------
# Stage 1: Classification (no API key needed)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_classify_easy_pdf(easy_pdf_path: Path) -> None:
    """YDAO PDF must be classified as TEXT (native text layer present)."""
    pdf_type = classify_pdf(easy_pdf_path)
    assert pdf_type == PDFType.TEXT, (
        f"Expected TEXT, got {pdf_type}. "
        "If HYBRID or SCANNED, OCR threshold or page sampling may need tuning."
    )


# ---------------------------------------------------------------------------
# Stage 2: Text extraction (no API key needed)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_extract_text_easy_pdf(easy_pdf_path: Path) -> None:
    """Text extraction must succeed with no OCR pages and no empty pages."""
    doc = extract_text(easy_pdf_path)

    assert doc.total_pages > 0, "Parsed document has no pages."
    assert doc.pdf_type == PDFType.TEXT

    # No page should be blank after native extraction
    blank_pages = [p.page_number for p in doc.pages if not p.text.strip()]
    assert len(blank_pages) == 0, f"Blank pages found: {blank_pages}"

    # Native extraction → no OCR should be triggered
    ocr_pages = [p.page_number for p in doc.pages if p.ocr_used]
    assert len(ocr_pages) == 0, (
        f"OCR was triggered on {len(ocr_pages)} page(s) in a TEXT-type PDF: {ocr_pages}"
    )

    # Average chars/page should be well above the OCR threshold
    avg_chars = sum(p.char_count for p in doc.pages) / doc.total_pages
    assert avg_chars >= 200, f"Unexpectedly low average chars/page: {avg_chars:.0f}"


@pytest.mark.integration
def test_extraction_warnings_easy_pdf(easy_pdf_path: Path) -> None:
    """A clean native-text PDF should produce zero extraction warnings."""
    doc = extract_text(easy_pdf_path)
    assert doc.extraction_warnings == [], (
        f"Unexpected extraction warnings: {doc.extraction_warnings}"
    )


# ---------------------------------------------------------------------------
# Stage 3: Section location (no API key needed for heuristic path)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_locate_eligibility_section_easy_pdf(easy_pdf_path: Path) -> None:
    """
    Heuristic section locator must find the eligibility section with ≥0.7 confidence
    so the LLM fallback is NOT triggered (saving tokens).
    """
    doc = extract_text(easy_pdf_path)
    location = locate_eligibility_section(doc, llm_fallback=False)

    assert location.start_page >= 1
    assert location.end_page >= location.start_page
    assert location.confidence >= 0.7, (
        f"Heuristic confidence too low ({location.confidence:.2f}); "
        "LLM fallback would be triggered in production — check section header patterns."
    )
    assert location.method == "heuristic", (
        f"Expected heuristic method, got '{location.method}'. "
        "LLM fallback should not be needed for this protocol."
    )
    assert location.section_name is not None, "Section name not captured from header."


@pytest.mark.integration
def test_section_pages_non_empty(easy_pdf_path: Path) -> None:
    """Section pages slice must be non-empty and shorter than the full document."""
    doc = extract_text(easy_pdf_path)
    location = locate_eligibility_section(doc, llm_fallback=False)
    section_pages = get_section_pages(doc, location)

    assert len(section_pages) > 0, "No section pages returned."
    assert len(section_pages) < doc.total_pages, (
        "Section spans the entire document — section locator likely fell back to full-doc."
    )


# ---------------------------------------------------------------------------
# Stage 4: LLM criteria extraction  (requires ANTHROPIC_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.anthropic
def test_extract_criteria_easy_pdf(easy_pdf_path: Path, anthropic_key: str) -> None:
    """
    Criteria extraction via claude-sonnet-4-6 must return a non-empty list
    with both inclusion and exclusion criteria, all citing a source page.

    API: Anthropic (ANTHROPIC_API_KEY)
    Model: claude-sonnet-4-6
    """
    doc = extract_text(easy_pdf_path)
    location = locate_eligibility_section(doc, llm_fallback=False)
    section_pages = get_section_pages(doc, location)

    result = extract_criteria(doc, section_pages)

    assert len(result.criteria) > 0, "LLM returned no criteria."

    inclusions = result.inclusion_criteria()
    exclusions = result.exclusion_criteria()
    assert len(inclusions) > 0, "No inclusion criteria extracted."
    assert len(exclusions) > 0, "No exclusion criteria extracted."

    # Hallucination guard: every criterion must cite a source page
    missing_citation = [c.id for c in result.criteria if c.source_page is None]
    assert missing_citation == [], (
        f"Criteria missing source_page citation (potential hallucination): {missing_citation}"
    )

    # Confidence should be reasonable for a clean PDF
    assert result.metadata.extraction_confidence >= 0.6, (
        f"Extraction confidence too low: {result.metadata.extraction_confidence:.2f}"
    )


@pytest.mark.integration
@pytest.mark.anthropic
def test_criteria_verbatim_in_source(easy_pdf_path: Path, anthropic_key: str) -> None:
    """
    Hallucination guard: the first 30 chars of every extracted criterion text
    must appear in the source document text.

    This is the primary anti-hallucination check — LLM must not fabricate content.

    API: Anthropic (ANTHROPIC_API_KEY)
    """
    doc = extract_text(easy_pdf_path)
    location = locate_eligibility_section(doc, llm_fallback=False)
    section_pages = get_section_pages(doc, location)
    result = extract_criteria(doc, section_pages)

    full_text = doc.full_text.lower()
    hallucinated = []
    for criterion in result.criteria:
        # Use first 30 chars as a fingerprint — enough to flag invention
        snippet = criterion.text[:30].lower().strip()
        if snippet and snippet not in full_text:
            hallucinated.append({"id": criterion.id, "snippet": snippet})

    assert hallucinated == [], (
        f"Possible hallucinated criteria (text not found in source):\n"
        + json.dumps(hallucinated, indent=2)
    )


# ---------------------------------------------------------------------------
# Stage 5: Full pipeline  (requires ANTHROPIC_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.anthropic
def test_full_pipeline_easy_pdf(easy_pdf_path: Path, anthropic_key: str) -> None:
    """
    End-to-end pipeline smoke test: PDF → ExtractedCriteria with top disqualifiers.

    API: Anthropic (ANTHROPIC_API_KEY)
    Models: claude-sonnet-4-6 (extraction), claude-haiku-4-5 (section fallback if needed)
    """
    result = run_protocol_pipeline(easy_pdf_path, top_n_disqualifiers=8)

    assert result.criteria, "Pipeline returned no criteria."
    assert result.top_disqualifiers, "No top disqualifiers ranked."
    assert len(result.top_disqualifiers) <= 8

    # All top disqualifiers must be exclusion criteria
    for c in result.top_disqualifiers:
        assert c.criterion_type == CriterionType.EXCLUSION, (
            f"Criterion {c.id} in top_disqualifiers is not an exclusion criterion."
        )

    # Pipeline metadata
    assert result.metadata.model_used, "model_used not recorded in metadata."
    assert result.metadata.section_found is True, "Pipeline did not confirm section was found."


@pytest.mark.integration
@pytest.mark.anthropic
def test_screening_disqualified_patient(easy_pdf_path: Path, anthropic_key: str) -> None:
    """
    A patient with obvious disqualifying conditions must be screened as DISQUALIFIED
    with high confidence.

    API: Anthropic (ANTHROPIC_API_KEY)
    Model: claude-sonnet-4-6
    """
    extracted = run_protocol_pipeline(easy_pdf_path)

    request = ScreeningRequest(
        patient_id="test-patient-001",
        protocol_id="J3R-MC-YDAO",
        patient_data={
            "age": 75,
            "diagnosis": "Advanced hepatocellular carcinoma with active hepatitis B (HBsAg positive)",
            "prior_malignancy": True,
            "prior_malignancy_type": "breast cancer (5 years ago)",
            "current_medications": ["warfarin", "insulin"],
            "eGFR": 22,  # severe renal impairment
            "ECOG_performance_status": 3,
            "pregnancy_status": "not applicable",
            "active_infections": ["active tuberculosis"],
        },
    )

    result = run_screening_pipeline(request, extracted)

    assert result.decision in (ScreeningDecision.DISQUALIFIED, ScreeningDecision.ESCALATE), (
        f"Heavily ineligible patient returned unexpected decision: {result.decision}"
    )
    assert result.model_used is not None


@pytest.mark.integration
@pytest.mark.anthropic
def test_screening_likely_eligible_patient(easy_pdf_path: Path, anthropic_key: str) -> None:
    """
    A patient with no obvious disqualifying conditions should pass pre-screen
    or be escalated (never hard-disqualified without cause).

    API: Anthropic (ANTHROPIC_API_KEY)
    """
    extracted = run_protocol_pipeline(easy_pdf_path)

    request = ScreeningRequest(
        patient_id="test-patient-002",
        protocol_id="J3R-MC-YDAO",
        patient_data={
            "age": 52,
            "diagnosis": "Stage IIB non-small cell lung cancer, newly diagnosed",
            "prior_malignancy": False,
            "current_medications": ["lisinopril 10mg"],
            "eGFR": 85,
            "ECOG_performance_status": 1,
            "pregnancy_status": "not applicable",
            "active_infections": [],
            "autoimmune_disease": False,
            "HIV": False,
            "hepatitis_B": False,
            "hepatitis_C": False,
        },
    )

    result = run_screening_pipeline(request, extracted)

    # Should not be hard-disqualified without a stated reason
    if result.decision == ScreeningDecision.DISQUALIFIED:
        assert result.failed_criteria, (
            "Patient was DISQUALIFIED but no failed_criteria were provided."
        )


# ---------------------------------------------------------------------------
# Stage 6: Gemini cross-validation  (requires GOOGLE_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.google
def test_gemini_criteria_extraction_easy_pdf(easy_pdf_path: Path, google_key: str) -> None:
    """
    Use Google Gemini to independently extract eligibility criteria from the
    YDAO protocol and verify structural validity of the response.

    This acts as a cross-validation layer against the Anthropic extraction —
    significant divergence in criterion count would warrant investigation.

    API: Google (GOOGLE_API_KEY)
    Model: gemini-2.0-flash
    """
    from docu_flow.pipeline.extractor import extract_text
    from docu_flow.pipeline.section_locator import locate_eligibility_section, get_section_pages
    from docu_flow.utils.gemini_client import get_gemini_model

    doc = extract_text(easy_pdf_path)
    location = locate_eligibility_section(doc, llm_fallback=False)
    section_pages = get_section_pages(doc, location)

    # Build section text (same format used by Anthropic extractor)
    section_text = "\n\n".join(
        f"--- PAGE {p.page_number} ---\n{p.text}"
        for p in section_pages
        if p.text.strip()
    )

    prompt = (
        "You are a clinical trial protocol analyst. Extract ALL eligibility criteria "
        "from the following protocol section.\n\n"
        "Return ONLY a JSON object with this structure:\n"
        '{"inclusion_count": <int>, "exclusion_count": <int>, '
        '"sample_exclusions": ["verbatim text of up to 3 exclusion criteria"]}\n\n'
        f"PROTOCOL SECTION:\n{section_text[:12000]}"  # stay within context budget
    )

    model = get_gemini_model()
    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    data = json.loads(raw)

    assert data.get("inclusion_count", 0) > 0, (
        f"Gemini returned 0 inclusion criteria. Raw: {raw[:300]}"
    )
    assert data.get("exclusion_count", 0) > 0, (
        f"Gemini returned 0 exclusion criteria. Raw: {raw[:300]}"
    )
    assert isinstance(data.get("sample_exclusions"), list), (
        "Gemini response missing sample_exclusions list."
    )


@pytest.mark.integration
@pytest.mark.anthropic
@pytest.mark.google
def test_anthropic_gemini_criteria_count_agreement(
    easy_pdf_path: Path,
    anthropic_key: str,
    google_key: str,
) -> None:
    """
    Cross-model sanity check: Anthropic and Gemini criterion counts must be
    within 40% of each other. Larger divergence suggests one model hallucinated
    or missed a section.

    APIs: Anthropic (ANTHROPIC_API_KEY) + Google (GOOGLE_API_KEY)
    """
    from docu_flow.utils.gemini_client import get_gemini_model

    # --- Anthropic extraction ---
    doc = extract_text(easy_pdf_path)
    location = locate_eligibility_section(doc, llm_fallback=False)
    section_pages = get_section_pages(doc, location)
    anthropic_result = extract_criteria(doc, section_pages)
    anthropic_count = len(anthropic_result.criteria)

    # --- Gemini extraction ---
    section_text = "\n\n".join(
        f"--- PAGE {p.page_number} ---\n{p.text}"
        for p in section_pages
        if p.text.strip()
    )
    prompt = (
        "Count the total number of eligibility criteria (inclusion + exclusion combined) "
        "in this protocol section. Return ONLY JSON: {\"total_criteria\": <int>}\n\n"
        f"PROTOCOL SECTION:\n{section_text[:12000]}"
    )
    model = get_gemini_model()
    response = model.generate_content(prompt)
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    gemini_count = json.loads(raw).get("total_criteria", 0)

    # Allow ±40% divergence
    if anthropic_count > 0 and gemini_count > 0:
        ratio = abs(anthropic_count - gemini_count) / max(anthropic_count, gemini_count)
        assert ratio <= 0.40, (
            f"Anthropic ({anthropic_count}) and Gemini ({gemini_count}) criteria counts "
            f"diverge by {ratio:.0%} — investigate for hallucination or missed section."
        )
