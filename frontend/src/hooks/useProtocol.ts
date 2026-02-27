import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import type { ExtractedCriteria, ProtocolJobStatus } from "../lib/types";

interface ProtocolState {
  protocolId: string | null;
  filename: string | null;
  status: ProtocolJobStatus | "idle";
  criteria: ExtractedCriteria | null;
  error: string | null;
  uploading: boolean;
}

const POLL_INTERVAL_MS = 2000;

export function useProtocol() {
  const [state, setState] = useState<ProtocolState>({
    protocolId: null,
    filename: null,
    status: "idle",
    criteria: null,
    error: null,
    uploading: false,
  });

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPoll = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => () => stopPoll(), [stopPoll]);

  const upload = useCallback(
    async (file: File) => {
      stopPoll();
      setState((s) => ({ ...s, uploading: true, error: null, status: "idle" }));
      try {
        const { protocol_id, filename } = await api.uploadProtocol(file);
        setState((s) => ({
          ...s,
          protocolId: protocol_id,
          filename,
          status: "processing",
          uploading: false,
        }));

        // Start polling
        pollRef.current = setInterval(async () => {
          try {
            const job = await api.getProtocol(protocol_id);
            setState((s) => ({
              ...s,
              status: job.status,
              criteria: job.extracted_criteria,
              error: job.error,
            }));
            if (job.status !== "processing") stopPoll();
          } catch (err) {
            setState((s) => ({
              ...s,
              status: "error",
              error: String(err),
            }));
            stopPoll();
          }
        }, POLL_INTERVAL_MS);
      } catch (err) {
        setState((s) => ({
          ...s,
          uploading: false,
          status: "error",
          error: String(err),
        }));
      }
    },
    [stopPoll]
  );

  const reset = useCallback(() => {
    stopPoll();
    setState({
      protocolId: null,
      filename: null,
      status: "idle",
      criteria: null,
      error: null,
      uploading: false,
    });
  }, [stopPoll]);

  return { ...state, upload, reset };
}
