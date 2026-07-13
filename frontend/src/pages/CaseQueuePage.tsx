/**
 * CaseQueuePage — home screen showing all pending/recent applications.
 * Professional layout with summary stats, filter controls, and queue table.
 */
import { useEffect, useState, useCallback } from "react";
import { api } from "../api/client";
import type { QueueItem } from "../api/client";
import QueueTable from "../components/QueueTable";

function StatCard({ label, value, sub, accent }: {
  label: string;
  value: number | string;
  sub?: string;
  accent?: "green" | "amber" | "red" | "neutral";
}) {
  const colorMap = {
    green:   "text-[#3A6B4C]",
    amber:   "text-[#C48A2A]",
    red:     "text-[#8C3B2E]",
    neutral: "text-[#12213A]",
  };
  const color = colorMap[accent ?? "neutral"];
  return (
    <div className="bg-white border border-[#D6D0C4] rounded p-4 flex flex-col gap-1">
      <div className="text-[10px] font-semibold uppercase tracking-widest text-[#8A8072]">{label}</div>
      <div className={`font-serif text-3xl font-bold tabular-nums leading-none ${color}`}>{value}</div>
      {sub && <div className="text-[10px] text-[#8A8072]">{sub}</div>}
    </div>
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

  // Derived stats
  const pending    = items.filter((i) => i.status === "pending_human_review" || i.status === "flag_fairness_fail").length;
  const decided    = items.filter((i) => i.status === "decided").length;
  const fairFlags  = items.filter((i) => !i.fairness_match).length;
  const chalFlags  = items.filter((i) => i.challenger_disagreement).length;

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">

      {/* ── Page header ─────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-serif text-2xl font-bold text-[#12213A]">Application Queue</h1>
          <p className="text-sm text-[#8A8072] mt-0.5">
            Human-gated credit decisioning · underwriter review required
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-2 text-xs font-medium
                     border border-[#D6D0C4] rounded text-[#8A8072]
                     hover:border-[#12213A] hover:text-[#12213A] transition-colors
                     disabled:opacity-40 focus:outline-none focus:ring-1 focus:ring-[#C48A2A]"
          aria-label="Refresh queue"
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
            <path d="M10 6A4 4 0 1 1 6 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            <path d="M6 1L8 3L6 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Refresh
        </button>
      </div>

      {/* ── Stats cards ─────────────────────────────────────────────── */}
      {!loading && items.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <StatCard label="Total" value={items.length} sub="all applications" accent="neutral" />
          <StatCard label="Pending review" value={pending} sub="awaiting underwriter" accent="amber" />
          <StatCard label="Decided" value={decided} sub="completed" accent="green" />
          <StatCard
            label="Flags"
            value={fairFlags + chalFlags}
            sub={`${fairFlags} fairness · ${chalFlags} challenger`}
            accent={fairFlags + chalFlags > 0 ? "red" : "neutral"}
          />
        </div>
      )}

      {/* ── Error state ─────────────────────────────────────────────── */}
      {error && (
        <div
          className="mb-5 p-4 flex items-center gap-3 text-sm text-[#8C3B2E]
                     bg-[#8C3B2E]/5 border border-[#8C3B2E]/30 rounded"
          role="alert"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" className="flex-shrink-0">
            <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5"/>
            <path d="M8 4.5V8.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            <circle cx="8" cy="11" r="0.75" fill="currentColor"/>
          </svg>
          <span className="flex-1">{error}</span>
          <button
            onClick={load}
            className="px-3 py-1 text-xs border border-[#8C3B2E]/40 rounded hover:bg-[#8C3B2E]/10 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* ── Queue table ─────────────────────────────────────────────── */}
      <div className="bg-white border border-[#D6D0C4] rounded overflow-hidden">
        {/* Table header bar */}
        <div className="px-4 py-3 border-b border-[#D6D0C4] flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-widest text-[#8A8072]">
            Applications
          </span>
          {!loading && (
            <span className="text-xs text-[#8A8072] tabular-nums">
              {items.length} record{items.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
        <div className="px-4 pb-4 pt-3">
          <QueueTable items={items} loading={loading} />
        </div>
      </div>
    </div>
  );
}
