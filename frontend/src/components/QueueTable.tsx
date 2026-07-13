/**
 * QueueTable — sortable, filterable table of all applications.
 * Professional ledger aesthetic with proper empty states.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { QueueItem } from "../api/client";
import StatusPill from "./StatusPill";

interface Props {
  items: QueueItem[];
  loading?: boolean;
}

type SortKey = "created_at" | "composite_score" | "status";

function formatAge(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1)  return "< 1m";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)  return `${hrs}h`;
  return `${Math.floor(hrs / 24)}d`;
}

export default function QueueTable({ items, loading }: Props) {
  const navigate = useNavigate();
  const [sort, setSort]     = useState<SortKey>("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [masked, setMasked] = useState(true);
  const [filter, setFilter] = useState<"all" | "pending" | "fairness" | "challenger">("all");

  function toggleSort(key: SortKey) {
    if (sort === key) setSortDir((d) => d === "asc" ? "desc" : "asc");
    else { setSort(key); setSortDir(key === "composite_score" ? "desc" : "asc"); }
  }

  const sorted = [...items]
    .filter((i) => {
      if (filter === "pending")    return i.status === "pending_human_review" || i.status === "flag_fairness_fail";
      if (filter === "fairness")   return !i.fairness_match;
      if (filter === "challenger") return i.challenger_disagreement;
      return true;
    })
    .sort((a, b) => {
      let cmp = 0;
      if (sort === "composite_score") cmp = a.composite_score - b.composite_score;
      else if (sort === "status")     cmp = a.status.localeCompare(b.status);
      else                            cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      return sortDir === "asc" ? cmp : -cmp;
    });

  function maskId(id: string) {
    if (!masked) return id;
    return id.slice(0, 3) + "-••••••";
  }

  function SortIndicator({ col }: { col: SortKey }) {
    if (sort !== col) return <span className="text-[#D6D0C4] ml-1">⇅</span>;
    return <span className="text-[#C48A2A] ml-1">{sortDir === "asc" ? "↑" : "↓"}</span>;
  }

  const thCls = "text-[10px] font-semibold uppercase tracking-widest text-[#8A8072] pb-3 text-left px-3 cursor-pointer select-none hover:text-[#12213A] transition-colors";
  const tdCls = "px-3 py-3.5 align-middle";

  // ── Loading skeleton ─────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="space-y-2 py-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-10 bg-[#F2EFE8] rounded animate-pulse" style={{ opacity: 1 - i * 0.15 }} />
        ))}
      </div>
    );
  }

  return (
    <div>
      {/* ── Filter bar ───────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        {([
          ["all",         "All"],
          ["pending",     "⏳ Pending"],
          ["fairness",    "⚠ Fairness"],
          ["challenger",  "⚖ Challenger"],
        ] as const).map(([f, label]) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded text-[11px] font-medium border transition-all ${
              filter === f
                ? "bg-[#12213A] text-[#FAF8F3] border-[#12213A] shadow-sm"
                : "bg-transparent text-[#8A8072] border-[#D6D0C4] hover:border-[#12213A] hover:text-[#12213A]"
            }`}
            aria-pressed={filter === f}
          >
            {label}
          </button>
        ))}

        <button
          onClick={() => setMasked((m) => !m)}
          className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded text-[11px] font-medium border border-[#D6D0C4] text-[#8A8072] hover:border-[#12213A] hover:text-[#12213A] transition-all"
          aria-pressed={masked}
          title={masked ? "Identity masked for privacy" : "Identity visible"}
        >
          {masked ? (
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <path d="M1 6C2.5 3 4.5 2 6 2s3.5 1 5 4c-1.5 3-3.5 4-5 4S2.5 9 1 6Z" stroke="currentColor" strokeWidth="1.2"/>
              <circle cx="6" cy="6" r="1.5" stroke="currentColor" strokeWidth="1.2"/>
              <path d="M1 1L11 11" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
            </svg>
          ) : (
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <path d="M1 6C2.5 3 4.5 2 6 2s3.5 1 5 4c-1.5 3-3.5 4-5 4S2.5 9 1 6Z" stroke="currentColor" strokeWidth="1.2"/>
              <circle cx="6" cy="6" r="1.5" stroke="currentColor" strokeWidth="1.2"/>
            </svg>
          )}
          {masked ? "Masked" : "Visible"}
        </button>
      </div>

      {/* ── Empty state ──────────────────────────────────────────────── */}
      {sorted.length === 0 && !loading && (
        <div className="py-16 text-center">
          <div className="text-4xl mb-3 opacity-20">◈</div>
          <div className="text-sm font-medium text-[#8A8072] mb-1">
            {filter === "all" ? "No applications yet" : "No applications match this filter"}
          </div>
          <div className="text-xs text-[#8A8072]/70">
            {filter === "all"
              ? "Submit an application via POST /applications to get started."
              : <button onClick={() => setFilter("all")} className="text-[#C48A2A] hover:underline">Show all applications</button>
            }
          </div>
        </div>
      )}

      {/* ── Table ────────────────────────────────────────────────────── */}
      {sorted.length > 0 && (
        <table className="w-full border-collapse text-sm" aria-label="Application queue">
          <thead>
            <tr className="border-b border-[#D6D0C4]">
              <th className={thCls} onClick={() => toggleSort("created_at")}>
                Application <SortIndicator col="created_at" />
              </th>
              <th className={thCls} onClick={() => toggleSort("composite_score")}>
                Score <SortIndicator col="composite_score" />
              </th>
              <th className={`${thCls} cursor-default`}>Band</th>
              <th className={thCls} onClick={() => toggleSort("status")}>
                Status <SortIndicator col="status" />
              </th>
              <th className={`${thCls} cursor-default`}>Age</th>
              <th className={`${thCls} cursor-default`}>Flags</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((item) => {
              const isFairFail = item.status === "flag_fairness_fail";
              const isPending  = item.status === "pending_human_review" || isFairFail;
              return (
                <tr
                  key={item.application_id}
                  onClick={() => navigate(`/applications/${item.application_id}`)}
                  className={`border-b border-[#D6D0C4] cursor-pointer transition-colors group
                    ${isFairFail ? "bg-[#8C3B2E]/3 hover:bg-[#8C3B2E]/8" : "hover:bg-[#F2EFE8]"}
                    ${isPending ? "" : "opacity-75"}`}
                  aria-label={`Open application ${item.application_id}`}
                >
                  {/* Application ID */}
                  <td className={tdCls}>
                    <span className="font-mono text-sm font-medium text-[#12213A] group-hover:text-[#C48A2A] transition-colors">
                      {maskId(item.application_id)}
                    </span>
                  </td>

                  {/* Score */}
                  <td className={tdCls}>
                    <div className="flex items-center gap-2" data-numeric>
                      <div className="w-20 h-1.5 bg-[#D6D0C4] rounded-full overflow-hidden flex-shrink-0">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${Math.round(item.composite_score * 100)}%`,
                            background: item.band === "approve" ? "#3A6B4C" : item.band === "refer" ? "#C48A2A" : "#8C3B2E",
                          }}
                        />
                      </div>
                      <span className="text-sm font-semibold tabular-nums text-[#12213A]">
                        {Math.round(item.composite_score * 100)}
                      </span>
                    </div>
                  </td>

                  {/* Band */}
                  <td className={tdCls}>
                    <StatusPill value={item.band} size="sm" />
                  </td>

                  {/* Status */}
                  <td className={tdCls}>
                    <StatusPill value={item.status} size="sm" />
                  </td>

                  {/* Age */}
                  <td className={`${tdCls} text-xs text-[#8A8072] tabular-nums`}>
                    {formatAge(item.created_at)}
                  </td>

                  {/* Flags */}
                  <td className={`${tdCls} text-xs`}>
                    <div className="flex items-center gap-1.5">
                      {!item.fairness_match && (
                        <span
                          className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-[#8C3B2E]/10 text-[#8C3B2E] border border-[#8C3B2E]/20"
                          title="Fairness mismatch"
                        >
                          ⚠ F
                        </span>
                      )}
                      {item.challenger_disagreement && (
                        <span
                          className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-[#C48A2A]/10 text-[#C48A2A] border border-[#C48A2A]/20"
                          title="Challenger model disagrees"
                        >
                          ⚖ C
                        </span>
                      )}
                      {item.fairness_match && !item.challenger_disagreement && (
                        <span className="text-[#3A6B4C]/50 text-[10px]">–</span>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
