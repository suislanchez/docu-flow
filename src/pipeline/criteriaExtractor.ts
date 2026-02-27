import type { EligibilityCriterion, ProtocolDocument } from "../types.js";

/**
 * Extracts eligibility criteria from a protocol document.
 * In production this calls an LLM with a structured extraction prompt.
 * This stub uses regex heuristics for tests.
 */
export function extractCriteria(
  doc: ProtocolDocument
): EligibilityCriterion[] {
  const text = doc.rawText;
  const criteria: EligibilityCriterion[] = [];

  const inclusionMatch = text.match(
    /inclusion criteria[:\s]+([\s\S]*?)(?=exclusion criteria|$)/i
  );
  const exclusionMatch = text.match(/exclusion criteria[:\s]+([\s\S]*?)$/i);

  if (inclusionMatch) {
    parseBullets(inclusionMatch[1], "inclusion").forEach((c, i) => {
      criteria.push({ ...c, id: `inc-${i + 1}` });
    });
  }

  if (exclusionMatch) {
    parseBullets(exclusionMatch[1], "exclusion").forEach((c, i) => {
      criteria.push({ ...c, id: `exc-${i + 1}` });
    });
  }

  return rankByEliminationRate(criteria);
}

function parseBullets(
  block: string,
  type: "inclusion" | "exclusion"
): Omit<EligibilityCriterion, "id">[] {
  return block
    .split(/\n/)
    .map((l) => l.replace(/^[-•*\d.]+\s*/, "").trim())
    .filter((l) => l.length > 10)
    .map((text) => ({
      type,
      text,
      eliminationRate: estimateEliminationRate(text),
      priority: 0, // set after ranking
    }));
}

/** Heuristic: keywords that suggest high elimination. Production: LLM. */
function estimateEliminationRate(text: string): number {
  const t = text.toLowerCase();
  if (/prior.*cancer|active.*malignancy/.test(t)) return 0.35;
  if (/age.*[<>]|between.*\d+.*and.*\d+.*years/.test(t)) return 0.3;
  if (/renal.*impairment|egfr.*</.test(t)) return 0.25;
  if (/hepatic.*impairment|liver.*disease/.test(t)) return 0.22;
  if (/pregnant|breastfeeding/.test(t)) return 0.2;
  if (/prior.*treatment|previous.*therapy/.test(t)) return 0.18;
  if (/allergy|hypersensitivity/.test(t)) return 0.15;
  if (/psychiatric|mental.*disorder/.test(t)) return 0.12;
  return 0.05;
}

function rankByEliminationRate(
  criteria: EligibilityCriterion[]
): EligibilityCriterion[] {
  return [...criteria]
    .sort((a, b) => b.eliminationRate - a.eliminationRate)
    .map((c, i) => ({ ...c, priority: criteria.length - i }));
}
