"""
Top-level orchestrator — ties all pipeline steps together.

run_protocol_pipeline:  PDF → ParsedDocument → ExtractedCriteria
run_screening_pipeline: ExtractedCriteria + patient → ScreeningResult
"""

from __future__ import annotations

from pathlib import Path

from docu_flow.logging import log
from docu_flow.pipeline.classifier import classify_pdf
from docu_flow.pipeline.criteria_extractor import extract_criteria
from docu_flow.pipeline.extractor import extract_text
from docu_flow.pipeline.ranker import rank_disqualifiers
from docu_flow.pipeline.screener import screen_patient
from docu_flow.pipeline.section_locator import get_section_pages, locate_eligibility_section
from docu_flow.schemas.criteria import ExtractedCriteria, ScreeningRequest, ScreeningResult
from docu_flow.schemas.pdf import ParsedDocument


def run_protocol_pipeline(pdf_path: Path, top_n_disqualifiers: int = 8) -> ExtractedCriteria:
    """
    Full pipeline: PDF file → structured ExtractedCriteria with ranked disqualifiers.

    Raises:
        ExtractionError: if the PDF cannot be read or the LLM fails after retries.
    """
    log.info("pipeline.start", pdf=str(pdf_path))

    # 1. Classify
    pdf_type = classify_pdf(pdf_path)

    # 2. Extract text (adaptive: native or OCR)
    document: ParsedDocument = extract_text(pdf_path, pdf_type=pdf_type)

    if document.extraction_warnings:
        log.warning("pipeline.extraction_warnings", warnings=document.extraction_warnings)

    # 3. Locate eligibility section
    location = locate_eligibility_section(document)
    section_pages = get_section_pages(document, location)

    if not section_pages:
        log.warning("pipeline.no_section_pages", using_full_doc=True)
        section_pages = document.pages

    # 4. Extract criteria via LLM
    extracted = extract_criteria(document, section_pages)

    # 5. Rank disqualifiers
    extracted = rank_disqualifiers(extracted, top_n=top_n_disqualifiers)

    log.info(
        "pipeline.complete",
        pdf=str(pdf_path),
        total_criteria=len(extracted.criteria),
        top_disqualifiers=len(extracted.top_disqualifiers),
    )
    return extracted


def run_screening_pipeline(
    request: ScreeningRequest,
    extracted: ExtractedCriteria,
) -> ScreeningResult:
    """Screen a patient against pre-extracted criteria."""
    return screen_patient(request, extracted)
