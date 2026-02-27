"""Unit tests for section locator (heuristic path only — no LLM calls)."""

import pytest

from docu_flow.pipeline.section_locator import locate_eligibility_section
from docu_flow.schemas.pdf import PDFType, PageText, ParsedDocument


def _make_doc(page_texts: list[str]) -> ParsedDocument:
    pages = [
        PageText(page_number=i + 1, text=t, char_count=len(t))
        for i, t in enumerate(page_texts)
    ]
    return ParsedDocument(
        source_filename="test.pdf",
        pdf_type=PDFType.TEXT,
        total_pages=len(pages),
        pages=pages,
    )


class TestHeuristicLocate:
    def test_finds_standard_section(self):
        doc = _make_doc([
            "Introduction to the study.",
            "Background and rationale.",
            "5. Inclusion and Exclusion Criteria\nPatients must be 18 or older.",
            "Exclusion: prior malignancy.",
            "6. Study Procedures\nBlood draws weekly.",
        ])
        result = locate_eligibility_section(doc, llm_fallback=False)
        assert result.start_page == 3
        assert result.confidence >= 0.7

    def test_fallback_on_no_section(self):
        doc = _make_doc([
            "Page 1 text with no criteria headings.",
            "Page 2 text continues the discussion.",
        ])
        result = locate_eligibility_section(doc, llm_fallback=False)
        assert result.start_page == 1
        assert result.confidence < 0.5
        assert result.method == "full_doc_fallback"

    def test_stop_at_procedures_section(self):
        doc = _make_doc([
            "Intro",
            "Inclusion Criteria\nAge >= 18",
            "Exclusion Criteria\nPregnant",
            "Study Procedures\nBlood draw",
            "More procedures",
        ])
        result = locate_eligibility_section(doc, llm_fallback=False)
        assert result.end_page <= 3
