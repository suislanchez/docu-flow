import { describe, expect, it } from "vitest";
import { extractCriteria } from "../../src/pipeline/criteriaExtractor.js";
import { parseDocument } from "../../src/pipeline/documentParser.js";
import {
  estimateCombinedEliminationRate,
  selectParetoCriteria,
} from "../../src/pipeline/paretoFilter.js";

const FULL_PROTOCOL = `
Phase II Oncology Trial – Investigational Agent ZX-100

Inclusion Criteria:
- Age between 18 and 75 years
- Histologically confirmed non-small cell lung cancer (NSCLC)
- ECOG performance status 0 or 1
- Written informed consent obtained

Exclusion Criteria:
- Prior cancer treatment with ZX-100 or related compounds
- Active malignancy other than NSCLC
- Renal impairment with eGFR < 45 mL/min/1.73m²
- Hepatic impairment (Child-Pugh B or C)
- Pregnant or breastfeeding women
- Known allergy or hypersensitivity to study drug excipients
- Psychiatric disorder requiring hospitalisation in the past 12 months
- Prior treatment with checkpoint inhibitor therapy within 6 months
- Active autoimmune disease requiring systemic treatment
- Concurrent use of strong CYP3A4 inhibitors
- Uncontrolled diabetes
`.trim();

describe("L4 · paretoFilter (integration)", () => {
  it("selectParetoCriteria returns at most 8 criteria", () => {
    const doc = parseDocument(FULL_PROTOCOL, { id: "proto-pareto-1" });
    const allCriteria = extractCriteria(doc);
    const pareto = selectParetoCriteria(allCriteria);

    expect(pareto.length).toBeLessThanOrEqual(8);
  });

  it("selectParetoCriteria contains only criteria from the full extracted set", () => {
    const doc = parseDocument(FULL_PROTOCOL, { id: "proto-pareto-2" });
    const allCriteria = extractCriteria(doc);
    const pareto = selectParetoCriteria(allCriteria);
    const allIds = new Set(allCriteria.map((c) => c.id));

    for (const c of pareto) {
      expect(allIds.has(c.id)).toBe(true);
    }
  });

  it("pareto set is sorted by eliminationRate descending", () => {
    const doc = parseDocument(FULL_PROTOCOL, { id: "proto-pareto-3" });
    const allCriteria = extractCriteria(doc);
    const pareto = selectParetoCriteria(allCriteria);

    for (let i = 0; i < pareto.length - 1; i++) {
      expect(pareto[i].eliminationRate).toBeGreaterThanOrEqual(
        pareto[i + 1].eliminationRate
      );
    }
  });

  it("estimateCombinedEliminationRate for pareto set is >= 0.70 (Pareto principle)", () => {
    const doc = parseDocument(FULL_PROTOCOL, { id: "proto-pareto-4" });
    const allCriteria = extractCriteria(doc);
    const pareto = selectParetoCriteria(allCriteria);
    const rate = estimateCombinedEliminationRate(pareto);

    expect(rate).toBeGreaterThanOrEqual(0.7);
  });

  it("combined elimination rate never exceeds 1", () => {
    const doc = parseDocument(FULL_PROTOCOL, { id: "proto-pareto-5" });
    const allCriteria = extractCriteria(doc);
    const pareto = selectParetoCriteria(allCriteria);
    const rate = estimateCombinedEliminationRate(pareto);

    expect(rate).toBeLessThanOrEqual(1);
  });

  it("a custom limit of 3 returns at most 3 criteria", () => {
    const doc = parseDocument(FULL_PROTOCOL, { id: "proto-pareto-6" });
    const allCriteria = extractCriteria(doc);
    const pareto = selectParetoCriteria(allCriteria, 3);

    expect(pareto.length).toBeLessThanOrEqual(3);
  });

  it("pareto criteria are a strict subset of all extracted criteria", () => {
    const doc = parseDocument(FULL_PROTOCOL, { id: "proto-pareto-7" });
    const allCriteria = extractCriteria(doc);
    const pareto = selectParetoCriteria(allCriteria);
    const allIds = new Set(allCriteria.map((c) => c.id));

    for (const c of pareto) {
      expect(allIds.has(c.id)).toBe(true);
    }
  });
});
