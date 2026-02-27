import type {
  ExtractedCriteria,
  ProtocolStatus,
  ScreeningRequest,
  ScreeningResult,
  UploadResponse,
} from "./types";

const BASE = "";  // proxied via vite dev server → http://localhost:8000

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  /** Upload a protocol PDF — returns immediately with protocol_id */
  uploadProtocol(file: File): Promise<UploadResponse> {
    const fd = new FormData();
    fd.append("file", file);
    return request<UploadResponse>("/protocols/upload", {
      method: "POST",
      headers: {},   // let browser set multipart boundary
      body: fd,
    });
  },

  /** Poll for processing status */
  getProtocol(protocolId: string): Promise<ProtocolStatus> {
    return request<ProtocolStatus>(`/protocols/${protocolId}`);
  },

  /** Screen a patient against a protocol */
  screenPatient(req: ScreeningRequest): Promise<ScreeningResult> {
    return request<ScreeningResult>("/screening/screen", {
      method: "POST",
      body: JSON.stringify(req),
    });
  },

  /** Health check */
  health(): Promise<{ status: string; version: string }> {
    return request("/health");
  },
};
