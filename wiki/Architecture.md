# Architecture

This page describes the full system architecture — components, data flow, design decisions, and the reasoning behind each choice.

---

## Design Principles

These four rules are non-negotiable and shape every architectural decision:

1. **The LLM never does arithmetic.** Scoring is pure Python against a versioned policy file. The LLM extracts, explains, drafts, and reasons in natural language — it never computes the DTI ratio or the composite score.

2. **Every recommendation is traceable to a policy clause ID**, not a paraphrase. Citations point at `policy_v1.yaml` clause IDs (e.g., `DTI-01`, `CH-02`).

3. **Nothing touching the applicant's outcome fires without a human click.** APPROVE/REFER/DECLINE are recommendations until an underwriter confirms.

4. **Identity-blindness is structural.** The fairness re-score runs through a code path that literally cannot see name/address — not a prompt instruction to "ignore" them.

---

## System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                               │
│  Streamlit (app.py :8501)  |  React (frontend/ :5173)              │
│  Applicant submit + status  |  Underwriter queue + decision         │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │ REST / JSON
┌─────────────────────────────────▼────────────────────────────────────┐
│                          FastAPI Backend (:8000)                      │
│                                                                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ Intake   │ │Decision  │ │ Queue    │ │Documents │ │ Audit /  │   │
│  │ Router   │ │Router    │ │ Router   │ │ Router   │ │ Amend /  │   │
│  │          │ │          │ │          │ │          │ │ Analysis │   │
│  └────┬─────┘ └────┬─────┘ └──────────┘ └────┬─────┘ └──────────┘   │
│       │            │                          │                       │
│  ┌────▼────────────▼──────────────────────────▼────────────────────┐  │
│  │              LangGraph Decisioning Agent                        │  │
│  │                                                                   │  │
│  │  VERIFY → EXTRACT → SCORE → CHALLENGER →                        │  │
│  │    FAIRNESS_RECHECK → FAIRNESS_LLM_REVIEW →                     │  │
│  │      RECOMMEND → DRAFT_NOTICE → HUMAN_GATE                      │  │
│  └──────┬──────────────┬──────────────┬──────────────┬─────────────┘  │
│         │              │              │              │                 │
│  ┌──────▼─────┐ ┌──────▼──────┐ ┌─────▼──────┐ ┌─────▼──────────┐   │
│  │ Doc Verify │ │ Policy RAG  │ │ Policy     │ │ GitHub Models   │   │
│  │ + Name     │ │ (Chroma)    │ │ Score      │ │ API (PAT auth)  │   │
│  │ Consistency│ │             │ │ Engine     │ │ primary +       │   │
│  │ (Pydantic) │ │             │ │(pure python│ │ challenger      │   │
│  └────────────┘ └─────────────┘ │  no LLM)   │ └─────────────────┘   │
│                                  └────────────┘                       │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │        Audit Log Store (append-only, SQLite + WAL)            │    │
│  └───────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### FastAPI Backend (`app/`)

| Module | Purpose |
|--------|---------|
| `app/main.py` | FastAPI app creation, CORS, rate limiting, router registration, `/health` endpoint |
| `app/config.py` | `Settings` class via pydantic-settings, loads `.env`, injects into `os.environ` |
| `app/routers/intake.py` | `POST /applications` — submits application, runs pipeline, persists to DB |
| `app/routers/decisions.py` | `POST /decision`, `POST /request-info`, `PATCH /notice` — human gate |
| `app/routers/queue.py` | `GET /queue` — summary list for the case queue UI |
| `app/routers/audit.py` | `GET /trace` — pipeline trace for audit trail viewer |
| `app/routers/amendments.py` | `POST /amendments`, `GET /amendments` — post-hoc corrections |
| `app/routers/analysis.py` | `GET /fairness`, `GET /challenger`, `POST /challenger/rerun` |
| `app/routers/documents.py` | `POST /documents`, `GET /documents`, `PATCH /verify`, `GET /pdf` |
| `app/middleware/rate_limit.py` | In-process rate limiter (10 POST/min/IP, `Retry-After` header) |

### LangGraph Agent (`app/agent/`)

