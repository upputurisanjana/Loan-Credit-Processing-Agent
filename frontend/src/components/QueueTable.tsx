import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { QueueItem } from "../api/client";
import StatusPill from "./StatusPill";

interface Props {
  items: QueueItem[];
  loading?: boolean;
}

type SortKey = "created_at" | "composite_score" | "status";

export default function QueueTable({ items, loading }: Props) {
  const navigate = useNavigate();
  const [sort, setSort] = useState<SortKey>("created_at");
  const [masked, setMasked] = useState(true);
  const [filter, setFilter] = useState<"all" | "fairness" | "challenger">("all");

  const sorted = [...items]
    .filter((i) => {
      if (filter === "fairness") return !i.fairness_match;
      if (filter === "challenger") return i.challenger_disagreement;
      return true;
    })
    .sort((a, b) => {
      if (sort === "composite_score") return b.composite_score - a.composite_score;
      if (sort === "status") return a.status.localeCompare(b.status);
      // Default: oldest pending first
      return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    });

  function maskId(id: string) {
    if (!masked) return id;
    // Show first 3 chars + ******
    return id.slice(0, 3) + "-" + "••••••";
  }

  const th = "text-xs font-medium uppercase tracking-wider text-[#8A8072] border-b border-[#D6D0C4] pb-2 text-left px-2 cursor-pointer select-none";

  if (loading) {
    return (
      <div className="py-12 text-center text-[#8A8072] text-sm">
        Loading queue…
      </div>
    );
  }

  return (
    <div>
      {/* Filter chips + identity toggle */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        {(["all", "fairness", "challenger"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded-sm text-xs font-medium border transition-colors ${
              filter === f
                ? "bg-[#12213A] text-[#FAF8F3] border-[#12213A]"
                : "bg-transparent text-[#8A8072] border-[#D6D0C4] hover:border-[#12213A]"
            }`}
            aria-pressed={filter === f}
          >
            {f === "all" ? "All" : f === "fairness" ? "⚠ Fairness" : "⚖ Challenger Disagree"}
          </button>
        ))}

        <button
          onClick={() => setMasked((m) => !m)}
          className="ml-auto px-3 py-1 rounded-sm text-xs font-medium border border-[#D6D0C4] text-[#8A8072] hover:border-[#12213A] transition-colors"
          aria-pressed={masked}
        >
          {masked ? "🔒 Identity masked" : "👁 Identity visible"}
        </button>
      </div>

      <table className="ledger-table" aria-label="Application queue">
        <thead>
          <tr>
            <th className={th} onClick={() => setSort("created_at")} aria-sort={sort === "created_at" ? "ascending" : "none"}>
              Application {sort === "created_at" && "↑"}
            </th>
            <th className={th} onClick={() => setSort("composite_score")} aria-sort={sort === "composite_score" ? "descending" : "none"}>
              Score {sort === "composite_score" && "↓"}
            </th>
            <th className={th}>Band</th>
            <th className={th} onClick={() => setSort("status")} aria-sort={sort === "status" ? "ascending" : "none"}>
              Status {sort === "status" && "↑"}
            </th>
            <th className={th}>Age</th>
            <th className={th}>Flags</th>
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 && (
            <tr>
              <td colSpan={6} className="py-8 text-center text-[#8A8072] text-sm">
                No applications in queue.
              </td>
            </tr>
          )}
          {sorted.map((item) => (
            <tr
              key={item.application_id}
              onClick={() => navigate(`/applications/${item.application_id}`)}
              className={item.status === "flag_fairness_fail" ? "bg-[#8C3B2E]/5" : ""}
              aria-label={`Application ${item.application_id}`}
            >
              <td className="px-2 font-mono text-sm">
                {maskId(item.application_id)}
              </td>
              <td className="px-2" data-numeric>
                {/* Mini score bar */}
                <div className="flex items-center gap-2">
                  <div className="w-16 h-1.5 bg-[#D6D0C4] rounded-full overflow-hidden flex-shrink-0">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.round(item.composite_score * 100)}%`,
                        background: item.band === "approve" ? "#3A6B4C" : item.band === "refer" ? "#C48A2A" : "#8C3B2E",
                      }}
                    />
                  </div>
                  <span className="text-sm">{Math.round(item.composite_score * 100)}</span>
                </div>
              </td>
              <td className="px-2">
                <StatusPill value={item.band} size="sm" />
              </td>
              <td className="px-2">
                <StatusPill value={item.status} size="sm" />
              </td>
              <td className="px-2 text-xs text-[#8A8072]" data-numeric>
                {formatAge(item.created_at)}
              </td>
              <td className="px-2 text-xs">
                {!item.fairness_match && (
                  <span className="text-[#8C3B2E] font-medium mr-1" title="Fairness mismatch">⚠ F</span>
                )}
                {item.challenger_disagreement && (
                  <span className="text-[#C48A2A] font-medium" title="Challenger model disagrees">⚖ C</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatAge(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  return `${Math.floor(hrs / 24)}d`;
}
