"""
Strategy 2 — Claude Vision (claude-sonnet-4-6 with PDF document input).

Pipeline:
  PDF → base64 encode → Claude document API (vision + native text combined)
      → single prompt: find section + extract all criteria + rank top 8
      → StrategyResult

The key difference from S1: Claude sees the full PDF visually — no prior text
extraction step. It handles multi-column layouts, scanned pages, and complex
tables natively.

Cost:   ~$1.65–$2.25 per 100-page doc (input tokens + vision)
        With prompt caching on the document block: ~$0.30 on repeated queries.
Speed:  15–60s depending on doc length (serial page processing)
Limit:  100 pages max per request — docs > 100 pages are split into two calls.
"""

from __future__ import annotations

import base64
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[4] / "src"))

from tests.pdf_strategies.result import CriterionResult, RankedDisqualifier, StrategyResult
from tests.pdf_strategies.strategies.base import BaseStrategy
from tests.pdf_strategies.strategies._shared_prompt import COMBINED_EXTRACTION_PROMPT, parse_llm_json

# Pricing as of 2026-02 (claude-sonnet-4-6)
_INPUT_COST_PER_TOKEN = 3.0 / 1_000_000
_OUTPUT_COST_PER_TOKEN = 15.0 / 1_000_000
_CACHED_INPUT_COST_PER_TOKEN = 0.30 / 1_000_000
# Vision: ~1,600 tokens per page image at standard resolution
_VISION_TOKENS_PER_PAGE = 1_600


class ClaudeVisionStrategy(BaseStrategy):
    name = "S2-Claude"

    def run(self, pdf_path: Path) -> StrategyResult:
        result = StrategyResult(strategy_name=self.name, pdf_name=pdf_path.name)
        t0 = time.perf_counter()

        try:
            from docu_flow.utils.llm_client import get_client
            from docu_flow.config import settings

            pdf_bytes = pdf_path.read_bytes()
            pdf_b64 = base64.standard_b64encode(pdf_bytes).decode()

            # Detect page count to decide if we need to split (100-page limit)
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count = len(doc)
            doc.close()

            client = get_client()
            prompt_text = COMBINED_EXTRACTION_PROMPT.format(content="[See the attached PDF document above]")

            if page_count <= 100:
                raw = _single_call(client, settings.primary_llm_model, pdf_b64, prompt_text)
            else:
                # Split: first call finds the section, second call extracts from it
                raw = _split_call(client, settings.primary_llm_model, pdf_bytes, prompt_text, page_count)

            result.raw_output_preview = raw[:500]

            # Estimate cost: page_count * vision_tokens + text tokens
            input_tokens = page_count * _VISION_TOKENS_PER_PAGE + len(prompt_text) // 4
            output_tokens = len(raw) // 4
            result.estimated_cost_usd = (
                input_tokens * _INPUT_COST_PER_TOKEN
                + output_tokens * _OUTPUT_COST_PER_TOKEN
            )

            data = parse_llm_json(raw)
            _populate_from_json(result, data)
            result.success = True

        except Exception as exc:  # noqa: BLE001
            result.error = str(exc)
        finally:
            result.latency_seconds = time.perf_counter() - t0

        return result


def _single_call(client, model: str, pdf_b64: str, prompt: str) -> str:
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    return response.content[0].text.strip()


def _split_call(client, model: str, pdf_bytes: bytes, prompt: str, page_count: int) -> str:
    """For PDFs > 100 pages: extract pages 1-100 first, find section, then extract."""
    import fitz
    import io

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    # Pass 1: first 100 pages to find section location
    first_chunk = fitz.open()
    for i in range(min(100, page_count)):
        first_chunk.insert_pdf(doc, from_page=i, to_page=i)
    buf = io.BytesIO()
    first_chunk.save(buf)
    first_b64 = base64.standard_b64encode(buf.getvalue()).decode()
    first_chunk.close()

    locate_prompt = (
        "This is the first 100 pages of a clinical trial protocol. "
        "Find the eligibility criteria section and tell me the start and end page numbers. "
        "Reply with JSON only: {\"start_page\": N, \"end_page\": N}"
    )
    from docu_flow.utils.llm_client import get_client as _get_client
    _client = _get_client()
    loc_resp = _single_call(_client, model, first_b64, locate_prompt)

    import json, re
    loc_data = json.loads(re.search(r"\{.*\}", loc_resp, re.DOTALL).group())
    start = max(0, int(loc_data.get("start_page", 1)) - 1)
    end = min(page_count - 1, int(loc_data.get("end_page", start + 15)))

    # Pass 2: extract just that section
    section_chunk = fitz.open()
    for i in range(start, end + 1):
        section_chunk.insert_pdf(doc, from_page=i, to_page=i)
    buf2 = io.BytesIO()
    section_chunk.save(buf2)
    section_b64 = base64.standard_b64encode(buf2.getvalue()).decode()
    section_chunk.close()
    doc.close()

    return _single_call(_client, model, section_b64, prompt)


def _populate_from_json(result: StrategyResult, data: dict) -> None:
    result.section_name = data.get("section_name")
    result.section_pages = data.get("section_pages", [])
    result.section_confidence = float(data.get("section_confidence", 0.0))
    result.section_found = bool(result.section_pages) or result.section_confidence > 0.3

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
