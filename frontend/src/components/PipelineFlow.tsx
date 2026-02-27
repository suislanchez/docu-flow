/**
 * n8n-style vertical pipeline flow with clickable nodes and right sidebar.
 */
import { useCallback, useState } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  type Node,
  type Edge,
  MarkerType,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  Search,
  FileText,
  MapPin,
  Cpu,
  BarChart3,
  Shield,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  X,
} from "lucide-react";
import { cn } from "../lib/utils";

type StepStatus = "idle" | "active" | "done" | "error";

export interface PipelineStep {
  id: string;
  label: string;
  sublabel: string;
  icon: string;
  status: StepStatus;
}

interface StepNodeData extends Record<string, unknown> {
  label: string;
  sublabel: string;
  stepIndex: number;
  status: StepStatus;
  selected?: boolean;
}

const STEP_ICONS = [Search, FileText, MapPin, Cpu, BarChart3, Shield];

const STATUS_STYLES = {
  idle: {
    border: "border-gray-200",
    bg: "bg-white",
    indicator: "bg-gray-300",
    label: "text-gray-900",
    sublabel: "text-gray-500",
  },
  active: {
    border: "border-blue-400 shadow-sm shadow-blue-100",
    bg: "bg-white",
    indicator: "bg-blue-500 animate-pulse",
    label: "text-gray-900",
    sublabel: "text-gray-500",
  },
  done: {
    border: "border-emerald-300",
    bg: "bg-white",
    indicator: "bg-emerald-500",
    label: "text-gray-900",
    sublabel: "text-gray-500",
  },
  error: {
    border: "border-red-300",
    bg: "bg-white",
    indicator: "bg-red-500",
    label: "text-gray-900",
    sublabel: "text-gray-500",
  },
};

