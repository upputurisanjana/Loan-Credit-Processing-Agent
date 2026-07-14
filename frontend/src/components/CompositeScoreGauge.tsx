/**
 * CompositeScoreGauge — clean score display with threshold ruler.
 */
import type { Band } from "../api/client";

interface Props {
  composite: number;
  band: Band;
  approveMin?: number;
  referMin?: number;
}

const BAND_COLOR: Record<Band, { text: string; bg: string; bar: string }> = {
  approve: { text: "text-green-700",  bg: "bg-green-50 border-green-200",  bar: "#16a34a" },
  refer:   { text: "text-amber-700",  bg: "bg-amber-50 border-amber-200",  bar: "#d97706" },
  decline: { text: "text-red-700",    bg: "bg-red-50 border-red-200",      bar: "#dc2626" },
};

export default function CompositeScoreGauge({
  composite,
  band,
  approveMin = 0.75,
  referMin   = 0.65,
}: Props) {
  const pct        = Math.round(composite * 100);
  const referPct   = Math.round(referMin  * 100);
  const approvePct = Math.round(approveMin * 100);
  const colors     = BAND_COLOR[band];

  return (
    <div className="py-2" aria-label={`Composite score: ${pct}%, band: ${band}`}>

      {/* Score + band pill */}
      <div className="flex items-end gap-4 mb-5">
        <span
          className={`text-5xl font-bold tabular-nums leading-none ${colors.text}`}
          data-numeric
        >
          {pct}
        </span>
        <div className="flex flex-col gap-1.5 mb-0.5">
          <span className="text-sm text-slate-400 font-medium">/ 100</span>
          <span
            className={`text-xs font-semibold uppercase tracking-wider px-2.5 py-0.5 rounded-full border ${colors.bg} ${colors.text}`}
          >
            {band}
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="relative">
        {/* Track */}
        <div
          className="relative h-2.5 rounded-full overflow-hidden bg-slate-100"
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          {/* Decline zone */}
          <div
            className="absolute inset-y-0 left-0 bg-red-200/60"
            style={{ width: `${referPct}%` }}
          />
          {/* Refer zone */}
          <div
            className="absolute inset-y-0 bg-amber-200/60"
            style={{ left: `${referPct}%`, width: `${approvePct - referPct}%` }}
          />
          {/* Approve zone */}
          <div
            className="absolute inset-y-0 right-0 bg-green-200/60"
            style={{ left: `${approvePct}%` }}
          />
          {/* Score fill */}
          <div
            className="absolute inset-y-0 left-0 rounded-full transition-all duration-700 ease-out"
            style={{ width: `${Math.min(pct, 100)}%`, backgroundColor: colors.bar, opacity: 0.85 }}
          />
        </div>

        {/* Score marker */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full border-2 border-white shadow-md transition-all duration-700 ease-out"
          style={{ left: `calc(${Math.min(pct, 99)}% - 8px)`, backgroundColor: colors.bar }}
          aria-hidden="true"
        />

        {/* Tick labels */}
        <div className="relative h-5 mt-2" aria-hidden="true">
          <span
            className="absolute text-[10px] text-slate-400 tabular-nums -translate-x-1/2"
            style={{ left: `${referPct}%` }}
          >
            {referPct}
          </span>
          <span
            className="absolute text-[10px] text-slate-400 tabular-nums -translate-x-1/2"
            style={{ left: `${approvePct}%` }}
          >
            {approvePct}
          </span>
          <span className="absolute right-0 text-[10px] text-slate-400">100</span>
          <span className="absolute left-0 text-[10px] text-slate-400">0</span>
        </div>

        {/* Zone labels */}
        <div className="flex text-[10px] mt-0.5 font-medium uppercase tracking-wide" aria-label="Score bands">
          <span className="text-red-500"    style={{ width: `${referPct}%` }}>Decline</span>
          <span className="text-amber-600 text-center" style={{ width: `${approvePct - referPct}%` }}>Refer</span>
          <span className="text-green-600 text-right flex-1">Approve</span>
        </div>
      </div>
    </div>
  );
}
