# ARCHITECTURE.md — Loan / Credit Application Processing Agent

Companion to `spec.md`. This is the technical design: agent graph, state machine, data contracts, and the policy engine.

---

## 1. Design principles

1. **The LLM never does arithmetic.** Scoring is pure Python against a versioned policy file. The LLM extracts, explains, drafts, and reasons in natural language — it never computes the DTI ratio or the composite score itself.
2. **Every recommendation is traceable to a policy clause ID**, not a paraphrase. Citations point at `policy.yaml` line-level clause IDs.
3. **Nothing touching the applicant's outcome fires without a human click.** APPROVE/REFER/DECLINE are recommendations until an underwriter confirms.
4. **Identity-blindness is structural.** The fairness re-score runs through a code path that literally cannot see name/address — not a prompt instruction to "ignore" them.

---

## 2. Agent graph (LangGraph)

```
        ┌───────────┐
        │  INTAKE   │  Parse uploaded docs + form fields into ApplicationRaw
        └─────┬─────┘
              │
        ┌─────▼─────┐
        │  VERIFY   │  Check presence + cross-doc consistency (name match,
        │           │  income match between pay stub and stated income, etc.)
        └─────┬─────┘
       missing│doc          ┌──────────────────────┐
       ───────┴────────────►│ HOLD_FOR_DOCUMENT     │──► (returns to applicant)
              │ ok           └──────────────────────┘
        ┌─────▼─────┐
        │ EXTRACT   │  LLM-assisted structured extraction into
        │           │  ApplicationFields (Pydantic-validated)
        └─────┬─────┘
              │
        ┌─────▼─────┐
        │  SCORE    │  Pure-Python policy engine → ScoreBreakdown
        │ (policy)  │  (DTI, credit history, income stability, weights,
        │           │  composite, band)
        └─────┬─────┘
              │
        ┌─────▼─────┐
        │ FAIRNESS  │  Re-run SCORE with identity-masked copy of the same
        │ RECHECK   │  ApplicationFields → compare composite scores/bands
        └─────┬─────┘
      mismatch│             ┌──────────────────────┐
       ───────┴────────────►│ FLAG_FAIRNESS_FAIL    │──► forced human review,
              │ match         └──────────────────────┘   never auto-anything
        ┌─────▼─────┐
        │ CHALLENGER│  Optional second model re-scores independently;
        │ COMPARE   │  disagreement > 1 band → force REFER
        └─────┬─────┘
              │
        ┌─────▼─────┐
        │ RECOMMEND │  LLM composes citations + plain-English rationale
        │           │  from the (already-computed) ScoreBreakdown — it
        │           │  explains the number, it doesn't invent it.
        └─────┬─────┘
              │
        ┌─────▼─────┐
        │  DRAFT    │  If DECLINE: draft adverse-action notice (held, not sent)
        │  NOTICE   │  If APPROVE/REFER: skip
        └─────┬─────┘
              │
        ┌─────▼─────┐
        │HUMAN_GATE │  Underwriter reviews full trace + breakdown + citations,
        │           │  approves / overrides (reason required) / requests more info
        └─────┬─────┘
              │
        ┌─────▼─────┐
        │  PERSIST  │  Append-only decision record written to audit store
        └───────────┘
```

Each node is a LangGraph node with a typed input/output (Pydantic models below). Conditional edges branch on `verify.status`, `fairness.match`, and `challenger.agreement`.

---

## 3. Data contracts (Pydantic)

```python
class ApplicationRaw(BaseModel):
    application_id: str
    submitted_at: datetime
    applicant_name: str
    applicant_address: str
    documents: list[UploadedDocument]   # ID, pay stub, bank statement, etc.
    stated_income: float
    stated_monthly_debt: float
    loan_amount_requested: float

class UploadedDocument(BaseModel):
    doc_type: Literal["id", "pay_stub", "bank_statement", "other"]
    file_path: str
    ocr_confidence: float | None = None
    extracted_text: str | None = None

class VerifyResult(BaseModel):
    all_required_present: bool
    missing_docs: list[str]
    consistency_flags: list[str]   # e.g. "stated_income does not match pay stub"
    status: Literal["ok", "hold_for_document"]

class ApplicationFields(BaseModel):
    # Extracted + validated, identity fields kept separate from scoring fields
    identity: IdentityBlock
    income_monthly: float
    debt_monthly: float
    credit_history_years: float
    credit_history_flags: list[str]   # late payments, defaults, etc.
    employment_months_current: int

class IdentityBlock(BaseModel):
    name: str
    address: str

class ScoreBreakdown(BaseModel):
    policy_version: str
    dti_ratio: float
    dti_subscore: float
    credit_history_subscore: float
    income_stability_subscore: float
    weights: dict[str, float]
    composite_score: float
    band: Literal["approve", "refer", "decline"]
    clause_citations: list[ClauseCitation]

class ClauseCitation(BaseModel):
    clause_id: str
    clause_text: str
    factor: str   # which sub-score this clause supports

class FairnessCheck(BaseModel):
    original_band: str
    masked_band: str
    original_composite: float
    masked_composite: float
    match: bool

class ChallengerResult(BaseModel):
    primary_band: str
    challenger_band: str
    bands_agree: bool
    delta: float

class DecisionRecord(BaseModel):
    application_id: str
    policy_version: str
    score_breakdown: ScoreBreakdown
    fairness_check: FairnessCheck
    challenger_result: ChallengerResult | None
    agent_recommendation: Literal["approve", "refer", "decline"]
    rationale: str
    adverse_action_draft: str | None
    human_decision: Literal["approve", "refer", "decline"] | None
    human_reviewer: str | None
    override_reason: str | None
    decided_at: datetime | None
    created_at: datetime
    immutable: bool = True   # enforced at the storage layer, not just a field
```

