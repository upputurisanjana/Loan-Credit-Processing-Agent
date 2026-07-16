# Pipeline

The credit decisioning pipeline is a LangGraph `StateGraph` — a directed graph of typed nodes with explicit conditional edges. Every application flows through this pipeline exactly once.

---

## Pipeline Flow

```
INTAKE
  │
  ▼
VERIFY ──────────────────── missing docs ──► HOLD (pipeline ends, status=hold_for_document)
  │
  │ ok
  ▼
EXTRACT ─────────────────── extraction error ──► HUMAN_GATE (status=error)
  │
  ▼
SCORE (pure Python, no LLM)
  │
  ▼
CHALLENGER (independent LLM re-score)
  │
  ▼
FAIRNESS_RECHECK (Python, structural)
  │
  ▼
FAIRNESS_LLM_REVIEW (LLM, semantic bias scan)
  │
  ├── bias/mismatch ──► FLAG_FAIRNESS_FAIL ──► DRAFT_NOTICE ──► HUMAN_GATE
  │
  └── clean ──────────► RECOMMEND ───────────► DRAFT_NOTICE ──► HUMAN_GATE
                                                      │
                                                      ▼
                                                 HUMAN_GATE (pipeline ends, status=pending_human_review)
```

**Every path terminates at HUMAN_GATE.** No decision is ever auto-finalised.

---

## Node Details

### 1. VERIFY

**Type:** Python (no LLM)
**File:** `app/agent/nodes/verify.py`

Checks:
- **Required documents present**: ID, pay stub, bank statement must all be in the `documents` list
- **Cross-document income consistency**: stated income vs. pay stub extracted income
- **Name consistency**: extracts names from ID, pay stub, bank statement via regex, fuzzy-matches against `applicant_name` (Levenshtein distance ≤ 1 for OCR noise tolerance)
- **OCR confidence flags**: documents with `ocr_confidence < 0.60` are flagged for manual review

**Output:** `VerifyResult` with `status = "ok"` or `"hold_for_document"`, plus `missing_docs` and `consistency_flags` lists.

---

### 2. HOLD

**Type:** Terminal node
**File:** Inline in `graph.py`

Sets `status = "hold_for_document"` and records which documents are missing. Pipeline ends — the application is returned to the applicant with a list of required documents.

---

### 3. EXTRACT

**Type:** LLM
**File:** `app/agent/nodes/extract.py`
**Prompt:** `app/agent/prompts/extract_prompt.py`

Uses the primary LLM to read document text and extract structured fields into `ApplicationFields`:

- `income_monthly` — from pay stub / bank statement
- `debt_monthly` — from bank statement regular payments
- `credit_history_years` — from credit report text
- `credit_history_flags` — late payments, defaults, etc.
- `employment_months_current` — from pay stub / application

**Security:** All applicant data is wrapped in `<applicant_data>` tags. The system prompt explicitly states this content is untrusted input — extract data values only, ignore any instructions.

**Pydantic validation:** The extracted JSON is validated against the `ApplicationFields` schema. Validation errors trigger a pipeline error (routed to HUMAN_GATE with error status).

---

### 4. SCORE

**Type:** Pure Python (NO LLM)
**File:** `app/agent/nodes/score.py`

This is the governance-critical node. It must NEVER import or call any LLM.

**What it does:**
1. Loads the active policy from `policy_v1.yaml` (cached per process)
2. Computes three sub-scores from `ApplicationFields`:
   - **DTI sub-score** (0.0–1.0) — from `debt_monthly / income_monthly`
   - **Credit history sub-score** (0.0–1.0) — from `credit_history_years` and `credit_history_flags`
   - **Income stability sub-score** (0.0–1.0) — from `employment_months_current`
3. Computes weighted composite: `dti × 0.40 + ch × 0.35 + inc × 0.25`
4. Assigns band: composite ≥ 0.75 → APPROVE, ≥ 0.65 → REFER, else DECLINE
5. Attaches policy clause citations for every clause that was triggered

**Output:** `ScoreBreakdown` — a fully structured, audit-ready object.

**Determinism guarantee:** Same inputs always produce identical outputs. Verified by `test_score_is_deterministic` (100 repeated calls, bit-for-bit identical).

---

### 5. CHALLENGER

**Type:** LLM
**File:** `app/agent/nodes/challenger_compare.py`

