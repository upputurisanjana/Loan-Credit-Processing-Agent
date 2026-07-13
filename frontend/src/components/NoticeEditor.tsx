/**
 * NoticeEditor — adverse-action notice editor for DECLINE cases.
 * Left: editable notice draft. Right: regulatory checklist.
 * Only shown when agent_recommendation === "decline" or adverse_action_draft is set.
 */
import { useState, useEffect } from "react";
import type { DecisionRecord } from "../api/client";
import { api } from "../api/client";

interface Props {
  record: DecisionRecord;
  onApproved?: (noticeDraft: string) => void;
}

const REQUIRED_ITEMS = [
  { id: "reasons",      label: "Specific reasons for decline" },
  { id: "credit_report", label: "Right to free credit report" },
  { id: "dispute",      label: "Right to dispute inaccurate information" },
  { id: "reconsider",   label: "Right to request reconsideration" },
  { id: "contact",      label: "Lender contact information" },
];

function checkItem(text: string, id: string): boolean {
  const lower = text.toLowerCase();
  switch (id) {
    case "reasons":       return lower.includes("decline") || lower.includes("denied") || lower.includes("reason");
    case "credit_report": return lower.includes("credit report");
    case "dispute":       return lower.includes("dispute") || lower.includes("inaccurate");
    case "reconsider":    return lower.includes("reconsider") || lower.includes("appeal") || lower.includes("documentation");
    case "contact":       return lower.includes("contact") || lower.includes("[lender");
    default:              return false;
  }
}

