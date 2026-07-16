# Credit Decisioning Agent — Wiki

Welcome to the project wiki. This is the comprehensive reference for the **Loan / Credit Application Processing Agent** — a single-pipeline, human-gated credit application processing system built with FastAPI, LangGraph, and GitHub Models API.

> **Capstone Project 05** — GenAI & Agentic AI Engineering Workshop

---

## Quick Navigation

| Page | Description |
|------|-------------|
| [Architecture](Architecture.md) | System design, component diagram, tech stack, design principles |
| [Pipeline](Pipeline.md) | Agent graph walkthrough — every node, conditional edge, and state transition |
| [Policy Engine](Policy-Engine.md) | Deterministic scoring engine — weights, bands, sub-scorers, clause citations |
| [Fairness & Governance](Fairness-Governance.md) | Identity-blind recheck, LLM semantic review, audit trail, immutability |
| [API Reference](API-Reference.md) | All REST endpoints — request/response schemas, examples |
| [Frontend](Frontend.md) | Streamlit UI and React frontend — screens, components, how to run |
| [Deployment](Deployment.md) | Setup instructions, environment config, deployment options |
| [Contributing](Contributing.md) | How to add nodes, endpoints, tests; code conventions |

---

## What This Project Does

A retail lender receives credit applications — each consisting of applicant data and supporting documents (ID, pay stubs, bank statements). The agent:

1. **Verifies** document presence and cross-document consistency
2. **Extracts** structured fields using LLM-assisted extraction
3. **Scores** the application deterministically against a versioned YAML policy
4. **Checks fairness** via identity-blind re-scoring and LLM semantic review
5. **Compares** against an independent challenger model
6. **Recommends** approve/refer/decline with policy clause citations
7. **Drafts** adverse action notices for declines (ECOA/Reg B style)
8. **Waits** at a mandatory human gate — no decision is ever auto-finalised

---

## Design Principles

1. **The LLM never does arithmetic.** Scoring is pure Python against a versioned policy file.
2. **Every recommendation is traceable to a policy clause ID**, not a paraphrase.
3. **Nothing fires without a human click.** APPROVE/REFER/DECLINE are recommendations until an underwriter confirms.
4. **Identity-blindness is structural.** The fairness re-score runs through a code path that literally cannot see name/address.

---

## Tech Stack at a Glance

| Layer | Technology |
|-------|-----------|
| Agent orchestration | LangGraph (StateGraph) |
| Backend API | FastAPI + Uvicorn |
| Validation | Pydantic v2 |
| Model access | GitHub Models API (OpenAI-compatible, PAT auth) |
| Policy storage | Versioned YAML |
| Vector store | Chroma (local, file-based) |
| Persistence | SQLite (WAL mode, append-only) |
| Frontend (primary) | Streamlit (app.py) |
| Frontend (optional) | React + Vite + Tailwind |
| Testing | pytest (86 tests) |
| OCR | pytesseract + Pillow |

---

## Repository Structure

```
loan-agent/
├── app/                          # FastAPI backend
│   ├── main.py                   # App entry point, router registration
│   ├── config.py                 # Settings from .env via pydantic-settings
│   ├── agent/
│   │   ├── graph.py              # LangGraph state machine
│   │   ├── nodes/                # Pipeline node implementations
│   │   └── prompts/              # LLM prompt templates
│   ├── models/                   # Pydantic data contracts
│   ├── routers/                  # API endpoint modules
│   ├── tools/                    # GitHub Models client, OCR
│   ├── db/                       # SQLAlchemy + SQLite
│   └── middleware/                # Rate limiting
├── policy/
│   ├── policy_v1.yaml            # Active credit policy
│   └── policy_corpus/            # Longer-form policy docs for RAG
├── frontend/                     # React + Vite + Tailwind
├── tests/                        # pytest test suite
├── scripts/                      # Utility scripts
├── docs/                         # Design documents
├── wiki/                         # This wiki
├── app.py                        # Streamlit frontend
├── requirements.txt
├── setup.ps1                     # Windows setup
├── start.sh / start.ps1          # Startup scripts
└── .env.example                  # Environment template
```
