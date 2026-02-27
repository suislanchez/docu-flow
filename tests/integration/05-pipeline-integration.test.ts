import { describe, expect, it } from "vitest";
import { runPipeline } from "../../src/pipeline/index.js";
import { parseDocument } from "../../src/pipeline/documentParser.js";
import type { Candidate } from "../../src/types.js";

const PROTOCOL_TEXT = `
Phase II Trial – ZX-100

Inclusion Criteria:
- Age between 18 and 75 years
- Confirmed non-small cell lung cancer diagnosis

Exclusion Criteria:
- Prior cancer treatment with ZX-100 or active malignancy other than NSCLC
- Renal impairment with eGFR < 45
- Pregnant or breastfeeding
- Prior treatment with checkpoint inhibitor therapy
`.trim();

// Clearly qualified
const QUALIFIED_CANDIDATE: Candidate = {
  id: "cand-q1",
  age: 55,
  diagnosis: ["NSCLC"],
  priorTreatments: [],
  labValues: { eGFR: 75 },
  comorbidities: [],
  metadata: { pregnant: false },
};

// Age disqualification
const TOO_YOUNG: Candidate = {
  id: "cand-f1",
  age: 14,
  diagnosis: ["NSCLC"],
  priorTreatments: [],
  labValues: { eGFR: 85 },
  comorbidities: [],
  metadata: {},
};

// Renal disqualification
const LOW_EGFR: Candidate = {
  id: "cand-f2",
  age: 60,
  diagnosis: ["NSCLC"],
  priorTreatments: [],
  labValues: { eGFR: 20 },
  comorbidities: [],
  metadata: {},
};

// Active malignancy disqualification
const ACTIVE_MALIGNANCY: Candidate = {
  id: "cand-f3",
  age: 50,
  diagnosis: ["cancer", "NSCLC"],
  priorTreatments: [],
  labValues: { eGFR: 70 },
  comorbidities: [],
  metadata: {},
};

// Pregnant disqualification
const PREGNANT: Candidate = {
  id: "cand-f4",
  age: 35,
  diagnosis: ["NSCLC"],
  priorTreatments: [],
  labValues: { eGFR: 80 },
  comorbidities: [],
  metadata: { pregnant: true },
};

describe("L5 · pipeline integration", () => {
  it("returns a PipelineResult with the correct protocolId", () => {
    const doc = parseDocument(PROTOCOL_TEXT, { id: "proto-int-1" });
    const result = runPipeline(doc, [QUALIFIED_CANDIDATE]);
    expect(result.protocolId).toBe("proto-int-1");
  });

  it("totalCandidates matches the number of candidates passed in", () => {
    const doc = parseDocument(PROTOCOL_TEXT, { id: "proto-int-2" });
    const candidates = [QUALIFIED_CANDIDATE, TOO_YOUNG, LOW_EGFR];
    const result = runPipeline(doc, candidates);
    expect(result.totalCandidates).toBe(3);
  });

  it("passed + failed + needsReview equals totalCandidates", () => {
    const doc = parseDocument(PROTOCOL_TEXT, { id: "proto-int-3" });
    const candidates = [QUALIFIED_CANDIDATE, TOO_YOUNG, LOW_EGFR, ACTIVE_MALIGNANCY, PREGNANT];
    const result = runPipeline(doc, candidates);

    const total =
      result.passed.length + result.failed.length + result.needsReview.length;
    expect(total).toBe(result.totalCandidates);
  });

  it("clearly disqualified candidates appear in failed bucket", () => {
    const doc = parseDocument(PROTOCOL_TEXT, { id: "proto-int-4" });
    const result = runPipeline(doc, [TOO_YOUNG, LOW_EGFR, ACTIVE_MALIGNANCY, PREGNANT]);

    const failedIds = result.failed.map((r) => r.candidateId);
    expect(failedIds).toContain("cand-f1");
    expect(failedIds).toContain("cand-f2");
    expect(failedIds).toContain("cand-f3");
    expect(failedIds).toContain("cand-f4");
  });

  it("paretoCriteria contains at most 8 entries", () => {
    const doc = parseDocument(PROTOCOL_TEXT, { id: "proto-int-5" });
    const result = runPipeline(doc, [QUALIFIED_CANDIDATE]);
    expect(result.paretoCriteria.length).toBeLessThanOrEqual(8);
  });

  it("durationMs is a non-negative number", () => {
    const doc = parseDocument(PROTOCOL_TEXT, { id: "proto-int-6" });
    const result = runPipeline(doc, [QUALIFIED_CANDIDATE, TOO_YOUNG]);
    expect(result.durationMs).toBeGreaterThanOrEqual(0);
  });

  it("handles an empty candidate list without throwing", () => {
    const doc = parseDocument(PROTOCOL_TEXT, { id: "proto-int-7" });
    const result = runPipeline(doc, []);
    expect(result.totalCandidates).toBe(0);
    expect(result.passed).toHaveLength(0);
    expect(result.failed).toHaveLength(0);
  });
});
