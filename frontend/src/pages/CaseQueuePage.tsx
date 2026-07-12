/**
 * CaseQueuePage — home screen showing all pending/recent applications.
 * Per UI_UX_DESIGN.md §3.1.
 */
import { useEffect, useState, useCallback } from "react";
import { api } from "../api/client";
import type { QueueItem } from "../api/client";
import QueueTable from "../components/QueueTable";

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

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Page header */}
      <div className="flex items-baseline justify-between mb-6">
        <div>
          <h1 className="font-serif text-2xl text-[#12213A]">Application Queue</h1>
          <p className="text-sm text-[#8A8072] mt-1">
            {loading ? "Loading…" : `${items.length} application${items.length !== 1 ? "s" : ""}`}
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="text-xs text-[#8A8072] border border-[#D6D0C4] px-3 py-1.5 rounded-sm
                     hover:border-[#12213A] hover:text-[#12213A] transition-colors
                     disabled:opacity-40 focus:outline-none focus:ring-1 focus:ring-[#C48A2A]"
          aria-label="Refresh queue"
        >
          ↻ Refresh
        </button>
      </div>

      {error && (
        <div
          className="mb-4 p-3 text-sm text-[#8C3B2E] bg-[#8C3B2E]/5 border border-[#8C3B2E]/30 rounded-sm"
          role="alert"
        >
          {error}
          <button onClick={load} className="ml-3 underline text-[#8C3B2E] hover:no-underline">
            Retry
          </button>
        </div>
      )}

      <QueueTable items={items} loading={loading} />
    </div>
  );
}
