import { useState } from "react";
import { ActivitySquare, ChevronRight, Loader2 } from "lucide-react";
import { PipelineFlow, type PipelineStep } from "./components/PipelineFlow";
import { ProtocolUpload } from "./components/ProtocolUpload";
import { CriteriaTable } from "./components/CriteriaTable";
import { ScreeningForm } from "./components/ScreeningForm";
import { ScreeningResultCard } from "./components/ScreeningResultCard";
import { useProtocol } from "./hooks/useProtocol";
import type { ScreeningResult } from "./lib/types";

// Map pipeline status → step statuses for the flow diagram
function buildSteps(status: string): PipelineStep[] {
  const stepDefs = [
    { id: "classify",  label: "Classify PDF",     sublabel: "text / scanned / hybrid",     icon: "🔍" },
    { id: "extract",   label: "Extract Text",      sublabel: "PyMuPDF + OCR fallback",       icon: "📄" },
    { id: "locate",    label: "Locate Section",    sublabel: "heuristic → LLM fallback",     icon: "🎯" },
    { id: "criteria",  label: "Extract Criteria",  sublabel: "LLM → structured JSON",        icon: "🤖" },
    { id: "rank",      label: "Rank Disqualifiers", sublabel: "Pareto top-8 scoring",        icon: "📊" },
    { id: "screen",    label: "Screen Patient",    sublabel: "fast pre-screen filter",       icon: "🏥" },
  ];

  type S = PipelineStep["status"];
  let statuses: S[];

  switch (status) {
    case "idle":       statuses = ["idle","idle","idle","idle","idle","idle"]; break;
    case "processing": statuses = ["done","done","done","active","idle","idle"]; break;
    case "ready":      statuses = ["done","done","done","done","done","idle"]; break;
    case "error":      statuses = ["done","done","error","idle","idle","idle"]; break;
    default:           statuses = ["idle","idle","idle","idle","idle","idle"];
  }

  return stepDefs.map((s, i) => ({ ...s, status: statuses[i] ?? "idle" }));
}

export default function App() {
  const protocol = useProtocol();
  const [screeningResult, setScreeningResult] = useState<ScreeningResult | null>(null);
  const steps = buildSteps(protocol.status);

  const isReady = protocol.status === "ready" && protocol.criteria != null;

  return (
    <div className="min-h-full bg-slate-950 text-slate-100 font-sans">
      {/* Header */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-3">
          <ActivitySquare className="w-6 h-6 text-brand-500" />
          <span className="font-bold text-lg tracking-tight">docu-flow</span>
          <span className="text-slate-600 text-sm">·</span>
          <span className="text-slate-400 text-sm">Clinical Trial Eligibility Screening</span>

          {protocol.status === "processing" && (
            <div className="ml-auto flex items-center gap-2 text-sm text-brand-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              Processing protocol…
            </div>
          )}
          {isReady && (
            <div className="ml-auto flex items-center gap-1.5 text-sm text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              Protocol ready
            </div>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Pipeline flow diagram */}
        <section className="space-y-3">
          <SectionHeader step={1} title="Pipeline" subtitle="Live status of each processing stage" />
          <PipelineFlow steps={steps} />
        </section>

        {/* Two-column layout below the flow */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left col: upload + criteria */}
          <div className="lg:col-span-2 space-y-6">
            {/* Upload */}
            <Card>
              <SectionHeader step={2} title="Upload Protocol" subtitle="Drop a clinical trial protocol PDF" />
              <div className="mt-4">
                <ProtocolUpload
                  onUpload={protocol.upload}
                  uploading={protocol.uploading}
                  filename={protocol.filename}
                  error={protocol.error}
                />
              </div>
            </Card>

            {/* Extracted criteria */}
            {isReady && protocol.criteria && (
              <Card>
                <SectionHeader step={4} title="Extracted Criteria" subtitle="LLM-structured output with ranked disqualifiers" />
                <div className="mt-5">
                  <CriteriaTable extracted={protocol.criteria} />
                </div>
              </Card>
            )}
          </div>

          {/* Right col: screening */}
          <div className="space-y-6">
            <Card>
              <SectionHeader step={3} title="Screen Patient" subtitle="Apply top-8 Pareto filter" />
              <div className="mt-4">
                {!isReady ? (
                  <EmptyState
                    message={
                      protocol.status === "idle"
                        ? "Upload a protocol PDF first"
                        : protocol.status === "processing"
                        ? "Waiting for protocol to finish processing…"
                        : "Protocol processing failed"
                    }
                  />
                ) : screeningResult ? (
                  <ScreeningResultCard
                    result={screeningResult}
                    onReset={() => setScreeningResult(null)}
                  />
                ) : (
                  <ScreeningForm
                    protocolId={protocol.protocolId!}
                    onResult={setScreeningResult}
                  />
                )}
              </div>
            </Card>

            {/* Stats summary when ready */}
            {isReady && protocol.criteria && (
              <Card>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
                  Protocol Summary
                </p>
                <div className="space-y-2">
                  {[
                    ["Total criteria",    protocol.criteria.criteria.length],
                    ["Inclusion",         protocol.criteria.criteria.filter(c => c.criterion_type === "inclusion").length],
                    ["Exclusion",         protocol.criteria.criteria.filter(c => c.criterion_type === "exclusion").length],
                    ["Top disqualifiers", protocol.criteria.top_disqualifiers.length],
                    ["Confidence",        `${Math.round(protocol.criteria.metadata.extraction_confidence * 100)}%`],
                    ["Warnings",          protocol.criteria.metadata.warnings.length],
                  ].map(([label, value]) => (
                    <div key={String(label)} className="flex justify-between text-sm">
                      <span className="text-slate-400">{label}</span>
                      <span className="font-medium text-slate-200">{value}</span>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-2xl bg-slate-900/70 border border-slate-800/80 p-5 backdrop-blur-sm">
      {children}
    </div>
  );
}

function SectionHeader({ step, title, subtitle }: { step: number; title: string; subtitle: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="shrink-0 w-7 h-7 rounded-full bg-brand-600/30 border border-brand-500/40 flex items-center justify-center text-xs font-bold text-brand-300">
        {step}
      </span>
      <div>
        <h2 className="text-base font-semibold text-slate-100 leading-none">{title}</h2>
        <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>
      </div>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-center">
      <ChevronRight className="w-6 h-6 text-slate-700" />
      <p className="text-sm text-slate-500">{message}</p>
    </div>
  );
}
