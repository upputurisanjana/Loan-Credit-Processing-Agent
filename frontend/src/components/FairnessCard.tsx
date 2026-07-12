/**
 * FairnessCard — identity-masked re-score result.
 * Per UI_UX_DESIGN.md §3.4: MATCH ✓ (green) or hard-stop red banner on MISMATCH.
 */
import type { FairnessCheck } from "../api/client";

interface Props { check: FairnessCheck }

export default function FairnessCard({ check }: Props) {
  const ok = check.match;

  return (
    <div
      className={`ledger-card ${ok ? "border-[#3A6B4C]/40 bg-[#3A6B4C]/5" : "border-[#8C3B2E] bg-[#8C3B2E]/5"}`}
      role={ok ? "region" : "alert"}
      aria-live={ok ? "polite" : "assertive"}
      aria-label={`Fairness check: ${ok ? "passed" : "FAILED"}`}
    >
      <div className="section-label">Fairness Check</div>

      {ok ? (
        <div className="flex items-center gap-2 text-[#3A6B4C]">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
            <circle cx="9" cy="9" r="8" stroke="currentColor" strokeWidth="1.5"/>
            <path d="M5.5 9L8 11.5L12.5 6.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span className="text-sm font-semibold">Identity-masked re-score: MATCH ✓</span>
        </div>
      ) : (
        <div className="flex items-start gap-2 text-[#8C3B2E]">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true" className="flex-shrink-0 mt-0.5">
            <circle cx="9" cy="9" r="8" stroke="currentColor" strokeWidth="1.5"/>
            <path d="M9 5.5V9.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            <circle cx="9" cy="12" r="0.75" fill="currentColor"/>
          </svg>
          <div>
            <div className="text-sm font-bold">MISMATCH — Do not proceed without review</div>
            <div className="text-xs mt-1 text-[#8C3B2E]/80">
              Application forced to REFER. Investigate the disparity before approving.
            </div>
          </div>
        </div>
      )}

      <div className="mt-3 grid grid-cols-2 gap-3 border-t border-[#D6D0C4] pt-3">
        <div>
          <div className="text-2xs text-[#8A8072] uppercase tracking-wider mb-0.5">Original band</div>
          <div className="text-sm font-semibold capitalize">{check.original_band}</div>
          <div className="text-xs text-[#8A8072]" data-numeric>Score: {(check.original_composite * 100).toFixed(1)}</div>
        </div>
        <div>
          <div className="text-2xs text-[#8A8072] uppercase tracking-wider mb-0.5">Masked band</div>
          <div className={`text-sm font-semibold capitalize ${!ok ? "text-[#8C3B2E]" : ""}`}>{check.masked_band}</div>
          <div className="text-xs text-[#8A8072]" data-numeric>Score: {(check.masked_composite * 100).toFixed(1)}</div>
        </div>
      </div>
    </div>
  );
}
