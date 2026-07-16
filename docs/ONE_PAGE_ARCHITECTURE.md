# Architecture — Credit Decisioning Agent
**One-page reference · v1.2 · July 2026**

---

## System Overview

```
╔══════════════════════════════╗     ╔══════════════════════════════╗
║   APPLICANT PORTAL           ║     ║   REVIEWER DASHBOARD         ║
║   Streamlit  :8501           ║     ║   React + Vite  :5173        ║
║                              ║     ║                              ║
║  • Submit application form   ║     ║  • Dashboard + metrics       ║
║  • Auto-generated App ID     ║     ║  • Case queue table          ║
║  • Upload PDF documents      ║     ║  • Application detail view   ║
║  • Check status by ref no.   ║     ║  • Score breakdown + rationale║
║  • Plain-English outcome     ║     ║  • Approve / Refer / Decline ║
╚══════════╤═══════════════════╝     ╚══════════╤═══════════════════╝
           │  REST / JSON                        │  REST / JSON
           └─────────────────┬──────────────────┘
                             ▼
╔═════════════════════════════════════════════════════════════════════╗
║                        FastAPI  :8000                               ║
║                                                                     ║
║  POST /applications          → submit + run pipeline               ║
║  GET  /applications/{id}     → get record (internal fields hidden) ║
║  POST /applications/{id}/decision   → underwriter decision         ║
║  POST /applications/{id}/documents  → upload PDFs                  ║
║  GET  /applications/{id}/pdf        → reviewer PDF report          ║
║  GET  /queue                 → all applications summary            ║
║  GET  /health                → live model probe                    ║
╚══════════════════════════╤══════════════════════════════════════════╝
                           │
                           ▼
╔═════════════════════════════════════════════════════════════════════╗
║              LangGraph Decisioning Pipeline                         ║
║                                                                     ║
║  ┌─────────┐  ok   ┌─────────┐  ┌─────────┐  ┌──────────────────┐ ║
║  │ VERIFY  ├──────►│ EXTRACT ├─►│  SCORE  ├─►│FAIRNESS_RECHECK  │ ║
║  │(Python) │       │  (LLM)  │  │(Python) │  │   (Python)       │ ║
║  └────┬────┘       └─────────┘  └─────────┘  └────────┬─────────┘ ║
║  hold │                          +CHALLENGER            │match      ║
║       ▼                          (LLM)         mismatch │           ║
║  ┌─────────┐                               ┌───────────▼─────────┐ ║
║  │  HOLD   │                               │  FLAG_FAIRNESS_FAIL │ ║
║  │  (END)  │                               │  → force REFER      │ ║
║  └─────────┘                               └───────────┬─────────┘ ║
║                                                        │           ║
║                          ┌─────────────────────────────┘           ║
║                          ▼                                         ║
║                    ┌───────────┐  decline  ┌──────────────┐        ║
║                    │ RECOMMEND ├──────────►│ DRAFT_NOTICE │        ║
║                    │   (LLM)   │           │    (LLM)     │        ║
║                    └─────┬─────┘           └──────┬───────┘        ║
║                          └───────────┬────────────┘                ║
║                                      ▼                             ║
║                               ┌────────────┐                       ║
║                               │ HUMAN_GATE │  ← ALL paths end here ║
║                               │  (END)     │  human_decision=null  ║
║                               └────────────┘                       ║
╚═════════════════════════════════════════════════════════════════════╝
                           │
           ┌───────────────┼───────────────────┐
           ▼               ▼                   ▼
   ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐
   │  SQLite DB   │  │ uploads/     │  │ GitHub Models API │
   │  audit.db    │  │ (PDF files)  │  │ (PAT auth)        │
   │              │  │              │  │                   │
   │ decision_    │  │ id.pdf       │  │ gpt-4o-mini       │
   │ records      │  │ pay_stub.pdf │  │ → EXTRACT         │
   │ (append-only)│  │ bank_stmt.pdf│  │ → RECOMMEND       │
   │              │  │              │  │ → DRAFT_NOTICE    │
   │ decision_    │  │ .metadata.   │  │                   │
   │ amendments   │  │  json        │  │                   │
   └──────────────┘  └──────────────┘  │ → CHALLENGER      │
                                        └───────────────────┘
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Scoring is pure Python, zero LLM** | Same inputs always produce the same score. Auditable, testable, no prompt drift. |
| **Fairness via structural isolation** | `IdentityBlock` is a separate sub-object the scorer never reads. Re-running the same function with masked identity is a true structural test, not a prompt instruction. |
| **Frozen `DecisionRecord`** | Pydantic `frozen=True` prevents in-place mutation. Updates create a new object. DB enforces append-only via `WHERE human_decision IS NULL` guard. |
| **Internal fields hidden from API** | `fairness_check`, `challenger_result`, `pipeline_trace` are stripped by `_public_payload()`. They run and are stored — never sent to the browser. |
| **No auto-finalisation** | Every path in the LangGraph ends at `HUMAN_GATE`. `human_decision` is always `null` after pipeline completes. Only `POST /decision` can set it. |
| **Policy in YAML** | Thresholds, weights, and clause text live in `policy/policy_v1.yaml`. Policy changes require no code change. Every decision record stores which version was active. |

---

## Data Flow — Single Application

```
Applicant submits form (Streamlit)
  │
  ├─ POST /applications/{id}/documents   ← PDF files uploaded first
  │
  └─ POST /applications                  ← ApplicationRaw JSON
        │
        ├─ VERIFY: check doc presence + income consistency
        │     └─ missing docs → hold_for_document (stop)
        │
        ├─ EXTRACT (LLM): parse OCR text → structured fields
        │     └─ error → status=error (stop)
        │
        ├─ SCORE (Python): DTI + credit history + income stability
        │     └─ composite_score, band, clause_citations
        │
        ├─ CHALLENGER (LLM): independent band assessment
        │     └─ >1 band gap → forces REFER at recommend time
        │
        ├─ FAIRNESS_RECHECK (Python): re-score with identity masked
        │     └─ mismatch → FLAG_FAIRNESS_FAIL → forces REFER
        │
        ├─ RECOMMEND (LLM): write plain-English rationale
        │
        ├─ DRAFT_NOTICE (LLM): adverse action draft if band=decline
        │
        └─ HUMAN_GATE: status=pending_human_review
              │
              └─ POST /applications/{id}/decision  ← underwriter acts
                    └─ human_decision recorded, override_reason if needed
