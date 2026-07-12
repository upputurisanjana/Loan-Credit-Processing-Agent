# PROJECT_STRUCTURE.md — Loan / Credit Application Processing Agent

```
loan-agent/
├── .env                          # secrets (git-ignored) — GITHUB_TOKEN lives here
├── .env.example                  # committed template, no real values
├── .gitignore
├── README.md                     # short pointer to spec.md + how to run
├── spec.md
├── ARCHITECTURE.md
├── UI_UX_DESIGN.md
├── SETUP_AND_TOOLS.md
├── ENHANCEMENTS_ROADMAP.md
├── PROJECT_STRUCTURE.md          # this file
│
├── policy/
│   ├── policy_v1.yaml            # active policy: weights, bands, clauses
│   ├── policy_v0.yaml            # prior version, kept for the diff view
│   └── policy_corpus/            # longer-form policy docs for RAG (if used
│       └── lending_policy.md     #   beyond the structured clause YAML)
│
├── app/                            # FastAPI backend
│   ├── main.py                     # FastAPI app, route registration
│   ├── config.py                   # loads .env, exposes settings object
│   ├── models/
│   │   ├── application.py          # ApplicationRaw, ApplicationFields, IdentityBlock
│   │   ├── verification.py         # VerifyResult, UploadedDocument
│   │   ├── scoring.py               # ScoreBreakdown, ClauseCitation
│   │   ├── fairness.py              # FairnessCheck, ChallengerResult
│   │   └── decision.py              # DecisionRecord, DecisionAmendment
│   ├── agent/
│   │   ├── graph.py                 # LangGraph state machine wiring all nodes
│   │   ├── nodes/
│   │   │   ├── intake.py
│   │   │   ├── verify.py
│   │   │   ├── extract.py
│   │   │   ├── score.py             # pure-Python scoring, NO LLM call
│   │   │   ├── fairness_recheck.py
│   │   │   ├── challenger_compare.py
│   │   │   ├── recommend.py         # LLM composes rationale from ScoreBreakdown
│   │   │   └── draft_notice.py      # adverse-action notice drafting
│   │   └── prompts/
│   │       ├── extract_prompt.py
│   │       ├── recommend_prompt.py
│   │       └── notice_prompt.py
│   ├── tools/
│   │   ├── doc_verify_tool.py       # presence + cross-doc consistency checks
│   │   ├── ocr_tool.py              # pytesseract wrapper, confidence scoring
│   │   ├── policy_rag_tool.py       # Chroma-backed clause retrieval
│   │   └── github_models_client.py  # OpenAI-compatible client wrapper, PAT auth
│   ├── routers/
│   │   ├── intake.py                # POST /applications
│   │   ├── decisions.py             # GET/POST /applications/{id}/decision
│   │   ├── queue.py                 # GET /queue
│   │   └── audit.py                 # GET /applications/{id}/trace, /export
│   ├── db/
│   │   ├── database.py              # SQLAlchemy engine/session
│   │   └── schema.sql                # append-only decision_records table DDL
│   └── evaluation/
│       ├── trace_eval.py            # trace-correctness checks
│       ├── tool_call_eval.py        # tool-call accuracy checks
│       └── kpi_report.py            # turnaround, straight-through rate, audit-pass rate
│
├── tests/
│   ├── fixtures/
│   │   ├── clear_approve.json
│   │   ├── borderline_refer.json
│   │   ├── missing_document.json
│   │   ├── fairness_pair_a.json     # original identity
│   │   ├── fairness_pair_b.json     # swapped identity, same financials
│   │   ├── injection_note.json
│   │   ├── scanned_low_quality.png
│   │   ├── challenger_disagreement.json
│   │   ├── override_case.json
│   │   └── decline_case.json
│   ├── test_scenarios.py            # the 10 scenarios from spec.md Section 5
│   ├── test_policy_engine.py        # unit tests on pure scoring function
│   └── test_fairness_structural.py  # verifies scorer literally can't see identity
│
├── frontend/                        # React + Vite + Tailwind
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── styles/
│   │   │   └── tokens.css           # palette, type scale from UI_UX_DESIGN.md
│   │   ├── components/
│   │   │   ├── StatusPill.tsx
│   │   │   ├── ScoreBar.tsx
│   │   │   ├── CompositeScoreGauge.tsx
│   │   │   ├── ClauseCitationChip.tsx
│   │   │   ├── QueueTable.tsx
│   │   │   ├── VerificationStrip.tsx
│   │   │   ├── FairnessCard.tsx
│   │   │   ├── ChallengerCard.tsx
│   │   │   ├── DecisionActionBar.tsx
│   │   │   ├── DecisionModal.tsx
│   │   │   ├── TraceTimeline.tsx
│   │   │   ├── NoticeEditor.tsx
│   │   │   └── PolicyDiffView.tsx
│   │   ├── pages/
│   │   │   ├── CaseQueuePage.tsx
│   │   │   ├── ApplicationDetailPage.tsx
│   │   │   ├── AuditTrailPage.tsx
│   │   │   └── PolicyAdminPage.tsx
│   │   └── api/
│   │       └── client.ts            # thin fetch wrapper to FastAPI backend
│   ├── tailwind.config.js
│   ├── index.html
│   └── package.json
│
└── scripts/
    ├── seed_demo_data.py             # populate a few queue items for the demo
    └── run_eval_suite.sh             # runs pytest + prints KPI summary
```

## File-count sanity check
This is intentionally more granular than a one-day MVP strictly needs. Build order priority for a one-day timebox:

**Must build (core path, ~day 1 morning–afternoon):**
`app/models/*`, `app/agent/graph.py` + `nodes/{verify,extract,score,recommend}.py`, `app/tools/github_models_client.py`, `app/routers/{intake,decisions}.py`, `policy/policy_v1.yaml`, minimal `CaseQueuePage` + `ApplicationDetailPage` + `DecisionActionBar` + `DecisionModal`.

**Should build (governance completeness, ~day 1 evening):**
`fairness_recheck.py`, `test_scenarios.py` (all 5 original scenarios passing), `TraceTimeline`, audit persistence.

**Stretch (if time remains):**
`challenger_compare.py`, `draft_notice.py` + `NoticeEditor`, OCR pipeline, `PolicyDiffView`, KPI report.
