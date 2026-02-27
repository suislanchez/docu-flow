"""
Step 5 — Rank exclusion criteria by estimated disqualification power.

The ranker assigns DisqualificationPower using a lightweight heuristic scoring
model (fast, no LLM call). An optional LLM re-rank can be enabled for more
accurate scoring at the cost of an extra API call.

Heuristic signals (higher score = more disqualifying):
  - Common high-exclusion categories: age, pregnancy, prior malignancy, organ failure
  - Numeric thresholds usually indicate measurable, objective criteria → easier to apply
  - Temporal conditions expand exclusion window
  - Ambiguous criteria are downranked (needs human interpretation)
"""

from __future__ import annotations

import re

from docu_flow.logging import log
from docu_flow.schemas.criteria import (
    CriterionType,
    DisqualificationPower,
    EligibilityCriterion,
    ExtractedCriteria,
)

# Keyword → score contribution
_HIGH_POWER_KEYWORDS: list[tuple[re.Pattern[str], float]] = [
    (re.compile(r"\bpregnant|pregnancy|lactating|breastfeeding\b", re.I), 3.0),
    (re.compile(r"\bprior\s+(malignancy|cancer|tumor|neoplasm)\b", re.I), 3.0),
    (re.compile(r"\brenal\s+(failure|impairment)|eGFR|creatinine\b", re.I), 2.5),
    (re.compile(r"\bhepatic|liver\s+(failure|impairment|disease)\b", re.I), 2.5),
    (re.compile(r"\bcardiac|heart\s+(failure|disease)\b", re.I), 2.5),
    (re.compile(r"\bage\s*[<>≤≥]\s*\d+|\b(under|over)\s+\d+\s+years?\b", re.I), 2.0),
    (re.compile(r"\bHIV|hepatitis\s+[BC]|HBV|HCV\b", re.I), 2.0),
    (re.compile(r"\bautoimmune\b", re.I), 1.5),
    (re.compile(r"\bactive\s+(infection|tuberculosis|TB)\b", re.I), 2.0),
    (re.compile(r"\bchemotherapy|immunotherapy|biologic\s+therapy\b", re.I), 1.5),
    (re.compile(r"\bseizure|epilepsy\b", re.I), 1.5),
    (re.compile(r"\bpsychiatric\b", re.I), 1.0),
]

_AMBIGUITY_PENALTY = -1.5


def rank_disqualifiers(
    extracted: ExtractedCriteria,
    top_n: int = 8,
) -> ExtractedCriteria:
    """
    Score and rank exclusion criteria; populate *extracted.top_disqualifiers*.
    Returns the mutated ExtractedCriteria.
    """
    exclusions = extracted.exclusion_criteria()
    scored = [(c, _score(c)) for c in exclusions]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Assign DisqualificationPower enum
    for criterion, score in scored:
        if score >= 4.0:
            criterion.disqualification_power = DisqualificationPower.VERY_HIGH
        elif score >= 2.5:
            criterion.disqualification_power = DisqualificationPower.HIGH
        elif score >= 1.0:
            criterion.disqualification_power = DisqualificationPower.MEDIUM
        else:
            criterion.disqualification_power = DisqualificationPower.LOW

    top = [c for c, _ in scored[:top_n]]
    extracted.top_disqualifiers = top

    log.info(
        "ranker.done",
        total_exclusions=len(exclusions),
        top_n=len(top),
        top_scores=[round(s, 2) for _, s in scored[:top_n]],
    )
    return extracted


def _score(criterion: EligibilityCriterion) -> float:
    score = 0.0
    text = criterion.text

    for pattern, weight in _HIGH_POWER_KEYWORDS:
        if pattern.search(text):
            score += weight

    if criterion.has_numeric_threshold:
        score += 1.0  # measurable → easier to apply → effectively more disqualifying
    if criterion.has_temporal_condition:
        score += 0.5
    if criterion.has_conditional_logic:
        score += 0.5  # complex → may catch more patients
    if criterion.is_ambiguous:
        score += _AMBIGUITY_PENALTY

    return score
