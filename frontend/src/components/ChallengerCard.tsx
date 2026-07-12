/**
 * ChallengerCard — shows primary vs challenger model band comparison.
 * Per UI_UX_DESIGN.md §3.4: "if they disagree, a clear 'Models disagree —
 * REFER enforced' note, non-dismissible until acknowledged."
 */
import { useState } from "react";
import type { ChallengerResult } from "../api/client";

interface Props { result: ChallengerResult | null }

export default function ChallengerCard({ result }: Props) {
  const [acknowledged, setAcknowledged] = useState(false);

  if (!result) {
    return (
      <div className="ledger-card" role="region" aria-label="Challenger model">
        <div className="section-label">Challenger Model</div>
        <div className="text-sm text-[#8A8072]">Challenger not run for this application.</div>
      </div>
    );
  }

  const agree = result.bands_agree;
  const showWarning = !agree && !acknowledged;

  return (
    <div
      className={`ledger-card ${agree ? "border-[#D6D0C4]" : "border-[#C48A2A] bg-[#C48A2A]/5"}`}
      role="region"
      aria-label={`Challenger check: models ${agree ? "agree" : "disagree"}`}
    >
      <div className="section-label">Challenger Model</div>

      {showWarning && (
        <div
          className="flex items-start gap-2 text-[#C48A2A] mb-3 p-2 rounded-sm border border-[#C48A2A]/40 bg-[#C48A2A]/8"
          role="alert"
          aria-live="assertive"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" className="flex-shrink-0 mt-0.5">
            <path d="M8 1.5L14.5 13H1.5L8 1.5Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
            <path d="M8 6V9" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
            <circle cx="8" cy="11" r="0.6" fill="currentColor"/>
          </svg>
          <div className="flex-1">
            <div className="text-sm font-bold">Models disagree — REFER enforced</div>
            <div className="text-xs mt-0.5 text-[#C48A2A]/80">
              Primary and challenger bands differ by more than 1. Case cannot be auto-approved.
            </div>
            <button
              onClick={() => setAcknowledged(true)}
              className="mt-2 px-3 py-1 text-xs font-semibold border border-[#C48A2A] rounded-sm
                         text-[#C48A2A] hover:bg-[#C48A2A] hover:text-white transition-colors
                         focus:outline-none focus:ring-2 focus:ring-[#C48A2A]"
            >
              Acknowledge
            </button>
          </div>
        </div>
      )}

      {!agree && acknowledged && (
        <div className="flex items-center gap-1.5 text-[#C48A2A] text-xs mb-3">
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
            <circle cx="6.5" cy="6.5" r="5.5" stroke="currentColor" strokeWidth="1.2"/>
            <path d="M4 6.5L6 8.5L9.5 5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Disagreement acknowledged — REFER enforced
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="text-2xs text-[#8A8072] uppercase tracking-wider mb-0.5">Primary band</div>
          <div className="text-sm font-semibold capitalize">{result.primary_band}</div>
        </div>
        <div>
          <div className="text-2xs text-[#8A8072] uppercase tracking-wider mb-0.5">Challenger band</div>
          <div className={`text-sm font-semibold capitalize ${!agree ? "text-[#C48A2A]" : ""}`}>
            {result.challenger_band}
          </div>
        </div>
      </div>

      {agree && (
        <div className="mt-2 flex items-center gap-1.5 text-[#3A6B4C] text-xs">
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
            <circle cx="6.5" cy="6.5" r="5.5" stroke="currentColor" strokeWidth="1.2"/>
            <path d="M4 6.5L6 8.5L9.5 5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Models agree
        </div>
      )}

      {!agree && (
        <div className="mt-2 text-xs text-[#8A8072]" data-numeric>
          Band delta: {result.delta.toFixed(2)}
        </div>
      )}
    </div>
  );
}
