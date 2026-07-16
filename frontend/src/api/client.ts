/**
 * api/client.ts — typed fetch wrapper for the FastAPI backend.
 *
 * Two surfaces:
 *   applicantApi — what the applicant-facing portal needs (submit + status)
 *   api          — full internal API (kept for future admin/reviewer use)
 */

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// ── Shared types ─────────────────────────────────────────────────────────

export type Band = "approve" | "refer" | "decline";
export type AppStatus =
  | "pending_human_review"
  | "decided"
  | "awaiting_information"
  | "hold_for_document"
  | "flag_fairness_fail"
  | "error";

// ── Applicant-facing types ────────────────────────────────────────────────

export interface DocumentInput {
  doc_type: "id" | "pay_stub" | "bank_statement" | "other";
  file_path: string;
  ocr_confidence?: number;
  extracted_text?: string;
}

export interface SubmitApplicationRequest {
  application_id: string;
  applicant_name: string;
  applicant_address: string;
  stated_income: number;
  stated_monthly_debt: number;
  loan_amount_requested: number;
  applicant_notes: string | null;
  documents: DocumentInput[];
}

/** Minimal view returned to the applicant — no internal scores exposed */
export interface ApplicantStatusView {
  application_id: string;
  status: AppStatus;
  submitted_at: string;
  human_decision: Band | null;
  awaiting_info_items: string[];
  missing_docs: string[];
  approved_notice_text: string | null;
}

// ── Internal types (kept for admin/reviewer future use) ───────────────────

export interface ClauseCitation {
  clause_id: string;
  clause_text: string;
  factor: string;
}

export interface ScoreBreakdown {
  policy_version: string;
  dti_ratio: number;
  dti_subscore: number;
  credit_history_subscore: number;
  income_stability_subscore: number;
  weights: Record<string, number>;
  composite_score: number;
  band: Band;
  clause_citations: ClauseCitation[];
}

export interface DecisionRecord {
  application_id: string;
  policy_version: string;
  applicant_name: string;
  applicant_address: string;
  loan_amount_requested: number;
  applicant_notes: string | null;
  score_breakdown: ScoreBreakdown;
  agent_recommendation: Band;
  rationale: string;
  adverse_action_draft: string | null;
  approved_notice_text: string | null;
  human_decision: Band | null;
  human_reviewer: string | null;
  override_reason: string | null;
  decided_at: string | null;
  awaiting_info_items: string[];
  created_at: string;
  immutable: boolean;
  status: AppStatus;
  missing_docs?: string[];
  consistency_flags?: string[];
}

export interface DocumentMeta {
  filename: string;
  size_bytes: number;
  uploaded_at: string;
  url: string;
  doc_type: string;
  doc_type_label: string;
  verification_status: "pending" | "verified" | "rejected";
  verification_note: string | null;
  verified_by: string | null;
  verified_at: string | null;
}

export interface UploadResponse {
  application_id: string;
  uploaded: DocumentMeta[];
  all_documents: DocumentMeta[];
}

// ── Helpers ───────────────────────────────────────────────────────────────

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${path}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ── Applicant API ─────────────────────────────────────────────────────────

export const applicantApi = {
  /** Upload documents before submitting — must be called first. */
  uploadDocuments: async (
    appId: string,
    files: File[],
    docTypes: string[],
  ): Promise<UploadResponse> => {
    const form = new FormData();
    for (const file of files) form.append("files", file);
    if (docTypes.length > 0) form.append("doc_types", docTypes.join(","));
    const res = await fetch(`${BASE}/applications/${appId}/documents`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText);
      throw new Error(`${res.status} upload: ${text}`);
    }
    return res.json() as Promise<UploadResponse>;
  },

  /** POST /applications — submit the application. */
  submitApplication: (body: SubmitApplicationRequest): Promise<DecisionRecord> =>
    request<DecisionRecord>("/applications", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  /**
   * GET /applications/:id — fetch current status.
   * Returns only applicant-safe fields — no scores, no rationale.
   */
  getStatus: async (appId: string): Promise<ApplicantStatusView> => {
    const full = await request<DecisionRecord>(`/applications/${appId}`);
    return {
      application_id:       full.application_id,
      status:               full.status,
      submitted_at:         full.created_at,
      human_decision:       full.human_decision,
      awaiting_info_items:  full.awaiting_info_items ?? [],
      missing_docs:         full.missing_docs ?? [],
      approved_notice_text: full.approved_notice_text ?? null,
    };
  },
};

// ── Full internal API (future reviewer / admin portal) ────────────────────

export interface QueueItem {
  application_id: string;
  applicant_name: string;
  loan_amount_requested: number;
  agent_recommendation: Band | null;
  status: AppStatus;
  created_at: string;
  composite_score: number | null;
  band: Band | null;
  policy_version: string;
  human_decision: Band | null;
  human_reviewer: string | null;
}

export const api = {
  getQueue: () => request<QueueItem[]>("/queue"),
  getApplication: (id: string) =>
    request<DecisionRecord>(`/applications/${id}`),
  listDocuments: (id: string) =>
    request<{ application_id: string; documents: DocumentMeta[] }>(`/applications/${id}/documents`),
  verifyDocument: (
    id: string,
    filename: string,
    body: { verification_status: "verified" | "rejected"; verified_by: string; verification_note?: string },
  ) =>
    request<DocumentMeta>(`/applications/${id}/documents/${encodeURIComponent(filename)}/verify`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  recordDecision: (
    id: string,
    body: { human_decision: Band; human_reviewer: string; override_reason?: string },
  ) =>
    request<DecisionRecord>(`/applications/${id}/decision`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  requestInfo: (
    id: string,
    body: { requested_items: string[]; reviewer: string },
  ) =>
    request<DecisionRecord>(`/applications/${id}/request-info`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateNotice: (
    id: string,
    body: { notice_text: string; reviewer: string },
  ) =>
    request<DecisionRecord>(`/applications/${id}/notice`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  getPdfUrl: (id: string) => `${BASE}/applications/${id}/pdf`,
  getDocumentUrl: (id: string, filename: string) =>
    `${BASE}/applications/${id}/documents/${encodeURIComponent(filename)}`,
};
