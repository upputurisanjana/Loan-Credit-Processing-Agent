/**
 * DocumentList — read-only document viewer for the reviewer (underwriter) workspace.
 *
 * Features:
 * - Lists all uploaded documents with their doc_type label and file info
 * - Reviewer can mark each document as verified ✓ or rejected ✗
 * - Verification status is persisted via PATCH /documents/:filename/verify
 * - Download individual files
 * - Download full PDF report
 *
 * This component intentionally has NO upload functionality — uploading is the
 * applicant's responsibility and is only available on the submission form.
 */
import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { DocumentMeta } from "../api/client";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function FileIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M3 1h5.5L11 3.5V13H3V1Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/>
      <path d="M8.5 1v3H11" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/>
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
      <path d="M6.5 1.5V9M4 6.5l2.5 2.5L9 6.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M1.5 10.5v1h10v-1" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
    </svg>
  );
}

function PDFIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <rect x="1.5" y="1.5" width="11" height="11" rx="1.5" stroke="currentColor" strokeWidth="1.2"/>
      <text x="7" y="9" textAnchor="middle" fontSize="5.5" fontWeight="bold" fill="currentColor">PDF</text>
    </svg>
  );
}

function VerificationBadge({ status }: { status: "pending" | "verified" | "rejected" }) {
  if (status === "verified") {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-green-50 text-green-700 border border-green-200">
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
          <circle cx="5" cy="5" r="4.5" stroke="currentColor" strokeWidth="1"/>
          <path d="M3 5L4.5 6.5L7 4" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        Verified
      </span>
    );
  }
  if (status === "rejected") {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-red-50 text-red-700 border border-red-200">
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
          <circle cx="5" cy="5" r="4.5" stroke="currentColor" strokeWidth="1"/>
          <path d="M3 3L7 7M7 3L3 7" stroke="currentColor" strokeWidth="1" strokeLinecap="round"/>
        </svg>
        Rejected
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
      <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
        <circle cx="5" cy="5" r="4.5" stroke="currentColor" strokeWidth="1"/>
        <path d="M5 2.5V5.5" stroke="currentColor" strokeWidth="1" strokeLinecap="round"/>
        <circle cx="5" cy="7" r="0.5" fill="currentColor"/>
      </svg>
      Pending
    </span>
  );
}

interface DocTypeTagProps {
  label: string;
}

function DocTypeTag({ label }: DocTypeTagProps) {
  return (
    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
      {label}
    </span>
  );
}

interface VerifyFormProps {
  doc: DocumentMeta;
  applicationId: string;
  reviewerId: string;
  onDone: (updated: DocumentMeta) => void;
  onCancel: () => void;
}

