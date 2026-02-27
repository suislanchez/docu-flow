// ── Document ──────────────────────────────────────────────────────────────────

export interface ProtocolDocument {
  id: string;
  title: string;
  rawText: string;
  pageCount: number;
}

// ── Eligibility Criteria ──────────────────────────────────────────────────────

export type CriterionType = "inclusion" | "exclusion";

export interface EligibilityCriterion {
  id: string;
  type: CriterionType;
  text: string;
  /** Estimated % of population eliminated by this criterion (0–1) */
  eliminationRate: number;
  /** Higher = checked earlier in the Pareto filter */
  priority: number;
}

// ── Candidate ─────────────────────────────────────────────────────────────────

export interface Candidate {
  id: string;
  age: number;
  diagnosis: string[];
  priorTreatments: string[];
  labValues: Record<string, number>;
  comorbidities: string[];
  metadata: Record<string, unknown>;
}

// ── Screening ─────────────────────────────────────────────────────────────────

export type ScreeningVerdict = "pass" | "fail" | "needs_review";

export interface CriterionResult {
  criterionId: string;
  verdict: ScreeningVerdict;
  reason: string;
}

export interface ScreeningResult {
  candidateId: string;
  verdict: ScreeningVerdict;
  criteriaResults: CriterionResult[];
  /** Criterion that caused immediate disqualification, if any */
  disqualifiedBy?: string;
  /** Milliseconds taken to screen */
  durationMs: number;
}

// ── Pipeline ──────────────────────────────────────────────────────────────────

export interface PipelineResult {
  protocolId: string;
  totalCandidates: number;
  passed: ScreeningResult[];
  failed: ScreeningResult[];
  needsReview: ScreeningResult[];
  /** Pareto criteria (top 8) used for fast pre-screening */
  paretoCriteria: EligibilityCriterion[];
  durationMs: number;
}