```

---

## Scoring Formula (Policy v1.2)

```
DTI ratio  = monthly_debt / monthly_income

DTI subscore:
  ≤ 0.30  → 1.0
  ≤ 0.43  → linear 1.0 → 0.5
  ≤ 0.55  → linear 0.5 → 0.0
  > 0.55  → 0.0

Credit History subscore:
  < 2 years   → 0.0                    [CH-01]
  2–5 years   → linear 0.0 → 1.0
  ≥ 5 years   → 1.0
  late_payment_12m → −0.30             [CH-02]
  default_36m/older → −0.50            [CH-03]
  (floor: 0.0)

Income Stability subscore:
  < 6 months  → 0.0                    [INC-01]
  6–24 months → linear 0.0 → 1.0
  ≥ 24 months → 1.0                    [INC-02]

Composite = 0.40 × DTI + 0.35 × CreditHistory + 0.25 × IncomeStability

Band:
  ≥ 0.75 → APPROVE
  ≥ 0.65 → REFER
  < 0.65 → DECLINE
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Agent framework | LangGraph 0.4 |
| LLM API | GitHub Models (OpenAI-compatible, PAT auth) |
| Primary model | `openai/gpt-4o-mini` |
| Challenger model | `meta/llama-3.1-70b-instruct` |
| Backend | FastAPI 0.115 + Uvicorn |
| Data validation | Pydantic v2 |
| Database | SQLite (WAL mode, append-only) |
| PDF generation | fpdf2 |
| Applicant UI | Streamlit 1.45 |
| Reviewer UI | React 19 + Vite + Tailwind CSS |
| Tests | pytest 8.4 + pytest-asyncio |
