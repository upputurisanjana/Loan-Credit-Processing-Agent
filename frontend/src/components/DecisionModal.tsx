/**
 * DecisionModal — Approve / Override / Request-more-info variants.
 * Per UI_UX_DESIGN.md §3.5:
 * - Approve: single confirm, no reason needed.
 * - Override: reason field required (min 20 chars), client-side enforced.
 * - Request more info: checklist from missingDocs + consistencyFlags.
 * All variants show "This will be recorded permanently in the audit trail."
 */
import { useEffect, useRef, useState } from "react";
import type { Band, DecisionRecord } from "../api/client";
import { api } from "../api/client";

type ModalVariant = "approve" | "override" | "request_info";

interface Props {
  record: DecisionRecord;
  variant: ModalVariant;
  onClose: () => void;
  onSuccess: (updated: DecisionRecord) => void;
}

const VARIANT_TITLES: Record<ModalVariant, string> = {
  approve:      "Confirm Approval",
  override:     "Override Agent Recommendation",
  request_info: "Request Additional Information",
};

// Maps variant → what human_decision value to send
const VARIANT_DECISION: Record<ModalVariant, Band> = {
  approve:      "approve",
  override:     "decline",   // default; user picks in override
  request_info: "refer",
};

export default function DecisionModal({ record, variant, onClose, onSuccess }: Props) {
  const [reviewer, setReviewer]       = useState("");
  const [reason, setReason]           = useState("");
  const [overrideTo, setOverrideTo]   = useState<Band>("decline");
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [submitting, setSubmitting]   = useState(false);
  const [error, setError]             = useState<string | null>(null);

  const firstInputRef = useRef<HTMLInputElement>(null);
  const dialogRef     = useRef<HTMLDivElement>(null);

  // Focus trap + ESC close
  useEffect(() => {
    firstInputRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Compute what decision to send
  const decision: Band = variant === "override" ? overrideTo : VARIANT_DECISION[variant];
  const needsOverrideReason = variant === "override" || decision !== record.agent_recommendation;
  const reasonTooShort = needsOverrideReason && reason.trim().length < 20;
  const canSubmit = reviewer.trim().length > 0 && !reasonTooShort;

  const missingDocs      = record.missing_docs ?? [];
  const consistencyFlags = record.consistency_flags ?? [];
  const checklistItems   = [...missingDocs, ...consistencyFlags];

  function toggleDoc(item: string) {
    setSelectedDocs((prev) =>
      prev.includes(item) ? prev.filter((d) => d !== item) : [...prev, item]
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const updated = await api.recordDecision(record.application_id, {
        human_decision: decision,
        human_reviewer: reviewer.trim(),
        override_reason: needsOverrideReason ? reason.trim() : undefined,
      });
      onSuccess(updated as DecisionRecord);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 bg-[#12213A]/60 flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      role="presentation"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className="w-full max-w-md bg-[#FAF8F3] border border-[#D6D0C4] rounded-sm shadow-xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#D6D0C4]">
          <h2 id="modal-title" className="font-serif text-lg text-[#12213A]">
            {VARIANT_TITLES[variant]}
          </h2>
          <button
            onClick={onClose}
            className="text-[#8A8072] hover:text-[#12213A] focus:outline-none focus:ring-1 focus:ring-[#C48A2A] rounded-sm"
            aria-label="Close dialog"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path d="M4 4L16 16M16 4L4 16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-5 py-4 space-y-4">
          {/* Reviewer ID */}
          <div>
            <label htmlFor="reviewer" className="block text-xs font-medium text-[#8A8072] uppercase tracking-wide mb-1">
              Reviewer ID *
            </label>
            <input
              id="reviewer"
              ref={firstInputRef}
              type="text"
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
              placeholder="underwriter_1"
              className="w-full border border-[#D6D0C4] rounded-sm px-3 py-2 text-sm
                         bg-white focus:outline-none focus:ring-1 focus:ring-[#C48A2A]
                         focus:border-[#C48A2A] text-[#12213A]"
              required
              aria-required="true"
            />
          </div>

          {/* Override target band (override variant only) */}
          {variant === "override" && (
            <div>
              <label className="block text-xs font-medium text-[#8A8072] uppercase tracking-wide mb-1">
                Decision *
              </label>
              <div className="flex gap-2">
                {(["approve", "refer", "decline"] as Band[])
                  .filter((b) => b !== record.agent_recommendation)
                  .map((b) => (
                    <button
                      key={b}
                      type="button"
                      onClick={() => setOverrideTo(b)}
                      className={`px-4 py-1.5 rounded-sm text-xs font-semibold border transition-colors capitalize
                        ${overrideTo === b
                          ? b === "approve" ? "bg-[#3A6B4C] text-white border-[#3A6B4C]"
                            : b === "decline" ? "bg-[#8C3B2E] text-white border-[#8C3B2E]"
                            : "bg-[#C48A2A] text-white border-[#C48A2A]"
                          : "bg-transparent text-[#8A8072] border-[#D6D0C4] hover:border-[#12213A]"
                        }`}
                      aria-pressed={overrideTo === b}
                    >
                      {b}
                    </button>
                  ))}
              </div>
            </div>
          )}

          {/* Override reason */}
          {needsOverrideReason && (
            <div>
              <label htmlFor="reason" className="block text-xs font-medium text-[#8A8072] uppercase tracking-wide mb-1">
                Override reason * (min 20 characters)
              </label>
              <textarea
                id="reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={3}
                placeholder="Describe the business rationale for overriding the agent recommendation…"
                className="w-full border border-[#D6D0C4] rounded-sm px-3 py-2 text-sm
                           bg-white focus:outline-none focus:ring-1 focus:ring-[#C48A2A]
                           focus:border-[#C48A2A] text-[#12213A] resize-none"
                aria-required="true"
                aria-describedby="reason-hint"
              />
              <p
                id="reason-hint"
                className={`text-xs mt-0.5 ${reason.trim().length < 20 && reason.length > 0 ? "text-[#8C3B2E]" : "text-[#8A8072]"}`}
              >
                {reason.trim().length}/20+ characters
              </p>
            </div>
          )}

          {/* Request-info checklist */}
          {variant === "request_info" && checklistItems.length > 0 && (
            <div>
              <div className="text-xs font-medium text-[#8A8072] uppercase tracking-wide mb-1">
                Missing / unclear items
              </div>
              <div className="space-y-1.5">
                {checklistItems.map((item) => (
                  <label key={item} className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedDocs.includes(item)}
                      onChange={() => toggleDoc(item)}
                      className="accent-[#C48A2A]"
                    />
                    {item.replace(/_/g, " ")}
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Audit notice */}
          <div className="text-xs text-[#8A8072] border-l-2 border-[#D6D0C4] pl-3">
            This action will be recorded permanently in the audit trail.
          </div>

          {error && (
            <div className="text-sm text-[#8C3B2E] bg-[#8C3B2E]/5 border border-[#8C3B2E]/30 rounded-sm px-3 py-2" role="alert">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-[#8A8072] border border-[#D6D0C4] rounded-sm
                         hover:border-[#12213A] hover:text-[#12213A] transition-colors focus:outline-none
                         focus:ring-1 focus:ring-[#C48A2A]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!canSubmit || submitting}
              className={`px-5 py-2 text-sm font-semibold rounded-sm border transition-colors
                focus:outline-none focus:ring-2 focus:ring-offset-1
                ${variant === "approve"
                  ? "border-[#3A6B4C] text-[#3A6B4C] hover:bg-[#3A6B4C] hover:text-white focus:ring-[#3A6B4C]"
                  : variant === "override"
                  ? "border-[#8C3B2E] text-[#8C3B2E] hover:bg-[#8C3B2E] hover:text-white focus:ring-[#8C3B2E]"
                  : "border-[#C48A2A] text-[#C48A2A] hover:bg-[#C48A2A] hover:text-white focus:ring-[#C48A2A]"
                }
                disabled:opacity-40 disabled:cursor-not-allowed`}
            >
              {submitting ? "Submitting…" : "Confirm"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
