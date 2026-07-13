/**
 * DecisionModal — Approve / Override / Request-more-info variants.
 * Approve: single confirm, no reason needed.
 * Override: reason field required (min 20 chars).
 * Request more info: checklist from missingDocs + consistencyFlags.
 * All variants show permanent audit trail notice.
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
  override:     "Override Recommendation",
  request_info: "Request Additional Information",
};

const VARIANT_DECISION: Record<ModalVariant, Band> = {
  approve:      "approve",
  override:     "decline",
  request_info: "refer",
};

const VARIANT_ACCENT: Record<ModalVariant, { ring: string; btn: string }> = {
  approve:      { ring: "focus:ring-[#3A6B4C]", btn: "border-[#3A6B4C] text-[#3A6B4C] hover:bg-[#3A6B4C] hover:text-white" },
  override:     { ring: "focus:ring-[#8C3B2E]", btn: "border-[#8C3B2E] text-[#8C3B2E] hover:bg-[#8C3B2E] hover:text-white" },
  request_info: { ring: "focus:ring-[#C48A2A]", btn: "border-[#C48A2A] text-[#C48A2A] hover:bg-[#C48A2A] hover:text-white" },
};

export default function DecisionModal({ record, variant, onClose, onSuccess }: Props) {
  const [reviewer, setReviewer]         = useState("");
  const [reason, setReason]             = useState("");
  const [overrideTo, setOverrideTo]     = useState<Band>("decline");
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [submitting, setSubmitting]     = useState(false);
  const [error, setError]               = useState<string | null>(null);

  const firstInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    firstInputRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const decision: Band        = variant === "override" ? overrideTo : VARIANT_DECISION[variant];
  const isOverride            = variant === "override" || decision !== record.agent_recommendation;
  const reasonTooShort        = isOverride && reason.trim().length < 20;
  const canSubmit             = reviewer.trim().length > 0 && !reasonTooShort;

  const missingDocs      = record.missing_docs ?? [];
  const consistencyFlags = record.consistency_flags ?? [];
  const checklistItems   = [...missingDocs, ...consistencyFlags];
  const accent           = VARIANT_ACCENT[variant];

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
        human_decision:  decision,
        human_reviewer:  reviewer.trim(),
        override_reason: isOverride ? reason.trim() : undefined,
      });
      onSuccess(updated as DecisionRecord);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  }

  const inputCls = `w-full border border-[#D6D0C4] rounded px-3 py-2 text-sm bg-white
                    focus:outline-none focus:ring-2 ${accent.ring} focus:border-transparent
                    text-[#12213A] placeholder-[#8A8072]/60`;

  return (
    <div
      className="fixed inset-0 z-50 bg-[#12213A]/50 flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className="w-full max-w-md bg-[#FAF8F3] border border-[#D6D0C4] rounded shadow-2xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#D6D0C4]">
          <h2 id="modal-title" className="font-serif text-lg font-bold text-[#12213A]">
            {VARIANT_TITLES[variant]}
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-[#8A8072] hover:text-[#12213A] focus:outline-none focus:ring-1 focus:ring-[#C48A2A] rounded"
            aria-label="Close dialog"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
              <path d="M4 4L14 14M14 4L4 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-5 py-5 space-y-4">

          {/* Reviewer ID */}
          <div>
            <label htmlFor="reviewer" className="block text-[10px] font-semibold text-[#8A8072] uppercase tracking-widest mb-1.5">
              Reviewer ID <span className="text-[#8C3B2E]">*</span>
            </label>
            <input
              id="reviewer"
              ref={firstInputRef}
              type="text"
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
              placeholder="underwriter_1"
              className={inputCls}
              required
              aria-required="true"
            />
          </div>

          {/* Override target band */}
          {variant === "override" && (
            <div>
              <div className="text-[10px] font-semibold text-[#8A8072] uppercase tracking-widest mb-1.5">
                Decision <span className="text-[#8C3B2E]">*</span>
              </div>
              <div className="flex gap-2">
                {(["approve", "refer", "decline"] as Band[])
                  .filter((b) => b !== record.agent_recommendation)
                  .map((b) => (
                    <button
                      key={b}
                      type="button"
                      onClick={() => setOverrideTo(b)}
                      className={`flex-1 py-2 rounded text-xs font-bold border transition-colors capitalize ${
                        overrideTo === b
                          ? b === "approve" ? "bg-[#3A6B4C] text-white border-[#3A6B4C]"
                            : b === "decline" ? "bg-[#8C3B2E] text-white border-[#8C3B2E]"
                            : "bg-[#C48A2A] text-white border-[#C48A2A]"
                          : "bg-white text-[#8A8072] border-[#D6D0C4] hover:border-[#12213A]"
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
          {isOverride && (
            <div>
              <label htmlFor="reason" className="block text-[10px] font-semibold text-[#8A8072] uppercase tracking-widest mb-1.5">
                Override reason <span className="text-[#8C3B2E]">*</span>
                <span className="normal-case ml-1 text-[#8A8072]/70">(min 20 chars)</span>
              </label>
              <textarea
                id="reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={3}
                placeholder="Describe the business rationale for overriding the agent recommendation…"
                className={`${inputCls} resize-none`}
                aria-required="true"
                aria-describedby="reason-hint"
              />
              <p
                id="reason-hint"
                className={`text-[10px] mt-1 tabular-nums ${
                  reason.trim().length < 20 && reason.length > 0 ? "text-[#8C3B2E]" : "text-[#8A8072]"
                }`}
              >
                {reason.trim().length} / 20 minimum characters
              </p>
            </div>
          )}

          {/* Request-info checklist */}
          {variant === "request_info" && checklistItems.length > 0 && (
            <div>
              <div className="text-[10px] font-semibold text-[#8A8072] uppercase tracking-widest mb-2">
                Outstanding items
              </div>
              <div className="space-y-2">
                {checklistItems.map((item) => (
                  <label key={item} className="flex items-center gap-2 text-sm cursor-pointer group">
                    <input
                      type="checkbox"
                      checked={selectedDocs.includes(item)}
                      onChange={() => toggleDoc(item)}
                      className="accent-[#C48A2A] w-4 h-4"
                    />
                    <span className="group-hover:text-[#12213A] text-[#8A8072] transition-colors">
                      {item.replace(/_/g, " ")}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Audit notice */}
          <div className="text-xs text-[#8A8072] border-l-2 border-[#D6D0C4] pl-3 py-0.5">
            This action will be permanently recorded in the audit trail.
          </div>

          {/* Error */}
          {error && (
            <div
              className="text-sm text-[#8C3B2E] bg-[#8C3B2E]/5 border border-[#8C3B2E]/30 rounded px-3 py-2"
              role="alert"
            >
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-[#8A8072] border border-[#D6D0C4] rounded
                         hover:border-[#12213A] hover:text-[#12213A] transition-colors
                         focus:outline-none focus:ring-1 focus:ring-[#C48A2A]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!canSubmit || submitting}
              className={`px-5 py-2 text-sm font-semibold rounded border transition-colors
                          focus:outline-none focus:ring-2 focus:ring-offset-1 ${accent.ring}
                          ${accent.btn}
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
