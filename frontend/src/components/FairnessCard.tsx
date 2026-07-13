/**
 * FairnessCard — identity-masked re-score result.
 * MATCH ✓ (green) or hard-stop red banner on MISMATCH.
 */
import type { FairnessCheck } from "../api/client";

interface Props { check: FairnessCheck }

export default function FairnessCard({ check }: Props) {
  const ok = check.match;

  return (
    <div
      className={`bg-white border rounded overflow-hidden ${
        ok ? "border-[#3A6B4C]/30" : "border-[#8C3B2E]"
      }`}
      role={ok ? "region" : "alert"}
      aria-live={ok ? "polite" : "assertive"}
      aria-label={`Fairness check: ${ok ? "passed" : "FAILED"}`}
    >
      {/* Header */}
      <div className={`px-4 py-2.5 border-b text-[10px] font-semibold uppercase tracking-widest
                       ${ok ? "border-[#3A6B4C]/20 bg-[#3A6B4C]/5 text-[#3A6B4C]"
                            : "border-[#8C3B2E]/30 bg-[#8C3B2E]/8 text-[#8C3B2E]"}`}>
        Fairness Check
      </div>

      <div className="px-4 py-4">
        {/* Result */}
        {ok ? (
          <div className="flex items-center gap-2 text-[#3A6B4C] mb-4">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M5 8L7 10L11 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <span className="text-sm font-semibold">Masked re-score: MATCH ✓</span>
          </div>
        ) : (
          <div className="flex items-start gap-2 text-[#8C3B2E] mb-4">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" className="flex-shrink-0 mt-0.5">
              <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M8 5V8.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              <circle cx="8" cy="11" r="0.75" fill="currentColor"/>
            </svg>
            <div>
              <div className="text-sm font-bold">MISMATCH – forced to REFER</div>
              <div className="text-xs mt-0.5 text-[#8C3B2E]/80">
                Investigate the score disparity before approving.
              </div>
            </div>
          </div>
        )}

        {/* Band comparison */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-[#FAF8F3] rounded p-3">
            <div className="text-[10px] text-[#8A8072] uppercase tracking-wider mb-1">Original</div>
            <div className="text-sm font-bold capitalize text-[#12213A]">{check.original_band}</div>
            <div className="text-xs text-[#8A8072] tabular-nums">{(check.original_composite * 100).toFixed(1)} pts</div>
          </div>
          <div className={`rounded p-3 ${!ok ? "bg-[#8C3B2E]/5" : "bg-[#FAF8F3]"}`}>
            <div className="text-[10px] text-[#8A8072] uppercase tracking-wider mb-1">Masked</div>
            <div className={`text-sm font-bold capitalize ${!ok ? "text-[#8C3B2E]" : "text-[#12213A]"}`}>
              {check.masked_band}
            </div>
            <div className="text-xs text-[#8A8072] tabular-nums">{(check.masked_composite * 100).toFixed(1)} pts</div>
          </div>
        </div>
      </div>
    </div>
  );
}
