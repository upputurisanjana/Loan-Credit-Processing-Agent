/**
 * api/client.ts — typed fetch wrapper for the FastAPI backend.
 * All types mirror the Pydantic models in app/models/.
 */

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// ── Types ────────────────────────────────────────────────────────────────

export type Band = "approve" | "refer" | "decline";
export type AppStatus =
  | "pending_human_review"
  | "decided"
  | "awaiting_information"
  | "hold_for_document"
  | "flag_fairness_fail"
  | "error";

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

export interface FairnessCheck {
  original_band: string;
  masked_band: string;
  original_composite: number;
  masked_composite: number;
  match: boolean;
}

export interface ChallengerResult {
  primary_band: string;
  challenger_band: string;
  bands_agree: boolean;
  delta: number;
}

export interface DecisionRecord {
  application_id: string;
  policy_version: string;
  // Applicant details
  applicant_name: string;
  applicant_address: string;
  loan_amount_requested: number;
  applicant_notes: string | null;
  // Pipeline outputs
  score_breakdown: ScoreBreakdown;
  fairness_check: FairnessCheck;
  challenger_result: ChallengerResult | null;
  agent_recommendation: Band;
  rationale: string;
  adverse_action_draft: string | null;
  approved_notice_text: string | null;
  // Human gate
  human_decision: Band | null;
  human_reviewer: string | null;
  override_reason: string | null;
  decided_at: string | null;
  // Request-info state
  awaiting_info_items: string[];
  created_at: string;
  immutable: boolean;
  status: AppStatus;
  // hold state fields
  missing_docs?: string[];
  consistency_flags?: string[];
  pipeline_trace?: TraceEntry[];
}

export interface TraceEntry {
  node: string;
  timestamp: string;
  [key: string]: unknown;
}

export interface QueueItem {
  application_id: string;
  agent_recommendation: Band | null;
  status: AppStatus;
  created_at: string;
  composite_score: number | null;
  band: Band | null;
  policy_version: string;
  fairness_match: boolean;
  challenger_disagreement: boolean;
  human_decision: Band | null;
}

export interface HumanDecisionRequest {
  human_decision: Band;
  human_reviewer: string;
  override_reason?: string;
}

export interface RequestInfoRequest {
  requested_items: string[];
  reviewer: string;
}

export interface NoticeUpdateRequest {
  notice_text: string;
  reviewer: string;
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

export interface DocumentsResponse {
  application_id: string;
  documents: DocumentMeta[];
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

// ── API calls ─────────────────────────────────────────────────────────────

export const api = {
  /** GET /queue — all applications in the pending queue */
  getQueue: () => request<QueueItem[]>("/queue"),

  /** GET /applications/:id — full decision record */
  getApplication: (id: string) =>
    request<DecisionRecord>(`/applications/${id}`),

  /** POST /applications/:id/decision — underwriter final decision */
  recordDecision: (id: string, body: HumanDecisionRequest) =>
    request<DecisionRecord>(`/applications/${id}/decision`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  /** POST /applications/:id/request-info — reviewer requests info without deciding */
  requestInfo: (id: string, body: RequestInfoRequest) =>
    request<DecisionRecord>(`/applications/${id}/request-info`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  /** PATCH /applications/:id/notice — save reviewer-edited notice text */
  updateNotice: (id: string, body: NoticeUpdateRequest) =>
    request<DecisionRecord>(`/applications/${id}/notice`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  /** GET /applications/:id/trace — audit node trace */
  getTrace: (id: string) =>
    request<{ application_id: string; trace: TraceEntry[] }>(
      `/applications/${id}/trace`
    ),

  /** POST /applications/:id/documents — upload supporting documents */
  uploadDocuments: async (
    id: string,
    files: File[],
    docTypes?: string[],
  ): Promise<UploadResponse> => {
    const form = new FormData();
    for (const file of files) {
      form.append("files", file);
    }
    // Pass doc_types as comma-separated string if provided
    if (docTypes && docTypes.length > 0) {
      form.append("doc_types", docTypes.join(","));
    }
    const res = await fetch(`${BASE}/applications/${id}/documents`, {
      method: "POST",
      body: form,
      // Do NOT set Content-Type — browser sets it with boundary automatically
    });
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText);
      throw new Error(`${res.status} upload: ${text}`);
    }
    return res.json() as Promise<UploadResponse>;
  },

  /** GET /applications/:id/documents — list uploaded documents */
  listDocuments: (id: string) =>
    request<DocumentsResponse>(`/applications/${id}/documents`),

  /** PATCH /applications/:id/documents/:filename/verify — reviewer verifies a doc */
  verifyDocument: (
    id: string,
    filename: string,
    body: { verification_status: "verified" | "rejected"; verified_by: string; verification_note?: string },
  ) =>
    request<DocumentMeta>(`/applications/${id}/documents/${encodeURIComponent(filename)}/verify`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  /** GET /applications/:id/pdf — download PDF report */
  getPdfUrl: (id: string) => `${BASE}/applications/${id}/pdf`,
};
