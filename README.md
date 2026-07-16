# Credit Decisioning Agent

A single-pipeline, human-gated credit application processing agent built with
FastAPI + LangGraph + GitHub Models API.

> **Capstone Project 05** · GenAI & Agentic AI Engineering Workshop

---

## Key Features

- **Deterministic scoring** — pure Python policy engine, no LLM arithmetic, same inputs = same output
- **Two-layer fairness check** — structural identity-blind recheck + LLM semantic bias review
- **Challenger model comparison** — independent LLM re-score; disagreement forces REFER
- **Mandatory human gate** — no decision is ever auto-finalised; every application requires underwriter approval
- **Adverse action notices** — ECOA/Reg B-style drafts held for human review before sending
- **Full audit trail** — append-only decision records, pipeline trace, immutable amendments
- **Policy-as-config** — credit policy lives in YAML; change thresholds without touching code
- **Two UIs** — Streamlit (applicant portal) + React (underwriter workspace)
- **Document management** — upload, verify, download, PDF report generation
- **Rate limiting** — configurable per-IP limits with Retry-After headers

---

## Architecture

```
POST /applications → VERIFY → EXTRACT (LLM) → SCORE (Python) →
  CHALLENGER (LLM) → FAIRNESS_RECHECK (Python) → FAIRNESS_LLM_REVIEW (LLM) →
    RECOMMEND (LLM) → DRAFT_NOTICE (LLM) → HUMAN_GATE (await underwriter)
```

| Node | Type | What it does |
|------|------|-------------|
| VERIFY | Python | Document presence + cross-doc consistency + name matching |
| EXTRACT | LLM | Structured field extraction into Pydantic-validated model |
| SCORE | **Python (no LLM)** | Deterministic scoring against versioned YAML policy |
| CHALLENGER | LLM | Independent model re-score; disagreement > 1 band forces REFER |
| FAIRNESS_RECHECK | Python | Re-runs SCORE with identity fields masked; band must match |
| FAIRNESS_LLM_REVIEW | LLM | Scans for identity-proxy language in rationale |
| RECOMMEND | LLM | Composes rationale + recommendation from ScoreBreakdown |
| DRAFT_NOTICE | LLM | Adverse-action notice for DECLINE (held, not sent) |
| HUMAN_GATE | Terminal | All paths converge; awaits `POST /decision` |

