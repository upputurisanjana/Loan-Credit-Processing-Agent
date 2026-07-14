/**
 * ChallengerCard — primary vs challenger model band comparison.
 */
import { useState } from "react";
import type { ChallengerResult } from "../api/client";

interface Props { result: ChallengerResult | null }

export default function ChallengerCard({ result }: Props) {
  const [acknowledged, setAcknowledged] = useState(false);

  if (!result) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg shadow-card overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-100 bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Challenger Model
        </div>
        <div className="px-4 py-4 text-sm text-slate-400">Not run for this application.</div>
      </div>
    );
  }

  const agree       = result.bands_agree;
  const showWarning = !agree && !acknowledged;

  return (
    <div
      className={`bg-white border rounded-lg shadow-card overflow-hidden ${
        agree ? "border-slate-200" : "border-amber-300"
      }`}
      role="region"
      aria-label={`Challenger: models ${agree ? "agree" : "disagree"}`}
    >
      {/* Header */}
      <div
        className={`px-4 py-3 border-b text-xs font-semibold uppercase tracking-wider ${
          agree
            ? "border-slate-100 bg-slate-50 text-slate-500"
            : "border-amber-200 bg-amber-50 text-amber-700"
        }`}
      >
        Challenger Model
      </div>

      <div className="px-4 py-4">
        {/* Disagreement alert */}
        {showWarning && (
          <div
            className="flex items-start gap-2.5 mb-4 p-3 rounded-lg border border-amber-200 bg-amber-50"
            role="alert"
          >
            <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true" className="flex-shrink-0 mt-0.5 text-amber-600">
              <path d="M7.5 1.5L13.5 12.5H1.5L7.5 1.5Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
              <path d="M7.5 5.5V8.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
              <circle cx="7.5" cy="10.5" r="0.6" fill="currentColor"/>
            </svg>
            <div className="flex-1">
              <p className="text-sm font-semibold text-amber-800">Models disagree — REFER enforced</p>
              <p className="text-xs mt-0.5 text-amber-600">
                Band delta exceeds threshold. Cannot be auto-approved.
              </p>
              <button
                onClick={() => setAcknowledged(true)}
                className="mt-2 px-3 py-1 text-xs font-semibold text-amber-700 border border-amber-300
                           rounded-md bg-white hover:bg-amber-50 transition-colors
                           focus:outline-none focus:ring-2 focus:ring-amber-400"
              >
                Acknowledge
              </button>
            </div>
          </div>
        )}

        {!agree && acknowledged && (
          <div className="flex items-center gap-1.5 text-amber-600 text-xs mb-3">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1.2"/>
              <path d="M3.5 6L5.5 8L8.5 4.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Acknowledged — REFER enforced
          </div>
        )}

        {/* Band comparison */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-slate-50 border border-slate-100 rounded-md p-3">
            <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">Primary</p>
            <p className="text-sm font-bold capitalize text-slate-900">{result.primary_band}</p>
          </div>
          <div className={`rounded-md p-3 border ${!agree ? "bg-amber-50 border-amber-100" : "bg-slate-50 border-slate-100"}`}>
            <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-1">Challenger</p>
            <p className={`text-sm font-bold capitalize ${!agree ? "text-amber-700" : "text-slate-900"}`}>
              {result.challenger_band}
            </p>
          </div>
        </div>

        {/* Agreement / delta */}
        {agree ? (
          <div className="mt-3 flex items-center gap-1.5 text-green-600 text-xs">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1.2"/>
              <path d="M3.5 6L5.5 8L8.5 4.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Models agree
          </div>
        ) : (
          <p className="mt-2 text-xs text-slate-400 tabular-nums">
            Band delta: <span className="font-semibold">{result.delta.toFixed(0)}</span>
          </p>
        )}
      </div>
    </div>
  );
}
