# Credit Decisioning Agent

A single-pipeline, human-gated credit application processing agent built with
FastAPI + LangGraph + GitHub Models API.

See `docs/spec.md` for the full spec, `docs/ARCHITECTURE.md` for the design,
and `docs/SETUP_AND_TOOLS.md` for detailed install/run instructions.

---

## Quick start

```bash
# 1. Clone & create virtualenv
python3 -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure credentials
cp .env.example .env
# Edit .env — add your GITHUB_TOKEN (PAT with models:read scope)

# 4. Start the API server
uvicorn app.main:app --reload --port 8000

# 5. Interactive docs
open http://localhost:8000/docs
```

---

## End-to-end curl demo

Submit the fixture application:
```bash
curl -s -X POST http://localhost:8000/applications \
     -H "Content-Type: application/json" \
     -d @tests/fixtures/clear_approve.json | python3 -m json.tool
```

Record the underwriter approval:
```bash
curl -s -X POST http://localhost:8000/applications/APP-001/decision \
     -H "Content-Type: application/json" \
     -d '{"human_decision":"approve","human_reviewer":"underwriter_1"}' \
     | python3 -m json.tool
```

---

## Pipeline

```
INTAKE → VERIFY → EXTRACT (LLM) → SCORE (pure Python) → FAIRNESS RECHECK → RECOMMEND (LLM) → HUMAN GATE
```

- **SCORE** is 100% deterministic Python — no LLM call, same inputs = same output.
- **No decision is ever auto-finalised** — every application waits at HUMAN_GATE.
- **Fairness recheck** re-runs the scorer with identity fields masked; any mismatch forces REFER.

---

## Key constraints (non-negotiable)

- The `app/agent/nodes/score.py` file has zero LLM imports — scoring is pure Python.
- No application moves past HUMAN_GATE without an explicit POST to `/decision`.
- `.env` is git-ignored; the GitHub token is never logged.
- This is a single decisioning agent, not multiple autonomous agents.