See [Pipeline](https://github.com/upputurisanjana/Loan-Credit-Processing-Agent/wiki/Pipeline) for the full walkthrough.

---

## Quick Start

### Windows (PowerShell)

```powershell
# 1. One-time setup
.\setup.ps1

# 2. Add your GitHub PAT
notepad .env

# 3. Start backend + frontend
.\start.ps1

# 4. Open docs
start http://localhost:8000/docs
```

Modes: `.\start.ps1 backend` · `.\start.ps1 frontend` · `.\start.ps1 streamlit` · `.\start.ps1 all` · `.\start.ps1 demo`

### Linux / macOS (bash)

```bash
# 1. Create virtualenv
python3 -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env — add GITHUB_TOKEN

# 4. Start
./start.sh

# 5. Open docs
open http://localhost:8000/docs
```

---

## End-to-end Demo

**bash / curl:**

```bash
# Submit the fixture application
curl -s -X POST http://localhost:8000/applications \
     -H "Content-Type: application/json" \
     -d @tests/fixtures/clear_approve.json | python3 -m json.tool

# Record the underwriter approval
curl -s -X POST http://localhost:8000/applications/APP-001/decision \
     -H "Content-Type: application/json" \
     -d '{"human_decision":"approve","human_reviewer":"underwriter_1"}' \
     | python3 -m json.tool
```

**PowerShell:**

```powershell
$body = Get-Content tests\fixtures\clear_approve.json -Raw
Invoke-RestMethod -Method Post -Uri http://localhost:8000/applications `
    -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 10

$decision = '{"human_decision":"approve","human_reviewer":"underwriter_1"}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/applications/APP-001/decision `
    -ContentType "application/json" -Body $decision | ConvertTo-Json -Depth 10
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent orchestration | LangGraph (StateGraph) |
| Backend API | FastAPI + Uvicorn |
| Data contracts | Pydantic v2 |
| Model access | GitHub Models API (OpenAI-compatible, PAT auth) |
| Policy engine | Versioned YAML (deterministic Python) |
| Vector store | Chroma (local) |
| Database | SQLite (WAL mode, append-only) |
| Primary UI | Streamlit (app.py) |
| Underwriter UI | React + Vite + Tailwind |
| Testing | pytest (86 tests) |
| OCR | pytesseract + Pillow |
| PDF generation | fpdf2 |

---

## Environment Variables

```bash
# Required
GITHUB_TOKEN=ghp_...                        # GitHub PAT with models:read scope

# Optional (defaults shown)
GITHUB_MODELS_ENDPOINT=https://models.github.ai/inference
PRIMARY_MODEL=openai/gpt-4o-mini
CHALLENGER_MODEL=meta/llama-3.1-70b-instruct
POLICY_PATH=./policy/policy_v1.yaml
DATABASE_URL=sqlite:///./audit.db
LENDER_NAME=Credit Decisioning Ltd
LENDER_CONTACT=decisions@creditagent.example.com | 0800 123 4567
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:8000
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60
```

---

## Project Structure

```
loan-agent/
├── app/                          # FastAPI backend
│   ├── main.py                   # App entry, routers, /health
│   ├── config.py                 # Settings from .env
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
│   └── policy_v1.yaml            # Active credit policy
├── frontend/                     # React + Vite + Tailwind
├── tests/                        # pytest (86 tests)
├── scripts/                      # Utility scripts
├── docs/                         # Design documents
├── app.py                        # Streamlit frontend
├── requirements.txt
├── setup.ps1 / start.sh / start.ps1 / start.bat
└── .env.example
```

---

## Wiki

Full documentation lives on the [GitHub Wiki](https://github.com/upputurisanjana/Loan-Credit-Processing-Agent/wiki):

| Page | Description |
|------|-------------|
| [Architecture](https://github.com/upputurisanjana/Loan-Credit-Processing-Agent/wiki/Architecture) | System design, components, data flow |
| [Pipeline](https://github.com/upputurisanjana/Loan-Credit-Processing-Agent/wiki/Pipeline) | Agent graph — every node and conditional edge |
| [Policy Engine](https://github.com/upputurisanjana/Loan-Credit-Processing-Agent/wiki/Policy-Engine) | Deterministic scoring — weights, bands, clauses |
| [Fairness & Governance](https://github.com/upputurisanjana/Loan-Credit-Processing-Agent/wiki/Fairness-Governance) | Identity-blind checks, audit trail, immutability |
| [API Reference](https://github.com/upputurisanjana/Loan-Credit-Processing-Agent/wiki/API-Reference) | All REST endpoints with request/response schemas |
| [Frontend](https://github.com/upputurisanjana/Loan-Credit-Processing-Agent/wiki/Frontend) | Streamlit + React UI guide |
| [Deployment](https://github.com/upputurisanjana/Loan-Credit-Processing-Agent/wiki/Deployment) | Setup, config, deployment options |
| [Contributing](https://github.com/upputurisanjana/Loan-Credit-Processing-Agent/wiki/Contributing) | How to extend — nodes, endpoints, tests |

Additional design docs in [`docs/`](docs/):

| Document | Description |
|----------|-------------|
| [spec.md](docs/spec.md) | Full project specification |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Technical architecture design |
| [UI_UX_DESIGN.md](docs/UI_UX_DESIGN.md) | UI/UX design system |
| [SETUP_AND_TOOLS.md](docs/SETUP_AND_TOOLS.md) | Detailed setup instructions |
| [ENHANCEMENTS_ROADMAP.md](docs/ENHANCEMENTS_ROADMAP.md) | Post-MVP enhancement phases |
| [EVALUATION_REPORT.md](docs/EVALUATION_REPORT.md) | Test results and evaluation |

---

## Key Constraints

- **`app/agent/nodes/score.py` has zero LLM imports** — scoring is pure Python
- **No application moves past HUMAN_GATE** without an explicit `POST /decision`
- **`.env` is git-ignored** — the GitHub token is never logged
- **Decision records are append-only** — corrections via amendments, never edits
- **This is a single decisioning agent**, not multiple autonomous agents

---

## Testing

```bash
pytest tests/ -v                           # all 86 tests
pytest tests/test_scenarios.py -v           # 5 end-to-end scenarios
pytest tests/test_fairness_structural.py -v  # 21 identity-blind tests
pytest tests/test_draft_notice.py -v         # 12 adverse action tests
pytest tests/test_challenger_compare.py -v   # 14 challenger tests
pytest tests/test_http_endpoints.py -v       # HTTP integration (needs server)
```

---

## License

Workshop capstone project.
