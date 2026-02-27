import { describe, expect, it } from "vitest";
import { extractCriteria } from "../../src/pipeline/criteriaExtractor.js";
import { parseDocument } from "../../src/pipeline/documentParser.js";

describe("L2 · criteriaExtractor", () => {
  it("extracts at least one exclusion criterion from a standard protocol", () => {
    const doc = parseDocument(
      `Phase II Oncology Trial

Inclusion Criteria:
- Age between 18 and 75 years
- Confirmed NSCLC diagnosis

Exclusion Criteria:
- Prior cancer treatment with investigational agent
- Active malignancy other than NSCLC
- Renal impairment with eGFR < 45`,
      { id: "proto-1" }
    );

    const criteria = extractCriteria(doc);
    const exclusions = criteria.filter((c) => c.type === "exclusion");
    expect(exclusions.length).toBeGreaterThanOrEqual(1);
  });

  it("extracts at least one inclusion criterion from a standard protocol", () => {
    const doc = parseDocument(
      `Trial Protocol

Inclusion Criteria:
- Age between 18 and 75 years
- Written informed consent

Exclusion Criteria:
- Pregnant or breastfeeding`,
      { id: "proto-2" }
    );

    const criteria = extractCriteria(doc);
    const inclusions = criteria.filter((c) => c.type === "inclusion");
    expect(inclusions.length).toBeGreaterThanOrEqual(1);
  });

  it("assigns unique ids to every criterion", () => {
    const doc = parseDocument(
      `Trial

Inclusion Criteria:
- Age between 18 and 75 years
- Confirmed diagnosis

Exclusion Criteria:
- Prior treatment with checkpoint inhibitor therapy
- Active malignancy
- Renal impairment with eGFR < 30`,
      { id: "proto-3" }
    );

    const criteria = extractCriteria(doc);
    const ids = criteria.map((c) => c.id);
    const unique = new Set(ids);
    expect(unique.size).toBe(ids.length);
  });

  it("assigns a numeric eliminationRate between 0 and 1 to each criterion", () => {
    const doc = parseDocument(
      `Trial

Inclusion Criteria:
- Age between 18 and 75 years

Exclusion Criteria:
- Prior cancer treatment with XYZ
- Pregnant or breastfeeding`,
      { id: "proto-4" }
    );

    const criteria = extractCriteria(doc);
    for (const c of criteria) {
      expect(c.eliminationRate).toBeGreaterThan(0);
      expect(c.eliminationRate).toBeLessThanOrEqual(1);
    }
  });

  it("ranks criteria so high-elimination-rate criteria come first (lower index = higher priority)", () => {
    const doc = parseDocument(
      `Trial

Exclusion Criteria:
- Known allergy or hypersensitivity to study drug
- Prior cancer treatment with investigational compound
- Active malignancy other than target indication`,
      { id: "proto-5" }
    );

    const criteria = extractCriteria(doc);
    for (let i = 0; i < criteria.length - 1; i++) {
      expect(criteria[i].eliminationRate).toBeGreaterThanOrEqual(
        criteria[i + 1].eliminationRate
      );
    }
  });

  it("returns an empty array for a document with no recognisable criteria blocks", () => {
    const doc = parseDocument(
      "This document contains no eligibility sections at all.",
      { id: "proto-6" }
    );

    const criteria = extractCriteria(doc);
    expect(criteria).toHaveLength(0);
  });
});
