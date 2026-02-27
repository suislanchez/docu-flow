import { BookOpen, Clock, Hash, GitBranch, AlertTriangle } from "lucide-react";
import type { EligibilityCriterion, ExtractedCriteria } from "../lib/types";
import { cn, POWER_COLORS } from "../lib/utils";

interface CriteriaTableProps {
  extracted: ExtractedCriteria;
}

export function CriteriaTable({ extracted }: CriteriaTableProps) {
  const { top_disqualifiers, criteria, metadata } = extracted;

  return (
    <div className="space-y-6">
      {/* Protocol meta */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Protocol",  value: extracted.protocol_title ?? "—" },
          { label: "Sponsor",   value: extracted.sponsor ?? "—" },
          { label: "Phase",     value: extracted.phase ?? "—" },
          { label: "Area",      value: extracted.therapeutic_area ?? "—" },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-lg bg-slate-800/60 border border-slate-700/60 px-3 py-2">
            <p className="text-xs text-slate-500 uppercase tracking-wide">{label}</p>
            <p className="text-sm text-slate-200 font-medium mt-0.5 truncate" title={value}>{value}</p>
          </div>
        ))}
      </div>

      {/* Stats row */}
      <div className="flex flex-wrap gap-3 text-sm">
        <Chip label={`${criteria.length} total criteria`} color="bg-slate-700/50 text-slate-300" />
        <Chip label={`${criteria.filter(c => c.criterion_type === "inclusion").length} inclusion`} color="bg-emerald-900/40 text-emerald-300" />
        <Chip label={`${criteria.filter(c => c.criterion_type === "exclusion").length} exclusion`} color="bg-red-900/40 text-red-300" />
        <Chip label={`${Math.round(metadata.extraction_confidence * 100)}% confidence`} color="bg-brand-900/40 text-brand-300" />
        {metadata.section_name && (
          <Chip label={`§ ${metadata.section_name}`} color="bg-slate-700/50 text-slate-400" />
        )}
      </div>

      {/* Top disqualifiers */}
      <div>
        <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
          <span className="w-5 h-5 rounded bg-red-500/20 flex items-center justify-center text-red-400 text-xs font-bold">!</span>
          Top {top_disqualifiers.length} Disqualifiers
          <span className="text-xs font-normal text-slate-500">(Pareto fast-filter)</span>
        </h3>

        <div className="space-y-2">
          {top_disqualifiers.map((c, i) => (
            <CriterionRow key={c.id} criterion={c} rank={i + 1} />
          ))}
        </div>
      </div>

      {/* Warnings */}
      {metadata.warnings.length > 0 && (
        <div className="rounded-lg bg-amber-900/20 border border-amber-500/20 p-3 space-y-1">
          <p className="text-xs font-semibold text-amber-400 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" />
            Extraction warnings
          </p>
          {metadata.warnings.map((w, i) => (
            <p key={i} className="text-xs text-amber-300/80">{w}</p>
          ))}
        </div>
      )}
    </div>
  );
}

function CriterionRow({ criterion, rank }: { criterion: EligibilityCriterion; rank: number }) {
  const { text, disqualification_power, source_page, has_temporal_condition, has_numeric_threshold, has_conditional_logic, is_ambiguous } = criterion;

  return (
    <div className="flex gap-3 rounded-lg bg-slate-800/40 border border-slate-700/40 p-3 hover:border-slate-600/60 transition-colors">
      <span className="shrink-0 w-6 h-6 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold text-slate-300">
        {rank}
      </span>

      <div className="min-w-0 flex-1 space-y-1.5">
        <p className="text-sm text-slate-200 leading-snug">{text}</p>

        <div className="flex flex-wrap gap-1.5">
          <span className={cn("inline-flex items-center text-xs px-2 py-0.5 rounded-full border font-medium", POWER_COLORS[disqualification_power])}>
            {disqualification_power.replace("_", " ")}
          </span>

          {source_page != null && (
            <Tag icon={<BookOpen className="w-3 h-3" />} label={`p.${source_page}`} />
          )}
          {has_temporal_condition && <Tag icon={<Clock className="w-3 h-3" />} label="temporal" />}
          {has_numeric_threshold  && <Tag icon={<Hash className="w-3 h-3" />} label="threshold" />}
          {has_conditional_logic  && <Tag icon={<GitBranch className="w-3 h-3" />} label="conditional" />}
          {is_ambiguous           && <Tag icon={<AlertTriangle className="w-3 h-3" />} label="ambiguous" color="text-amber-400/80" />}
        </div>
      </div>
    </div>
  );
}

function Tag({ icon, label, color = "text-slate-500" }: { icon: React.ReactNode; label: string; color?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1 text-xs", color)}>
      {icon}{label}
    </span>
  );
}

function Chip({ label, color }: { label: string; color: string }) {
  return (
    <span className={cn("inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium", color)}>
      {label}
    </span>
  );
}
