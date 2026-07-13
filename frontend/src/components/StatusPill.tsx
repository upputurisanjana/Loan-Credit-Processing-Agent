/**
 * StatusPill — colour-coded pill for band and status values.
 */
import type { Band, AppStatus } from "../api/client";

interface Props {
  value: Band | AppStatus | string;
  size?: "sm" | "md";
}

const CONFIG: Record<string, { label: string; cls: string }> = {
  approve:              { label: "Approve",       cls: "bg-[#3A6B4C]/10 text-[#3A6B4C] border-[#3A6B4C]/25" },
  refer:                { label: "Refer",          cls: "bg-[#C48A2A]/10 text-[#C48A2A] border-[#C48A2A]/25" },
  decline:              { label: "Decline",        cls: "bg-[#8C3B2E]/10 text-[#8C3B2E] border-[#8C3B2E]/25" },
  pending_human_review: { label: "Pending",        cls: "bg-[#C48A2A]/10 text-[#C48A2A] border-[#C48A2A]/25" },
  hold_for_document:    { label: "Hold – Docs",    cls: "bg-[#8A8072]/10 text-[#8A8072] border-[#8A8072]/25" },
  flag_fairness_fail:   { label: "Fairness Flag",  cls: "bg-[#8C3B2E]/10 text-[#8C3B2E] border-[#8C3B2E]/35 font-bold" },
  decided:              { label: "Decided",        cls: "bg-[#3A6B4C]/10 text-[#3A6B4C] border-[#3A6B4C]/25" },
  error:                { label: "Error",          cls: "bg-[#8C3B2E]/10 text-[#8C3B2E] border-[#8C3B2E]/25" },
};

export default function StatusPill({ value, size = "md" }: Props) {
  const cfg = CONFIG[value] ?? {
    label: String(value).replace(/_/g, " "),
    cls: "bg-[#8A8072]/10 text-[#8A8072] border-[#8A8072]/25",
  };
  const textCls = size === "sm" ? "text-[10px]" : "text-xs";
  return (
    <span
      className={`inline-flex items-center border rounded font-semibold tracking-wide uppercase whitespace-nowrap
                  ${textCls} px-2 py-0.5 ${cfg.cls}`}
      aria-label={`Status: ${cfg.label}`}
    >
      {cfg.label}
    </span>
  );
}
