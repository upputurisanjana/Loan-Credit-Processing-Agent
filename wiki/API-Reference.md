# API Reference

Base URL: `http://localhost:8000`

Interactive docs available at: `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc`

---

## Intake

### `POST /applications`

Submit a new credit application. Runs the full agent pipeline synchronously.

**Request body** (`ApplicationRaw`):

```json
{
  "application_id": "APP-001",
  "submitted_at": "2026-07-15T10:00:00Z",
  "applicant_name": "Jane Smith",
  "applicant_address": "123 Main St, London, SW1A 1AA",
  "stated_income": 5000,
  "stated_monthly_debt": 900,
  "loan_amount_requested": 25000,
  "applicant_notes": null,
  "documents": [
    {
      "doc_type": "id",
      "file_path": "passport.pdf",
      "ocr_confidence": 0.95,
      "extracted_text": "IDENTITY DOCUMENT\nName: Jane Smith\n"
    },
    {
      "doc_type": "pay_stub",
      "file_path": "payslip.pdf",
      "ocr_confidence": 0.95,
      "extracted_text": "PAYSLIP\nMonthly Gross Income: 5000.00\n"
    },
    {
      "doc_type": "bank_statement",
      "file_path": "statement.pdf",
      "ocr_confidence": 0.95,
      "extracted_text": "BANK STATEMENT\nMonthly Income Credits: 5000.00\n"
    }
  ]
}
```

**Response (202 Accepted)** — `DecisionRecord` (public payload):

```json
{
  "application_id": "APP-001",
  "policy_version": "v1.2",
  "applicant_name": "Jane Smith",
  "applicant_address": "123 Main St, London, SW1A 1AA",
  "loan_amount_requested": 25000,
  "status": "pending_human_review",
  "score_breakdown": {
    "policy_version": "v1.2",
    "dti_ratio": 0.18,
    "dti_subscore": 1.0,
    "credit_history_subscore": 1.0,
    "income_stability_subscore": 1.0,
    "weights": {"dti": 0.40, "credit_history": 0.35, "income_stability": 0.25},
    "composite_score": 1.0,
    "band": "approve",
    "clause_citations": [
      {"clause_id": "DTI-02", "clause_text": "...", "factor": "dti"},
      {"clause_id": "CH-01", "clause_text": "...", "factor": "credit_history"},
      {"clause_id": "INC-02", "clause_text": "...", "factor": "income_stability"}
    ]
  },
  "agent_recommendation": "approve",
  "rationale": "Application demonstrates strong financial profile...",
  "human_decision": null,
  "created_at": "2026-07-15T10:00:05Z"
}
```

**Possible statuses:**
- `pending_human_review` — pipeline completed, awaiting underwriter
- `hold_for_document` — required documents missing
- `error` — pipeline failed (details in `message`)

---

### `GET /applications/{application_id}`

Retrieve the current state of an application.

**Response (200 OK)** — same shape as POST response.

**Errors:** 404 if not found.

---

## Human Gate

### `POST /applications/{application_id}/decision`

Record the underwriter's final decision.

**Request body:**

```json
{
  "human_decision": "approve",
  "human_reviewer": "underwriter_1",
  "override_reason": null
}
```

**Rules:**
- `human_decision` must be one of: `approve`, `refer`, `decline`
- `human_reviewer` is required (non-empty string)
- `override_reason` is **required** (min 20 chars) when `human_decision` differs from `agent_recommendation`
- Application must be in `pending_human_review` or `awaiting_information` state
- Cannot re-decide an already-decided application (use amendments endpoint)

**Response (200 OK)** — updated `DecisionRecord`.

**Errors:** 404 (not found), 409 (already decided / wrong state), 422 (missing override reason).

---

### `POST /applications/{application_id}/request-info`

Reviewer requests additional information without finalising the decision.

**Request body:**

```json
{
  "requested_items": ["bank_statement", "proof_of_address"],
  "reviewer": "underwriter_1"
}
```

Sets `status = "awaiting_information"` and stores the requested items. The application remains open for later decision via `POST /decision`.

---

### `PATCH /applications/{application_id}/notice`

Save the reviewer-edited adverse action notice text.

**Request body:**

```json
{
  "notice_text": "Dear Applicant, following a review of your credit application...",
  "reviewer": "underwriter_1"
}
```

The edited text is stored in `approved_notice_text`. When the applicant checks their status, they see this approved version instead of the raw LLM draft.

---

## Queue

### `GET /queue`

