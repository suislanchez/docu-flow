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
      <div className={cn("rounded-xl border px-5 py-4 flex items-start gap-4", config.color)}>
        <Icon className="w-7 h-7 shrink-0 mt-0.5" />
        <div>
          <p className="font-bold text-base">{config.label}</p>
          <p className="text-sm opacity-80 mt-0.5">
            Patient <span className="font-mono">{patient_id}</span> · Confidence {pct(confidence)}
          </p>
        </div>
        <div className="ml-auto text-right shrink-0">
          <p className="text-2xl font-bold tabular-nums">{pct(confidence)}</p>
          <p className="text-xs opacity-60">confidence</p>
        </div>
      </div>

      {/* Confidence bar */}
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs text-slate-500">
          <span>Confidence</span>
          <span>{pct(confidence)}</span>
        </div>
        <div className="h-2 rounded-full bg-slate-800">
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
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
            Failed criteria ({failed_criteria.length})
          </p>
          {failed_criteria.map(({ criterion, reason }) => (
            <div key={criterion.id} className="rounded-lg bg-red-900/20 border border-red-500/20 p-3 space-y-1">
              <p className="text-xs font-mono text-red-400">{criterion.id}</p>
              <p className="text-sm text-slate-200 leading-snug">{criterion.text}</p>
              <p className="text-xs text-red-300/80 italic">↳ {reason}</p>
            </div>
          ))}
        </div>
      )}

      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-3 text-center">
        <div className="rounded-lg bg-slate-800/60 border border-slate-700/40 py-3">
          <p className="text-2xl font-bold text-emerald-400 tabular-nums">{passed_criteria_count}</p>
          <p className="text-xs text-slate-500 mt-0.5">criteria passed</p>
        </div>
        <div className="rounded-lg bg-slate-800/60 border border-slate-700/40 py-3">
          <p className="text-2xl font-bold text-red-400 tabular-nums">{failed_criteria.length}</p>
          <p className="text-xs text-slate-500 mt-0.5">criteria failed</p>
        </div>
      </div>

      {/* Escalation reason */}
      {escalation_reason && (
        <div className="rounded-lg bg-amber-900/20 border border-amber-500/20 px-3 py-2 text-xs text-amber-300">
          <span className="font-semibold">Escalation reason:</span> {escalation_reason}
        </div>
      )}

      {model_used && (
        <p className="text-xs text-slate-600 text-right font-mono">model: {model_used}</p>
      )}

      <button
        onClick={onReset}
        className="w-full flex items-center justify-center gap-2 rounded-lg border border-slate-700 hover:border-slate-600 bg-slate-800/40 hover:bg-slate-800/70 text-slate-400 hover:text-slate-200 text-sm py-2 transition-colors"
      >
        <RotateCcw className="w-3.5 h-3.5" />
        Screen another patient
      </button>
    </div>
  );
}
