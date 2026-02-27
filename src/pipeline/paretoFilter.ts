import type { EligibilityCriterion } from "../types.js";

const PARETO_LIMIT = 8;

/**
 * Returns the top N criteria by elimination rate — the Pareto pre-screen set.
 * These criteria alone should eliminate ~80% of unqualified candidates cheaply
 * before expensive LLM or human review.
 */
export function selectParetoCriteria(
  criteria: EligibilityCriterion[],
  limit = PARETO_LIMIT
): EligibilityCriterion[] {
  // Include both exclusion AND inclusion criteria — a candidate who fails an
  // inclusion requirement (e.g. age out of range) is equally disqualified.
  return [...criteria]
    .sort((a, b) => b.eliminationRate - a.eliminationRate)
    .slice(0, limit);
}

/**
 * Projects the combined elimination power of a set of criteria.
 * Assumes independent probabilities (upper bound estimate).
 */
export function estimateCombinedEliminationRate(
  criteria: EligibilityCriterion[]
): number {
  // P(eliminated) = 1 - P(passes all) = 1 - ∏(1 - rᵢ)
  const passProbability = criteria.reduce(
    (acc, c) => acc * (1 - c.eliminationRate),
    1
  );
  return 1 - passProbability;
}