Returns all applications in summary form for the case queue table.

**Response (200 OK):**

```json
[
  {
    "application_id": "APP-001",
    "applicant_name": "Jane Smith",
    "loan_amount_requested": 25000,
    "agent_recommendation": "approve",
    "status": "pending_human_review",
    "created_at": "2026-07-15T10:00:05Z",
    "composite_score": 1.0,
    "band": "approve",
    "policy_version": "v1.2",
    "human_decision": null,
    "human_reviewer": null
  }
]
```

Sorted oldest-first. REFER applications surface first in the UI (client-side sort).

---

## Audit & Trace

### `GET /applications/{application_id}/trace`

Returns the ordered node-by-node pipeline trace.

**Response (200 OK):**

```json
{
  "application_id": "APP-001",
  "trace": [
    {"node": "VERIFY", "timestamp": "...", "status": "ok", "missing_docs": [], "consistency_flags": []},
    {"node": "EXTRACT", "timestamp": "...", "income_monthly": 5000, "debt_monthly": 900},
    {"node": "SCORE", "timestamp": "...", "composite_score": 1.0, "band": "approve", "policy_version": "v1.2"},
    {"node": "CHALLENGER", "timestamp": "...", "primary_band": "approve", "challenger_band": "approve", "bands_agree": true},
    {"node": "FAIRNESS_RECHECK", "timestamp": "...", "original_band": "approve", "masked_band": "approve", "match": true},
    {"node": "FAIRNESS_LLM_REVIEW", "timestamp": "...", "bias_detected": false},
    {"node": "RECOMMEND", "timestamp": "...", "recommendation": "approve"},
    {"node": "DRAFT_NOTICE", "timestamp": "...", "skipped": true},
    {"node": "HUMAN_GATE", "timestamp": "...", "status": "pending_human_review"}
  ]
}
```

---

## Fairness & Challenger Analysis

### `GET /applications/{application_id}/fairness`

Returns the stored fairness recheck result with full explainability detail.

### `GET /applications/{application_id}/challenger`

Returns the stored challenger model result with full explainability detail.

### `POST /applications/{application_id}/challenger/rerun`

Re-runs the challenger LLM call live. Consumes one LLM API call. Result stored in memory only (DB record unchanged).

---

## Documents

### `POST /applications/{application_id}/documents`

Upload supporting documents (multipart form data).

- Accepted types: PDF, PNG, JPEG, TIFF, WEBP
- Max file size: 20 MB per file
- Optional `doc_types` field: comma-separated values (`id`, `pay_stub`, `bank_statement`, `other`)

### `GET /applications/{application_id}/documents`

List all uploaded documents with metadata and verification status.

### `GET /applications/{application_id}/documents/{filename}`

Download a specific uploaded document.

### `PATCH /applications/{application_id}/documents/{filename}/verify`

Reviewer marks a document as `verified` or `rejected` (with required note on rejection).

### `GET /applications/{application_id}/pdf`

Generate and download a PDF report containing application summary, score breakdown, recommendation, clause citations, and document list.

---

## Amendments

### `POST /applications/{application_id}/amendments`

Record a post-hoc correction to a decided application. The original record is **never modified** — the amendment is a new linked row.

**Request body:**

```json
{
  "amended_by": "senior_underwriter",
  "amendment_reason": "Additional evidence submitted showing corrected income figures",
  "field_changes": {
    "human_decision": "refer",
    "override_reason": "New evidence changes the assessment"
  }
}
```

### `GET /applications/{application_id}/amendments`

Return all amendments for a given application.

---

## Meta

### `GET /health`

Returns API status, model config, and live reachability probes for both primary and challenger models.

```json
{
  "status": "ok",
  "version": "0.1.0",
  "primary_model": {"status": "ok", "model": "openai/gpt-4o-mini"},
  "challenger_model": {"status": "ok", "model": "meta/llama-3.1-70b-instruct"},
  "policy_path": "./policy/policy_v1.yaml"
}
```

---

## Error Responses

All errors follow the FastAPI standard format:

```json
{
  "detail": "Application 'APP-999' not found."
}
```

Common HTTP status codes:
| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created (amendments, document uploads) |
| 202 | Accepted (application submitted, pipeline running) |
| 404 | Application/document not found |
| 409 | Conflict (duplicate ID, already decided, wrong state) |
| 413 | File too large (>20 MB) |
| 422 | Validation error (missing fields, invalid values) |
| 429 | Rate limit exceeded (Retry-After header included) |
| 500 | Internal server error |