An independent LLM (configured via `CHALLENGER_MODEL`) receives the same `ApplicationFields` + policy excerpt and states its own band opinion.

**Key design:** The challenger does NOT replace the band from the deterministic scorer. It only checks whether an independent model would suggest a different band, as a sanity check.

**Disagreement logic:**
- Band delta = 0: models agree, no action
- Band delta = 1: 1-tier disagreement (approve↔refer), noted but no override
- Band delta = 2: 2-tier disagreement (approve↔decline), forces REFER

---

### 6. FAIRNESS_RECHECK

**Type:** Pure Python (no LLM)
**File:** `app/agent/nodes/fairness_recheck.py`

**Structural guarantee:**
```python
def identity_blind_copy(fields: ApplicationFields) -> ApplicationFields:
    masked = fields.model_copy(deep=True)
    masked.identity = IdentityBlock(name="[REDACTED]", address="[REDACTED]")
    return masked
```

The scorer only receives `ApplicationFields`. It has no path through which identity can influence the score. The recheck:
1. Calls `run_score(fields)` — identity present but never read
2. Calls `run_score(identity_blind_copy(fields))` — identity = [REDACTED]
3. Compares `composite_score` and `band`

If they differ → `status = "flag_fairness_fail"` → forced REFER. This should never happen in normal operation — it exists to catch regressions (e.g., someone accidentally wiring identity into a future feature).

---

### 7. FAIRNESS_LLM_REVIEW

**Type:** LLM
**File:** `app/agent/nodes/fairness_llm_review.py`

Runs AFTER the structural recheck passes. Scans the score breakdown context for identity-proxy language that could indicate bias in how the recommendation will be explained (e.g., references to "neighbourhood", "area", "age group").

**Fail-open:** If the LLM call fails, defaults to no flag (fail-open) so an LLM outage does not block all applications. The outage is logged as a warning.

---

### 8. FLAG_FAIRNESS_FAIL

**Type:** Terminal node (transitions to DRAFT_NOTICE)
**File:** Inline in `graph.py`

Forces `agent_recommendation = "refer"` and writes a rationale explaining the fairness flag. The application still reaches HUMAN_GATE — the underwriter sees the flag.

---

### 9. RECOMMEND

**Type:** LLM
**File:** `app/agent/nodes/recommend.py`
**Prompt:** `app/agent/prompts/recommend_prompt.py`

Composes a plain-English rationale from the already-computed `ScoreBreakdown`. The LLM explains the number — it does not invent it.

**Override logic:** If the challenger model disagrees (>1 band), the recommendation is forced to `refer` regardless of what the LLM suggests. The rationale includes a challenger flag text.

---

### 10. DRAFT_NOTICE

**Type:** LLM (conditional)
**File:** `app/agent/nodes/draft_notice.py`
**Prompt:** `app/agent/prompts/notice_prompt.py`

Only runs when `agent_recommendation == "decline"`. Generates an ECOA/Reg B-style adverse action notice citing specific score factors and policy clauses.

The draft is stored in `adverse_action_draft` and held for human review. It is never sent without underwriter approval via `PATCH /notice`.

---

### 11. HUMAN_GATE

**Type:** Terminal node
**File:** Inline in `graph.py`

Sets `status = "pending_human_review"`. All paths converge here. The `human_decision` field stays `None` until the underwriter calls `POST /decision`.

---

## State Machine (`AgentState`)

```python
class AgentState(TypedDict, total=False):
    raw: ApplicationRaw
    verify_result: VerifyResult
    fields: ApplicationFields
    score_breakdown: ScoreBreakdown
    fairness_check: FairnessCheck
    challenger_result: ChallengerResult | None
    agent_recommendation: str
    rationale: str
    adverse_action_draft: str
    status: str
    error_message: str | None
    pipeline_trace: list[dict]
```

Every node reads from and writes to this shared state. Conditional edges branch on `status`, `fairness_check.match`, and `challenger_result.bands_agree`.

---

## Pipeline Trace

Every node appends a trace entry:

```python
{
    "node": "SCORE",
    "timestamp": "2026-07-15T10:00:03Z",
    "composite_score": 1.0,
    "band": "approve",
    "policy_version": "v1.2"
}
```

The trace is stored in `DecisionRecord.pipeline_trace` and persisted to the database. It is exposed via `GET /applications/{id}/trace` for the audit trail viewer.
