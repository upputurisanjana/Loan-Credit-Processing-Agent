/**
 * DashboardPage — reviewer overview with metrics, pipeline breakdown,
 * decision distribution, and recent activity feed.
 */
import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { QueueItem, Band, AppStatus } from "../api/client";

// ── Metric card ───────────────────────────────────────────────────────────

function MetricCard({
  label, value, sub, icon, color = "blue",
}: {
  label: string; value: string | number; sub?: string;
  icon: React.ReactNode; color?: "blue" | "green" | "amber" | "red" | "slate";
}) {
  const bg  = { blue: "bg-blue-50",   green: "bg-green-50",  amber: "bg-amber-50",  red: "bg-red-50",   slate: "bg-slate-100" }[color];
  const ic  = { blue: "text-blue-600", green: "text-green-600", amber: "text-amber-600", red: "text-red-600", slate: "text-slate-500" }[color];
  const val = { blue: "text-blue-700", green: "text-green-700", amber: "text-amber-700", red: "text-red-700",  slate: "text-slate-700" }[color];
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex items-start gap-4">
      <div className={`w-10 h-10 rounded-lg ${bg} flex items-center justify-center flex-shrink-0`}>
        <span className={ic}>{icon}</span>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">{label}</p>
        <p className={`text-3xl font-bold tabular-nums leading-none ${val}`}>{value}</p>
        {sub && <p className="text-xs text-slate-400 mt-1.5">{sub}</p>}
      </div>
    </div>
  );
}

// ── Mini bar chart ────────────────────────────────────────────────────────

function BarChart({ data }: { data: { label: string; value: number; color: string }[] }) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div className="space-y-3">
      {data.map((d) => (
        <div key={d.label} className="flex items-center gap-3">
          <span className="text-xs text-slate-500 w-32 flex-shrink-0">{d.label}</span>
          <div className="flex-1 h-5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${d.color}`}
              style={{ width: `${(d.value / max) * 100}%` }}
            />
          </div>
          <span className="text-sm font-semibold text-slate-700 tabular-nums w-8 text-right">{d.value}</span>
        </div>
      ))}
    </div>
  );
}

// ── Donut chart (CSS-based) ───────────────────────────────────────────────

function DonutChart({ approve, refer, decline, total }: { approve: number; refer: number; decline: number; total: number }) {
  if (total === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-slate-300 text-sm">No data yet</div>
    );
  }
  const approveP = Math.round((approve / total) * 100);
  const referP   = Math.round((refer   / total) * 100);
  const declineP = 100 - approveP - referP;

  // CSS conic-gradient donut
  const gradient = `conic-gradient(#16a34a 0% ${approveP}%, #d97706 ${approveP}% ${approveP + referP}%, #dc2626 ${approveP + referP}% 100%)`;

  return (
    <div className="flex items-center gap-6">
      <div className="relative w-24 h-24 flex-shrink-0">
        <div
          className="w-24 h-24 rounded-full"
          style={{ background: gradient }}
          aria-hidden="true"
        />
        {/* Hole */}
        <div className="absolute inset-3 bg-white rounded-full flex items-center justify-center">
          <span className="text-xs font-bold text-slate-700 tabular-nums">{total}</span>
        </div>
      </div>
      <div className="space-y-2 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-600 flex-shrink-0" />
          <span className="text-slate-600">Approve</span>
          <span className="ml-auto font-semibold text-slate-800 tabular-nums">{approve} <span className="text-slate-400">({approveP}%)</span></span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-amber-600 flex-shrink-0" />
          <span className="text-slate-600">Refer</span>
          <span className="ml-auto font-semibold text-slate-800 tabular-nums">{refer} <span className="text-slate-400">({referP}%)</span></span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-600 flex-shrink-0" />
          <span className="text-slate-600">Decline</span>
          <span className="ml-auto font-semibold text-slate-800 tabular-nums">{decline} <span className="text-slate-400">({declineP}%)</span></span>
        </div>
      </div>
    </div>
  );
}

// ── Recent activity feed ──────────────────────────────────────────────────

