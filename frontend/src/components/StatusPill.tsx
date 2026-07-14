/**
 * StatusPill — standard enterprise SaaS status badge with status dot.
 */
import type { Band, AppStatus } from "../api/client";

interface Props {
  value: Band | AppStatus | string;
  size?: "sm" | "md";
}

const CONFIG: Record<string, { label: string; cls: string; dot: string }> = {
  approve: {
    label: "Approve",
    cls:   "bg-green-50 text-green-700 border-green-200",
    dot:   "bg-green-500",
  },
  refer: {
    label: "Refer",
    cls:   "bg-amber-50 text-amber-700 border-amber-200",
    dot:   "bg-amber-400",
  },
  decline: {
    label: "Decline",
    cls:   "bg-red-50 text-red-700 border-red-200",
    dot:   "bg-red-500",
  },
  pending_human_review: {
    label: "Pending Review",
    cls:   "bg-amber-50 text-amber-700 border-amber-200",
    dot:   "bg-amber-400",
  },
  awaiting_information: {
    label: "Awaiting Info",
    cls:   "bg-purple-50 text-purple-700 border-purple-200",
    dot:   "bg-purple-400",
  },
  hold_for_document: {
    label: "Hold – Docs",
    cls:   "bg-slate-100 text-slate-600 border-slate-200",
    dot:   "bg-slate-400",
  },
  flag_fairness_fail: {
    label: "Fairness Flag",
    cls:   "bg-red-50 text-red-700 border-red-300",
    dot:   "bg-red-600",
  },
  decided: {
    label: "Decided",
    cls:   "bg-green-50 text-green-700 border-green-200",
    dot:   "bg-green-500",
  },
  error: {
    label: "Error",
    cls:   "bg-red-50 text-red-600 border-red-200",
    dot:   "bg-red-400",
  },
};

export default function StatusPill({ value, size = "md" }: Props) {
  const cfg = CONFIG[value] ?? {
    label: String(value).replace(/_/g, " "),
    cls:   "bg-slate-100 text-slate-600 border-slate-200",
    dot:   "bg-slate-400",
  };

  const textSize = size === "sm" ? "text-[10px] px-2 py-0.5" : "text-xs px-2.5 py-0.5";

  return (
    <span
      className={`inline-flex items-center gap-1.5 border rounded-full font-medium
                  tracking-wide uppercase whitespace-nowrap ${textSize} ${cfg.cls}`}
      aria-label={`Status: ${cfg.label}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${cfg.dot}`} aria-hidden="true" />
      {cfg.label}
    </span>
  );
}
