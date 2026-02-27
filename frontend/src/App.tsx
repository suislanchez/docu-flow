import { useState } from "react";
import { ActivitySquare, Loader2, ChevronRight, Upload, ClipboardList, UserCheck } from "lucide-react";
import { PipelineFlow, NodeSidebar, type PipelineStep } from "./components/PipelineFlow";
import { ProtocolUpload } from "./components/ProtocolUpload";
import { CriteriaTable } from "./components/CriteriaTable";
import { ScreeningForm } from "./components/ScreeningForm";
import { ScreeningResultCard } from "./components/ScreeningResultCard";
import { useProtocol } from "./hooks/useProtocol";
import type { ScreeningResult } from "./lib/types";

function buildSteps(status: string): PipelineStep[] {
  const stepDefs = [
    { id: "classify",  label: "Classify PDF",       sublabel: "text / scanned / hybrid",   icon: "search" },
    { id: "extract",   label: "Extract Text",        sublabel: "PyMuPDF + OCR fallback",    icon: "file" },
    { id: "locate",    label: "Locate Section",      sublabel: "heuristic + LLM fallback",  icon: "pin" },
    { id: "criteria",  label: "Extract Criteria",    sublabel: "LLM structured output",     icon: "cpu" },
    { id: "rank",      label: "Rank Disqualifiers",  sublabel: "Pareto top-8 scoring",      icon: "chart" },
    { id: "screen",    label: "Screen Patient",      sublabel: "confidence-gated filter",    icon: "shield" },
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

type Panel = "upload" | "criteria" | "screening" | null;

export default function App() {
  const protocol = useProtocol();
  const [screeningResult, setScreeningResult] = useState<ScreeningResult | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [activePanel, setActivePanel] = useState<Panel>(null);
  const steps = buildSteps(protocol.status);

  const isReady = protocol.status === "ready" && protocol.criteria != null;

  return (
    <div className="h-full flex flex-col bg-white text-gray-900 font-sans">
      {/* Header */}
      <header className="shrink-0 border-b border-gray-200 bg-white z-10">
        <div className="flex items-center justify-between px-5 h-14">
          <div className="flex items-center gap-3">
            <ActivitySquare className="w-5 h-5 text-blue-600" />
            <span className="font-semibold text-base tracking-tight text-gray-900">docu-flow</span>
            <span className="text-gray-300">|</span>
            <span className="text-gray-500 text-sm">Clinical Trial Eligibility Screening</span>
          </div>

          <div className="flex items-center gap-2">
            {protocol.status === "processing" && (
              <div className="flex items-center gap-2 text-sm text-blue-600">
                <Loader2 className="w-4 h-4 animate-spin" />
                Processing
              </div>
            )}
            {isReady && (
              <div className="flex items-center gap-1.5 text-sm text-emerald-600">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                Ready
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left toolbar */}
        <div className="shrink-0 w-14 border-r border-gray-200 bg-gray-50 flex flex-col items-center py-3 gap-1">
          <ToolbarButton
            icon={Upload}
            label="Upload"
            active={activePanel === "upload"}
            onClick={() => setActivePanel(activePanel === "upload" ? null : "upload")}
          />
          <ToolbarButton
            icon={ClipboardList}
            label="Criteria"
            active={activePanel === "criteria"}
            disabled={!isReady}
            onClick={() => setActivePanel(activePanel === "criteria" ? null : "criteria")}
          />
          <ToolbarButton
            icon={UserCheck}
            label="Screen"
            active={activePanel === "screening"}
            disabled={!isReady}
            onClick={() => setActivePanel(activePanel === "screening" ? null : "screening")}
          />
        </div>

        {/* Left panel (upload / criteria / screening) */}
        {activePanel && (
          <div className="shrink-0 w-[420px] border-r border-gray-200 bg-white overflow-y-auto">
            <div className="p-5">
              {activePanel === "upload" && (
                <div className="space-y-4">
                  <PanelHeader title="Upload Protocol" subtitle="Drop a clinical trial protocol PDF" />
                  <ProtocolUpload
                    onUpload={protocol.upload}
                    uploading={protocol.uploading}
                    filename={protocol.filename}
                    error={protocol.error}
                  />
                  {/* Protocol summary when ready */}
                  {isReady && protocol.criteria && (
                    <div className="mt-6 space-y-3">
                      <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Protocol Summary</p>
                      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-2">
                        {([
                          ["Total criteria",    protocol.criteria.criteria.length],
                          ["Inclusion",         protocol.criteria.criteria.filter(c => c.criterion_type === "inclusion").length],
                          ["Exclusion",         protocol.criteria.criteria.filter(c => c.criterion_type === "exclusion").length],
                          ["Top disqualifiers", protocol.criteria.top_disqualifiers.length],
                          ["Confidence",        `${Math.round(protocol.criteria.metadata.extraction_confidence * 100)}%`],
                          ["Warnings",          protocol.criteria.metadata.warnings.length],
                        ] as const).map(([label, value]) => (
                          <div key={String(label)} className="flex justify-between text-sm">
                            <span className="text-gray-500">{label}</span>
                            <span className="font-medium text-gray-800">{value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activePanel === "criteria" && isReady && protocol.criteria && (
                <div className="space-y-4">
                  <PanelHeader title="Extracted Criteria" subtitle="LLM-structured output with ranked disqualifiers" />
                  <CriteriaTable extracted={protocol.criteria} />
                </div>
              )}

              {activePanel === "screening" && (
                <div className="space-y-4">
                  <PanelHeader title="Screen Patient" subtitle="Apply top-8 Pareto filter" />
                  {!isReady ? (
                    <EmptyState
                      message={
                        protocol.status === "idle"
                          ? "Upload a protocol PDF first"
                          : protocol.status === "processing"
                          ? "Waiting for protocol to finish processing"
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
              )}
            </div>
          </div>
        )}

        {/* Flow canvas - takes remaining space */}
        <div className="flex-1 relative bg-[#fafafa]">
          <PipelineFlow
            steps={steps}
            onSelectNode={setSelectedNodeId}
            selectedNodeId={selectedNodeId}
          />
        </div>

        {/* Right sidebar for node details */}
        <NodeSidebar
          nodeId={selectedNodeId}
          steps={steps}
          onClose={() => setSelectedNodeId(null)}
        />
      </div>
    </div>
  );
}

function ToolbarButton({
  icon: Icon,
  label,
  active,
  disabled,
  onClick,
}: {
  icon: typeof Upload;
  label: string;
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={label}
      className={`w-10 h-10 rounded-lg flex items-center justify-center transition-colors ${
        disabled
          ? "text-gray-300 cursor-not-allowed"
          : active
          ? "bg-blue-100 text-blue-700"
          : "text-gray-500 hover:bg-gray-200 hover:text-gray-700"
      }`}
    >
      <Icon className="w-5 h-5" />
    </button>
  );
}

function PanelHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="mb-1">
      <h2 className="text-base font-semibold text-gray-900">{title}</h2>
      <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-center">
      <ChevronRight className="w-5 h-5 text-gray-300" />
      <p className="text-sm text-gray-400">{message}</p>
    </div>
  );
}
