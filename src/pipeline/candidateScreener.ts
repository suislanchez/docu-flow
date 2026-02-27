import type {
  Candidate,
  CriterionResult,
  EligibilityCriterion,
  ScreeningResult,
  ScreeningVerdict,
} from "../types.js";

/**
 * Screens a single candidate against a set of criteria.
 * Applies criteria in priority order — short-circuits on first hard disqualification.
 */
export function screenCandidate(
  candidate: Candidate,
  criteria: EligibilityCriterion[]
): ScreeningResult {
  const start = performance.now();
  const sorted = [...criteria].sort((a, b) => b.priority - a.priority);
  const criteriaResults: CriterionResult[] = [];
  let disqualifiedBy: string | undefined;
  let verdict: ScreeningVerdict = "pass";

  for (const criterion of sorted) {
    const result = evaluateCriterion(candidate, criterion);
    criteriaResults.push(result);

    if (result.verdict === "fail") {
      verdict = "fail";
      disqualifiedBy = criterion.id;
      break; // Pareto short-circuit
    }
    if (result.verdict === "needs_review") {
      verdict = "needs_review";
      // Don't break — keep checking for hard fails
    }
  }

  return {
    candidateId: candidate.id,
    verdict,
    criteriaResults,
    disqualifiedBy,
    durationMs: performance.now() - start,
  };
}

/**
 * Rule-based evaluator. In production, ambiguous criteria route to an LLM.
 */
function evaluateCriterion(
  candidate: Candidate,
  criterion: EligibilityCriterion
): CriterionResult {
  const text = criterion.text.toLowerCase();
  let verdict: ScreeningVerdict = "pass";
  let reason = "Criterion met";

  // ── Age checks ────────────────────────────────────────────────────────────
  const ageMin = text.match(/age\s*[>=]{1,2}\s*(\d+)/);
  const ageMax = text.match(/age\s*[<=]{1,2}\s*(\d+)/);
  const ageBetween = text.match(/between\s*(\d+)\s*and\s*(\d+)/);

  if (ageBetween) {
    const [, min, max] = ageBetween;
    if (candidate.age < Number(min) || candidate.age > Number(max)) {
      verdict = "fail";
      reason = `Age ${candidate.age} outside required ${min}–${max}`;
    }
  } else if (ageMin && candidate.age < Number(ageMin[1])) {
    verdict = "fail";
    reason = `Age ${candidate.age} below minimum ${ageMin[1]}`;
  } else if (ageMax && candidate.age > Number(ageMax[1])) {
    verdict = "fail";
    reason = `Age ${candidate.age} above maximum ${ageMax[1]}`;
  }

  // ── Prior cancer / malignancy ─────────────────────────────────────────────
  if (
    /prior.*cancer|active.*malignancy/.test(text) &&
    candidate.diagnosis.some((d) => /cancer|malignancy|tumor/i.test(d))
  ) {
    verdict = "fail";
    reason = "Candidate has prior cancer / active malignancy";
  }

  // ── Renal impairment ──────────────────────────────────────────────────────
  const eGFRLimit = text.match(/egfr\s*<\s*(\d+)/);
  if (eGFRLimit && candidate.labValues.eGFR !== undefined) {
    if (candidate.labValues.eGFR < Number(eGFRLimit[1])) {
      verdict = "fail";
      reason = `eGFR ${candidate.labValues.eGFR} below required ${eGFRLimit[1]}`;
    }
  }

  // ── Prior treatments ──────────────────────────────────────────────────────
  if (/prior.*treatment|previous.*therapy/.test(text)) {
    const treatmentMatch = text.match(
      /prior\s+([\w-]+)\s+treatment|previous\s+([\w-]+)\s+therapy/
    );
    if (treatmentMatch) {
      const drug = (treatmentMatch[1] ?? treatmentMatch[2]).toLowerCase();
      if (candidate.priorTreatments.some((t) => t.toLowerCase().includes(drug))) {
        verdict = "fail";
        reason = `Candidate has prior ${drug} treatment`;
      }
    }
  }

  // ── Pregnancy ─────────────────────────────────────────────────────────────
  if (
    /pregnant|breastfeeding/.test(text) &&
    (candidate.metadata.pregnant === true ||
      candidate.metadata.breastfeeding === true)
  ) {
    verdict = "fail";
    reason = "Candidate is pregnant or breastfeeding";
  }

  // ── Unrecognised rule → needs human review ────────────────────────────────
  if (verdict === "pass" && !hasKnownPattern(text)) {
    verdict = "needs_review";
    reason = "Criterion requires manual review";
  }

  return { criterionId: criterion.id, verdict, reason };
}

function hasKnownPattern(text: string): boolean {
  return (
    /age|cancer|malignancy|egfr|renal|hepatic|prior.*treatment|previous.*therapy|pregnant|breastfeeding/.test(
      text
    )
  );
}