function VerifyForm({ doc, applicationId, reviewerId, onDone, onCancel }: VerifyFormProps) {
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(verificationStatus: "verified" | "rejected") {
    if (verificationStatus === "rejected" && !note.trim()) {
      setError("Please provide a reason for rejection.");
      return;
    }
    if (!reviewerId.trim()) {
      setError("Reviewer ID is required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const updated = await api.verifyDocument(applicationId, doc.filename, {
        verification_status: verificationStatus,
        verified_by: reviewerId.trim(),
        verification_note: note.trim() || undefined,
      });
      onDone(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mt-2 p-3 bg-slate-50 border border-slate-200 rounded-md space-y-2">
      <p className="text-xs font-medium text-slate-700">
        Verify <span className="font-semibold">{doc.filename}</span>
      </p>
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Note (required for rejection, optional for verification)"
        rows={2}
        className="w-full text-xs border border-slate-200 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400 resize-none"
      />
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex items-center gap-2">
        <button
          onClick={() => void submit("verified")}
          disabled={submitting}
          className="flex items-center gap-1 px-3 py-1 text-xs font-semibold bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 transition-colors"
        >
          ✓ Verify
        </button>
        <button
          onClick={() => void submit("rejected")}
          disabled={submitting}
          className="flex items-center gap-1 px-3 py-1 text-xs font-semibold bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 transition-colors"
        >
          ✗ Reject
        </button>
        <button
          onClick={onCancel}
          className="px-3 py-1 text-xs text-slate-500 hover:text-slate-700 transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

interface Props {
  applicationId: string;
  reviewerId?: string; // When provided, enables verification controls
}

export default function DocumentList({ applicationId, reviewerId = "" }: Props) {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [loading, setLoading]     = useState(true);
  const [verifyingFile, setVerifyingFile] = useState<string | null>(null);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.listDocuments(applicationId);
      setDocuments(res.documents);
    } catch {
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, [applicationId]);

  useEffect(() => { void loadDocuments(); }, [loadDocuments]);

  const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

  // Summary counts
  const verifiedCount  = documents.filter((d) => d.verification_status === "verified").length;
  const rejectedCount  = documents.filter((d) => d.verification_status === "rejected").length;
  const pendingCount   = documents.filter((d) => d.verification_status === "pending").length;

  if (loading) {
    return (
      <div className="space-y-1.5">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-10 bg-slate-100 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="text-center py-6">
        <p className="text-sm text-slate-400 italic">No documents have been uploaded for this application.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">

      {/* ── Summary strip ───────────────────────────────────────────── */}
      <div className="flex items-center gap-3 text-xs text-slate-500">
        <span>{documents.length} document{documents.length !== 1 ? "s" : ""}</span>
        {verifiedCount > 0 && <span className="text-green-600 font-medium">✓ {verifiedCount} verified</span>}
        {rejectedCount > 0 && <span className="text-red-600 font-medium">✗ {rejectedCount} rejected</span>}
        {pendingCount  > 0 && <span className="text-amber-600 font-medium">? {pendingCount} pending review</span>}
      </div>

      {/* ── Document rows ────────────────────────────────────────────── */}
      <div className="divide-y divide-slate-100 border border-slate-200 rounded-lg overflow-hidden">
        {documents.map((doc) => {
          const downloadUrl = `${BASE_URL}${doc.url}`;
          const isVerifying = verifyingFile === doc.filename;

          return (
            <div key={doc.filename} className="bg-white">
              <div className="flex items-start gap-3 px-4 py-3">
                {/* File icon */}
                <span className="text-slate-400 flex-shrink-0 mt-0.5">
                  <FileIcon />
                </span>

                {/* File info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <p className="text-sm font-medium text-slate-800 truncate">{doc.filename}</p>
                    <DocTypeTag label={doc.doc_type_label} />
                    <VerificationBadge status={doc.verification_status} />
                  </div>
                  <p className="text-[11px] text-slate-400 tabular-nums">
                    {formatBytes(doc.size_bytes)} · {doc.uploaded_at.slice(0, 19).replace("T", " ")} UTC
                  </p>
                  {doc.verification_note && (
                    <p className="text-[11px] text-slate-500 mt-0.5 italic">
                      Note: {doc.verification_note}
                      {doc.verified_by && <span className="not-italic"> — {doc.verified_by}</span>}
                    </p>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  {/* Verify button — only shown to reviewers */}
                  {reviewerId !== undefined && doc.verification_status === "pending" && (
                    <button
                      onClick={() => setVerifyingFile(isVerifying ? null : doc.filename)}
                      className="text-[11px] font-medium text-blue-600 hover:text-blue-800 px-2 py-1 rounded border border-blue-200 hover:border-blue-400 bg-blue-50 hover:bg-blue-100 transition-colors"
                    >
                      Review
                    </button>
                  )}
                  {reviewerId !== undefined && doc.verification_status !== "pending" && (
                    <button
                      onClick={() => setVerifyingFile(isVerifying ? null : doc.filename)}
                      className="text-[11px] font-medium text-slate-500 hover:text-slate-700 px-2 py-1 rounded border border-slate-200 hover:border-slate-300 transition-colors"
                    >
                      Revise
                    </button>
                  )}
                  {/* Download */}
                  <a
                    href={downloadUrl}
                    download={doc.filename}
                    className="flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-800 px-2 py-1 rounded hover:bg-blue-50 transition-colors"
                    aria-label={`Download ${doc.filename}`}
                  >
                    <DownloadIcon />
                    Download
                  </a>
                </div>
              </div>

              {/* Inline verify form */}
              {isVerifying && (
                <div className="px-4 pb-3">
                  <VerifyForm
                    doc={doc}
                    applicationId={applicationId}
                    reviewerId={reviewerId}
                    onDone={(updated) => {
                      setDocuments((prev) =>
                        prev.map((d) => (d.filename === updated.filename ? { ...d, ...updated } : d))
                      );
                      setVerifyingFile(null);
                    }}
                    onCancel={() => setVerifyingFile(null)}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ── PDF report download ──────────────────────────────────────── */}
      <div className="pt-1 border-t border-slate-100">
        <a
          href={api.getPdfUrl(applicationId)}
          download={`application_${applicationId}.pdf`}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors shadow-sm"
          aria-label="Download full application report as PDF"
        >
          <PDFIcon />
          Download Full Report (PDF)
        </a>
        <p className="mt-1 text-[11px] text-slate-400">
          Includes application scores, rationale, policy clauses, document list, and verification status.
        </p>
      </div>
    </div>
  );
}
