/**
 * FairnessCard — identity-masked re-score result panel.
 */
import type { FairnessCheck } from "../api/client";

interface Props { check: FairnessCheck }

export default function FairnessCard({ check }: Props) {
  const ok = check.match;

  return (
    <div
      className={`bg-white border rounded-lg shadow-card overflow-hidden ${
        ok ? "border-slate-200" : "border-red-300"
      }`}
      role={ok ? "region" : "alert"}
      aria-live={ok ? "polite" : "assertive"}
      aria-label={`Fairness check: ${ok ? "passed" : "FAILED"}`}
    >
      {/* Header */}
      <div
        className={`px-4 py-3 border-b text-xs font-semibold uppercase tracking-wider ${
          ok
            ? "border-slate-100 bg-slate-50 text-slate-500"
            : "border-red-200 bg-red-50 text-red-600"
        }`}
      >
        Fairness Check
      </div>

      <div className="px-4 py-4">
        {/* Result badge */}
        {ok ? (
          <div className="flex items-center gap-2 text-green-700 mb-4">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M5 8L7 10L11 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <span className="text-sm font-semibold">Masked re-score matched</span>
          </div>
        ) : (
          <div className="flex items-start gap-2 text-red-700 mb-4">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" className="flex-shrink-0 mt-0.5">
              <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M8 5V9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              <circle cx="8" cy="11.5" r="0.75" fill="currentColor"/>
            </svg>
            <div>
              <p className="text-sm font-bold">Mismatch — forced to REFER</p>
              <p className="text-xs mt-0.5 text-red-500">Investigate disparity before approving.</p>
            </div>
          </div>
        )}

        {/* Band comparison */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-slate-50 border border-slate-100 rounded-md p-3">
            <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">Original</p>
            <p className="text-sm font-bold capitalize text-slate-900">{check.original_band}</p>
            <p className="text-xs text-slate-400 tabular-nums">{(check.original_composite * 100).toFixed(1)} pts</p>
          </div>
          <div className={`rounded-md p-3 border ${!ok ? "bg-red-50 border-red-100" : "bg-slate-50 border-slate-100"}`}>
            <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">Masked</p>
            <p className={`text-sm font-bold capitalize ${!ok ? "text-red-700" : "text-slate-900"}`}>
              {check.masked_band}
            </p>
            <p className="text-xs text-slate-400 tabular-nums">{(check.masked_composite * 100).toFixed(1)} pts</p>
          </div>
        </div>
      </div>
    </div>
  );
}
