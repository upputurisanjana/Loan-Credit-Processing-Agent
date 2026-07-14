/**
 * DocumentsPanel — upload-only component for the APPLICANT submission form.
 *
 * This component is intentionally NOT used on the reviewer (ApplicationDetailPage).
 * The reviewer sees DocumentList instead, which is read-only with verification controls.
 *
 * Features:
 * - Drag-and-drop or click-to-browse file picker
 * - Per-file doc_type selection (id, pay_stub, bank_statement, other)
 * - Client-side validation: file type, size (max 20 MB)
 * - Upload progress / error feedback
 * - List of uploaded documents after upload
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { DocumentMeta } from "../api/client";

const ALLOWED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".webp"];
const MAX_SIZE_MB = 20;

const DOC_TYPE_OPTIONS = [
  { value: "id",            label: "Identity Document (ID / Passport)" },
  { value: "pay_stub",      label: "Pay Stub / Payslip" },
  { value: "bank_statement", label: "Bank Statement" },
  { value: "other",         label: "Other Document" },
];

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface PendingFile {
  file: File;
  docType: string;
  id: string; // local key
}

interface ValidationError {
  filename: string;
  reason: string;
}

interface Props {
  applicationId: string;
}

export default function DocumentsPanel({ applicationId }: Props) {
  const [documents, setDocuments]         = useState<DocumentMeta[]>([]);
  const [loadingDocs, setLoadingDocs]     = useState(false);
  const [pendingFiles, setPendingFiles]   = useState<PendingFile[]>([]);
  const [uploading, setUploading]         = useState(false);
  const [uploadErrors, setUploadErrors]   = useState<string[]>([]);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [dragOver, setDragOver]           = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadDocuments = useCallback(async () => {
    setLoadingDocs(true);
    try {
      const res = await api.listDocuments(applicationId);
      setDocuments(res.documents);
    } catch {
      setDocuments([]);
    } finally {
      setLoadingDocs(false);
    }
  }, [applicationId]);

  useEffect(() => { void loadDocuments(); }, [loadDocuments]);

  function validateFiles(files: File[]): { valid: File[]; errors: ValidationError[] } {
    const valid: File[] = [];
    const errors: ValidationError[] = [];
    for (const file of files) {
      const ext = "." + (file.name.split(".").pop() ?? "").toLowerCase();
      if (!ALLOWED_EXTENSIONS.includes(ext)) {
        errors.push({ filename: file.name, reason: `Unsupported type '${ext}'.` });
        continue;
      }
      if (file.size > MAX_SIZE_MB * 1024 * 1024) {
        errors.push({ filename: file.name, reason: `File too large (${formatBytes(file.size)}). Max ${MAX_SIZE_MB} MB.` });
        continue;
      }
      valid.push(file);
    }
    return { valid, errors };
  }

  function addFilesToQueue(files: File[]) {
    setValidationErrors([]);
    setUploadSuccess(null);
    const { valid, errors } = validateFiles(files);
    if (errors.length > 0) setValidationErrors(errors);
    if (valid.length === 0) return;

    setPendingFiles((prev) => [
      ...prev,
      ...valid.map((f) => ({
        file: f,
        docType: inferDocType(f.name),
        id: `${f.name}-${Date.now()}-${Math.random()}`,
      })),
    ]);
  }

  function inferDocType(filename: string): string {
    const lower = filename.toLowerCase();
    if (lower.includes("passport") || lower.includes("id") || lower.includes("licence") || lower.includes("license")) return "id";
    if (lower.includes("payslip") || lower.includes("pay_stub") || lower.includes("paystub") || lower.includes("salary")) return "pay_stub";
    if (lower.includes("bank") || lower.includes("statement")) return "bank_statement";
    return "other";
  }

  function updateDocType(id: string, docType: string) {
    setPendingFiles((prev) =>
      prev.map((pf) => (pf.id === id ? { ...pf, docType } : pf))
    );
  }

  function removeFile(id: string) {
    setPendingFiles((prev) => prev.filter((pf) => pf.id !== id));
  }

  async function handleUpload() {
    if (pendingFiles.length === 0) return;
    setUploadErrors([]);
    setUploadSuccess(null);
    setUploading(true);
    try {
      const files    = pendingFiles.map((pf) => pf.file);
      const docTypes = pendingFiles.map((pf) => pf.docType);
      const res = await api.uploadDocuments(applicationId, files, docTypes);
      setDocuments(res.all_documents);
      setPendingFiles([]);
      setUploadSuccess(`${res.uploaded.length} file${res.uploaded.length !== 1 ? "s" : ""} uploaded.`);
    } catch (err) {
      setUploadErrors([err instanceof Error ? err.message : "Upload failed."]);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    addFilesToQueue(Array.from(e.dataTransfer.files));
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    addFilesToQueue(Array.from(e.target.files ?? []));
  }

  return (
    <div className="space-y-4">

      {/* ── Drop zone ─────────────────────────────────────────────────── */}
      <div
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer ${
          dragOver ? "border-blue-400 bg-blue-50" : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label="Add documents — click or drag and drop"
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click(); }}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ALLOWED_EXTENSIONS.join(",")}
          className="hidden"
          onChange={handleFileInput}
          aria-hidden="true"
        />
        <div className="flex flex-col items-center gap-2 text-slate-400">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
            <path d="M14 4v14M9 9l5-5 5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M4 22h20" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
          </svg>
          <div>
            <p className="text-sm font-medium text-slate-600">Drop files here or click to browse</p>
            <p className="text-xs text-slate-400 mt-0.5">PDF, PNG, JPG, TIFF · Max {MAX_SIZE_MB} MB per file</p>
          </div>
        </div>
      </div>

      {/* ── Validation errors ─────────────────────────────────────────── */}
      {validationErrors.length > 0 && (
        <div className="rounded-md bg-amber-50 border border-amber-200 p-3 space-y-1">
          <p className="text-xs font-semibold text-amber-700">Cannot add — fix these issues:</p>
          {validationErrors.map((e, i) => (
            <p key={i} className="text-xs text-amber-700">
              <span className="font-medium">{e.filename}:</span> {e.reason}
            </p>
          ))}
        </div>
      )}

      {/* ── Pending files queue (with doc type selector) ──────────────── */}
      {pendingFiles.length > 0 && (
        <div className="border border-slate-200 rounded-lg overflow-hidden">
          <div className="px-4 py-2 bg-slate-50 border-b border-slate-200">
            <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
              Ready to upload — select document type for each file
            </p>
          </div>
          <div className="divide-y divide-slate-100">
            {pendingFiles.map((pf) => (
              <div key={pf.id} className="flex items-center gap-3 px-4 py-3 bg-white">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">{pf.file.name}</p>
                  <p className="text-[11px] text-slate-400">{formatBytes(pf.file.size)}</p>
                </div>
                <select
                  value={pf.docType}
                  onChange={(e) => updateDocType(pf.id, e.target.value)}
                  className="text-xs border border-slate-200 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
                  aria-label={`Document type for ${pf.file.name}`}
                >
                  {DOC_TYPE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
                <button
                  onClick={() => removeFile(pf.id)}
                  className="text-slate-400 hover:text-red-500 transition-colors p-1"
                  aria-label={`Remove ${pf.file.name}`}
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2 2L10 10M10 2L2 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                </button>
              </div>
            ))}
          </div>
          <div className="px-4 py-3 bg-slate-50 border-t border-slate-200">
            <button
              onClick={() => void handleUpload()}
              disabled={uploading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md disabled:opacity-50 transition-colors"
            >
              {uploading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Uploading…
                </>
              ) : (
                <>
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <path d="M7 2v8M4 5l3-3 3 3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M2 11h10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                  </svg>
                  Upload {pendingFiles.length} file{pendingFiles.length !== 1 ? "s" : ""}
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* ── Upload errors ─────────────────────────────────────────────── */}
      {uploadErrors.length > 0 && (
        <div className="rounded-md bg-red-50 border border-red-200 p-3">
          {uploadErrors.map((e, i) => <p key={i} className="text-xs text-red-700">{e}</p>)}
        </div>
      )}

      {/* ── Success message ───────────────────────────────────────────── */}
      {uploadSuccess && (
        <div className="rounded-md bg-green-50 border border-green-200 p-3 flex items-center gap-2">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-green-600 flex-shrink-0">
            <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.2"/>
            <path d="M4.5 7L6.5 9L9.5 5.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <p className="text-xs font-medium text-green-700">{uploadSuccess}</p>
        </div>
      )}

      {/* ── Already uploaded list ─────────────────────────────────────── */}
      {loadingDocs ? (
        <div className="space-y-1.5">
          {[...Array(2)].map((_, i) => <div key={i} className="h-9 bg-slate-100 rounded animate-pulse" />)}
        </div>
      ) : documents.length > 0 ? (
        <div className="divide-y divide-slate-100 border border-slate-200 rounded-lg overflow-hidden">
          {documents.map((doc) => (
            <div key={doc.filename} className="flex items-center gap-3 px-4 py-3 bg-white">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-slate-400 flex-shrink-0">
                <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.2"/>
                <path d="M4.5 7L6.5 9L9.5 5.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-800 truncate">{doc.filename}</p>
                <p className="text-[11px] text-slate-400">
                  {doc.doc_type_label} · {formatBytes(doc.size_bytes)}
                </p>
              </div>
              <span className="text-[10px] font-medium text-green-700 bg-green-50 border border-green-200 px-1.5 py-0.5 rounded">
                Uploaded
              </span>
            </div>
          ))}
        </div>
      ) : (
        pendingFiles.length === 0 && (
          <p className="text-sm text-slate-400 italic text-center py-4">
            No documents uploaded yet. Use the area above to add your supporting documents.
          </p>
        )
      )}
    </div>
  );
}
