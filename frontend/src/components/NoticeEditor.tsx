/**
 * NoticeEditor — adverse-action notice editor for DECLINE cases.
 * Per UI_UX_DESIGN.md §3.6:
 * - Left: editable notice draft with score factor back-links.
 * - Right: locked "must-include" checklist.
 * - "Approve & Queue for Send" button (send is stubbed).
 * - Only shown when adverse_action_draft is present.
 */
import { useState, useEffect } from "react";
import type { DecisionRecord } from "../api/client";

interface Props {
  record: DecisionRecord;
  onApproved?: (noticeDraft: string) => void;
}

// Regulatory checklist items that must remain in the notice
const REQUIRED_ITEMS = [
  { id: "reasons",     label: "Specific reasons for decline" },
  { id: "credit_report", label: "Right to free credit report" },
  { id: "dispute",     label: "Right to dispute inaccurate information" },
  { id: "reconsider",  label: "Right to request reconsideration" },
  { id: "contact",     label: "Lender contact information" },
];

function checkItem(text: string, id: string): boolean {
  const lower = text.toLowerCase();
  switch (id) {
    case "reasons":      return lower.includes("decline") || lower.includes("denied") || lower.includes("reason");
    case "credit_report": return lower.includes("credit report");
    case "dispute":      return lower.includes("dispute") || lower.includes("inaccurate");
    case "reconsider":   return lower.includes("reconsider") || lower.includes("appeal") || lower.includes("documentation");
    case "contact":      return lower.includes("contact") || lower.includes("[lender");
    default:             return false;
  }
}

export default function NoticeEditor({ record, onApproved }: Props) {
  const [draft, setDraft]       = useState(record.adverse_action_draft ?? "");
  const [approved, setApproved] = useState(false);
  const [sending, setSending]   = useState(false);

  // Keep draft in sync if the record changes (e.g. after re-fetch)
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
    setSending(true);
    // Stub — no real send integration per spec
    setTimeout(() => {
      setSending(false);
      setApproved(true);
      onApproved?.(draft);
    }, 800);
  }

  return (
    <section
      className="border border-[#8C3B2E]/40 rounded-sm bg-[#FAF8F3]"
      aria-labelledby="notice-heading"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-[#8C3B2E]/30 bg-[#8C3B2E]/5">
        <div>
          <h2 id="notice-heading" className="font-serif text-base text-[#8C3B2E] font-semibold">
            Adverse Action Notice — DECLINE
          </h2>
          <p className="text-xs text-[#8A8072] mt-0.5">
            Review and edit before approving for send. Sending is stubbed in this demo.
          </p>
        </div>
        {approved && (
          <span className="flex items-center gap-1.5 text-xs text-[#3A6B4C] font-semibold">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.4"/>
              <path d="M4.5 7L6 8.5L9.5 5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Approved for send
          </span>
        )}
      </div>

      <div className="flex flex-col md:flex-row gap-0">
        {/* ── Left: editable notice ─────────────────────────────────── */}
        <div className="flex-1 px-5 py-4 md:border-r border-[#D6D0C4]">
          <div className="section-label mb-2">Draft notice</div>

          {/* Score factor highlights */}
          <div className="mb-3 flex flex-wrap gap-1.5">
            <span className="text-2xs text-[#8A8072]">Score factors:</span>
            {[
              { label: `DTI ${(record.score_breakdown.dti_ratio * 100).toFixed(1)}%`, score: record.score_breakdown.dti_subscore },
              { label: `Credit history ${Math.round(record.score_breakdown.credit_history_subscore * 100)}`, score: record.score_breakdown.credit_history_subscore },
              { label: `Income stability ${Math.round(record.score_breakdown.income_stability_subscore * 100)}`, score: record.score_breakdown.income_stability_subscore },
            ].map(({ label, score }) => (
              <span
                key={label}
                className="inline-block text-2xs font-mono px-1.5 py-0.5 rounded-sm border
                           bg-[#12213A]/5 border-[#12213A]/20 text-[#12213A]"
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
            rows={16}
            className="w-full border border-[#D6D0C4] rounded-sm px-3 py-2 text-sm
                       font-sans leading-relaxed bg-white text-[#12213A]
                       focus:outline-none focus:ring-1 focus:ring-[#C48A2A]
                       disabled:bg-[#F2EFE8] disabled:text-[#8A8072] resize-none"
            aria-label="Adverse action notice draft — editable"
            aria-readonly={approved}
          />

          <div className="text-xs text-[#8A8072] mt-1 text-right" data-numeric>
            {draft.split(/\s+/).filter(Boolean).length} words
          </div>
        </div>

        {/* ── Right: regulatory checklist ───────────────────────────── */}
        <div className="md:w-60 px-5 py-4 flex-shrink-0">
          <div className="section-label mb-3">Must include</div>

          <ul className="space-y-2.5" role="list" aria-label="Regulatory requirements checklist">
            {checklist.map((item) => (
              <li key={item.id} className="flex items-start gap-2">
                {item.present ? (
                  <svg width="15" height="15" viewBox="0 0 15 15" fill="none"
                       className="text-[#3A6B4C] flex-shrink-0 mt-0.5" aria-hidden="true">
                    <circle cx="7.5" cy="7.5" r="6.5" stroke="currentColor" strokeWidth="1.4"/>
                    <path d="M4.5 7.5L6.5 9.5L10.5 5.5" stroke="currentColor" strokeWidth="1.4"
                          strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                ) : (
                  <svg width="15" height="15" viewBox="0 0 15 15" fill="none"
                       className="text-[#8C3B2E] flex-shrink-0 mt-0.5" aria-hidden="true">
                    <circle cx="7.5" cy="7.5" r="6.5" stroke="currentColor" strokeWidth="1.4"/>
                    <path d="M7.5 4.5V8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                    <circle cx="7.5" cy="10" r="0.7" fill="currentColor"/>
                  </svg>
                )}
                <span className={`text-xs ${item.present ? "text-[#12213A]" : "text-[#8C3B2E]"}`}>
                  {item.label}
                </span>
              </li>
            ))}
          </ul>

          {!allPresent && (
            <p className="mt-4 text-xs text-[#8C3B2E]" role="alert">
              All items must be present before approving.
            </p>
          )}

          <button
            onClick={handleApprove}
            disabled={!allPresent || approved || sending}
            className="mt-6 w-full px-4 py-2 text-sm font-semibold rounded-sm border
                       border-[#3A6B4C] text-[#3A6B4C] hover:bg-[#3A6B4C] hover:text-white
                       transition-colors focus:outline-none focus:ring-2 focus:ring-[#3A6B4C]
                       disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label="Approve notice and queue for send"
          >
            {sending ? "Queuing…" : approved ? "✓ Queued for send" : "Approve & Queue for Send"}
          </button>

          {approved && (
            <p className="mt-2 text-xs text-[#8A8072] text-center">
              [Stub] No real send integration in demo.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
