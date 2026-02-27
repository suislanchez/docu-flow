import { describe, expect, it } from "vitest";
import { parseDocument } from "../../src/pipeline/documentParser.js";

describe("L1 · documentParser", () => {
  it("parses a short protocol string into a ProtocolDocument", () => {
    const raw = "Phase II Trial – Drug XYZ\n\nInclusion Criteria:\n- Age >= 18";
    const doc = parseDocument(raw, { id: "proto-001", title: "Drug XYZ Trial" });

    expect(doc.id).toBe("proto-001");
    expect(doc.title).toBe("Drug XYZ Trial");
    expect(doc.rawText).toBe(raw.trim());
    expect(doc.pageCount).toBeGreaterThanOrEqual(1);
  });

  it("auto-derives title from the first non-empty line when none is supplied", () => {
    const raw = "PROTOCOL TITLE LINE\n\nBody text follows.";
    const doc = parseDocument(raw);
    expect(doc.title).toBe("PROTOCOL TITLE LINE");
  });

  it("estimates pageCount as at least 1 for very short text", () => {
    const doc = parseDocument("Short text.");
    expect(doc.pageCount).toBe(1);
  });

  it("estimates pageCount proportional to character count (~3000 chars per page)", () => {
    const page = "A".repeat(3000);
    const doc = parseDocument(page.repeat(5)); // ~5 pages
    expect(doc.pageCount).toBeGreaterThanOrEqual(4);
    expect(doc.pageCount).toBeLessThanOrEqual(6);
  });

  it("throws when given an empty string", () => {
    expect(() => parseDocument("")).toThrow("Document text is empty");
  });

  it("throws when given only whitespace", () => {
    expect(() => parseDocument("   \n  ")).toThrow("Document text is empty");
  });

  it("trims leading and trailing whitespace from rawText", () => {
    const doc = parseDocument("  \n  Protocol body.  \n  ");
    expect(doc.rawText.startsWith(" ")).toBe(false);
    expect(doc.rawText.endsWith(" ")).toBe(false);
  });

  it("auto-generates a UUID id when none is provided", () => {
    const doc = parseDocument("Some protocol text");
    expect(doc.id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
    );
  });
});
