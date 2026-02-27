import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function pct(n: number) {
  return `${Math.round(n * 100)}%`;
}

export const POWER_COLORS: Record<string, string> = {
  very_high: "bg-red-500/20 text-red-300 border-red-500/30",
  high:      "bg-orange-500/20 text-orange-300 border-orange-500/30",
  medium:    "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  low:       "bg-slate-500/20 text-slate-300 border-slate-500/30",
  unknown:   "bg-slate-700/20 text-slate-400 border-slate-700/30",
};

export const DECISION_CONFIG = {
  disqualified: {
    label: "Disqualified",
    color: "bg-red-500/20 text-red-300 border-red-500/40",
    dot: "bg-red-400",
  },
  passed_prescreen: {
    label: "Passed Pre-screen",
    color: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
    dot: "bg-emerald-400",
  },
  escalate: {
    label: "Escalate to Human",
    color: "bg-amber-500/20 text-amber-300 border-amber-500/40",
    dot: "bg-amber-400",
  },
} as const;
