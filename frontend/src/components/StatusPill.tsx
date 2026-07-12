import type { Band, AppStatus } from "../api/client";

interface Props {
  value: Band | AppStatus | string;
  size?: "sm" | "md";
}

const CONFIG: Record<string, { label: string; className: string }> = {
  approve:              { label: "Approve",      className: "bg-[#3A6B4C]/10 text-[#3A6B4C] border-[#3A6B4C]/30" },
  refer:                { label: "Refer",         className: "bg-[#C48A2A]/10 text-[#C48A2A] border-[#C48A2A]/30" },
  decline:              { label: "Decline",       className: "bg-[#8C3B2E]/10 text-[#8C3B2E] border-[#8C3B2E]/30" },
  pending_human_review: { label: "Pending",       className: "bg-[#C48A2A]/10 text-[#C48A2A] border-[#C48A2A]/30" },
  hold_for_document:    { label: "Hold – Docs",   className: "bg-[#8A8072]/10 text-[#8A8072] border-[#8A8072]/30" },
  flag_fairness_fail:   { label: "Fairness Flag", className: "bg-[#8C3B2E]/10 text-[#8C3B2E] border-[#8C3B2E]/30" },
  decided:              { label: "Decided",       className: "bg-[#3A6B4C]/10 text-[#3A6B4C] border-[#3A6B4C]/30" },
  error:                { label: "Error",         className: "bg-[#8C3B2E]/10 text-[#8C3B2E] border-[#8C3B2E]/30" },
};

export default function StatusPill({ value, size = "md" }: Props) {
  const cfg = CONFIG[value] ?? { label: value, className: "bg-[#8A8072]/10 text-[#8A8072] border-[#8A8072]/30" };
  const text = size === "sm" ? "text-2xs" : "text-xs";
  return (
    <span
      className={`inline-flex items-center gap-1 border rounded-sm font-medium tracking-wide uppercase ${text} px-2 py-0.5 ${cfg.className}`}
      aria-label={`Status: ${cfg.label}`}
    >
      {cfg.label}
    </span>
  );
}
