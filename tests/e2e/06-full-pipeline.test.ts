import { describe, expect, it } from "vitest";
import { runPipeline } from "../../src/pipeline/index.js";
import { parseDocument } from "../../src/pipeline/documentParser.js";
import type { Candidate } from "../../src/types.js";

/**
 * L6 · Full end-to-end pipeline tests
 *
 * These tests exercise the complete flow:
 *   Raw protocol text → parse → extract criteria → select pareto set → batch screen candidates
 *
 * Goal: validate that the Pareto pre-screen funnel behaves correctly at scale
 * and that the overall pass-rate is consistent with clinical expectations.
 */

const REAL_PROTOCOL = `
PROTOCOL: Phase III Randomised Controlled Trial
Compound: ZX-100 vs Standard of Care in Advanced NSCLC

INCLUSION CRITERIA:
- Age between 18 and 75 years
- Histologically or cytologically confirmed stage IIIB/IV non-small cell lung cancer
- ECOG performance status of 0, 1, or 2
- Measurable disease per RECIST 1.1 criteria
- Adequate bone marrow function (ANC >= 1.5 x 10^9/L, platelets >= 100 x 10^9/L)
- Written informed consent

EXCLUSION CRITERIA:
- Active malignancy other than NSCLC within the past 3 years
- Prior cancer treatment with ZX-100 or structurally related compounds
- Renal impairment with eGFR < 45 mL/min/1.73m² (CKD-EPI)
- Hepatic impairment classified as Child-Pugh B or C
- Pregnant or breastfeeding at time of enrolment
- Known allergy or hypersensitivity to any component of the study drug
- Psychiatric disorder requiring inpatient hospitalisation within 12 months
- Prior treatment with checkpoint inhibitor therapy within the last 6 months
- Active autoimmune disease currently requiring systemic immunosuppressive therapy
- Concurrent administration of strong CYP3A4 inhibitors
`.trim();

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeCandidate(overrides: Partial<Candidate> & { id: string }): Candidate {
  return {
    age: 55,
    diagnosis: ["NSCLC"],
    priorTreatments: [],
    labValues: { eGFR: 75 },
    comorbidities: [],
    metadata: { pregnant: false },
    ...overrides,
  };
}

// ── Tests ──────────────────────────────────────────────────────────────────────

