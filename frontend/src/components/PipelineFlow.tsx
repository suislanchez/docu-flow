/**
 * Animated React Flow diagram showing the 6-step pipeline.
 * Each node lights up as the protocol moves through the pipeline.
 */
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
  icon: string;
  status: StepStatus;
}

function StepNode({ data }: { data: StepNodeData }) {
  const { label, sublabel, icon, status } = data;

  const border = {
    idle:   "border-slate-700",
    active: "border-brand-500 shadow-[0_0_16px_rgba(14,165,233,0.4)]",
    done:   "border-emerald-500/60",
    error:  "border-red-500/60",
  }[status];

  const bg = {
    idle:   "bg-slate-800/60",
    active: "bg-brand-900/60",
    done:   "bg-slate-800/80",
    error:  "bg-red-900/30",
  }[status];

  const dot = {
    idle:   "bg-slate-600",
    active: "bg-brand-500 animate-pulse",
    done:   "bg-emerald-500",
    error:  "bg-red-500",
  }[status];

  return (
    <div
      className={cn(
        "relative w-52 rounded-xl border px-4 py-3 backdrop-blur-sm transition-all duration-500",
        border,
        bg
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-slate-600 !border-slate-500 !w-2 !h-2" />
      <div className="flex items-start gap-3">
        <span className="text-2xl leading-none mt-0.5">{icon}</span>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-slate-100 truncate">{label}</span>
            <span className={cn("shrink-0 w-2 h-2 rounded-full", dot)} />
          </div>
          <p className="text-xs text-slate-400 mt-0.5 leading-snug">{sublabel}</p>
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="!bg-slate-600 !border-slate-500 !w-2 !h-2" />
    </div>
  );
}

// Fork node — after extraction, splits into "disqualified" and "qualified" paths
function ForkNode({ data }: { data: Record<string, unknown> }) {
  const active = data.active as boolean | undefined;
  return (
    <div
      className={cn(
        "w-10 h-10 rounded-full border-2 flex items-center justify-center text-lg transition-all duration-500",
        active
          ? "border-brand-500 bg-brand-900/60 shadow-[0_0_12px_rgba(14,165,233,0.3)]"
          : "border-slate-600 bg-slate-800/60"
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-slate-600 !border-slate-500 !w-2 !h-2" />
      ⑃
      <Handle type="source" id="a" position={Position.Right} className="!bg-slate-600 !border-slate-500 !w-2 !h-2" />
      <Handle type="source" id="b" position={Position.Bottom} className="!bg-slate-600 !border-slate-500 !w-2 !h-2" />
    </div>
  );
}

function OutcomeNode({ data }: { data: Record<string, unknown> }) {
  const variant = data.variant as "pass" | "fail" | "escalate";
  const config = {
    pass:     { bg: "bg-emerald-900/40 border-emerald-500/50", text: "text-emerald-300", icon: "✓", label: "Passed Pre-screen", sub: "→ Full human review" },
    fail:     { bg: "bg-red-900/40 border-red-500/50",         text: "text-red-300",     icon: "✗", label: "Disqualified",      sub: "~80% of candidates" },
    escalate: { bg: "bg-amber-900/40 border-amber-500/50",     text: "text-amber-300",   icon: "⚠", label: "Escalate",          sub: "Low confidence → human" },
  }[variant];

  return (
    <div className={cn("rounded-xl border px-4 py-3 w-44 backdrop-blur-sm", config.bg)}>
      <Handle type="target" position={Position.Left} className="!bg-slate-600 !border-slate-500 !w-2 !h-2" />
      <Handle type="target" id="top" position={Position.Top} className="!bg-slate-600 !border-slate-500 !w-2 !h-2" />
      <div className={cn("font-semibold text-sm flex items-center gap-2", config.text)}>
        <span>{config.icon}</span>
        {config.label}
      </div>
      <p className="text-xs text-slate-400 mt-0.5">{config.sub}</p>
    </div>
  );
}

const nodeTypes = { step: StepNode, fork: ForkNode, outcome: OutcomeNode };

interface PipelineFlowProps {
  steps: PipelineStep[];
}

export function PipelineFlow({ steps }: PipelineFlowProps) {
  const Y = 0;
  const GAP = 240;

  const nodes: Node[] = [
    { id: "s1", type: "step", position: { x: 0,          y: Y }, data: { ...steps[0] } },
    { id: "s2", type: "step", position: { x: GAP,        y: Y }, data: { ...steps[1] } },
    { id: "s3", type: "step", position: { x: GAP * 2,    y: Y }, data: { ...steps[2] } },
    { id: "s4", type: "step", position: { x: GAP * 3,    y: Y }, data: { ...steps[3] } },
    { id: "s5", type: "step", position: { x: GAP * 4,    y: Y }, data: { ...steps[4] } },
    { id: "s6", type: "step", position: { x: GAP * 5,    y: Y }, data: { ...steps[5] } },
    { id: "fork", type: "fork", position: { x: GAP * 5 + 220, y: Y + 12 }, data: { active: steps[5].status === "active" || steps[5].status === "done" } },
    { id: "out-pass",     type: "outcome", position: { x: GAP * 5 + 300, y: Y - 70 }, data: { variant: "pass" } },
    { id: "out-fail",     type: "outcome", position: { x: GAP * 5 + 300, y: Y + 90 }, data: { variant: "fail" } },
    { id: "out-escalate", type: "outcome", position: { x: GAP * 5 + 300, y: Y + 250 }, data: { variant: "escalate" } },
  ];

  const edgeStyle = { stroke: "#334155", strokeWidth: 1.5 };
  const activeEdge = { stroke: "#0ea5e9", strokeWidth: 2 };

  function edgeColor(fromIdx: number) {
    return steps[fromIdx]?.status === "done" ? activeEdge : edgeStyle;
  }

  const edges: Edge[] = [
    { id: "e1-2",  source: "s1",   target: "s2",   animated: steps[0].status === "done", style: edgeColor(0), markerEnd: { type: MarkerType.ArrowClosed, color: edgeColor(0).stroke } },
    { id: "e2-3",  source: "s2",   target: "s3",   animated: steps[1].status === "done", style: edgeColor(1), markerEnd: { type: MarkerType.ArrowClosed, color: edgeColor(1).stroke } },
    { id: "e3-4",  source: "s3",   target: "s4",   animated: steps[2].status === "done", style: edgeColor(2), markerEnd: { type: MarkerType.ArrowClosed, color: edgeColor(2).stroke } },
    { id: "e4-5",  source: "s4",   target: "s5",   animated: steps[3].status === "done", style: edgeColor(3), markerEnd: { type: MarkerType.ArrowClosed, color: edgeColor(3).stroke } },
    { id: "e5-6",  source: "s5",   target: "s6",   animated: steps[4].status === "done", style: edgeColor(4), markerEnd: { type: MarkerType.ArrowClosed, color: edgeColor(4).stroke } },
    { id: "e6-f",  source: "s6",   target: "fork", animated: steps[5].status === "done", style: edgeColor(5), markerEnd: { type: MarkerType.ArrowClosed, color: edgeColor(5).stroke } },
    { id: "ef-p",  source: "fork", target: "out-pass",     sourceHandle: "a", style: { stroke: "#10b981", strokeWidth: 1.5 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#10b981" }, label: "passed", labelStyle: { fill: "#6ee7b7", fontSize: 10 } },
    { id: "ef-f",  source: "fork", target: "out-fail",     sourceHandle: "b", style: { stroke: "#ef4444", strokeWidth: 1.5 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#ef4444" }, label: "disqualified", labelStyle: { fill: "#fca5a5", fontSize: 10 } },
    { id: "ef-e",  source: "fork", target: "out-escalate", sourceHandle: "b", style: { stroke: "#f59e0b", strokeWidth: 1.5, strokeDasharray: "4 3" }, markerEnd: { type: MarkerType.ArrowClosed, color: "#f59e0b" }, label: "escalate", labelStyle: { fill: "#fcd34d", fontSize: 10 } },
  ];

  return (
    <div className="w-full h-64 rounded-2xl border border-slate-700/60 overflow-hidden bg-slate-900/50">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnDrag={false}
        zoomOnScroll={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#1e293b" />
      </ReactFlow>
    </div>
  );
}