function StepNode({ data }: { data: StepNodeData }) {
  const { label, sublabel, stepIndex, status, selected } = data;
  const styles = STATUS_STYLES[status];
  const Icon = STEP_ICONS[stepIndex] ?? Search;

  return (
    <div
      className={cn(
        "relative w-[280px] rounded-lg border-2 px-5 py-4 transition-all duration-300 cursor-pointer",
        styles.border,
        styles.bg,
        selected && "ring-2 ring-blue-500 ring-offset-2"
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-300 !border-gray-400 !w-2.5 !h-2.5 !-top-[6px]" />
      <div className="flex items-center gap-4">
        <div className={cn(
          "shrink-0 w-10 h-10 rounded-lg flex items-center justify-center",
          status === "done" ? "bg-emerald-50 text-emerald-600" :
          status === "active" ? "bg-blue-50 text-blue-600" :
          status === "error" ? "bg-red-50 text-red-600" :
          "bg-gray-50 text-gray-400"
        )}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className={cn("text-sm font-semibold", styles.label)}>{label}</span>
            <span className={cn("shrink-0 w-2 h-2 rounded-full", styles.indicator)} />
          </div>
          <p className={cn("text-xs mt-0.5 leading-snug", styles.sublabel)}>{sublabel}</p>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-gray-300 !border-gray-400 !w-2.5 !h-2.5 !-bottom-[6px]" />
    </div>
  );
}

function ForkNode({ data }: { data: Record<string, unknown> }) {
  const active = data.active as boolean | undefined;
  return (
    <div
      className={cn(
        "w-10 h-10 rounded-full border-2 flex items-center justify-center transition-all duration-300",
        active
          ? "border-blue-400 bg-blue-50 text-blue-600"
          : "border-gray-300 bg-white text-gray-400"
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-300 !border-gray-400 !w-2.5 !h-2.5 !-top-[6px]" />
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M6 3v12M18 3v6M6 21a3 3 0 100-6 3 3 0 000 6zM18 12a3 3 0 100-6 3 3 0 000 6z" />
        <path d="M18 9a9 9 0 01-9 9" />
      </svg>
      <Handle type="source" id="left" position={Position.Left} className="!bg-gray-300 !border-gray-400 !w-2.5 !h-2.5" />
      <Handle type="source" id="right" position={Position.Right} className="!bg-gray-300 !border-gray-400 !w-2.5 !h-2.5" />
      <Handle type="source" id="bottom" position={Position.Bottom} className="!bg-gray-300 !border-gray-400 !w-2.5 !h-2.5 !-bottom-[6px]" />
    </div>
  );
}

function OutcomeNode({ data }: { data: Record<string, unknown> }) {
  const variant = data.variant as "pass" | "fail" | "escalate";
  const config = {
    pass: {
      bg: "bg-emerald-50 border-emerald-200",
      text: "text-emerald-700",
      Icon: CheckCircle2,
      label: "Passed Pre-screen",
      sub: "Full human review",
    },
    fail: {
      bg: "bg-red-50 border-red-200",
      text: "text-red-700",
      Icon: XCircle,
      label: "Disqualified",
      sub: "~80% of candidates",
    },
    escalate: {
      bg: "bg-amber-50 border-amber-200",
      text: "text-amber-700",
      Icon: AlertTriangle,
      label: "Escalate",
      sub: "Low confidence",
    },
  }[variant];

  return (
    <div className={cn("rounded-lg border-2 px-4 py-3 w-[180px]", config.bg)}>
      <Handle type="target" position={Position.Left} className="!bg-gray-300 !border-gray-400 !w-2.5 !h-2.5" />
      <Handle type="target" id="top" position={Position.Top} className="!bg-gray-300 !border-gray-400 !w-2.5 !h-2.5 !-top-[6px]" />
      <div className={cn("font-semibold text-sm flex items-center gap-2", config.text)}>
        <config.Icon className="w-4 h-4" />
        {config.label}
      </div>
      <p className="text-xs text-gray-500 mt-0.5">{config.sub}</p>
    </div>
  );
}

const nodeTypes = { step: StepNode, fork: ForkNode, outcome: OutcomeNode };

// Step detail descriptions for sidebar
const STEP_DETAILS: Record<string, { title: string; description: string; details: string[] }> = {
  classify: {
    title: "Classify PDF",
    description: "Determines the type of PDF document to select the optimal extraction strategy.",
    details: [
      "Detects text-based, scanned, hybrid, or encrypted PDFs",
      "Routes to appropriate extraction pipeline",
      "Validates document integrity before processing",
    ],
  },
  extract: {
    title: "Extract Text",
    description: "Extracts raw text content from the PDF using adaptive strategies per page.",
    details: [
      "PyMuPDF for text-based pages",
      "Tesseract OCR fallback for scanned pages",
      "Per-page quality assessment (char count threshold)",
      "ftfy encoding repair on all extracted text",
    ],
  },
  locate: {
    title: "Locate Section",
    description: "Finds the eligibility criteria section within the extracted text.",
    details: [
      "Heuristic regex matching first (fast path)",
      "RapidFuzz fuzzy header matching for OCR typos",
      "LLM fallback for non-standard section headers",
    ],
  },
  criteria: {
    title: "Extract Criteria",
    description: "Parses eligibility criteria into structured data using LLM constrained decoding.",
    details: [
      "Anthropic messages.parse() for guaranteed valid output",
      "Pydantic v2 schema enforcement",
      "Source page citation for every criterion",
      "Inclusion and exclusion classification",
    ],
  },
  rank: {
    title: "Rank Disqualifiers",
    description: "Scores and ranks criteria by disqualification power using Pareto analysis.",
    details: [
      "Top-8 disqualifier selection",
      "Both inclusion and exclusion criteria considered",
      "Disqualification power: very_high / high / medium / low",
    ],
  },
  screen: {
    title: "Screen Patient",
    description: "Evaluates patient data against the top disqualifiers for rapid pre-screening.",
    details: [
      "Rule-based fast path for clear matches",
      "LLM escalation for ambiguous criteria",
      "Confidence < 0.70 triggers mandatory human escalation",
      "Three outcomes: pass / disqualify / escalate",
    ],
  },
};

interface PipelineFlowProps {
  steps: PipelineStep[];
  onSelectNode?: (nodeId: string | null) => void;
  selectedNodeId?: string | null;
}

export function PipelineFlow({ steps, onSelectNode, selectedNodeId }: PipelineFlowProps) {
  const X_CENTER = 140;
  const GAP_Y = 120;

  const nodes: Node[] = [
    { id: "s1", type: "step", position: { x: X_CENTER, y: 0 },          data: { ...steps[0], stepIndex: 0, selected: selectedNodeId === "s1" } },
    { id: "s2", type: "step", position: { x: X_CENTER, y: GAP_Y },      data: { ...steps[1], stepIndex: 1, selected: selectedNodeId === "s2" } },
    { id: "s3", type: "step", position: { x: X_CENTER, y: GAP_Y * 2 },  data: { ...steps[2], stepIndex: 2, selected: selectedNodeId === "s3" } },
    { id: "s4", type: "step", position: { x: X_CENTER, y: GAP_Y * 3 },  data: { ...steps[3], stepIndex: 3, selected: selectedNodeId === "s4" } },
    { id: "s5", type: "step", position: { x: X_CENTER, y: GAP_Y * 4 },  data: { ...steps[4], stepIndex: 4, selected: selectedNodeId === "s5" } },
    { id: "s6", type: "step", position: { x: X_CENTER, y: GAP_Y * 5 },  data: { ...steps[5], stepIndex: 5, selected: selectedNodeId === "s6" } },
    { id: "fork", type: "fork", position: { x: X_CENTER + 135, y: GAP_Y * 5 + 100 }, data: { active: steps[5].status === "active" || steps[5].status === "done" } },
    { id: "out-pass",     type: "outcome", position: { x: X_CENTER - 140, y: GAP_Y * 5 + 80 },  data: { variant: "pass" } },
    { id: "out-fail",     type: "outcome", position: { x: X_CENTER + 290, y: GAP_Y * 5 + 80 },  data: { variant: "fail" } },
    { id: "out-escalate", type: "outcome", position: { x: X_CENTER + 290, y: GAP_Y * 5 + 170 }, data: { variant: "escalate" } },
  ];

  const baseEdge = { stroke: "#d1d5db", strokeWidth: 1.5 };
  const activeEdge = { stroke: "#3b82f6", strokeWidth: 2 };

  function edgeStyle(fromIdx: number) {
    return steps[fromIdx]?.status === "done" ? activeEdge : baseEdge;
  }

  const edges: Edge[] = [
    { id: "e1-2", source: "s1", target: "s2", animated: steps[0].status === "done", style: edgeStyle(0), markerEnd: { type: MarkerType.ArrowClosed, color: edgeStyle(0).stroke } },
    { id: "e2-3", source: "s2", target: "s3", animated: steps[1].status === "done", style: edgeStyle(1), markerEnd: { type: MarkerType.ArrowClosed, color: edgeStyle(1).stroke } },
    { id: "e3-4", source: "s3", target: "s4", animated: steps[2].status === "done", style: edgeStyle(2), markerEnd: { type: MarkerType.ArrowClosed, color: edgeStyle(2).stroke } },
    { id: "e4-5", source: "s4", target: "s5", animated: steps[3].status === "done", style: edgeStyle(3), markerEnd: { type: MarkerType.ArrowClosed, color: edgeStyle(3).stroke } },
    { id: "e5-6", source: "s5", target: "s6", animated: steps[4].status === "done", style: edgeStyle(4), markerEnd: { type: MarkerType.ArrowClosed, color: edgeStyle(4).stroke } },
    { id: "e6-f", source: "s6", target: "fork", animated: steps[5].status === "done", style: edgeStyle(5), markerEnd: { type: MarkerType.ArrowClosed, color: edgeStyle(5).stroke } },
    {
      id: "ef-p", source: "fork", target: "out-pass", sourceHandle: "left",
      style: { stroke: "#10b981", strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: "#10b981" },
      label: "passed", labelStyle: { fill: "#059669", fontSize: 11, fontFamily: "Inter" },
    },
    {
      id: "ef-f", source: "fork", target: "out-fail", sourceHandle: "right",
      style: { stroke: "#ef4444", strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: "#ef4444" },
      label: "disqualified", labelStyle: { fill: "#dc2626", fontSize: 11, fontFamily: "Inter" },
    },
    {
      id: "ef-e", source: "fork", target: "out-escalate", sourceHandle: "bottom",
      style: { stroke: "#f59e0b", strokeWidth: 1.5, strokeDasharray: "4 3" },
      markerEnd: { type: MarkerType.ArrowClosed, color: "#f59e0b" },
      label: "escalate", labelStyle: { fill: "#d97706", fontSize: 11, fontFamily: "Inter" },
    },
  ];

  const handleNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    if (node.id.startsWith("s")) {
      onSelectNode?.(node.id === selectedNodeId ? null : node.id);
    }
  }, [onSelectNode, selectedNodeId]);

  const handlePaneClick = useCallback(() => {
    onSelectNode?.(null);
  }, [onSelectNode]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.3 }}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={true}
      onNodeClick={handleNodeClick}
      onPaneClick={handlePaneClick}
      panOnDrag={true}
      zoomOnScroll={true}
      minZoom={0.4}
      maxZoom={1.5}
      proOptions={{ hideAttribution: true }}
    >
      <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#e5e7eb" />
    </ReactFlow>
  );
}

