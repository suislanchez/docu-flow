import { describe, expect, it } from "vitest";
import { screenCandidate } from "../../src/pipeline/candidateScreener.js";
import type { Candidate, EligibilityCriterion } from "../../src/types.js";

// ── Shared criteria ────────────────────────────────────────────────────────────

const AGE_CRITERION: EligibilityCriterion = {
  id: "exc-age",
  type: "exclusion",
  text: "Age between 18 and 75 years",
  eliminationRate: 0.3,
  priority: 10,
};

const CANCER_CRITERION: EligibilityCriterion = {
  id: "exc-cancer",
  type: "exclusion",
  text: "Prior cancer treatment with XYZ or active malignancy",
  eliminationRate: 0.35,
  priority: 9,
};

const RENAL_CRITERION: EligibilityCriterion = {
  id: "exc-renal",
  type: "exclusion",
  text: "Renal impairment with eGFR < 45",
  eliminationRate: 0.25,
  priority: 8,
};

const PREGNANCY_CRITERION: EligibilityCriterion = {
  id: "exc-preg",
  type: "exclusion",
  text: "Pregnant or breastfeeding",
  eliminationRate: 0.2,
  priority: 7,
};

// ── Tests ──────────────────────────────────────────────────────────────────────

describe("L3 · candidateScreener", () => {
  it("passes a candidate who meets all criteria", () => {
    const candidate: Candidate = {
      id: "cand-001",
      age: 45,
      diagnosis: ["NSCLC"],
      priorTreatments: [],
      labValues: { eGFR: 80 },
      comorbidities: [],
      metadata: { pregnant: false },
    };

    const result = screenCandidate(candidate, [
      AGE_CRITERION,
      RENAL_CRITERION,
      PREGNANCY_CRITERION,
    ]);

    expect(result.verdict).toBe("pass");
    expect(result.disqualifiedBy).toBeUndefined();
  });

  it("fails a candidate who is too young", () => {
    const candidate: Candidate = {
      id: "cand-002",
      age: 15,
      diagnosis: ["NSCLC"],
      priorTreatments: [],
      labValues: { eGFR: 90 },
      comorbidities: [],
      metadata: {},
    };

    const result = screenCandidate(candidate, [AGE_CRITERION]);

    expect(result.verdict).toBe("fail");
    expect(result.disqualifiedBy).toBe("exc-age");
  });

  it("fails a candidate who is too old", () => {
    const candidate: Candidate = {
      id: "cand-003",
      age: 80,
      diagnosis: ["NSCLC"],
      priorTreatments: [],
      labValues: {},
      comorbidities: [],
      metadata: {},
    };

    const result = screenCandidate(candidate, [AGE_CRITERION]);

    expect(result.verdict).toBe("fail");
    expect(result.disqualifiedBy).toBe("exc-age");
  });

  it("fails a candidate with active malignancy", () => {
    const candidate: Candidate = {
      id: "cand-004",
      age: 52,
      diagnosis: ["cancer", "NSCLC"],
      priorTreatments: [],
      labValues: { eGFR: 70 },
      comorbidities: [],
      metadata: {},
    };

    const result = screenCandidate(candidate, [CANCER_CRITERION]);

    expect(result.verdict).toBe("fail");
    expect(result.disqualifiedBy).toBe("exc-cancer");
  });

  it("fails a candidate with eGFR below threshold", () => {
    const candidate: Candidate = {
      id: "cand-005",
      age: 60,
      diagnosis: ["NSCLC"],
      priorTreatments: [],
      labValues: { eGFR: 30 },
      comorbidities: [],
      metadata: {},
    };

    const result = screenCandidate(candidate, [RENAL_CRITERION]);

    expect(result.verdict).toBe("fail");
    expect(result.disqualifiedBy).toBe("exc-renal");
  });

  it("fails a candidate who is pregnant", () => {
    const candidate: Candidate = {
      id: "cand-006",
      age: 32,
      diagnosis: ["NSCLC"],
      priorTreatments: [],
      labValues: { eGFR: 85 },
      comorbidities: [],
      metadata: { pregnant: true },
    };

    const result = screenCandidate(candidate, [PREGNANCY_CRITERION]);

    expect(result.verdict).toBe("fail");
    expect(result.disqualifiedBy).toBe("exc-preg");
  });

  it("short-circuits on the highest-priority failing criterion", () => {
    const candidate: Candidate = {
      id: "cand-007",
      age: 15, // fails AGE (priority 10)
      diagnosis: ["cancer"], // would also fail CANCER (priority 9)
      priorTreatments: [],
      labValues: { eGFR: 20 }, // would also fail RENAL (priority 8)
      comorbidities: [],
      metadata: {},
    };

    const result = screenCandidate(candidate, [
      AGE_CRITERION,
      CANCER_CRITERION,
      RENAL_CRITERION,
    ]);

    // Should stop at highest priority fail (age, priority=10)
    expect(result.disqualifiedBy).toBe("exc-age");
    // Only one criterion evaluated before bail-out
    expect(result.criteriaResults).toHaveLength(1);
  });

  it("includes a durationMs value greater than or equal to 0", () => {
    const candidate: Candidate = {
      id: "cand-008",
      age: 45,
      diagnosis: ["NSCLC"],
      priorTreatments: [],
      labValues: { eGFR: 75 },
      comorbidities: [],
      metadata: {},
    };

    const result = screenCandidate(candidate, [AGE_CRITERION, RENAL_CRITERION]);
    expect(result.durationMs).toBeGreaterThanOrEqual(0);
  });
});
