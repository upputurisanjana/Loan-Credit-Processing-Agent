/**
 * QueuePage — reviewer home: stat cards + rich application queue table.
 */
import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { QueueItem, AppStatus, Band } from "../api/client";

// ── Status badge ──────────────────────────────────────────────────────────

const STATUS_MAP: Record<AppStatus, { label: string; cls: string }> = {
  pending_human_review: { label: "Pending Review",  cls: "bg-amber-100 text-amber-700 border-amber-200" },
  decided:              { label: "Decided",          cls: "bg-green-100 text-green-700 border-green-200" },
  awaiting_information: { label: "Awaiting Info",   cls: "bg-blue-100  text-blue-700  border-blue-200"  },
  hold_for_document:    { label: "Hold – Docs",      cls: "bg-orange-100 text-orange-700 border-orange-200" },
  flag_fairness_fail:   { label: "Needs Review",     cls: "bg-red-100   text-red-700   border-red-200"   },
  error:                { label: "Error",             cls: "bg-slate-100 text-slate-500 border-slate-200" },
};

function StatusBadge({ status }: { status: AppStatus }) {
  const { label, cls } = STATUS_MAP[status] ?? { label: status, cls: "bg-slate-100 text-slate-500 border-slate-200" };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border ${cls}`}>
      {label}
    </span>
  );
}

function BandBadge({ band }: { band: Band | null | undefined }) {
  if (!band) return <span className="text-slate-300 text-xs">—</span>;
  const cls: Record<Band, string> = {
    approve: "text-green-600 font-semibold",
    refer:   "text-amber-600 font-semibold",
    decline: "text-red-600   font-semibold",
  };
  return <span className={`text-xs capitalize ${cls[band]}`}>{band}</span>;
}

function ScoreMini({ score }: { score: number | null }) {
  if (score === null) return <span className="text-slate-300 text-xs">—</span>;
  const pct   = Math.round(score * 100);
  const color = pct >= 75 ? "bg-green-500" : pct >= 65 ? "bg-amber-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-600 tabular-nums">{pct}</span>
    </div>
  );
}

function StatCard({
  label, value, sub, variant = "default",
}: { label: string; value: number | string; sub?: string; variant?: "default" | "warning" | "success" | "danger" }) {
  const vColor = { default: "text-slate-900", warning: "text-amber-600", success: "text-green-600", danger: "text-red-600" }[variant];
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">{label}</p>
      <p className={`text-3xl font-bold tabular-nums leading-none ${vColor}`}>{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1.5">{sub}</p>}
    </div>
  );
}

// ── Row highlight by status ───────────────────────────────────────────────

function rowCls(status: AppStatus): string {
  if (status === "flag_fairness_fail") return "border-b border-red-100 bg-red-50/30 hover:bg-red-50/60";
  if (status === "pending_human_review") return "border-b border-slate-100 hover:bg-blue-50/40";
  if (status === "decided") return "border-b border-slate-50 bg-slate-50/40 hover:bg-slate-100/50";
  if (status === "awaiting_information") return "border-b border-amber-100 bg-amber-50/20 hover:bg-amber-50/50";
  return "border-b border-slate-100 hover:bg-slate-50";
}

// ── Main ──────────────────────────────────────────────────────────────────

export default function QueuePage() {
  const navigate = useNavigate();
  const [items, setItems]     = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { setItems(await api.getQueue()); }
    catch (e) { setError(e instanceof Error ? e.message : "Failed to load queue."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const pending  = items.filter((i) => ["pending_human_review", "flag_fairness_fail", "awaiting_information"].includes(i.status)).length;
  const decided  = items.filter((i) => i.status === "decided").length;
  const holds    = items.filter((i) => i.status === "hold_for_document").length;

  return (
    <div className="px-8 py-6 max-w-screen-xl mx-auto">

      {/* ── Page header ──────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 tracking-tight">Application Queue</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Human-gated credit decisioning · every application requires underwriter review
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-200 rounded-md
                     text-slate-600 bg-white hover:bg-slate-50 disabled:opacity-50 transition-colors"
        >
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
            <path d="M11 6.5A4.5 4.5 0 1 1 6.5 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            <path d="M6.5 1L8.5 3L6.5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Refresh
        </button>
      </div>

      {/* ── Stat cards ───────────────────────────────────────────────── */}
      {!loading && items.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          <StatCard label="Total"          value={items.length}  sub="all applications"      />
          <StatCard label="Pending Review" value={pending}       sub="awaiting underwriter"  variant="warning" />
          <StatCard label="Decided"        value={decided}       sub="completed"             variant="success" />
          <StatCard label="On Hold"        value={holds}         sub="docs missing"          variant={holds > 0 ? "danger" : "default"} />
        </div>
      )}

      {/* ── Error ────────────────────────────────────────────────────── */}
      {error && (
        <div className="mb-5 flex items-center gap-3 p-3.5 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg" role="alert">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="flex-shrink-0" aria-hidden="true">
            <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5"/>
            <path d="M8 5V9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            <circle cx="8" cy="11.5" r="0.75" fill="currentColor"/>
          </svg>
          <span className="flex-1">{error}</span>
          <button onClick={load} className="text-xs font-semibold hover:underline">Retry</button>
        </div>
      )}

      {/* ── Queue table ──────────────────────────────────────────────── */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        {/* Panel header */}
        <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/60">
          <h2 className="text-sm font-semibold text-slate-700">Applications</h2>
          {!loading && (
            <span className="text-xs text-slate-400 tabular-nums">
              {items.length} record{items.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        {loading ? (
          <div className="p-8 space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-10 bg-slate-100 rounded animate-pulse" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="p-12 text-center">
            <div className="text-slate-300 text-4xl mb-3">📋</div>
            <p className="text-sm text-slate-500 font-medium">No applications yet</p>
            <p className="text-xs text-slate-400 mt-1">Submit one via the Streamlit applicant portal</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[800px]">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  {[
                    "Application ID", "Applicant", "Loan Amount",
                    "Score", "Agent Rec.", "Status", "Decision", "Submitted",
                  ].map((h) => (
                    <th key={h} className="px-4 py-2.5 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.application_id}
                    className={`cursor-pointer transition-colors ${rowCls(item.status)}`}
                    onClick={() => navigate(`/applications/${item.application_id}`)}
                  >
                    <td className="px-4 py-3 font-mono text-xs font-semibold text-blue-700 whitespace-nowrap">
                      {item.application_id}
                    </td>
                    <td className="px-4 py-3 text-slate-800 font-medium">
                      {item.applicant_name || <span className="text-slate-300">—</span>}
                    </td>
                    <td className="px-4 py-3 text-slate-600 tabular-nums whitespace-nowrap">
                      {item.loan_amount_requested > 0
                        ? `£${item.loan_amount_requested.toLocaleString("en-GB")}`
                        : <span className="text-slate-300">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      <ScoreMini score={item.composite_score} />
                    </td>
                    <td className="px-4 py-3">
                      <BandBadge band={item.agent_recommendation} />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={item.status} />
                    </td>
                    <td className="px-4 py-3">
                      {item.human_decision
                        ? <BandBadge band={item.human_decision} />
                        : <span className="text-slate-300 text-xs">—</span>
                      }
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs tabular-nums whitespace-nowrap">
                      {new Date(item.created_at).toLocaleDateString("en-GB", {
                        day: "2-digit", month: "short", year: "numeric",
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Legend */}
      {items.length > 0 && (
        <div className="flex flex-wrap gap-4 mt-4 text-xs text-slate-400">
          <span>Click any row to open the full review workspace.</span>
          <span className="text-red-400">Red rows = fairness flag raised.</span>
          <span className="text-amber-500">Amber rows = awaiting information.</span>
        </div>
      )}
    </div>
  );
}
