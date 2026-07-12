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
  referMin = 0.65,
}: Props) {
  const pct = Math.round(composite * 100);
  const color = BAND_COLOR[band];

  // Positions on the 0–100 ruler
  const referPos  = referMin  * 100;
  const approvePos = approvMin * 100;

  return (
    <div className="py-4" aria-label={`Composite score: ${pct}%, band: ${band}`}>
      {/* Large score number */}
      <div className="flex items-baseline gap-3 mb-4">
        <span
          className="font-serif text-5xl font-bold tabular-nums"
          style={{ color }}
          data-numeric
        >
          {pct}
        </span>
        <span className="text-[#8A8072] text-sm">/100 composite</span>
        <span
          className="ml-auto text-sm font-semibold uppercase tracking-wide px-2 py-1 rounded-sm"
          style={{ color, background: `${color}18` }}
        >
          {band}
        </span>
      </div>

      {/* Threshold ruler */}
      <div className="relative">
        {/* Track */}
        <div className="h-3 bg-[#D6D0C4] rounded-full overflow-hidden" role="presentation">
          {/* Decline zone */}
          <div className="absolute left-0 top-0 h-full rounded-l-full bg-[#8C3B2E]/20"
               style={{ width: `${referPos}%` }} />
          {/* Refer zone */}
          <div className="absolute top-0 h-full bg-[#C48A2A]/20"
               style={{ left: `${referPos}%`, width: `${approvePos - referPos}%` }} />
          {/* Approve zone */}
          <div className="absolute top-0 h-full rounded-r-full bg-[#3A6B4C]/20"
               style={{ left: `${approvePos}%`, right: 0 }} />
        </div>

        {/* Score marker */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full border-2 border-white shadow-md transition-all duration-500"
          style={{ left: `calc(${Math.min(pct, 99)}% - 8px)`, background: color }}
          aria-hidden="true"
        />

        {/* Threshold labels */}
        <div className="relative h-6 mt-1 text-2xs text-[#8A8072]" aria-hidden="true">
          <span className="absolute" style={{ left: `${referPos}%`, transform: "translateX(-50%)" }}>
            {Math.round(referMin * 100)}
          </span>
          <span className="absolute" style={{ left: `${approvePos}%`, transform: "translateX(-50%)" }}>
            {Math.round(approvMin * 100)}
          </span>
          <span className="absolute right-0">100</span>
          <span className="absolute left-0">0</span>
        </div>

        {/* Zone labels */}
        <div className="flex text-2xs mt-1" aria-label="Score zones">
          <span className="text-[#8C3B2E]" style={{ width: `${referPos}%` }}>Decline</span>
          <span className="text-[#C48A2A]" style={{ width: `${approvePos - referPos}%`, textAlign: "center" }}>Refer</span>
          <span className="text-[#3A6B4C] text-right flex-1">Approve</span>
        </div>
      </div>
    </div>
  );
}