export default function NoticeEditor({ record, onApproved }: Props) {
  const [draft, setDraft]         = useState(record.adverse_action_draft ?? "");
  const [approved, setApproved]   = useState(false);
  const [sending, setSending]     = useState(false);
  const [reviewerId, setReviewer] = useState("");
  const [apiError, setApiError]   = useState<string | null>(null);

  useEffect(() => {
    if (record.adverse_action_draft) setDraft(record.adverse_action_draft);
  }, [record.adverse_action_draft]);

  if (!record.adverse_action_draft && record.agent_recommendation !== "decline") {
    return null;
  }

  const checklist = REQUIRED_ITEMS.map((item) => ({
    ...item,
    present: checkItem(draft, item.id),
  }));
  const allPresent = checklist.every((c) => c.present);

  function handleApprove() {
    if (!reviewerId.trim()) return;
    setSending(true);
    setApiError(null);
    api
      .recordDecision(record.application_id, {
        human_decision: "decline",
        human_reviewer: reviewerId.trim(),
        // decline matching agent_recommendation — no override_reason needed
      })
      .then(() => {
        setApproved(true);
        onApproved?.(draft);
      })
      .catch((err: unknown) => {
        setApiError(err instanceof Error ? err.message : "Submission failed.");
      })
      .finally(() => setSending(false));
  }

  return (
    <div
      className="bg-white border border-[#8C3B2E]/40 rounded overflow-hidden"
      aria-labelledby="notice-heading"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-[#8C3B2E]/25 bg-[#8C3B2E]/5">
        <div>
          <h2 id="notice-heading" className="text-[10px] font-bold uppercase tracking-widest text-[#8C3B2E]">
            Adverse Action Notice — Decline
          </h2>
          <p className="text-xs text-[#8A8072] mt-0.5">
            Review and edit before approving. Sending is stubbed in this demo.
          </p>
        </div>
        {approved && (
          <span className="flex items-center gap-1.5 text-xs text-[#3A6B4C] font-semibold">
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
              <circle cx="6.5" cy="6.5" r="5.5" stroke="currentColor" strokeWidth="1.3"/>
              <path d="M4 6.5L6 8.5L9.5 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Queued for send
          </span>
        )}
      </div>

      <div className="flex flex-col md:flex-row">
        {/* ── Editable draft ─────────────────────────────────────────── */}
        <div className="flex-1 px-5 py-4 md:border-r border-[#D6D0C4]">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-[#8A8072] mb-3">
            Draft notice
          </div>

          {/* Score factor chips */}
          <div className="mb-3 flex flex-wrap items-center gap-1.5">
            <span className="text-[10px] text-[#8A8072]">Score factors:</span>
            {[
              { label: `DTI ${(record.score_breakdown.dti_ratio * 100).toFixed(1)}%`, score: record.score_breakdown.dti_subscore },
              { label: `Credit ${Math.round(record.score_breakdown.credit_history_subscore * 100)}`, score: record.score_breakdown.credit_history_subscore },
              { label: `Income ${Math.round(record.score_breakdown.income_stability_subscore * 100)}`, score: record.score_breakdown.income_stability_subscore },
            ].map(({ label, score }) => (
              <span
                key={label}
                className="text-[10px] font-mono px-1.5 py-0.5 rounded border bg-[#FAF8F3] border-[#D6D0C4] text-[#12213A] tabular-nums"
                title={`Sub-score: ${(score * 100).toFixed(1)}`}
              >
                {label}
              </span>
            ))}
          </div>

          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            disabled={approved}
            rows={14}
            className="w-full border border-[#D6D0C4] rounded px-3 py-2.5 text-sm leading-relaxed
                       bg-white text-[#12213A] font-sans
                       focus:outline-none focus:ring-2 focus:ring-[#C48A2A] focus:border-transparent
                       disabled:bg-[#FAF8F3] disabled:text-[#8A8072] resize-none"
            aria-label="Adverse action notice draft"
            aria-readonly={approved}
          />
          <div className="text-[10px] text-[#8A8072] mt-1 text-right tabular-nums">
            {draft.split(/\s+/).filter(Boolean).length} words
          </div>
        </div>

        {/* ── Regulatory checklist ───────────────────────────────────── */}
        <div className="md:w-56 flex-shrink-0 px-5 py-4">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-[#8A8072] mb-3">
            Must include
          </div>

          <ul className="space-y-2.5" aria-label="Regulatory checklist">
            {checklist.map((item) => (
              <li key={item.id} className="flex items-start gap-2">
                {item.present ? (
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" className="flex-shrink-0 mt-0.5 text-[#3A6B4C]">
                    <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.4"/>
                    <path d="M4.5 7L6 8.5L9.5 5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                ) : (
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" className="flex-shrink-0 mt-0.5 text-[#8C3B2E]">
                    <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.4"/>
                    <path d="M7 4V7.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                    <circle cx="7" cy="9.5" r="0.6" fill="currentColor"/>
                  </svg>
                )}
                <span className={`text-xs ${item.present ? "text-[#12213A]" : "text-[#8C3B2E]"}`}>
                  {item.label}
                </span>
              </li>
            ))}
          </ul>

          {!allPresent && (
            <p className="mt-3 text-xs text-[#8C3B2E]" role="alert">
              Complete all items above before approving.
            </p>
          )}

          {/* Reviewer ID required to submit */}
          {!approved && (
            <div className="mt-4">
              <label
                htmlFor="notice-reviewer"
                className="block text-[10px] font-semibold text-[#8A8072] uppercase tracking-widest mb-1"
              >
                Reviewer ID <span className="text-[#8C3B2E]">*</span>
              </label>
              <input
                id="notice-reviewer"
                type="text"
                value={reviewerId}
                onChange={(e) => setReviewer(e.target.value)}
                placeholder="underwriter_1"
                className="w-full border border-[#D6D0C4] rounded px-2 py-1.5 text-xs
                           focus:outline-none focus:ring-2 focus:ring-[#3A6B4C] bg-white text-[#12213A]
                           placeholder-[#8A8072]/60"
              />
            </div>
          )}

          {apiError && (
            <p className="mt-2 text-xs text-[#8C3B2E]" role="alert">{apiError}</p>
          )}

          <button
            onClick={handleApprove}
            disabled={!allPresent || approved || sending || !reviewerId.trim()}
            className="mt-5 w-full px-3 py-2 text-xs font-semibold rounded border
                       border-[#3A6B4C] text-[#3A6B4C] hover:bg-[#3A6B4C] hover:text-white
                       transition-colors focus:outline-none focus:ring-2 focus:ring-[#3A6B4C]
                       disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {sending ? "Submitting…" : approved ? "✓ Queued for send" : "Approve & Queue for Send"}
          </button>

          {approved && (
            <p className="mt-2 text-[10px] text-[#8A8072] text-center">
              [Demo] No real send integration.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