---

## 4. Policy engine (deterministic, versioned)

`policy/policy_v1.yaml`:

```yaml
version: "v1.2"
effective_date: "2026-01-01"
weights:
  dti: 0.4
  credit_history: 0.35
  income_stability: 0.25
bands:
  approve_min: 0.75
  refer_min: 0.65     # 0.65–0.75 => refer, below 0.65 => decline
clauses:
  DTI-01:
    text: "Debt-to-income ratio must not exceed 43% for automatic approval consideration."
    factor: dti
  CH-01:
    text: "Minimum 2 years of credit history required; late payments in the last 12 months reduce the sub-score proportionally."
    factor: credit_history
  INC-01:
    text: "Minimum 6 months in current employment required for income-stability credit."
    factor: income_stability
```

The scoring function is pure Python: load the active policy version, compute each sub-score from `ApplicationFields`, apply weights, threshold into a band, and attach the clause IDs that were actually used. No LLM call in this function — it is unit-testable and deterministic, which is also what makes test scenarios 1–2 reliably reproducible.

---

## 5. Fairness recheck — structural guarantee

```python
def identity_blind_copy(fields: ApplicationFields) -> ApplicationFields:
    masked = fields.model_copy(deep=True)
    masked.identity = IdentityBlock(name="[REDACTED]", address="[REDACTED]")
    return masked

# The scoring function only ever receives ApplicationFields.
# It has no parameter through which identity could influence the score,
# so masking identity and re-running score() is a true structural test,
# not a prompt-based one.
```

This is important: the fairness check is not "ask the LLM to ignore the name." It is architected so the deterministic scorer literally never receives identity fields in the first place for the masked pass — and in fact never uses identity in the *unmasked* scoring path either, since `ScoreBreakdown` is computed only from financial/credit fields. The two runs should be identical by construction; the test exists to catch a regression (e.g., someone accidentally wiring identity into a future feature), not because identity was ever a scoring input.

---

## 6. Challenger model comparison

- Primary model: your main GitHub Models-backed model (see `SETUP_AND_TOOLS.md`).
- Challenger model: a different model on the same GitHub Models endpoint (e.g., a different family/size).
- Both receive the same `ApplicationFields` + policy excerpt, and are asked to independently reason about the band — but note the **actual band assignment still comes from the deterministic engine** for both; the "challenger" role here is to sanity-check the *rationale/explanation*, and to flag if an independent LLM's read of the policy would suggest a materially different band than the deterministic engine computed (which would indicate a policy-application bug worth a human look, not a model preference).

---

## 7. Governance & audit log

- Every node emits a trace event: `{node, input_hash, output_summary, timestamp, model_used, tokens}`.
- The full trace + `DecisionRecord` is written to an append-only table (`decision_records`), with a separate `decision_amendments` table for any post-hoc human correction — corrections never mutate the original row.
- Refusal/out-of-scope handling: if `VERIFY` or `EXTRACT` cannot proceed (e.g., a non-lending document is uploaded, or the request tries to ask the agent to do something outside application processing), the agent responds with a scoped refusal and logs it — it does not attempt to "be helpful" outside its lane.
- Prompt-injection handling: any free-text field (notes, uploaded document OCR text) is treated as **data, not instructions**. The system prompt for every LLM call explicitly states that content inside `<applicant_data>` tags is untrusted input to be reasoned about, never executed as a command. Test scenario 5 (and its expanded variant) verifies this.

---

## 8. Tech stack summary

| Layer | Choice | Why |
|---|---|---|
| Agent orchestration | LangGraph | Explicit state machine matches the verify→score→recommend flow; easy to add conditional edges for holds/escalation |
| Backend API | FastAPI | Async, Pydantic-native, fast to stand up in a one-day MVP |
| Validation | Pydantic v2 | Same models used for extraction validation, tool I/O, and audit records |
| Model access | GitHub Models API (OpenAI-compatible), authenticated with a GitHub PAT | No separate provider key needed; workshop-friendly; swap models by changing a model string |
| Policy storage | Versioned YAML | Human-readable, diffable, no redeploy needed to change thresholds |
| Vector store (policy RAG) | Chroma (local, file-based) | Zero-infra for a one-day build; fine for a policy corpus this size |
| Persistence | SQLite (upgrade path: Postgres) | Append-only table pattern works the same in both; SQLite is enough for the demo |
| Frontend | React + Tailwind | See `UI_UX_DESIGN.md` |
| OCR | Tesseract (pytesseract) or a vision-capable model call | Only needed if scanned images are supported (scenario 6) |

See `SETUP_AND_TOOLS.md` for exact install commands and how to wire the GitHub PAT.
