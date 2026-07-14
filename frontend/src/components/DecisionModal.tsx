/**
 * DecisionModal — Approve / Override / Request-more-info variants.
 *
 * Fixes applied:
 * - request_info now calls POST /request-info (not /decision with refer).
 *   The selected checklist items are sent as requested_items to the backend.
 *   Status becomes awaiting_information without finalising the decision.
 * - Approve: single confirm, no reason needed.
 * - Override: reason field required (min 20 chars).
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

const VARIANT_ACCENT: Record<ModalVariant, { ring: string; btn: string }> = {
  approve:      { ring: "focus:ring-[#3A6B4C]", btn: "border-[#3A6B4C] text-[#3A6B4C] hover:bg-[#3A6B4C] hover:text-white" },
  override:     { ring: "focus:ring-[#8C3B2E]", btn: "border-[#8C3B2E] text-[#8C3B2E] hover:bg-[#8C3B2E] hover:text-white" },
  request_info: { ring: "focus:ring-[#C48A2A]", btn: "border-[#C48A2A] text-[#C48A2A] hover:bg-[#C48A2A] hover:text-white" },
};

export default function DecisionModal({ record, variant, onClose, onSuccess }: Props) {
  const [reviewer, setReviewer]         = useState("");
  const [reason, setReason]             = useState("");
  const [overrideTo, setOverrideTo]     = useState<Band>("decline");
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [customItem, setCustomItem]     = useState("");
  const [submitting, setSubmitting]     = useState(false);
  const [error, setError]               = useState<string | null>(null);

  const firstInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    firstInputRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const decision: Band = variant === "override" ? overrideTo : "approve";
  const isOverride     = variant === "override" || (variant === "approve" && decision !== record.agent_recommendation);
  const reasonTooShort = isOverride && reason.trim().length < 20;

  // For request_info: need at least one item selected
  const canSubmitRequestInfo = variant === "request_info"
    ? reviewer.trim().length > 0 && (selectedItems.length > 0 || customItem.trim().length > 0)
    : false;
  const canSubmit = variant === "request_info"
    ? canSubmitRequestInfo
    : reviewer.trim().length > 0 && !reasonTooShort;

  const missingDocs      = record.missing_docs ?? [];
  const consistencyFlags = record.consistency_flags ?? [];
  // Pre-populate checklist from known issues + current awaiting items
  const knownItems       = [
    ...missingDocs.map((d) => `Missing document: ${d.replace(/_/g, " ")}`),
    ...consistencyFlags,
    ...record.awaiting_info_items.filter(
      (i) => !missingDocs.includes(i) && !consistencyFlags.includes(i)
    ),
  ];
  const accent = VARIANT_ACCENT[variant];

  function toggleItem(item: string) {
    setSelectedItems((prev) =>
      prev.includes(item) ? prev.filter((d) => d !== item) : [...prev, item]
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);

    try {
      if (variant === "request_info") {
        // Build final list: checked items + any custom item
        const items = [
          ...selectedItems,
          ...(customItem.trim() ? [customItem.trim()] : []),
        ];
        const updated = await api.requestInfo(record.application_id, {
          requested_items: items,
          reviewer: reviewer.trim(),
        });
        onSuccess(updated as DecisionRecord);
      } else {
        // approve or override — POST to /decision
        const overrideReason = isOverride ? reason.trim() : undefined;
        const updated = await api.recordDecision(record.application_id, {
          human_decision:  decision,
          human_reviewer:  reviewer.trim(),
          override_reason: overrideReason,
        });
        onSuccess(updated as DecisionRecord);
      }
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
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M4 4L14 14M14 4L4 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        <form onSubmit={(e) => void handleSubmit(e)} className="px-5 py-5 space-y-4">

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
          {isOverride && variant !== "request_info" && (
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
              />
              <p className={`text-[10px] mt-1 tabular-nums ${reason.trim().length < 20 && reason.length > 0 ? "text-[#8C3B2E]" : "text-[#8A8072]"}`}>
                {reason.trim().length} / 20 minimum characters
              </p>
            </div>
          )}

          {/* Request-info checklist */}
          {variant === "request_info" && (
            <div className="space-y-3">
              <div className="text-[10px] font-semibold text-[#8A8072] uppercase tracking-widest">
                Items to request from applicant
                <span className="ml-1 normal-case text-[#8A8072]/70">(select all that apply)</span>
              </div>

              {/* Known issues pre-populated */}
              {knownItems.length > 0 && (
                <div className="space-y-2">
                  {knownItems.map((item) => (
                    <label key={item} className="flex items-center gap-2 text-sm cursor-pointer group">
                      <input
                        type="checkbox"
                        checked={selectedItems.includes(item)}
                        onChange={() => toggleItem(item)}
                        className="accent-[#C48A2A] w-4 h-4"
                      />
                      <span className="group-hover:text-[#12213A] text-[#8A8072] transition-colors">
                        {item}
                      </span>
                    </label>
                  ))}
                </div>
              )}

              {/* Custom item input */}
              <div>
                <label className="block text-[10px] text-[#8A8072] mb-1">Add custom request:</label>
                <input
                  type="text"
                  value={customItem}
                  onChange={(e) => setCustomItem(e.target.value)}
                  placeholder="e.g. Updated bank statements for last 6 months"
                  className={`${inputCls} text-xs`}
                />
              </div>

              {knownItems.length === 0 && !customItem && (
                <p className="text-xs text-[#8A8072]">
                  No outstanding issues detected. Add a custom request above.
                </p>
              )}

              <div className="text-xs text-[#8A8072] bg-[#FFFBEB] border border-[#FDE68A] rounded px-3 py-2">
                <strong>Note:</strong> This will NOT finalise the decision. The application
                status changes to "Awaiting Information" and remains open for review once
                the applicant responds.
              </div>
            </div>
          )}

          {/* Audit notice */}
          <div className="text-xs text-[#8A8072] border-l-2 border-[#D6D0C4] pl-3 py-0.5">
            {variant === "request_info"
              ? "This action will be recorded in the audit trail. The application stays open."
              : "This action will be permanently recorded in the audit trail."}
          </div>

          {/* Error */}
          {error && (
            <div className="text-sm text-[#8C3B2E] bg-[#8C3B2E]/5 border border-[#8C3B2E]/30 rounded px-3 py-2" role="alert">
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
              {submitting
                ? "Submitting…"
                : variant === "request_info"
                ? "Send Request"
                : "Confirm"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
