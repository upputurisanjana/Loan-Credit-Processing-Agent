/**
 * ScoreBar — single factor score visualization with policy clause link.
 */
interface Props {
  label: string;
  subscore: number;      // 0–1
  weight: number;        // 0–1
  clauseId?: string;
  onViewClause?: (id: string) => void;
}

export default function ScoreBar({ label, subscore, weight, clauseId, onViewClause }: Props) {
  const pct        = Math.round(subscore * 100);
  const contribution = (subscore * weight * 100).toFixed(1);
  const barColor   = pct >= 70 ? "#3A6B4C" : pct >= 50 ? "#C48A2A" : "#8C3B2E";

  return (
    <div className="py-2.5" aria-label={`${label}: ${pct}%`}>
      <div className="flex justify-between items-baseline mb-1.5">
        <span className="text-sm font-medium text-[#12213A]">{label}</span>
        <div className="flex items-center gap-3 text-xs text-[#8A8072]">
          <span className="tabular-nums">
            <span className="font-semibold text-[#12213A]">{pct}</span>
            <span>/100</span>
          </span>
          <span className="hidden sm:inline">wt {Math.round(weight * 100)}%</span>
          <span className="font-medium text-[#12213A] tabular-nums">+{contribution}pts</span>
          {clauseId && (
            <button
              onClick={() => onViewClause?.(clauseId)}
              className="font-mono text-[#C48A2A] hover:underline focus:outline-none focus:underline"
              aria-label={`View policy clause ${clauseId}`}
            >
              [{clauseId}]
            </button>
          )}
        </div>
      </div>
      <div
        className="h-2 bg-[#E8E4DC] rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${pct}%`, background: barColor }}
        />
      </div>
    </div>
  );
}
