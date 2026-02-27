import { CheckCircle2, XCircle, AlertTriangle, RotateCcw } from "lucide-react";
import type { ScreeningResult } from "../lib/types";
import { cn, DECISION_CONFIG, pct } from "../lib/utils";

interface ScreeningResultCardProps {
  result: ScreeningResult;
  onReset: () => void;
}

export function ScreeningResultCard({ result, onReset }: ScreeningResultCardProps) {
  const { decision, confidence, failed_criteria, passed_criteria_count, escalation_reason, patient_id, model_used } = result;
  const config = DECISION_CONFIG[decision];

  const Icon = {
    disqualified:     XCircle,
    passed_prescreen: CheckCircle2,
    escalate:         AlertTriangle,
  }[decision];

  return (
    <div className="space-y-4">
      {/* Decision banner */}
      <div className={cn("rounded-lg border px-5 py-4 flex items-start gap-4", config.color)}>
        <Icon className="w-7 h-7 shrink-0 mt-0.5" />
        <div>
          <p className="font-bold text-base">{config.label}</p>
          <p className="text-sm opacity-80 mt-0.5">
            Patient <span className="font-mono">{patient_id}</span> -- Confidence {pct(confidence)}
          </p>
        </div>
        <div className="ml-auto text-right shrink-0">
          <p className="text-2xl font-bold tabular-nums">{pct(confidence)}</p>
          <p className="text-xs opacity-60">confidence</p>
        </div>
      </div>

      {/* Confidence bar */}
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs text-gray-400">
          <span>Confidence</span>
          <span>{pct(confidence)}</span>
        </div>
        <div className="h-2 rounded-full bg-gray-100">
          <div
            className={cn(
              "h-2 rounded-full transition-all duration-700",
              decision === "disqualified"     ? "bg-red-500" :
              decision === "passed_prescreen" ? "bg-emerald-500" :
              "bg-amber-500"
            )}
            style={{ width: pct(confidence) }}
          />
        </div>
      </div>

      {/* Failed criteria */}
      {failed_criteria.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">
            Failed criteria ({failed_criteria.length})
          </p>
          {failed_criteria.map(({ criterion, reason }) => (
            <div key={criterion.id} className="rounded-lg bg-red-50 border border-red-200 p-3 space-y-1">
              <p className="text-xs font-mono text-red-500">{criterion.id}</p>
              <p className="text-sm text-gray-800 leading-snug">{criterion.text}</p>
              <p className="text-xs text-red-600 italic">{reason}</p>
            </div>
          ))}
        </div>
      )}

      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-3 text-center">
        <div className="rounded-lg bg-gray-50 border border-gray-200 py-3">
          <p className="text-2xl font-bold text-emerald-600 tabular-nums">{passed_criteria_count}</p>
          <p className="text-xs text-gray-400 mt-0.5">criteria passed</p>
        </div>
        <div className="rounded-lg bg-gray-50 border border-gray-200 py-3">
          <p className="text-2xl font-bold text-red-600 tabular-nums">{failed_criteria.length}</p>
          <p className="text-xs text-gray-400 mt-0.5">criteria failed</p>
        </div>
      </div>

      {/* Escalation reason */}
      {escalation_reason && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-700">
          <span className="font-semibold">Escalation reason:</span> {escalation_reason}
        </div>
      )}

      {model_used && (
        <p className="text-xs text-gray-400 text-right font-mono">model: {model_used}</p>
      )}

      <button
        onClick={onReset}
        className="w-full flex items-center justify-center gap-2 rounded-lg border border-gray-200 hover:border-gray-300 bg-white hover:bg-gray-50 text-gray-500 hover:text-gray-700 text-sm py-2 transition-colors"
      >
        <RotateCcw className="w-3.5 h-3.5" />
        Screen another patient
      </button>
    </div>
  );
}
