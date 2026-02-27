"""
Shared extraction + ranking prompt used by all strategies.

All strategies produce the same JSON schema so the evaluator can compare them
on equal footing.

Ranking convention:
  rank 8 = highest disqualification power (eliminates the most candidates from
           a general population)
  rank 1 = lowest within the top 8
  Together the top 8 should account for ~80% of total disqualifications.
"""

from __future__ import annotations

import json
import re


COMBINED_EXTRACTION_PROMPT = """\
You are a clinical trial protocol analyst.

Your task:
1. Find the eligibility criteria section (inclusion and exclusion criteria).
2. Extract EVERY criterion verbatim — do not paraphrase or invent.
3. For each criterion, note the source page number.
4. Flag criteria with: temporal conditions ("within 4 weeks"), numeric thresholds \
("eGFR >= 30"), conditional logic ("unless..."), or ambiguous language \
("clinically significant", "adequate").
5. Rank the top 8 EXCLUSION criteria by estimated disqualification power against a \
general adult population:
   - rank 8 = eliminates the MOST candidates (highest prevalence of disqualifying condition)
   - rank 1 = eliminates the fewest within the top 8
   - Together these 8 should account for ~80%% of all candidate disqualifications.

OUTPUT: ONLY valid JSON matching this exact schema. No prose, no markdown fences.

{{
  "protocol_title": "string or null",
  "sponsor": "string or null",
  "phase": "string or null",
  "therapeutic_area": "string or null",
  "section_name": "string or null",
  "section_pages": [12, 13, 14],
  "section_confidence": 0.95,
  "criteria": [
    {{
      "id": "exc_001",
      "criterion_type": "exclusion",
      "text": "verbatim criterion text from document",
      "source_page": 12,
      "has_temporal_condition": false,
      "has_numeric_threshold": true,
      "has_conditional_logic": false,
      "is_ambiguous": false
    }}
  ],
  "top_8_disqualifiers": [
    {{
      "rank": 8,
      "criterion_id": "exc_003",
      "criterion_text": "verbatim text of this criterion",
      "disqualification_power": "very_high",
      "estimated_prevalence_pct": 35,
      "reasoning": "35%% of adults have hypertension; this criterion immediately screens them out"
    }}
  ]
}}

DOCUMENT CONTENT:
{content}
"""


def parse_llm_json(raw: str) -> dict:
    """Strip markdown fences and parse JSON from LLM response."""
    # Remove ```json ... ``` or ``` ... ``` fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw.strip(), flags=re.MULTILINE)
    raw = raw.strip()

    # Find the outermost JSON object if there's surrounding text
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start != -1 and end > start:
        raw = raw[start:end]

    return json.loads(raw)
