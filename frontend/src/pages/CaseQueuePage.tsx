/**
 * CaseQueuePage — home screen with stat cards + application queue table.
 */
import { useEffect, useState, useCallback } from "react";
import { api } from "../api/client";
import type { QueueItem } from "../api/client";
import QueueTable from "../components/QueueTable";

function StatCard({
  label,
  value,
  sub,
  variant = "default",
}: {
  label: string;
  value: number | string;
  sub?: string;
  variant?: "default" | "warning" | "success" | "danger";
}) {
  const valueColor = {
    default: "text-slate-900",
    warning: "text-amber-600",
    success: "text-green-600",
    danger:  "text-red-600",
  }[variant];

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-card">
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">{label}</p>
      <p className={`text-3xl font-bold tabular-nums leading-none ${valueColor}`}>{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1.5">{sub}</p>}
    </div>
  );
}

function RefreshIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
      <path d="M11 6.5A4.5 4.5 0 1 1 6.5 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M6.5 1L8.5 3L6.5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

export default function CaseQueuePage() {
  const [items, setItems]     = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getQueue();
      setItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load queue.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const pending   = items.filter((i) => i.status === "pending_human_review" || i.status === "flag_fairness_fail").length;
  const decided   = items.filter((i) => i.status === "decided").length;
  const fairFlags = items.filter((i) => !i.fairness_match).length;
  const chalFlags = items.filter((i) => i.challenger_disagreement).length;

  return (
    <div className="px-8 py-6 max-w-6xl mx-auto">

      {/* ── Page header ─────────────────────────────────────────────── */}
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
          className="btn-secondary gap-1.5"
          aria-label="Refresh queue"
        >
          <RefreshIcon />
          Refresh
        </button>
      </div>

      {/* ── Stat cards ─────────────────────────────────────────────── */}
      {!loading && items.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          <StatCard label="Total"          value={items.length}             sub="all applications"       variant="default" />
          <StatCard label="Pending Review" value={pending}                  sub="awaiting underwriter"   variant="warning" />
          <StatCard label="Decided"        value={decided}                  sub="completed"              variant="success" />
          <StatCard
            label="Flags"
            value={fairFlags + chalFlags}
            sub={`${fairFlags} fairness · ${chalFlags} challenger`}
            variant={fairFlags + chalFlags > 0 ? "danger" : "default"}
          />
        </div>
      )}

      {/* ── Error banner ────────────────────────────────────────────── */}
      {error && (
        <div
          className="mb-5 flex items-center gap-3 p-3.5 text-sm text-red-700
                     bg-red-50 border border-red-200 rounded-lg"
          role="alert"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="flex-shrink-0" aria-hidden="true">
            <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5"/>
            <path d="M8 5V9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            <circle cx="8" cy="11.5" r="0.75" fill="currentColor"/>
          </svg>
          <span className="flex-1">{error}</span>
          <button onClick={load} className="text-xs font-medium text-red-700 hover:underline">
            Retry
          </button>
        </div>
      )}

      {/* ── Queue panel ─────────────────────────────────────────────── */}
      <div className="bg-white border border-slate-200 rounded-lg shadow-card overflow-hidden">
        {/* Panel header */}
        <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">Applications</h2>
          {!loading && (
            <span className="text-xs text-slate-400 tabular-nums">
              {items.length} record{items.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
        <div className="p-5">
          <QueueTable items={items} loading={loading} />
        </div>
      </div>
    </div>
  );
}
