/**
 * CompositeScoreGauge — large score display with threshold ruler.
 */
import type { Band } from "../api/client";

interface Props {
  composite: number;   // 0–1
  band: Band;
  approvMin?: number;  // default 0.75
  referMin?: number;   // default 0.65
}

const BAND_COLOR: Record<Band, string> = {
  approve: "#3A6B4C",
  refer:   "#C48A2A",
  decline: "#8C3B2E",
};

export default function CompositeScoreGauge({
  composite,
  band,
  approvMin = 0.75,
  referMin  = 0.65,
}: Props) {
  const pct     = Math.round(composite * 100);
  const color   = BAND_COLOR[band];
  const referPct   = Math.round(referMin  * 100);
  const approvePct = Math.round(approvMin * 100);

  return (
    <div className="py-3" aria-label={`Composite score: ${pct}%, band: ${band}`}>

      {/* Score + band */}
      <div className="flex items-baseline gap-3 mb-5">
        <span className="font-serif text-6xl font-bold tabular-nums leading-none" style={{ color }} data-numeric>
          {pct}
        </span>
        <div className="flex flex-col gap-1">
          <span className="text-sm text-[#8A8072]">/100 composite</span>
          <span
            className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded self-start"
            style={{ color, background: `${color}18`, border: `1px solid ${color}30` }}
          >
            {band}
          </span>
        </div>
      </div>

      {/* Threshold ruler */}
      <div className="relative">
        {/* Track */}
        <div className="relative h-3 rounded-full overflow-hidden bg-[#E8E4DC]">
          <div className="absolute inset-y-0 left-0 rounded-l-full bg-[#8C3B2E]/25"
               style={{ width: `${referPct}%` }} />
          <div className="absolute inset-y-0 bg-[#C48A2A]/25"
               style={{ left: `${referPct}%`, width: `${approvePct - referPct}%` }} />
          <div className="absolute inset-y-0 right-0 rounded-r-full bg-[#3A6B4C]/25"
               style={{ left: `${approvePct}%` }} />
        </div>

        {/* Score marker */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full border-2 border-white shadow-md transition-all duration-700 ease-out"
          style={{ left: `calc(${Math.min(pct, 99)}% - 8px)`, background: color }}
          aria-hidden="true"
        />

        {/* Threshold tick labels */}
        <div className="relative h-5 mt-1.5" aria-hidden="true">
          <span className="absolute text-[10px] text-[#8A8072] tabular-nums"
                style={{ left: `${referPct}%`, transform: "translateX(-50%)" }}>
            {referPct}
          </span>
          <span className="absolute text-[10px] text-[#8A8072] tabular-nums"
                style={{ left: `${approvePct}%`, transform: "translateX(-50%)" }}>
            {approvePct}
          </span>
          <span className="absolute right-0 text-[10px] text-[#8A8072]">100</span>
          <span className="absolute left-0 text-[10px] text-[#8A8072]">0</span>
        </div>

        {/* Zone labels */}
        <div className="flex text-[10px] mt-0.5 font-medium uppercase tracking-wide" aria-label="Score bands">
          <span className="text-[#8C3B2E]"    style={{ width: `${referPct}%` }}>Decline</span>
          <span className="text-[#C48A2A] text-center" style={{ width: `${approvePct - referPct}%` }}>Refer</span>
          <span className="text-[#3A6B4C] text-right flex-1">Approve</span>
        </div>
      </div>
    </div>
  );
}
