/**
 * ChallengerCard — shows primary vs challenger model band comparison.
 * Disagree → non-dismissible warning until acknowledged.
 */
import { useState } from "react";
import type { ChallengerResult } from "../api/client";

interface Props { result: ChallengerResult | null }

export default function ChallengerCard({ result }: Props) {
  const [acknowledged, setAcknowledged] = useState(false);

  if (!result) {
    return (
      <div className="bg-white border border-[#D6D0C4] rounded overflow-hidden">
        <div className="px-4 py-2.5 border-b border-[#D6D0C4] bg-[#FAF8F3] text-[10px] font-semibold uppercase tracking-widest text-[#8A8072]">
          Challenger Model
        </div>
        <div className="px-4 py-4 text-sm text-[#8A8072]">Not run for this application.</div>
      </div>
    );
  }

  const agree       = result.bands_agree;
  const showWarning = !agree && !acknowledged;

  return (
    <div
      className={`bg-white border rounded overflow-hidden ${
        agree ? "border-[#D6D0C4]" : "border-[#C48A2A]"
      }`}
      role="region"
      aria-label={`Challenger: models ${agree ? "agree" : "disagree"}`}
    >
      {/* Header */}
      <div className={`px-4 py-2.5 border-b text-[10px] font-semibold uppercase tracking-widest
                       ${agree ? "border-[#D6D0C4] bg-[#FAF8F3] text-[#8A8072]"
                               : "border-[#C48A2A]/30 bg-[#C48A2A]/5 text-[#C48A2A]"}`}>
        Challenger Model
      </div>

      <div className="px-4 py-4">
        {/* Disagreement warning */}
        {showWarning && (
          <div
            className="flex items-start gap-2.5 text-[#C48A2A] mb-4 p-3 rounded border border-[#C48A2A]/30 bg-[#C48A2A]/5"
            role="alert"
            aria-live="assertive"
          >
            <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true" className="flex-shrink-0 mt-0.5">
              <path d="M7.5 1.5L13.5 12.5H1.5L7.5 1.5Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
              <path d="M7.5 5.5V8.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
              <circle cx="7.5" cy="10.5" r="0.6" fill="currentColor"/>
            </svg>
            <div className="flex-1">
              <div className="text-sm font-bold">Models disagree — REFER enforced</div>
              <div className="text-xs mt-0.5 text-[#C48A2A]/80">
                Band delta exceeds threshold. Cannot be auto-approved.
              </div>
              <button
                onClick={() => setAcknowledged(true)}
                className="mt-2 px-3 py-1 text-xs font-semibold border border-[#C48A2A] rounded
                           hover:bg-[#C48A2A] hover:text-white transition-colors focus:outline-none focus:ring-1 focus:ring-[#C48A2A]"
              >
                Acknowledge
              </button>
            </div>
          </div>
        )}

        {!agree && acknowledged && (
          <div className="flex items-center gap-1.5 text-[#C48A2A] text-xs mb-3">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1.2"/>
              <path d="M3.5 6L5.5 8L8.5 4.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Acknowledged — REFER enforced
          </div>
        )}

        {/* Band comparison */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-[#FAF8F3] rounded p-3">
            <div className="text-[10px] text-[#8A8072] uppercase tracking-wider mb-1">Primary</div>
            <div className="text-sm font-bold capitalize text-[#12213A]">{result.primary_band}</div>
          </div>
          <div className={`rounded p-3 ${!agree ? "bg-[#C48A2A]/5" : "bg-[#FAF8F3]"}`}>
            <div className="text-[10px] text-[#8A8072] uppercase tracking-wider mb-1">Challenger</div>
            <div className={`text-sm font-bold capitalize ${!agree ? "text-[#C48A2A]" : "text-[#12213A]"}`}>
              {result.challenger_band}
            </div>
          </div>
        </div>

        {/* Agreement / delta */}
        {agree ? (
          <div className="mt-3 flex items-center gap-1.5 text-[#3A6B4C] text-xs">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1.2"/>
              <path d="M3.5 6L5.5 8L8.5 4.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Models agree
          </div>
        ) : (
          <div className="mt-2 text-xs text-[#8A8072] tabular-nums">
            Delta: <span className="font-semibold">{result.delta.toFixed(3)}</span>
          </div>
        )}
      </div>
    </div>
  );
}
