/**
 * AuditTracePage — full node-by-node pipeline trace viewer.
 * Professional timeline with collapsible detail nodes.
 */
import { useEffect, useState, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { TraceEntry } from "../api/client";

const NODE_ICONS: Record<string, { icon: string; color: string }> = {
  VERIFY:             { icon: "✓", color: "#3A6B4C" },
  EXTRACT:            { icon: "⚙", color: "#12213A" },
  SCORE:              { icon: "∑", color: "#12213A" },
  FAIRNESS_RECHECK:   { icon: "⚖", color: "#C48A2A" },
  FLAG_FAIRNESS_FAIL: { icon: "⚠", color: "#8C3B2E" },
  RECOMMEND:          { icon: "◈", color: "#12213A" },
  HUMAN_GATE:         { icon: "◉", color: "#3A6B4C" },
  HOLD_FOR_DOCUMENT:  { icon: "⏸", color: "#C48A2A" },
  CHALLENGER:         { icon: "⚡", color: "#C48A2A" },
  DRAFT_NOTICE:       { icon: "✎", color: "#8A8072" },
};

function TraceTimeline({ entries }: { entries: TraceEntry[] }) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  function toggle(i: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  }

  return (
    <ol className="relative" aria-label="Pipeline execution timeline">
      {entries.map((entry, i) => {
        const isOpen = expanded.has(i);
        const { node, timestamp, ...rest } = entry;
        const isLast = i === entries.length - 1;
        const nodeMeta = NODE_ICONS[node] ?? { icon: "·", color: "#8A8072" };
        const hasError = "error" in rest;

        return (
          <li key={i} className="relative pl-12 pb-5">
            {/* Connector line */}
            {!isLast && (
              <div
                className="absolute left-[22px] top-7 bottom-0 w-px bg-[#D6D0C4]"
                aria-hidden="true"
              />
            )}

            {/* Node dot */}
            <div
              className="absolute left-3 top-1 w-8 h-8 rounded-full border-2 border-white shadow-sm
                         flex items-center justify-center text-xs font-bold"
              style={{
                background: `${nodeMeta.color}15`,
                color: nodeMeta.color,
                borderColor: `${nodeMeta.color}25`,
                boxShadow: `0 0 0 1px ${nodeMeta.color}30`,
              }}
              aria-hidden="true"
            >
              {nodeMeta.icon}
            </div>

            {/* Node header */}
            <button
              className="w-full text-left focus:outline-none group"
              onClick={() => toggle(i)}
              aria-expanded={isOpen}
              aria-controls={`trace-${i}`}
            >
              <div className="flex items-center gap-3">
                <span className="font-mono text-sm font-bold text-[#12213A]">{node}</span>
                {hasError && (
                  <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-[#8C3B2E]/10 text-[#8C3B2E] border border-[#8C3B2E]/20">
                    ERROR
                  </span>
                )}
                <span className="text-xs text-[#8A8072] tabular-nums ml-auto">
                  {new Date(timestamp).toLocaleTimeString(undefined, {
                    hour12: false,
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                    fractionalSecondDigits: 3 as 3,
                  })}
                </span>
                <span className="text-[10px] text-[#C48A2A] group-hover:underline ml-2">
                  {isOpen ? "▲" : "▼"}
                </span>
              </div>
            </button>

            {/* Expandable JSON */}
            {isOpen && (
              <pre
                id={`trace-${i}`}
                className="mt-2 text-xs font-mono bg-[#12213A] text-[#E8E4DC]/90
                           rounded px-4 py-3 overflow-x-auto leading-relaxed"
                role="region"
                aria-label={`${node} trace detail`}
              >
                {JSON.stringify(rest, null, 2)}
              </pre>
            )}
          </li>
        );
      })}
    </ol>
  );
}

// ── Standalone search screen shown when /audit is opened without an ID ──
function AuditSearch() {
  const navigate = useNavigate();
  const [input, setInput] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const id = input.trim();
    if (id) navigate(`/applications/${id}/trace`);
  }

  return (
    <div className="max-w-md mx-auto px-6 py-20">
      <div className="text-4xl mb-5 text-center opacity-10">⏱</div>
      <h1 className="font-serif text-2xl font-bold text-[#12213A] mb-2 text-center">Audit Trace</h1>
      <p className="text-sm text-[#8A8072] text-center mb-8 leading-relaxed">
        Enter an application ID to view its full pipeline execution log, or open
        an application from the{" "}
        <Link to="/" className="text-[#C48A2A] hover:underline">case queue</Link>
        {" "}and click "View full pipeline trace".
      </p>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="APP-001"
          className="flex-1 border border-[#D6D0C4] rounded px-3 py-2 text-sm bg-white
                     text-[#12213A] placeholder-[#8A8072]/60
                     focus:outline-none focus:ring-2 focus:ring-[#C48A2A] focus:border-transparent"
          aria-label="Application ID"
          autoFocus
        />
        <button
          type="submit"
          disabled={!input.trim()}
          className="px-4 py-2 text-sm font-semibold rounded border border-[#12213A]
                     text-[#12213A] hover:bg-[#12213A] hover:text-white transition-colors
                     focus:outline-none focus:ring-2 focus:ring-[#C48A2A]
                     disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Load trace
        </button>
      </form>
    </div>
  );
}

export default function AuditTracePage() {
  const { id }  = useParams<{ id: string }>();
  const [trace,   setTrace]   = useState<TraceEntry[]>([]);
  const [appId,   setAppId]   = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    try {
      const data = await api.getTrace(id);
      setTrace(data.trace);
      setAppId(data.application_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load trace.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { void load(); }, [load]);

  function downloadTrace() {
    const blob = new Blob([JSON.stringify({ application_id: appId, trace }, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `trace-${appId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ── No application context ──────────────────────────────────────────
  if (!id) {
    return <AuditSearch />;
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">

      {/* ── Header ───────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <Link
            to={`/applications/${id}`}
            className="text-xs text-[#8A8072] hover:text-[#12213A] mb-2 inline-flex items-center gap-1 transition-colors"
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
              <path d="M7 2L3 5L7 8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Application {appId || id}
          </Link>
          <h1 className="font-serif text-2xl font-bold text-[#12213A]">Audit Trace</h1>
          {trace.length > 0 && (
            <p className="text-sm text-[#8A8072] mt-0.5">{trace.length} pipeline nodes executed</p>
          )}
        </div>
        {trace.length > 0 && (
          <button
            onClick={downloadTrace}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium border border-[#D6D0C4]
                       rounded text-[#8A8072] hover:border-[#12213A] hover:text-[#12213A] transition-colors
                       focus:outline-none focus:ring-1 focus:ring-[#C48A2A]"
          >
            <svg width="11" height="11" viewBox="0 0 11 11" fill="none" aria-hidden="true">
              <path d="M5.5 1V7M3 5L5.5 7.5L8 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M1 9H10" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
            </svg>
            Export JSON
          </button>
        )}
      </div>

      {/* ── Loading ──────────────────────────────────────────────────── */}
      {loading && (
        <div className="space-y-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-10 bg-[#F2EFE8] rounded animate-pulse" style={{ opacity: 1 - i * 0.12 }} />
          ))}
        </div>
      )}

      {/* ── Error ────────────────────────────────────────────────────── */}
      {error && (
        <div
          className="text-sm text-[#8C3B2E] bg-[#8C3B2E]/5 border border-[#8C3B2E]/30 rounded px-4 py-3"
          role="alert"
        >
          {error}
        </div>
      )}

      {/* ── Empty ────────────────────────────────────────────────────── */}
      {!loading && !error && trace.length === 0 && (
        <div className="py-16 text-center">
          <div className="text-4xl mb-3 opacity-20">⌛</div>
          <div className="text-sm text-[#8A8072]">No trace data available for this application.</div>
        </div>
      )}

      {/* ── Timeline ─────────────────────────────────────────────────── */}
      {trace.length > 0 && (
        <div className="bg-white border border-[#D6D0C4] rounded overflow-hidden">
          <div className="px-5 py-3 border-b border-[#D6D0C4] bg-[#FAF8F3]">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-[#8A8072]">
              Pipeline execution
            </div>
          </div>
          <div className="px-5 py-5">
            <TraceTimeline entries={trace} />
          </div>
        </div>
      )}
    </div>
  );
}
