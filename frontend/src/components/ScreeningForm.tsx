import { useState } from "react";
import { User, FlaskConical, Loader2 } from "lucide-react";
import { cn } from "../lib/utils";
import type { ScreeningRequest, ScreeningResult } from "../lib/types";
import { api } from "../lib/api";

interface ScreeningFormProps {
  protocolId: string;
  onResult: (result: ScreeningResult) => void;
}

const PRESETS: Array<{ label: string; data: ScreeningRequest["patient_data"] }> = [
  {
    label: "Healthy Adult M",
    data: { age: 42, sex: "male", diagnoses: [], prior_malignancy: false, is_pregnant: false, HbA1c: 5.6, eGFR: 88 },
  },
  {
    label: "DM + Renal",
    data: { age: 58, sex: "female", diagnoses: ["type 2 diabetes"], HbA1c: 8.4, eGFR: 26, prior_malignancy: false, is_pregnant: false },
  },
  {
    label: "Prior Cancer",
    data: { age: 51, sex: "male", diagnoses: ["colorectal cancer (remission 18 mo)"], prior_malignancy: true, is_pregnant: false, HbA1c: 5.9, eGFR: 72 },
  },
  {
    label: "Pregnant",
    data: { age: 31, sex: "female", is_pregnant: true, diagnoses: [], prior_malignancy: false },
  },
];

export function ScreeningForm({ protocolId, onResult }: ScreeningFormProps) {
  const [patientId, setPatientId] = useState("pt-001");
  const [json, setJson] = useState(JSON.stringify(PRESETS[0]!.data, null, 2));
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  function applyPreset(data: ScreeningRequest["patient_data"]) {
    setJson(JSON.stringify(data, null, 2));
    setJsonError(null);
  }

  function handleJsonChange(v: string) {
    setJson(v);
    try {
      JSON.parse(v);
      setJsonError(null);
    } catch {
      setJsonError("Invalid JSON");
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (jsonError) return;
    setApiError(null);
    setLoading(true);
    try {
      const patientData = JSON.parse(json) as ScreeningRequest["patient_data"];
      const result = await api.screenPatient({ patient_id: patientId, protocol_id: protocolId, patient_data: patientData });
      onResult(result);
    } catch (err) {
      setApiError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
          <User className="w-4 h-4 text-gray-400" />
          Patient ID
        </label>
        <input
          type="text"
          value={patientId}
          onChange={e => setPatientId(e.target.value)}
          className="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400"
          placeholder="pt-001"
        />
      </div>

      {/* Presets */}
      <div className="space-y-2">
        <p className="text-xs text-gray-400 uppercase tracking-wide">Quick presets</p>
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              type="button"
              onClick={() => applyPreset(p.data)}
              className="text-xs px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-600 border border-gray-200 transition-colors"
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Patient JSON editor */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
          <FlaskConical className="w-4 h-4 text-gray-400" />
          Patient Data
          <span className="text-xs text-gray-400 font-normal">(JSON)</span>
        </label>
        <textarea
          value={json}
          onChange={e => handleJsonChange(e.target.value)}
          rows={10}
          spellCheck={false}
          className={cn(
            "w-full font-mono text-xs bg-gray-50 border rounded-lg px-3 py-2.5 text-gray-800 focus:outline-none focus:ring-2 resize-y",
            jsonError
              ? "border-red-300 focus:ring-red-300"
              : "border-gray-300 focus:ring-blue-500/30 focus:border-blue-400"
          )}
        />
        {jsonError && <p className="text-xs text-red-500">{jsonError}</p>}
      </div>

      {apiError && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
          {apiError}
        </div>
      )}

      <button
        type="submit"
        disabled={loading || !!jsonError}
        className="w-full flex items-center justify-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm py-2.5 transition-colors"
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Screening...
          </>
        ) : (
          "Run Pre-screen"
        )}
      </button>
    </form>
  );
}
