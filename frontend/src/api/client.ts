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
  score_breakdown: ScoreBreakdown;
  fairness_check: FairnessCheck;
  challenger_result: ChallengerResult | null;
  agent_recommendation: Band;
  rationale: string;
  adverse_action_draft: string | null;
  human_decision: Band | null;
  human_reviewer: string | null;
  override_reason: string | null;
  decided_at: string | null;
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
  agent_recommendation: Band;
  status: AppStatus;
  created_at: string;
  composite_score: number;
  band: Band;
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

  /** GET /applications/:id/decision — just the decision state */
  getDecision: (id: string) =>
    request<DecisionRecord>(`/applications/${id}/decision`),

  /** POST /applications/:id/decision — underwriter action */
  recordDecision: (id: string, body: HumanDecisionRequest) =>
    request<DecisionRecord>(`/applications/${id}/decision`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  /** GET /applications/:id/trace — audit node trace */
  getTrace: (id: string) =>
    request<{ application_id: string; trace: TraceEntry[] }>(
      `/applications/${id}/trace`
    ),
};
