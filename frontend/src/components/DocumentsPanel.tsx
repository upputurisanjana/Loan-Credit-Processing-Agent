/**
 * DocumentsPanel — read-only list of uploaded documents for the reviewer.
 * Shows doc type, filename, size, upload date, and a download link.
 */
import { useEffect, useState, useCallback } from "react";
import { api } from "../api/client";
import type { DocumentMeta } from "../api/client";

const DOC_ICON: Record<string, string> = {
  id:             "🪪",
  pay_stub:       "💰",
  bank_statement: "🏦",
  other:          "📄",
};

interface Props {
  applicationId: string;
}

export default function DocumentsPanel({ applicationId }: Props) {
  const [docs, setDocs]       = useState<DocumentMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await api.listDocuments(applicationId);
      setDocs(res.documents);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load documents.");
    } finally {
      setLoading(false);
    }
  }, [applicationId]);

  useEffect(() => { void load(); }, [load]);

  if (loading) return <div className="text-xs text-slate-400 py-3 animate-pulse">Loading documents…</div>;
  if (error)   return <div className="text-xs text-red-500 py-2" role="alert">{error}</div>;

  if (docs.length === 0) {
    return (
      <div className="text-center py-6 text-sm text-slate-400">
        No documents uploaded for this application.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {docs.map((doc) => (
        <div
          key={doc.filename}
          className="flex items-center gap-3 px-4 py-3 border border-slate-200 rounded-lg bg-slate-50/50 hover:bg-white transition-colors"
        >
          {/* Icon */}
          <span className="text-xl flex-shrink-0" aria-hidden="true">
            {DOC_ICON[doc.doc_type] ?? "📄"}
          </span>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-slate-800">{doc.doc_type_label}</p>
            <p className="text-xs text-slate-400 truncate">
              {doc.filename}
              {" · "}
              {(doc.size_bytes / 1024).toFixed(1)} KB
              {" · "}
              {new Date(doc.uploaded_at).toLocaleDateString("en-GB", {
                day: "2-digit", month: "short", year: "numeric",
              })}
            </p>
          </div>

          {/* Download link */}
          <a
            href={api.getDocumentUrl(applicationId, doc.filename)}
            target="_blank"
            rel="noreferrer"
            className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 transition-colors"
            aria-label={`Open ${doc.doc_type_label}`}
          >
            <svg width="11" height="11" viewBox="0 0 11 11" fill="none" aria-hidden="true">
              <path d="M5.5 1V7.5M5.5 7.5L3 5M5.5 7.5L8 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M1 9H10" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
            </svg>
            Open
          </a>
        </div>
      ))}
    </div>
  );
}
