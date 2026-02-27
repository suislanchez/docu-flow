import { BookOpen, Clock, Hash, GitBranch, AlertTriangle } from "lucide-react";
import type { EligibilityCriterion, ExtractedCriteria } from "../lib/types";
import { cn, POWER_COLORS } from "../lib/utils";

interface CriteriaTableProps {
  extracted: ExtractedCriteria;
}

export function CriteriaTable({ extracted }: CriteriaTableProps) {
  const { top_disqualifiers, criteria, metadata } = extracted;

  return (
    <div className="space-y-5">
      {/* Protocol meta */}
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: "Protocol",  value: extracted.protocol_title ?? "--" },
          { label: "Sponsor",   value: extracted.sponsor ?? "--" },
          { label: "Phase",     value: extracted.phase ?? "--" },
          { label: "Area",      value: extracted.therapeutic_area ?? "--" },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-lg bg-gray-50 border border-gray-200 px-3 py-2">
            <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
            <p className="text-sm text-gray-800 font-medium mt-0.5 truncate" title={value}>{value}</p>
          </div>
        ))}
      </div>

      {/* Stats row */}
      <div className="flex flex-wrap gap-2 text-sm">
        <Chip label={`${criteria.length} total`} color="bg-gray-100 text-gray-600" />
        <Chip label={`${criteria.filter(c => c.criterion_type === "inclusion").length} inclusion`} color="bg-emerald-50 text-emerald-700" />
        <Chip label={`${criteria.filter(c => c.criterion_type === "exclusion").length} exclusion`} color="bg-red-50 text-red-700" />
        <Chip label={`${Math.round(metadata.extraction_confidence * 100)}% confidence`} color="bg-blue-50 text-blue-700" />
        {metadata.section_name && (
          <Chip label={metadata.section_name} color="bg-gray-100 text-gray-500" />
        )}
      </div>

      {/* Top disqualifiers */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
          <span className="w-5 h-5 rounded bg-red-100 flex items-center justify-center text-red-500 text-xs font-bold">!</span>
          Top {top_disqualifiers.length} Disqualifiers
          <span className="text-xs font-normal text-gray-400">(Pareto fast-filter)</span>
        </h3>

        <div className="space-y-2">
          {top_disqualifiers.map((c, i) => (
            <CriterionRow key={c.id} criterion={c} rank={i + 1} />
          ))}
        </div>
      </div>

      {/* Warnings */}
      {metadata.warnings.length > 0 && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 space-y-1">
          <p className="text-xs font-semibold text-amber-700 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" />
            Extraction warnings
          </p>
          {metadata.warnings.map((w, i) => (
            <p key={i} className="text-xs text-amber-600">{w}</p>
          ))}
        </div>
      )}
    </div>
  );
}

function CriterionRow({ criterion, rank }: { criterion: EligibilityCriterion; rank: number }) {
  const { text, disqualification_power, source_page, has_temporal_condition, has_numeric_threshold, has_conditional_logic, is_ambiguous } = criterion;

  return (
    <div className="flex gap-3 rounded-lg bg-white border border-gray-200 p-3 hover:border-gray-300 transition-colors">
      <span className="shrink-0 w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-500">
        {rank}
      </span>

      <div className="min-w-0 flex-1 space-y-1.5">
        <p className="text-sm text-gray-800 leading-snug">{text}</p>

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
          {is_ambiguous           && <Tag icon={<AlertTriangle className="w-3 h-3" />} label="ambiguous" color="text-amber-600" />}
        </div>
      </div>
    </div>
  );
}

function Tag({ icon, label, color = "text-gray-400" }: { icon: React.ReactNode; label: string; color?: string }) {
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
