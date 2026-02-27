"""
Strategy 1 — PyMuPDF + heuristic section locator + Claude text extraction.

Pipeline:
  PDF → PyMuPDF native text extraction (+ Tesseract OCR fallback per page)
      → regex section locator (LLM fallback if low confidence)
      → Claude text-only extraction + ranking prompt
      → StrategyResult

Cost:   ~$0 for parsing; Claude text call ~$0.01–0.05 per doc
Speed:  1–5s extraction + LLM latency
Value:  Baseline. Shows whether native text + heuristics are enough.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from tests.pdf_strategies.result import CriterionResult, RankedDisqualifier, StrategyResult
from tests.pdf_strategies.strategies.base import BaseStrategy
from tests.pdf_strategies.strategies._shared_prompt import COMBINED_EXTRACTION_PROMPT, parse_llm_json


class PyMuPDFStrategy(BaseStrategy):
    name = "S1-PyMuPDF"

    def run(self, pdf_path: Path) -> StrategyResult:
        result = StrategyResult(strategy_name=self.name, pdf_name=pdf_path.name)
        t0 = time.perf_counter()

        try:
            # -- Step 1: extract text using existing pipeline --
            from docu_flow.pipeline.classifier import classify_pdf
            from docu_flow.pipeline.extractor import extract_text
            from docu_flow.pipeline.section_locator import locate_eligibility_section, get_section_pages

            pdf_type = classify_pdf(pdf_path)
            doc = extract_text(pdf_path, pdf_type)

            # -- Step 2: locate section --
            location = locate_eligibility_section(doc, llm_fallback=True)
            section_pages = get_section_pages(doc, location)

            result.section_found = location.confidence >= 0.5
            result.section_pages = [p.page_number for p in section_pages]
            result.section_name = location.section_name
            result.section_confidence = location.confidence

            if not section_pages:
                result.error = "Section not found"
                return result

            # -- Step 3: build section text for LLM --
            section_text = "\n\n".join(
                f"--- PAGE {p.page_number} ---\n{p.text}"
                for p in section_pages
                if p.text.strip()
            )

            # -- Step 4: LLM extraction + ranking (text-only, no vision) --
            from docu_flow.utils.llm_client import get_client
            from docu_flow.config import settings

            client = get_client()
            prompt = COMBINED_EXTRACTION_PROMPT.format(content=section_text)

            response = client.messages.create(
                model=settings.primary_llm_model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            result.raw_output_preview = raw[:500]

            # Approximate cost: input ~(len(section_text)/4) tokens, output ~1000 tokens
            input_tokens = len(section_text) // 4
            output_tokens = len(raw) // 4
            result.estimated_cost_usd = (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000

            _populate_from_json(result, parse_llm_json(raw))
            result.success = True

        except Exception as exc:  # noqa: BLE001
            result.error = str(exc)
        finally:
            result.latency_seconds = time.perf_counter() - t0

        return result


def _populate_from_json(result: StrategyResult, data: dict) -> None:
    result.section_name = data.get("section_name", result.section_name)
    if data.get("section_pages"):
        result.section_pages = data["section_pages"]
        result.section_found = True

    criteria_raw = data.get("criteria", [])
    criteria: list[CriterionResult] = []
    for c in criteria_raw:
        criteria.append(CriterionResult(
            id=c.get("id", ""),
            criterion_type=c.get("criterion_type", "exclusion"),
            text=c.get("text", ""),
            source_page=c.get("source_page"),
            has_temporal_condition=bool(c.get("has_temporal_condition")),
            has_numeric_threshold=bool(c.get("has_numeric_threshold")),
            has_conditional_logic=bool(c.get("has_conditional_logic")),
            is_ambiguous=bool(c.get("is_ambiguous")),
        ))

    result.criteria = criteria
    result.total_criteria = len(criteria)
    result.inclusion_count = sum(1 for c in criteria if c.criterion_type == "inclusion")
    result.exclusion_count = sum(1 for c in criteria if c.criterion_type == "exclusion")

    top8_raw = data.get("top_8_disqualifiers", [])
    result.top_8_disqualifiers = [
        RankedDisqualifier(
            rank=item.get("rank", i + 1),
            criterion_id=item.get("criterion_id", ""),
            criterion_text=item.get("criterion_text", ""),
            disqualification_power=item.get("disqualification_power", "unknown"),
            reasoning=item.get("reasoning", ""),
        )
        for i, item in enumerate(top8_raw)
    ]
