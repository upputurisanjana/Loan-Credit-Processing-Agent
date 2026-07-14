/**
 * NoticeEditor — adverse-action notice editor for DECLINE cases.
 *
 * Fixes applied:
 * - Edited text is now saved via PATCH /applications/:id/notice before deciding.
 * - Button is labelled "Save & Mark Ready to Send" — not "Send" (no real dispatch).
 * - Lender details are already injected by the backend via LENDER_NAME/LENDER_CONTACT
 *   env vars — no more [LENDER CONTACT — fill in before send] placeholder.
 * - The applicant will see approved_notice_text (the edited version) not the raw draft.
 */
import { useState, useEffect } from "react";
import type { DecisionRecord } from "../api/client";
import { api } from "../api/client";

interface Props {
  record: DecisionRecord;
  onNoticeApproved?: (updatedRecord: DecisionRecord) => void;
}

const REQUIRED_ITEMS = [
  { id: "reasons",       label: "Specific reasons for decline" },
  { id: "credit_report", label: "Right to free credit report" },
  { id: "dispute",       label: "Right to dispute inaccurate information" },
  { id: "reconsider",    label: "Right to request reconsideration" },
  { id: "contact",       label: "Lender contact information" },
];

function checkItem(text: string, id: string): boolean {
  const lower = text.toLowerCase();
  switch (id) {
    case "reasons":       return lower.includes("decline") || lower.includes("denied") || lower.includes("reason");
    case "credit_report": return lower.includes("credit report");
    case "dispute":       return lower.includes("dispute") || lower.includes("inaccurate");
    case "reconsider":    return lower.includes("reconsider") || lower.includes("appeal") || lower.includes("documentation");
    case "contact":       return (
      lower.includes("contact") ||
      lower.includes("sincerely") ||
      lower.includes("@") ||
      lower.includes("phone") ||
      lower.includes("email")
    );
    default:              return false;
  }
}

export default function NoticeEditor({ record, onNoticeApproved }: Props) {
  // Show approved_notice_text if already saved, otherwise start from draft
  const initialText = record.approved_notice_text ?? record.adverse_action_draft ?? "";
  const [draft, setDraft]           = useState(initialText);
  const [saving, setSaving]         = useState(false);
  const [saved, setSaved]           = useState(!!record.approved_notice_text);
  const [reviewerId, setReviewer]   = useState("");
  const [apiError, setApiError]     = useState<string | null>(null);

  useEffect(() => {
    const latest = record.approved_notice_text ?? record.adverse_action_draft ?? "";
    setDraft(latest);
    setSaved(!!record.approved_notice_text);
  }, [record.approved_notice_text, record.adverse_action_draft]);

  // Don't render if there's no notice to edit
  if (!record.adverse_action_draft && record.agent_recommendation !== "decline") {
    return null;
  }

  const checklist   = REQUIRED_ITEMS.map((item) => ({ ...item, present: checkItem(draft, item.id) }));
  const allPresent  = checklist.every((c) => c.present);
  const isDecided   = record.human_decision !== null;

  async function handleSaveNotice() {
    if (!reviewerId.trim() || !draft.trim()) return;
    setSaving(true);
    setApiError(null);
    try {
      const updated = await api.updateNotice(record.application_id, {
        notice_text: draft.trim(),
        reviewer: reviewerId.trim(),
      });
      setSaved(true);
      onNoticeApproved?.(updated);
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Failed to save notice.");
    } finally {
      setSaving(false);
    }
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
            {isDecided
              ? "Decision recorded. Notice text locked."
              : "Edit the notice, then save it. The applicant will see this edited version."}
          </p>
        </div>
        {saved && (
          <span className="flex items-center gap-1.5 text-xs text-[#3A6B4C] font-semibold">
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
              <circle cx="6.5" cy="6.5" r="5.5" stroke="currentColor" strokeWidth="1.3"/>
              <path d="M4 6.5L6 8.5L9.5 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Notice saved
          </span>
        )}
      </div>

      <div className="flex flex-col md:flex-row">
        {/* ── Editable draft ─────────────────────────────────────────── */}
        <div className="flex-1 px-5 py-4 md:border-r border-[#D6D0C4]">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-[#8A8072] mb-3">
            {saved ? "Approved notice text" : "Draft notice (edit before saving)"}
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
            onChange={(e) => { setDraft(e.target.value); setSaved(false); }}
            disabled={isDecided}
            rows={14}
            className="w-full border border-[#D6D0C4] rounded px-3 py-2.5 text-sm leading-relaxed
                       bg-white text-[#12213A] font-sans
                       focus:outline-none focus:ring-2 focus:ring-[#C48A2A] focus:border-transparent
                       disabled:bg-[#FAF8F3] disabled:text-[#8A8072] resize-none"
            aria-label="Adverse action notice text"
            aria-readonly={isDecided}
          />
          <div className="text-[10px] text-[#8A8072] mt-1 text-right tabular-nums">
            {draft.split(/\s+/).filter(Boolean).length} words
          </div>
        </div>

        {/* ── Regulatory checklist + save controls ──────────────────── */}
        <div className="md:w-56 flex-shrink-0 px-5 py-4">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-[#8A8072] mb-3">
            Must include
          </div>

          <ul className="space-y-2.5" aria-label="Regulatory checklist">
            {checklist.map((item) => (
              <li key={item.id} className="flex items-start gap-2">
                {item.present ? (
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="flex-shrink-0 mt-0.5 text-[#3A6B4C]">
                    <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.4"/>
                    <path d="M4.5 7L6 8.5L9.5 5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                ) : (
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="flex-shrink-0 mt-0.5 text-[#8C3B2E]">
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

          {!allPresent && !isDecided && (
            <p className="mt-3 text-xs text-[#8C3B2E]" role="alert">
              Ensure all items above are present before saving.
            </p>
          )}

          {!isDecided && (
            <>
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

              {apiError && (
                <p className="mt-2 text-xs text-[#8C3B2E]" role="alert">{apiError}</p>
              )}

              <button
                onClick={() => void handleSaveNotice()}
                disabled={!allPresent || saving || !reviewerId.trim() || saved}
                className="mt-4 w-full px-3 py-2 text-xs font-semibold rounded border
                           border-[#3A6B4C] text-[#3A6B4C] hover:bg-[#3A6B4C] hover:text-white
                           transition-colors focus:outline-none focus:ring-2 focus:ring-[#3A6B4C]
                           disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {saving ? "Saving…" : saved ? "✓ Notice Saved" : "Save Notice"}
              </button>

              <p className="mt-2 text-[10px] text-[#8A8072] text-center leading-relaxed">
                Saving stores the edited text for the applicant to see. No email is sent automatically.
                Send manually after the final decision is recorded.
              </p>
            </>
          )}

          {isDecided && (
            <p className="mt-4 text-[10px] text-[#8A8072] leading-relaxed">
              The decision has been recorded. The applicant can now view the
              {record.approved_notice_text ? " approved" : " draft"} notice.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