// Sidebar component for node details
interface NodeSidebarProps {
  nodeId: string | null;
  steps: PipelineStep[];
  onClose: () => void;
}

export function NodeSidebar({ nodeId, steps, onClose }: NodeSidebarProps) {
  if (!nodeId) return null;

  const stepIndex = parseInt(nodeId.replace("s", "")) - 1;
  const step = steps[stepIndex];
  if (!step) return null;

  const detail = STEP_DETAILS[step.id];
  if (!detail) return null;

  const Icon = STEP_ICONS[stepIndex] ?? Search;

  const statusLabel = {
    idle: "Waiting",
    active: "Running",
    done: "Completed",
    error: "Failed",
  }[step.status];

  const statusColor = {
    idle: "bg-gray-100 text-gray-600",
    active: "bg-blue-100 text-blue-700",
    done: "bg-emerald-100 text-emerald-700",
    error: "bg-red-100 text-red-700",
  }[step.status];

  return (
    <div className="w-[380px] shrink-0 border-l border-gray-200 bg-white overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <div className={cn(
            "w-9 h-9 rounded-lg flex items-center justify-center",
            step.status === "done" ? "bg-emerald-50 text-emerald-600" :
            step.status === "active" ? "bg-blue-50 text-blue-600" :
            step.status === "error" ? "bg-red-50 text-red-600" :
            "bg-gray-50 text-gray-400"
          )}>
            <Icon className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">{detail.title}</h3>
            <span className={cn("inline-block text-xs font-medium px-2 py-0.5 rounded-full mt-1", statusColor)}>
              {statusLabel}
            </span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-md hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="px-5 py-4 space-y-5">
        <div>
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">Description</p>
          <p className="text-sm text-gray-700 leading-relaxed">{detail.description}</p>
        </div>

        <div>
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">Details</p>
          <ul className="space-y-2">
            {detail.details.map((d, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                <span className="shrink-0 w-1.5 h-1.5 rounded-full bg-gray-300 mt-1.5" />
                {d}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">Configuration</p>
          <div className="rounded-lg bg-gray-50 border border-gray-100 p-3 space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Step</span>
              <span className="text-gray-700 font-medium">{stepIndex + 1} of 6</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">ID</span>
              <span className="text-gray-700 font-mono font-medium">{step.id}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Status</span>
              <span className="text-gray-700 font-medium">{statusLabel}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
