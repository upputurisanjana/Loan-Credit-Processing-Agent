/**
 * ScoreBar — single factor score bar with policy clause link.
 */
interface Props {
  label: string;
  subscore: number;
  weight: number;
  clauseId?: string;
  onViewClause?: (id: string) => void;
}

export default function ScoreBar({ label, subscore, weight, clauseId, onViewClause }: Props) {
  const pct          = Math.round(subscore * 100);
  const contribution = (subscore * weight * 100).toFixed(1);

  const barColor =
    pct >= 70 ? "#16a34a" :
    pct >= 50 ? "#d97706" :
                "#dc2626";

  const labelColor =
    pct >= 70 ? "text-green-600" :
    pct >= 50 ? "text-amber-600" :
                "text-red-600";

  return (
    <div className="py-2.5" aria-label={`${label}: ${pct}%`}>
      <div className="flex justify-between items-baseline mb-1.5">
        <span className="text-sm font-medium text-slate-700">{label}</span>
        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span className="tabular-nums">
            <span className={`font-semibold ${labelColor}`}>{pct}</span>
            <span>/100</span>
          </span>
          <span className="hidden sm:inline text-slate-300">wt {Math.round(weight * 100)}%</span>
          <span className="font-medium text-slate-600 tabular-nums">+{contribution} pts</span>
          {clauseId && (
            <button
              onClick={() => onViewClause?.(clauseId)}
              className="font-mono text-blue-600 hover:text-blue-800 hover:underline
                         focus:outline-none focus:underline text-xs"
              aria-label={`View policy clause ${clauseId}`}
            >
              [{clauseId}]
            </button>
          )}
        </div>
      </div>
      <div
        className="h-1.5 bg-slate-100 rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${pct}%`, backgroundColor: barColor }}
        />
      </div>
    </div>
  );
}