| Module | Purpose |
|--------|---------|
| `graph.py` | StateGraph definition, node wiring, conditional edges, `run_pipeline()` entry point |
| `nodes/verify.py` | Document presence + cross-doc consistency + name matching + OCR confidence |
| `nodes/extract.py` | LLM-assisted structured extraction into `ApplicationFields` |
| `nodes/score.py` | **Pure Python** deterministic scoring — zero LLM imports |
| `nodes/challenger_compare.py` | Independent LLM re-score via CHALLENGER_MODEL |
| `nodes/fairness_recheck.py` | Structural identity-blind re-score (Python, deterministic) |
| `nodes/fairness_llm_review.py` | LLM semantic scan for identity-proxy language in rationale |
| `nodes/recommend.py` | LLM composes rationale + recommendation from ScoreBreakdown |
| `nodes/draft_notice.py` | LLM generates ECOA-style adverse-action notice (decline only) |

### Data Models (`app/models/`)

| Model | Fields |
|-------|--------|
| `ApplicationRaw` | application_id, submitted_at, applicant_name/address, documents, stated_income/debt, loan_amount |
| `ApplicationFields` | identity (IdentityBlock), income_monthly, debt_monthly, credit_history_years/flags, employment_months |
| `VerifyResult` | all_required_present, missing_docs, consistency_flags, status |
| `ScoreBreakdown` | policy_version, dti_ratio, sub-scores, weights, composite_score, band, clause_citations |
| `FairnessCheck` | original_band, masked_band, composite scores, match, llm_review_flag |
| `ChallengerResult` | primary_band, challenger_band, bands_agree, delta |
| `DecisionRecord` | Full audit record — all of the above plus human_decision, rationale, adverse_action_draft, pipeline_trace |

### Tools (`app/tools/`)

| Tool | Purpose |
|------|---------|
| `github_models_client.py` | OpenAI-compatible client wrapper for GitHub Models API (PAT auth) |
| `ocr.py` | pytesseract wrapper with confidence scoring |

### Database (`app/db/`)

| File | Purpose |
|------|---------|
| `database.py` | SQLAlchemy engine, singleton connection, CRUD functions |
| `schema.sql` | DDL for `decision_records` (append-only) and `decision_amendments` tables |

---

## Data Flow

1. **Intake**: Client sends `POST /applications` with `ApplicationRaw` JSON
2. **Pipeline**: `run_pipeline(raw)` invokes the LangGraph compiled graph
3. **State machine**: `AgentState` TypedDict is threaded through every node
4. **Branching**: Conditional edges on `verify.status`, `fairness.match`, `challenger.agreement`
5. **Convergence**: All paths end at `HUMAN_GATE` with `status = "pending_human_review"`
6. **Persistence**: `DecisionRecord` written to SQLite (WAL mode), rehydrated into memory on startup
7. **Human action**: Underwriter calls `POST /decision` → record updated (new instance, never mutated)

---

## In-Memory Store + DB Write-Through

```
POST /applications  →  run_pipeline()  →  insert_decision(db)  →  _store[app_id] = record
                                                                       ↑
POST /decision      →  _store[app_id].model_copy(update=...)  →  db_record_human_decision()
                                                                       ↑
GET /queue          →  iterate _store.values()  →  return summaries
```

- All writes go to DB first — if DB fails, HTTP 500 is returned and the in-memory store is NOT populated
- On startup, `_load_store_from_db()` rehydrates the in-memory store from SQLite
- `_public_payload()` strips internal fields (`fairness_check`, `challenger_result`, `pipeline_trace`) from API responses

---

## Tech Stack Rationale

| Choice | Why |
|--------|-----|
| **LangGraph** | Explicit state machine matches the verify->score->recommend flow; conditional edges for holds/escalation |
| **FastAPI** | Async, Pydantic-native, fast to stand up, interactive docs at `/docs` |
| **Pydantic v2** | Same models for extraction validation, tool I/O, and audit records |
| **GitHub Models API** | No separate provider key; workshop-friendly; swap models by changing a string |
| **Versioned YAML policy** | Human-readable, diffable, no redeploy needed to change thresholds |
| **Chroma** | Zero-infra local vector store for policy RAG |
| **SQLite + WAL** | Append-only pattern; upgrade path to Postgres; enough for demo |
| **Streamlit** | Rapid prototyping for applicant-facing UI |
| **React + Tailwind** | Production-quality underwriter UI with full design system |
