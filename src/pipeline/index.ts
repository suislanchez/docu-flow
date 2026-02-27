import type { Candidate, PipelineResult, ProtocolDocument } from "../types.js";
import { screenCandidate } from "./candidateScreener.js";
import { extractCriteria } from "./criteriaExtractor.js";
import { selectParetoCriteria } from "./paretoFilter.js";

/**
 * Full pre-screening pipeline:
 *   1. Extract all criteria from the protocol document
 *   2. Select the top-8 Pareto (fast-disqualification) criteria
 *   3. Screen every candidate — short-circuit on first hard fail
 *   4. Bucket results: passed / failed / needs_review
 */
export function runPipeline(
  doc: ProtocolDocument,
  candidates: Candidate[]
): PipelineResult {
  const start = performance.now();

  const allCriteria = extractCriteria(doc);
  const paretoCriteria = selectParetoCriteria(allCriteria);

  const results = candidates.map((c) => screenCandidate(c, paretoCriteria));

  return {
    protocolId: doc.id,
    totalCandidates: candidates.length,
    passed: results.filter((r) => r.verdict === "pass"),
    failed: results.filter((r) => r.verdict === "fail"),
    needsReview: results.filter((r) => r.verdict === "needs_review"),
    paretoCriteria,
    durationMs: performance.now() - start,
  };
}
