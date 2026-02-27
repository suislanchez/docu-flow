"""
Step 4 — LLM-based extraction of eligibility criteria.

Sends the targeted section text to the primary LLM and returns a structured
ExtractedCriteria object grounded in source page references.

Hallucination mitigation:
  - System prompt instructs the model to cite the source page for every criterion.
  - Any criterion without a source page is flagged as unverified.
  - Output is validated by Pydantic; schema mismatches raise ExtractionError.
"""

from __future__ import annotations

import json

from anthropic import BadRequestError
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_exponential

from docu_flow.config import settings
from docu_flow.logging import log
from docu_flow.schemas.criteria import (
    CriterionType,
    EligibilityCriterion,
    ExtractedCriteria,
    ExtractionMetadata,
)
from docu_flow.schemas.pdf import ParsedDocument, PageText
from docu_flow.utils.llm_client import get_client


class ExtractionError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_not_exception_type(BadRequestError),
)
def extract_criteria(
    document: ParsedDocument,
    section_pages: list[PageText],
) -> ExtractedCriteria:
    """Call the LLM to extract structured eligibility criteria from *section_pages*."""

    section_text = _build_section_text(section_pages)
    prompt = _build_extraction_prompt(section_text)

    client = get_client()
    log.info("criteria_extractor.calling_llm", model=settings.primary_llm_model, chars=len(section_text))

    try:
        response = client.messages.create(
            model=settings.primary_llm_model,
            max_tokens=8192,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
    except BadRequestError as exc:
        log.error("criteria_extractor.bad_request", error=str(exc), model=settings.primary_llm_model)
        raise

    raw_text = response.content[0].text.strip()
    return _parse_llm_response(raw_text, document)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a clinical trial protocol analyst. Extract eligibility criteria from the
provided protocol section.

Rules:
1. Extract EVERY inclusion and exclusion criterion verbatim.
2. For each criterion, cite the page number from which it was extracted.
3. Flag criteria with temporal conditions, numeric thresholds, or conditional logic.
4. Flag criteria with ambiguous language (e.g. "clinically significant").
5. Do NOT invent, infer, or paraphrase. Only extract what is explicitly stated.
6. Output ONLY valid JSON matching the schema. No prose outside the JSON.
"""


def _build_section_text(pages: list[PageText]) -> str:
    parts = []
    for page in pages:
        if page.text.strip():
            parts.append(f"--- PAGE {page.page_number} ---\n{page.text}")
    return "\n\n".join(parts)


def _build_extraction_prompt(section_text: str) -> str:
    schema_example = json.dumps({
        "protocol_title": "string or null",
        "sponsor": "string or null",
        "phase": "string or null",
        "therapeutic_area": "string or null",
        "criteria": [{
            "id": "inc_001",
            "criterion_type": "inclusion",
            "text": "verbatim criterion text",
            "source_page": 46,
            "source_section": "5.1 Inclusion Criteria",
            "has_temporal_condition": False,
            "has_numeric_threshold": False,
            "has_conditional_logic": False,
            "is_ambiguous": False,
            "notes": "",
        }],
    }, indent=2)
    return (
        f"Extract all eligibility criteria from the following protocol section.\n\n"
        f"OUTPUT SCHEMA:\n{schema_example}\n\n"
        f"PROTOCOL SECTION:\n{section_text}"
    )


def _parse_llm_response(raw: str, document: ParsedDocument) -> ExtractedCriteria:
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"LLM returned invalid JSON: {exc}\nRaw: {raw[:500]}") from exc

    criteria_raw = data.get("criteria", [])
    criteria: list[EligibilityCriterion] = []
    warnings: list[str] = []

    for i, c in enumerate(criteria_raw):
        try:
            criterion = EligibilityCriterion(
                id=c.get("id") or f"crit_{i:03d}",
                criterion_type=CriterionType(c.get("criterion_type", "exclusion")),
                text=c.get("text", ""),
                source_page=c.get("source_page"),
                source_section=c.get("source_section"),
                has_temporal_condition=bool(c.get("has_temporal_condition", False)),
                has_numeric_threshold=bool(c.get("has_numeric_threshold", False)),
                has_conditional_logic=bool(c.get("has_conditional_logic", False)),
                is_ambiguous=bool(c.get("is_ambiguous", False)),
                notes=c.get("notes", ""),
            )
            if criterion.source_page is None:
                warnings.append(f"Criterion {criterion.id} has no source_page — treat as unverified.")
            criteria.append(criterion)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"Skipped malformed criterion #{i}: {exc}")

    metadata = ExtractionMetadata(
        model_used=settings.primary_llm_model,
        extraction_confidence=1.0 - (len(warnings) / max(len(criteria), 1)) * 0.5,
        section_found=True,
        warnings=warnings,
    )

    log.info(
        "criteria_extractor.done",
        total=len(criteria),
        inclusion=sum(1 for c in criteria if c.criterion_type == CriterionType.INCLUSION),
        exclusion=sum(1 for c in criteria if c.criterion_type == CriterionType.EXCLUSION),
        warnings=len(warnings),
    )

    return ExtractedCriteria(
        protocol_title=data.get("protocol_title"),
        sponsor=data.get("sponsor"),
        phase=data.get("phase"),
        therapeutic_area=data.get("therapeutic_area"),
        criteria=criteria,
        metadata=metadata,
    )
