"""
Step 6 — Screen a patient against the top disqualifiers (fast pre-screen).

The screener sends the top-8 criteria + patient data to the LLM and asks for
a binary disqualify/pass decision with reasoning.

Design principles:
  - "Fail fast" on high-confidence disqualifications.
  - "Escalate" when the LLM confidence is below threshold.
  - Never silently swallow ambiguous criteria — always escalate those.
"""

from __future__ import annotations

import json

from tenacity import retry, stop_after_attempt, wait_exponential

from docu_flow.config import settings
from docu_flow.logging import log
from docu_flow.schemas.criteria import (
    EligibilityCriterion,
    ExtractedCriteria,
    FailedCriterion,
    ScreeningDecision,
    ScreeningRequest,
    ScreeningResult,
)
from docu_flow.utils.llm_client import get_client

_CONFIDENCE_ESCALATION_THRESHOLD = 0.70


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def screen_patient(
    request: ScreeningRequest,
    extracted: ExtractedCriteria,
) -> ScreeningResult:
    """Screen *request.patient_data* against the top disqualifiers."""
    disqualifiers = extracted.top_disqualifiers or extracted.exclusion_criteria()

    if not disqualifiers:
        log.warning("screener.no_disqualifiers", protocol_id=request.protocol_id)
        return ScreeningResult(
            patient_id=request.patient_id,
            protocol_id=request.protocol_id,
            decision=ScreeningDecision.ESCALATE,
            confidence=0.0,
            escalation_reason="No disqualifying criteria available for screening.",
            model_used=settings.primary_llm_model,
        )

    prompt = _build_screening_prompt(request, disqualifiers)
    client = get_client()

    response = client.messages.create(
        model=settings.primary_llm_model,
        max_tokens=1024,
        system=_SCREENING_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    return _parse_screening_response(raw, request, disqualifiers)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_SCREENING_SYSTEM_PROMPT = """\
You are a clinical trial eligibility screener. You will be given:
1. A patient's clinical data.
2. A list of exclusion criteria from a clinical trial protocol.

For each criterion, determine if the patient data provides enough information to
evaluate it. Then decide:

- "disqualified": patient clearly meets one or more exclusion criteria (high confidence).
- "passed_prescreen": patient does not meet any listed exclusion criteria.
- "escalate": patient data is insufficient, ambiguous, or the criterion requires
  clinical judgment beyond what you can determine from the data.

Output ONLY valid JSON. No prose outside the JSON object.
"""


def _build_screening_prompt(
    request: ScreeningRequest,
    criteria: list[EligibilityCriterion],
) -> str:
    criteria_block = json.dumps(
        [{"id": c.id, "text": c.text, "is_ambiguous": c.is_ambiguous} for c in criteria],
        indent=2,
    )
    patient_block = json.dumps(request.patient_data, indent=2)

    schema = json.dumps({
        "decision": "disqualified | passed_prescreen | escalate",
        "confidence": 0.95,
        "failed_criteria": [
            {"criterion_id": "exc_001", "reason": "Patient has active hepatitis B (HBsAg positive)"}
        ],
        "escalation_reason": "string or null",
    }, indent=2)

    return (
        f"PATIENT DATA:\n{patient_block}\n\n"
        f"EXCLUSION CRITERIA:\n{criteria_block}\n\n"
        f"OUTPUT SCHEMA:\n{schema}"
    )


def _parse_screening_response(
    raw: str,
    request: ScreeningRequest,
    criteria: list[EligibilityCriterion],
) -> ScreeningResult:
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.error("screener.invalid_json", raw=raw[:300])
        return ScreeningResult(
            patient_id=request.patient_id,
            protocol_id=request.protocol_id,
            decision=ScreeningDecision.ESCALATE,
            confidence=0.0,
            escalation_reason="LLM returned unparseable response — escalating to human review.",
            model_used=settings.primary_llm_model,
        )

    raw_decision = data.get("decision", "escalate")
    try:
        decision = ScreeningDecision(raw_decision)
    except ValueError:
        decision = ScreeningDecision.ESCALATE

    confidence = float(data.get("confidence", 0.5))

    # Force escalation if confidence is too low
    if confidence < _CONFIDENCE_ESCALATION_THRESHOLD and decision != ScreeningDecision.DISQUALIFIED:
        decision = ScreeningDecision.ESCALATE

    criteria_index = {c.id: c for c in criteria}
    failed: list[FailedCriterion] = []
    for f in data.get("failed_criteria", []):
        crit = criteria_index.get(f.get("criterion_id", ""))
        if crit:
            failed.append(FailedCriterion(criterion=crit, reason=f.get("reason", "")))

    log.info(
        "screener.result",
        patient_id=request.patient_id,
        protocol_id=request.protocol_id,
        decision=decision,
        confidence=confidence,
        failed_count=len(failed),
    )

    return ScreeningResult(
        patient_id=request.patient_id,
        protocol_id=request.protocol_id,
        decision=decision,
        confidence=confidence,
        failed_criteria=failed,
        passed_criteria_count=len(criteria) - len(failed),
        escalation_reason=data.get("escalation_reason"),
        model_used=settings.primary_llm_model,
    )
