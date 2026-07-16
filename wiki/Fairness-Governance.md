# Fairness & Governance

This page covers the fairness architecture, audit trail, immutability guarantees, and security measures.

---

## Two-Layer Fairness Check

The system implements two independent fairness checks — a structural Python check and an LLM semantic review.

### Layer 1: Structural Recheck (Python, deterministic)

**File:** `app/agent/nodes/fairness_recheck.py`

**How it works:**

```python
# Pass 1: score with identity present (but never read by scorer)
original = run_score(fields)

# Pass 2: score with identity masked
masked = identity_blind_copy(fields)  # name="[REDACTED]", address="[REDACTED]"
re_scored = run_score(masked)

# Compare
assert original.composite_score == re_scored.composite_score
assert original.band == re_scored.band
```

**Why this works:** The `run_score()` function only reads `income_monthly`, `debt_monthly`, `credit_history_years`, `credit_history_flags`, and `employment_months_current` from `ApplicationFields`. The `IdentityBlock` sub-object (name, address) is never accessed by any scoring arithmetic. Therefore, masking identity and re-running the scorer produces bit-for-bit identical results.

**If they differ:** This means identity leaked into a scoring path — a serious regression. The application is forced to `REFER` with `status = "flag_fairness_fail"`.

**Structural guarantee:** This is not "ask the LLM to ignore the name." The scorer literally cannot see identity fields. Verified by 21 structural tests in `test_fairness_structural.py`.

---

### Layer 2: LLM Semantic Review

**File:** `app/agent/nodes/fairness_llm_review.py`

Runs AFTER the structural recheck passes. The LLM scans the score breakdown context for identity-proxy language that could indicate bias in how the recommendation will be explained.

**Examples of identity-proxy language:**
- References to "neighbourhood" or "area" (geographic proxy for race)
- References to "age group" or "young/old" (age proxy)
- References to "background" or "origin"

**Fail-open:** If the LLM call fails (timeout, API error), the review defaults to no flag. An LLM outage should not block all applications. The failure is logged as a warning.

**If bias detected:** The recommendation is forced to `REFER` with `status = "flag_fairness_fail"`. The `llm_review_flag` and `llm_review_note` are stored in `FairnessCheck`.

---

## FairnessCheck Data Model

```python
class FairnessCheck(BaseModel):
    original_band: str           # Band from the original score
    masked_band: str             # Band from the identity-masked re-score
    original_composite: float    # Original composite score
    masked_composite: float      # Masked composite score
    match: bool                  # True if bands and scores match
    llm_review_flag: bool = False    # True if LLM detected bias language
    llm_review_note: str = ""        # LLM's explanation of the flag
```

---

## Audit Trail

### Append-Only Decision Records

Every application produces a `DecisionRecord` that is:
- Written to SQLite on pipeline completion
- Never modified after writing (append-only)
- Rehydrated into memory on server startup

```python
class DecisionRecord(BaseModel):
    application_id: str
    policy_version: str
    applicant_name: str
    applicant_address: str
    loan_amount_requested: float
    score_breakdown: ScoreBreakdown
    fairness_check: FairnessCheck
    challenger_result: ChallengerResult | None
    agent_recommendation: str
    rationale: str
    adverse_action_draft: str | None
    approved_notice_text: str | None
    human_decision: str | None
    human_reviewer: str | None
    override_reason: str | None
    decided_at: datetime | None
    awaiting_info_items: list[str]
    pipeline_trace: list[dict]
    created_at: datetime
```

### Amendments Table

Post-hoc corrections are stored in a separate `decision_amendments` table:

```python
class DecisionAmendment(BaseModel):
    amendment_id: str
    original_application_id: str
    amended_by: str
    amendment_reason: str
    field_changes: dict
    amended_at: datetime
```

**The original `decision_records` row is never touched.** Amendments are linked rows that document what changed, who changed it, and why.

---

## Immutability Guarantees

1. **DecisionRecord is frozen:** Pydantic model with `frozen=True` — no in-place mutation possible
2. **Updates create new instances:** `record.model_copy(update={...})` replaces the store entry
3. **DB enforces immutability:** `human_decision` column only updatable when currently `NULL`
4. **No DELETE statements:** The `decision_records` table has no DELETE operations
5. **Amendments are separate:** Corrections go to `decision_amendments` — linked by `application_id`

---

## Override Handling

When an underwriter overrides the agent's recommendation:

1. `override_reason` is **required** (minimum 20 characters)
2. The original `agent_recommendation` is **never overwritten**
3. Both fields coexist in the `DecisionRecord`: `agent_recommendation=approve`, `human_decision=decline`
4. The `override_reason` is stored alongside both — full audit trail
5. The override is logged with the reviewer ID and timestamp

---

## Security Measures

| Measure | Implementation |
|---------|---------------|
| **Path traversal prevention** | `application_id` validated by regex `^[A-Z0-9][A-Z0-9\-]{2,29}$` |
| **Internal field stripping** | `_public_payload()` removes `fairness_check`, `challenger_result`, `pipeline_trace` from API responses |
| **Token protection** | GitHub token never logged (confirmed by log-statement audit) |
| **Rate limiting** | 10 POST/PUT/PATCH requests per 60s per IP; `Retry-After` header on 429 |
| **Prompt injection defence** | Applicant data wrapped in `<applicant_data>` tags; system prompt marks content as untrusted input |
| **CORS** | Origins configurable via `ALLOWED_ORIGINS` in `.env`; defaults to localhost only |

---

## Governance Dashboard (Analysis Endpoints)

The analysis router provides on-demand access to fairness and challenger results:

- `GET /applications/{id}/fairness` — full fairness check result with explanation
- `GET /applications/{id}/challenger` — full challenger result with explanation
- `POST /applications/{id}/challenger/rerun` — re-run challenger model live

These endpoints surface the internal pipeline mechanics to the underwriter UI, enabling informed decision-making.
