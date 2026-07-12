interface Props {
  label: string;
  subscore: number;      // 0–1
  weight: number;        // 0–1
  clauseId?: string;
  onViewClause?: (id: string) => void;
}

export default function ScoreBar({ label, subscore, weight, clauseId, onViewClause }: Props) {
  const pct = Math.round(subscore * 100);
  const contribution = (subscore * weight * 100).toFixed(1);

  return (
    <div className="py-2" aria-label={`${label} score: ${pct}%`}>
      <div className="flex justify-between items-baseline mb-1">
        <span className="text-sm font-medium text-[#12213A]">{label}</span>
        <div className="flex items-center gap-3 text-xs text-[#8A8072]">
          <span data-numeric>
            <span className="font-semibold text-[#12213A]">{pct}</span>
            <span>/100</span>
          </span>
          <span>wt {Math.round(weight * 100)}%</span>
          <span className="text-[#12213A] font-medium">+{contribution}pts</span>
          {clauseId && (
            <button
              onClick={() => onViewClause?.(clauseId)}
              className="text-[#C48A2A] hover:underline focus:outline-none focus:underline"
              aria-label={`View policy clause ${clauseId}`}
            >
              [{clauseId}]
            </button>
          )}
        </div>
      </div>
      {/* Single-hue bar — deep ink fill */}
      <div className="h-2 bg-[#D6D0C4] rounded-full overflow-hidden" role="progressbar"
           aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div
          className="h-full bg-[#12213A] rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