function ActivityFeed({ items }: { items: QueueItem[] }) {
  const navigate = useNavigate();
  const recent = [...items]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 8);

  const statusIcon: Record<AppStatus, string> = {
    pending_human_review: "🟡",
    decided:              "✅",
    awaiting_information: "🔵",
    hold_for_document:    "🟠",
    flag_fairness_fail:   "🔴",
    error:                "⚠️",
  };

  if (recent.length === 0) {
    return <p className="text-sm text-slate-400 py-4 text-center">No applications yet.</p>;
  }

  return (
    <div className="divide-y divide-slate-50">
      {recent.map((item) => (
        <div
          key={item.application_id}
          className="flex items-center gap-3 py-3 hover:bg-slate-50 rounded-lg px-2 cursor-pointer transition-colors"
          onClick={() => navigate(`/applications/${item.application_id}`)}
        >
          <span className="text-base flex-shrink-0" aria-hidden="true">{statusIcon[item.status]}</span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-slate-800 font-mono">{item.application_id}</p>
            <p className="text-xs text-slate-500 truncate">{item.applicant_name || "—"}</p>
          </div>
          <div className="text-right flex-shrink-0">
            {item.composite_score != null && (
              <p className="text-sm font-bold tabular-nums text-slate-700">
                {Math.round(item.composite_score * 100)}
                <span className="text-xs font-normal text-slate-400">/100</span>
              </p>
            )}
            <p className="text-[10px] text-slate-400 tabular-nums">
              {new Date(item.created_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short" })}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Score distribution ────────────────────────────────────────────────────

function ScoreDistribution({ items }: { items: QueueItem[] }) {
  const decided = items.filter((i) => i.composite_score != null);
  const buckets = [
    { label: "0 – 25",  color: "bg-red-500",    count: 0 },
    { label: "26 – 50", color: "bg-orange-400",  count: 0 },
    { label: "51 – 64", color: "bg-amber-400",   count: 0 },
    { label: "65 – 74", color: "bg-yellow-400",  count: 0 },
    { label: "75 – 100",color: "bg-green-500",   count: 0 },
  ];
  for (const item of decided) {
    const s = Math.round((item.composite_score ?? 0) * 100);
    if      (s <= 25)  buckets[0].count++;
    else if (s <= 50)  buckets[1].count++;
    else if (s <= 64)  buckets[2].count++;
    else if (s <= 74)  buckets[3].count++;
    else               buckets[4].count++;
  }
  return <BarChart data={buckets.map((b) => ({ label: b.label, value: b.count, color: b.color }))} />;
}

// ── Pipeline stage breakdown ──────────────────────────────────────────────

function PipelineBreakdown({ items }: { items: QueueItem[] }) {
  const counts: Record<string, number> = {};
  for (const item of items) {
    counts[item.status] = (counts[item.status] ?? 0) + 1;
  }
  const stages = [
    { label: "Pending Review",  key: "pending_human_review", color: "bg-amber-400" },
    { label: "Decided",         key: "decided",              color: "bg-green-500" },
    { label: "Awaiting Info",   key: "awaiting_information", color: "bg-blue-500"  },
    { label: "Hold – Docs",     key: "hold_for_document",    color: "bg-orange-400"},
    { label: "Needs Review",    key: "flag_fairness_fail",   color: "bg-red-500"   },
    { label: "Error",           key: "error",                color: "bg-slate-400" },
  ].map((s) => ({ ...s, value: counts[s.key] ?? 0 }))
   .filter((s) => s.value > 0);

  if (stages.length === 0) return <p className="text-sm text-slate-400 py-4 text-center">No data yet.</p>;
  return <BarChart data={stages} />;
}

// ── Main page ─────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [items, setItems]     = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try { setItems(await api.getQueue()); }
    catch { /* silent — dashboard degrades gracefully */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const total      = items.length;
  const pending    = items.filter((i) => i.status === "pending_human_review" || i.status === "flag_fairness_fail" || i.status === "awaiting_information").length;
  const decided    = items.filter((i) => i.status === "decided").length;
  const holds      = items.filter((i) => i.status === "hold_for_document").length;
  const avgScore   = items.filter((i) => i.composite_score != null).length > 0
    ? Math.round(items.filter((i) => i.composite_score != null).reduce((s, i) => s + (i.composite_score ?? 0), 0) / items.filter((i) => i.composite_score != null).length * 100)
    : null;

  const decidedItems = items.filter((i) => i.human_decision != null);
  const approveCount = decidedItems.filter((i) => i.human_decision === "approve").length;
  const referCount   = decidedItems.filter((i) => i.human_decision === "refer").length;
  const declineCount = decidedItems.filter((i) => i.human_decision === "decline").length;

  const agentApprove  = items.filter((i) => i.agent_recommendation === "approve").length;
  const agentRefer    = items.filter((i) => i.agent_recommendation === "refer").length;
  const agentDecline  = items.filter((i) => i.agent_recommendation === "decline").length;

  if (loading) {
    return (
      <div className="px-8 py-6 max-w-screen-xl mx-auto">
        <div className="h-8 bg-slate-100 animate-pulse rounded w-64 mb-6" />
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[...Array(4)].map((_, i) => <div key={i} className="h-24 bg-slate-100 animate-pulse rounded-xl" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="px-8 py-6 max-w-screen-xl mx-auto space-y-6">

      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 tracking-tight">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Overview of your credit decisioning pipeline
          </p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-200 rounded-md text-slate-600 bg-white hover:bg-slate-50 transition-colors"
        >
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
            <path d="M11 6.5A4.5 4.5 0 1 1 6.5 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            <path d="M6.5 1L8.5 3L6.5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Refresh
        </button>
      </div>

      {/* ── Metric cards ────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Total Applications" value={total} sub="all time"
          color="blue" icon={
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><rect x="2" y="3" width="14" height="2" rx="1" fill="currentColor"/><rect x="2" y="8" width="10" height="2" rx="1" fill="currentColor"/><rect x="2" y="13" width="12" height="2" rx="1" fill="currentColor"/></svg>
          } />
        <MetricCard label="Pending Review" value={pending} sub="awaiting underwriter"
          color="amber" icon={
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="9" r="7" stroke="currentColor" strokeWidth="1.5"/><path d="M9 5V9L11.5 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
          } />
        <MetricCard label="Decided" value={decided} sub={`${approveCount} approved · ${declineCount} declined`}
          color="green" icon={
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="9" r="7" stroke="currentColor" strokeWidth="1.5"/><path d="M5.5 9L7.5 11L12.5 6.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
          } />
        <MetricCard label="Avg. Score" value={avgScore != null ? `${avgScore}/100` : "—"} sub="across all applications"
          color="slate" icon={
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M2 13L6 8L9 11L12 6L16 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
          } />
      </div>

      {/* ── Charts row ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Human decision distribution */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">Human Decision Distribution</h3>
          <DonutChart
            approve={approveCount}
            refer={referCount}
            decline={declineCount}
            total={decidedItems.length}
          />
        </div>

        {/* Agent recommendation distribution */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">Agent Recommendations</h3>
          <BarChart data={[
            { label: "Approve", value: agentApprove, color: "bg-green-500" },
            { label: "Refer",   value: agentRefer,   color: "bg-amber-400" },
            { label: "Decline", value: agentDecline, color: "bg-red-500"   },
          ]} />
          {items.length > 0 && (
            <p className="text-xs text-slate-400 mt-4 pt-3 border-t border-slate-100">
              Pipeline: Verify → Extract → Score → Recommend → Human Gate
            </p>
          )}
        </div>

        {/* Score distribution */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">Score Distribution</h3>
          <ScoreDistribution items={items} />
          <p className="text-xs text-slate-400 mt-4 pt-3 border-t border-slate-100">
            Approve ≥75 · Refer ≥65 · Decline &lt;65
          </p>
        </div>
      </div>

      {/* ── Bottom row ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {/* Pipeline status breakdown */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">Pipeline Status Breakdown</h3>
          <PipelineBreakdown items={items} />
        </div>

        {/* Recent activity */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-700">Recent Activity</h3>
            <span className="text-xs text-slate-400">Click to review</span>
          </div>
          <ActivityFeed items={items} />
        </div>
      </div>

      {/* ── Policy info ──────────────────────────────────────────────── */}
      <div className="bg-gradient-to-r from-slate-900 to-blue-900 rounded-xl p-5 text-white">
        <div className="flex flex-wrap items-start gap-8">
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Pipeline</p>
            <p className="text-sm font-mono text-slate-200">
              VERIFY → EXTRACT → SCORE → FAIRNESS → RECOMMEND → HUMAN GATE
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Policy</p>
            <p className="text-sm text-slate-200">v1.2 · DTI 40% · Credit History 35% · Income Stability 25%</p>
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Guarantee</p>
            <p className="text-sm text-slate-200">No decision is ever auto-finalised — all require underwriter approval</p>
          </div>
        </div>
      </div>

    </div>
  );
}