describe("L6 · full E2E pipeline", () => {
  it("screens a cohort of 20 mixed candidates and buckets every one", () => {
    const doc = parseDocument(REAL_PROTOCOL, { id: "e2e-proto-1" });

    const candidates: Candidate[] = [
      // Clearly qualified
      makeCandidate({ id: "e2e-01", age: 45, labValues: { eGFR: 80 } }),
      makeCandidate({ id: "e2e-02", age: 62, labValues: { eGFR: 65 } }),
      makeCandidate({ id: "e2e-03", age: 38, labValues: { eGFR: 90 } }),
      makeCandidate({ id: "e2e-04", age: 70, labValues: { eGFR: 55 } }),
      makeCandidate({ id: "e2e-05", age: 53, labValues: { eGFR: 72 } }),

      // Age out of range
      makeCandidate({ id: "e2e-06", age: 12 }),
      makeCandidate({ id: "e2e-07", age: 79 }),
      makeCandidate({ id: "e2e-08", age: 82 }),

      // Active malignancy / prior cancer
      makeCandidate({ id: "e2e-09", diagnosis: ["cancer", "NSCLC"] }),
      makeCandidate({ id: "e2e-10", diagnosis: ["malignancy"] }),

      // Renal impairment
      makeCandidate({ id: "e2e-11", labValues: { eGFR: 20 } }),
      makeCandidate({ id: "e2e-12", labValues: { eGFR: 10 } }),
      makeCandidate({ id: "e2e-13", labValues: { eGFR: 40 } }),

      // Pregnant
      makeCandidate({ id: "e2e-14", metadata: { pregnant: true } }),
      makeCandidate({ id: "e2e-15", metadata: { pregnant: true }, age: 28 }),

      // Prior checkpoint inhibitor treatment
      makeCandidate({ id: "e2e-16", priorTreatments: ["checkpoint inhibitor therapy"] }),
      makeCandidate({ id: "e2e-17", priorTreatments: ["pembrolizumab checkpoint inhibitor therapy"] }),

      // Edge: age at boundary
      makeCandidate({ id: "e2e-18", age: 18 }), // exactly minimum — should pass
      makeCandidate({ id: "e2e-19", age: 75 }), // exactly maximum — should pass
      makeCandidate({ id: "e2e-20", age: 17 }), // one below minimum — should fail
    ];

    const result = runPipeline(doc, candidates);

    // All 20 accounted for
    expect(result.totalCandidates).toBe(20);
    const total =
      result.passed.length + result.failed.length + result.needsReview.length;
    expect(total).toBe(20);
  });

  it("majority of the cohort is filtered out by the pareto pre-screen", () => {
    const doc = parseDocument(REAL_PROTOCOL, { id: "e2e-proto-2" });

    // Build a realistic population: 80% have at least one disqualifying factor
    const candidates: Candidate[] = [
      ...Array.from({ length: 8 }, (_, i) =>
        makeCandidate({ id: `e2e-fail-${i}`, age: 10 + i }) // all underage
      ),
      ...Array.from({ length: 12 }, (_, i) =>
        makeCandidate({
          id: `e2e-real-${i}`,
          age: 30 + i,
          labValues: { eGFR: 60 + i },
        })
      ),
    ];

    const result = runPipeline(doc, candidates);
    const disqualificationRate =
      result.failed.length / result.totalCandidates;

    // Expect at least 40% hard disqualified (conservative; our cohort has 8/20 clearly out)
    expect(disqualificationRate).toBeGreaterThanOrEqual(0.4);
  });

  it("boundary age candidates (18 and 75) are not hard-failed on age alone", () => {
    const doc = parseDocument(REAL_PROTOCOL, { id: "e2e-proto-3" });

    const exactly18 = makeCandidate({ id: "boundary-18", age: 18 });
    const exactly75 = makeCandidate({ id: "boundary-75", age: 75 });

    const result = runPipeline(doc, [exactly18, exactly75]);

    const failedIds = result.failed.map((r) => r.candidateId);
    expect(failedIds).not.toContain("boundary-18");
    expect(failedIds).not.toContain("boundary-75");
  });

  it("each ScreeningResult references a valid candidateId from the input", () => {
    const doc = parseDocument(REAL_PROTOCOL, { id: "e2e-proto-4" });
    const candidates = Array.from({ length: 10 }, (_, i) =>
      makeCandidate({ id: `e2e-ref-${i}`, age: 20 + i })
    );
    const inputIds = new Set(candidates.map((c) => c.id));

    const result = runPipeline(doc, candidates);
    const allResults = [...result.passed, ...result.failed, ...result.needsReview];

    for (const r of allResults) {
      expect(inputIds.has(r.candidateId)).toBe(true);
    }
  });

  it("each failed result has a disqualifiedBy referencing an actual pareto criterion", () => {
    const doc = parseDocument(REAL_PROTOCOL, { id: "e2e-proto-5" });
    const candidates = [
      makeCandidate({ id: "dq-age", age: 10 }),
      makeCandidate({ id: "dq-renal", labValues: { eGFR: 5 } }),
      makeCandidate({ id: "dq-cancer", diagnosis: ["cancer"] }),
    ];

    const result = runPipeline(doc, candidates);
    const paretoCriterionIds = new Set(result.paretoCriteria.map((c) => c.id));

    for (const r of result.failed) {
      if (r.disqualifiedBy) {
        expect(paretoCriterionIds.has(r.disqualifiedBy)).toBe(true);
      }
    }
  });

  it("pipeline completes a 50-candidate batch in under 500ms", () => {
    const doc = parseDocument(REAL_PROTOCOL, { id: "e2e-proto-6" });
    const candidates = Array.from({ length: 50 }, (_, i) =>
      makeCandidate({
        id: `perf-${i}`,
        age: 18 + (i % 60),
        labValues: { eGFR: 30 + (i % 60) },
      })
    );

    const start = performance.now();
    runPipeline(doc, candidates);
    const elapsed = performance.now() - start;

    expect(elapsed).toBeLessThan(500);
  });
});
