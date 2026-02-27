import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function pct(n: number) {
  return `${Math.round(n * 100)}%`;
}

export const POWER_COLORS: Record<string, string> = {
  very_high: "bg-red-50 text-red-700 border-red-200",
  high:      "bg-orange-50 text-orange-700 border-orange-200",
  medium:    "bg-yellow-50 text-yellow-700 border-yellow-200",
  low:       "bg-gray-50 text-gray-600 border-gray-200",
  unknown:   "bg-gray-50 text-gray-500 border-gray-200",
};

export const DECISION_CONFIG = {
  disqualified: {
    label: "Disqualified",
    color: "bg-red-50 text-red-700 border-red-200",
    dot: "bg-red-500",
  },
  passed_prescreen: {
    label: "Passed Pre-screen",
    color: "bg-emerald-50 text-emerald-700 border-emerald-200",
    dot: "bg-emerald-500",
  },
  escalate: {
    label: "Escalate to Human",
    color: "bg-amber-50 text-amber-700 border-amber-200",
    dot: "bg-amber-500",
  },
} as const;
