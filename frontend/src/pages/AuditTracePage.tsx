/**
 * AuditTracePage — full node-by-node pipeline trace viewer.
 * Spec: UI_UX_DESIGN.md §3.7
 * Implemented fully in task 7; this file is the complete version.
 */
import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";
import type { TraceEntry } from "../api/client";

function TraceTimeline({ entries }: { entries: TraceEntry[] }) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  function toggle(i: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  }

  const NODE_ICONS: Record<string, string> = {
    VERIFY:            "✓",
    EXTRACT:           "⚙",
    SCORE:             "∑",
    FAIRNESS_RECHECK:  "⚖",
    FLAG_FAIRNESS_FAIL: "⚠",
    RECOMMEND:         "◈",
    HUMAN_GATE:        "◉",
    HOLD_FOR_DOCUMENT: "⏸",
    CHALLENGER:        "⚡",
    DRAFT_NOTICE:      "✎",
  };

  return (
    <ol className="relative" aria-label="Pipeline trace timeline">
      {entries.map((entry, i) => {
        const isOpen  = expanded.has(i);
        const { node, timestamp, ...rest } = entry;
        const icon    = NODE_ICONS[node] ?? "·";
        const isLast  = i === entries.length - 1;

        return (
          <li key={i} className="relative pl-10 pb-6">
            {/* Vertical connector line */}
            {!isLast && (
              <div className="absolute left-[18px] top-6 bottom-0 w-px bg-[#D6D0C4]" aria-hidden="true" />
            )}

            {/* Node dot */}
            <div
              className="absolute left-2 top-1 w-6 h-6 rounded-full border border-[#D6D0C4]
                         bg-[#FAF8F3] flex items-center justify-center text-xs font-mono
                         text-[#12213A]"
              aria-hidden="true"
            >
              {icon}
            </div>

            {/* Node header */}
            <button
              className="w-full text-left focus:outline-none group"
              onClick={() => toggle(i)}
              aria-expanded={isOpen}
              aria-controls={`trace-detail-${i}`}
            >
              <div className="flex items-baseline gap-3">
                <span className="font-mono text-sm font-semibold text-[#12213A]">{node}</span>
                <span className="text-xs text-[#8A8072] tabular-nums" data-numeric>
                  {new Date(timestamp).toLocaleTimeString(undefined, { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit", fractionalSecondDigits: 3 })}
                </span>
                <span className="ml-auto text-xs text-[#C48A2A] group-hover:underline">
                  {isOpen ? "▲ collapse" : "▼ expand"}
                </span>
              </div>
            </button>

            {/* Expandable JSON detail */}
            {isOpen && (
              <pre
                id={`trace-detail-${i}`}
                className="mt-2 text-xs font-mono bg-[#12213A] text-[#FAF8F3]/90
                           rounded-sm px-4 py-3 overflow-x-auto leading-relaxed"
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

export default function AuditTracePage() {
  const { id }  = useParams<{ id: string }>();

  const [trace,   setTrace]   = useState<TraceEntry[]>([]);
  const [appId,   setAppId]   = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) {
      // Audit home — no specific application
      setLoading(false);
      return;
    }
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
    const a   = document.createElement("a");
    a.href     = url;
    a.download = `trace-${appId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // No application in context — show instructions
  if (!id) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <h1 className="font-serif text-2xl text-[#12213A] mb-3">Audit Trace</h1>
        <p className="text-sm text-[#8A8072]">
          Open an application from the{" "}
          <Link to="/" className="text-[#C48A2A] hover:underline">queue</Link>
          , then click "View full audit trace" to inspect the pipeline execution.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-baseline justify-between mb-6">
        <div>
          <Link to={`/applications/${id}`} className="text-xs text-[#8A8072] hover:text-[#12213A] mb-1 inline-block">
            ← Application {appId || id}
          </Link>
          <h1 className="font-serif text-2xl text-[#12213A]">Audit Trace</h1>
        </div>
        {trace.length > 0 && (
          <button
            onClick={downloadTrace}
            className="px-3 py-1.5 text-xs font-medium border border-[#D6D0C4] rounded-sm
                       text-[#8A8072] hover:border-[#12213A] hover:text-[#12213A] transition-colors
                       focus:outline-none focus:ring-1 focus:ring-[#C48A2A]"
            aria-label="Export trace as JSON"
          >
            ↓ Export JSON
          </button>
        )}
      </div>

      {loading && (
        <div className="py-12 text-center text-sm text-[#8A8072]">Loading trace…</div>
      )}

      {error && (
        <div className="text-sm text-[#8C3B2E] bg-[#8C3B2E]/5 border border-[#8C3B2E]/30 rounded-sm px-3 py-2 mb-4" role="alert">
          {error}
        </div>
      )}

      {!loading && trace.length === 0 && !error && (
        <div className="py-12 text-center text-sm text-[#8A8072]">
          No trace data available for this application.
        </div>
      )}

      {trace.length > 0 && (
        <div className="ledger-card">
          <div className="section-label mb-4">Pipeline execution — {trace.length} nodes</div>
          <TraceTimeline entries={trace} />
        </div>
      )}
    </div>
  );
}
