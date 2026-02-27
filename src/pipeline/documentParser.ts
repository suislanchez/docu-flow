import type { ProtocolDocument } from "../types.js";

/**
 * Parses raw input (text, future: PDF buffer) into a structured ProtocolDocument.
 * In production this will call a PDF extraction service.
 */
export function parseDocument(
  raw: string,
  options: { id?: string; title?: string } = {}
): ProtocolDocument {
  if (!raw || raw.trim().length === 0) {
    throw new Error("Document text is empty");
  }

  // Estimate pages: ~3000 characters per page
  const pageCount = Math.max(1, Math.ceil(raw.length / 3000));

  return {
    id: options.id ?? crypto.randomUUID(),
    title: options.title ?? extractTitle(raw),
    rawText: raw.trim(),
    pageCount,
  };
}

function extractTitle(text: string): string {
  // Take first non-empty line as title
  const firstLine = text.split("\n").find((l) => l.trim().length > 0);
  return firstLine?.trim().slice(0, 120) ?? "Untitled Protocol";
}
