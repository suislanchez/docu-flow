"""
Strategy 4 — Unstructured (fast strategy) + Claude text extraction.

Pipeline:
  PDF → unstructured.partition_pdf (strategy="fast")
      → filter elements by type (Title, NarrativeText, ListItem, Table)
      → find eligibility section via Title element matching
      → concatenate section elements
      → Claude text-only extraction + ranking prompt
      → StrategyResult

The value of Unstructured vs raw PyMuPDF:
  - Returns typed elements (Title / NarrativeText / ListItem / Table) instead of
    raw text strings — section boundary detection can be done on Title elements
    rather than regex on raw text
  - Better handling of bulleted lists (each criterion as its own ListItem)
  - Tables are extracted as Table elements with HTML representation

Note: Using strategy="fast" (no GPU/Docker needed). For production accuracy,
      switch to strategy="hi_res" which adds Detectron2 layout detection.
      Install: pip install "unstructured[pdf]"
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[4] / "src"))

from tests.pdf_strategies.result import CriterionResult, RankedDisqualifier, StrategyResult
from tests.pdf_strategies.strategies.base import BaseStrategy
from tests.pdf_strategies.strategies._shared_prompt import COMBINED_EXTRACTION_PROMPT, parse_llm_json

# Section-header patterns (same as section_locator.py)
_SECTION_PATTERNS = [
    re.compile(r"(inclusion|exclusion)\s+(and\s+)?(exclusion\s+)?criteria", re.IGNORECASE),
    re.compile(r"eligibility\s+criteria", re.IGNORECASE),
    re.compile(r"study\s+population", re.IGNORECASE),
    re.compile(r"patient\s+selection", re.IGNORECASE),
    re.compile(r"subject\s+selection", re.IGNORECASE),
    re.compile(r"enrollment\s+criteria", re.IGNORECASE),
]

_STOP_PATTERNS = [
    re.compile(r"study\s+(procedures?|design|objectives?|endpoints?)", re.IGNORECASE),
    re.compile(r"treatment\s+(plan|regimen|administration)", re.IGNORECASE),
    re.compile(r"statistical\s+analysis", re.IGNORECASE),
]


class UnstructuredStrategy(BaseStrategy):
    name = "S4-Unstructured"

    def run(self, pdf_path: Path) -> StrategyResult:
        result = StrategyResult(strategy_name=self.name, pdf_name=pdf_path.name)
        t0 = time.perf_counter()

        try:
            from unstructured.partition.pdf import partition_pdf

            elements = partition_pdf(
                filename=str(pdf_path),
                strategy="fast",          # "hi_res" needs Docker + detectron2
                include_page_breaks=True,
            )

            # -- Find the eligibility section using Title elements --
            section_text, section_pages, section_name = _extract_section(elements)

            if not section_text.strip():
                # Fallback: use all NarrativeText + ListItem elements
                section_text = "\n".join(
                    str(el) for el in elements
                    if type(el).__name__ in ("NarrativeText", "ListItem", "Table")
                )
                result.section_found = False
            else:
                result.section_found = True
                result.section_pages = section_pages
                result.section_name = section_name
                result.section_confidence = 0.75

            # -- Claude text extraction + ranking --
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

            input_tokens = len(section_text) // 4
            output_tokens = len(raw) // 4
            result.estimated_cost_usd = (
                input_tokens * 3.0 + output_tokens * 15.0
            ) / 1_000_000

            data = parse_llm_json(raw)
            _populate_from_json(result, data)
            result.success = True

        except ImportError:
            result.error = (
                "unstructured not installed. "
                "Run: pip install 'unstructured[pdf]'"
            )
        except Exception as exc:  # noqa: BLE001
            result.error = str(exc)
        finally:
            result.latency_seconds = time.perf_counter() - t0

        return result


def _extract_section(elements: list) -> tuple[str, list[int], str | None]:
    """
    Walk Unstructured elements to find the eligibility section.
    Returns (section_text, page_numbers, section_name).
    """
    in_section = False
    section_parts: list[str] = []
    pages: set[int] = set()
    section_name: str | None = None
    current_page = 1

    for el in elements:
        el_type = type(el).__name__
        el_text = str(el).strip()

        # Track page number from metadata
        try:
            if el.metadata and el.metadata.page_number:
                current_page = el.metadata.page_number
        except AttributeError:
            pass

        if el_type == "PageBreak":
            continue

        if not in_section:
            # Look for section start in Title elements
            if el_type == "Title":
                for pattern in _SECTION_PATTERNS:
                    if pattern.search(el_text):
                        in_section = True
                        section_name = el_text
                        pages.add(current_page)
                        break
        else:
            # Look for stop signal in Title elements
            if el_type == "Title":
                for pattern in _STOP_PATTERNS:
                    if pattern.search(el_text):
                        return "\n".join(section_parts), sorted(pages), section_name

                # Another Title that doesn't match stop — include it (subsection header)
                section_parts.append(f"\n## {el_text}")
                pages.add(current_page)
            elif el_type in ("NarrativeText", "ListItem", "Table", "Text"):
                section_parts.append(el_text)
                pages.add(current_page)

    return "\n".join(section_parts), sorted(pages), section_name


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
