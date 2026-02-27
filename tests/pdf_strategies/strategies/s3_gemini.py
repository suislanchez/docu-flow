"""
Strategy 3 — Gemini 2.5 Flash (native PDF ingestion via google-genai SDK).

Pipeline:
  PDF → inline bytes (< 18 MB) or Files API (>= 18 MB)
      → single generateContent call: find section + extract + rank top 8
      → StrategyResult

Key advantages over S2:
  - 258 tokens/page flat rate vs ~1,600/page for Claude vision
  - 1M token context window — entire 200-page protocol in one call, no chunking
  - ~40x cheaper than Claude on input tokens

Cost:   ~$0.02–$0.05 per 100-page doc (gemini-2.5-flash)
Speed:  10–30s for a full protocol
Limit:  50 MB file size, 1,000 pages max
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from tests.pdf_strategies.result import CriterionResult, RankedDisqualifier, StrategyResult
from tests.pdf_strategies.strategies.base import BaseStrategy
from tests.pdf_strategies.strategies._shared_prompt import COMBINED_EXTRACTION_PROMPT, parse_llm_json

_INPUT_COST_PER_TOKEN = 0.15 / 1_000_000   # gemini-2.5-flash
_OUTPUT_COST_PER_TOKEN = 0.60 / 1_000_000
_TOKENS_PER_PAGE = 258


class GeminiStrategy(BaseStrategy):
    name = "S3-Gemini"

    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        self.model = model

    def run(self, pdf_path: Path) -> StrategyResult:
        result = StrategyResult(strategy_name=self.name, pdf_name=pdf_path.name)
        t0 = time.perf_counter()

        try:
            import google.genai as genai
            from google.genai import types

            api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError("GOOGLE_API_KEY not set. Add it to your .env file.")

            client = genai.Client(api_key=api_key)
            pdf_bytes = pdf_path.read_bytes()
            file_size_mb = len(pdf_bytes) / (1024 * 1024)

            prompt_text = COMBINED_EXTRACTION_PROMPT.format(
                content="[See the attached PDF document above]"
            )

            if file_size_mb < 18:
                # Inline: pass PDF bytes directly
                response = client.models.generate_content(
                    model=self.model,
                    contents=[
                        types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                        prompt_text,
                    ],
                )
            else:
                # Files API for large PDFs
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(pdf_bytes)
                    tmp_path = tmp.name
                try:
                    uploaded = client.files.upload(
                        file=tmp_path,
                        config=types.UploadFileConfig(
                            mime_type="application/pdf",
                            display_name=pdf_path.name,
                        ),
                    )
                    import time as _time
                    while uploaded.state.name == "PROCESSING":
                        _time.sleep(1)
                        uploaded = client.files.get(name=uploaded.name)
                    response = client.models.generate_content(
                        model=self.model,
                        contents=[uploaded, prompt_text],
                    )
                finally:
                    os.unlink(tmp_path)

            raw = response.text.strip()
            result.raw_output_preview = raw[:500]

            try:
                import fitz
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                page_count = len(doc)
                doc.close()
            except Exception:  # noqa: BLE001
                page_count = len(pdf_bytes) // 3000

            input_tokens = page_count * _TOKENS_PER_PAGE + len(prompt_text) // 4
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
