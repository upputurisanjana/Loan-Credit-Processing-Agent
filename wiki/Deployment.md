# Deployment

Everything needed to get from zero to a running system, plus deployment considerations.

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend runtime |
| npm | 9+ | Frontend package manager |
| GitHub PAT | models:read scope | LLM API access via GitHub Models |

---

## Quick Start — Windows (PowerShell)

```powershell
# 1. One-time setup (creates .venv, installs deps, copies .env.example → .env)
.\setup.ps1

# 2. Edit .env — add your GITHUB_TOKEN
notepad .env

# 3. Start backend + frontend
.\start.ps1

# 4. Interactive docs
start http://localhost:8000/docs
```

**Modes:**
```powershell
.\start.ps1              # backend + React frontend (default)
.\start.ps1 backend      # backend only
.\start.ps1 frontend     # React frontend only
.\start.ps1 streamlit    # backend + Streamlit UI
.\start.ps1 all          # backend + React + Streamlit
.\start.ps1 demo         # start both + auto-submit fixture
```

> **Migrating from WSL?** Your old `.venv` was built for Linux and won't work on Windows. `setup.ps1` detects and removes it automatically.

---

## Quick Start — Linux / macOS (bash)

```bash
# 1. Create virtualenv
python3 -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure credentials
cp .env.example .env
# Edit .env — add your GITHUB_TOKEN

# 4. Start the API server
./start.sh              # backend + frontend
# or
uvicorn app.main:app --reload --port 8000

# 5. Interactive docs
open http://localhost:8000/docs
```

---

## Environment Configuration

All configuration lives in `.env` (git-ignored). Copy `.env.example` to `.env` and fill in real values:

```bash
# GitHub Models — OpenAI-compatible endpoint authenticated with a GitHub PAT
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_MODELS_ENDPOINT=https://models.github.ai/inference

# Models — swap by changing model strings
PRIMARY_MODEL=openai/gpt-4o-mini
CHALLENGER_MODEL=meta/llama-3.1-70b-instruct

# Policy — path to the active policy YAML
POLICY_PATH=./policy/policy_v1.yaml

# Database — SQLite for demo; swap to postgres:// for production
DATABASE_URL=sqlite:///./audit.db

# Lender identity — shown in adverse action notices
LENDER_NAME=Credit Decisioning Ltd
LENDER_CONTACT=decisions@creditagent.example.com | 0800 123 4567

# CORS — comma-separated allowed origins
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:8000

# Rate limiting
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60
```

---

## GitHub PAT Setup

1. GitHub → **Settings → Developer settings → Personal access tokens**
2. Create a token with **`models:read`** scope (least privilege)
3. Copy the token once (it won't be shown again)
4. Paste into `.env` as `GITHUB_TOKEN=ghp_...`

**Never commit `.env`** — it's in `.gitignore`. If it leaks, rotate the token immediately.

---

## Swapping Models

Change `PRIMARY_MODEL` and/or `CHALLENGER_MODEL` in `.env` to use different models:

```
PRIMARY_MODEL=openai/gpt-4o-mini          # fast, cheap
PRIMARY_MODEL=openai/gpt-4o               # more capable
CHALLENGER_MODEL=meta/llama-3.1-70b-instruct  # different model family
```

No code changes needed — the GitHub Models API endpoint is the same for all models.

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | API status + model reachability probes |
| `/docs` | GET | Swagger UI (interactive API docs) |
| `/redoc` | GET | ReDoc (alternative API docs) |
| `/applications` | POST | Submit a new application |
| `/applications/{id}` | GET | Retrieve an application |
| `/applications/{id}/decision` | POST | Underwriter records final decision |
| `/applications/{id}/request-info` | POST | Request additional information |
| `/applications/{id}/notice` | PATCH | Save edited adverse action notice |
| `/applications/{id}/trace` | GET | Full pipeline trace |
| `/applications/{id}/fairness` | GET | Fairness recheck result |
| `/applications/{id}/challenger` | GET | Challenger model result |
| `/applications/{id}/challenger/rerun` | POST | Re-run challenger LLM |
| `/applications/{id}/documents` | POST/GET | Upload/list documents |
| `/applications/{id}/documents/{file}` | GET | Download a document |
| `/applications/{id}/documents/{file}/verify` | PATCH | Verify/reject a document |
| `/applications/{id}/pdf` | GET | Generate PDF report |
| `/applications/{id}/amendments` | POST/GET | Post-hoc corrections |
| `/queue` | GET | Case queue summary |

---

## Ports

| Service | Default Port | Config |
|---------|-------------|--------|
| FastAPI backend | 8000 | `BACKEND_PORT` env var |
| React frontend | 5173 | `FRONTEND_PORT` env var |
| Streamlit UI | 8501 | `STREAMLIT_PORT` env var |

---

## Production Considerations

### Database

- **Demo:** SQLite with WAL mode (built-in, zero config)
- **Production:** Swap `DATABASE_URL` to `postgresql://...` — the append-only pattern works identically in both

### Rate Limiting

- **Demo:** In-process rate limiter (10 POST/min/IP)
- **Production:** Redis-backed rate limiter for multi-worker deployments

### Authentication

- **Demo:** No auth — role toggle only
- **Production:** SSO + role-based access (underwriter, senior underwriter, compliance officer, admin)

### Scaling

- Single-worker FastAPI with SQLite is sufficient for demo/workshop
- For production: multiple Uvicorn workers + Postgres + Redis cache
- The append-only database pattern scales well for audit-heavy workloads

### CORS

Set `ALLOWED_ORIGINS` in `.env` to your production domain:

```
ALLOWED_ORIGINS=https://your-app.example.com,https://admin.example.com
```

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test files
pytest tests/test_scenarios.py -v           # 5 end-to-end scenarios
pytest tests/test_fairness_structural.py -v  # 21 fairness tests
pytest tests/test_draft_notice.py -v         # 12 notice tests
pytest tests/test_challenger_compare.py -v   # 14 challenger tests
pytest tests/test_http_endpoints.py -v       # HTTP integration (requires live server)
```

**86 tests total, 0 failures.**

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `.venv` won't work on Windows after WSL | Run `.\setup.ps1` — it detects and removes Linux venvs |
| `GITHUB_TOKEN is empty` | Edit `.env` and add your PAT |
| `uvicorn not found` | Run `pip install -r requirements.txt` |
| `node not found` | Install Node.js 18+ from https://nodejs.org |
| `node_modules missing` | Run `npm install` in `frontend/` |
| Rate limit hit mid-demo | Test your exact demo script end-to-end beforehand to know your token budget |
| Backend starts but health fails | Check `GITHUB_TOKEN` is valid and `models:read` scope is granted |
