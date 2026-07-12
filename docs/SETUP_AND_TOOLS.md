# SETUP_AND_TOOLS.md — Loan / Credit Application Processing Agent

Everything needed to get from zero to a running demo, including wiring up a **GitHub Personal Access Token (PAT)** as your model API key via **GitHub Models**.

---

## 1. Tool stack — what to install and why

| Tool | Purpose | Install |
|---|---|---|
| Python 3.11+ | Backend runtime | system / pyenv |
| Node.js 20+ | Frontend runtime | system / nvm |
| FastAPI + Uvicorn | API server | `pip install fastapi uvicorn` |
| LangGraph | Agent state machine | `pip install langgraph` |
| LangChain (openai-compatible client) | Model calling glue, easiest way to point at GitHub Models' OpenAI-compatible endpoint | `pip install langchain langchain-openai` |
| Pydantic v2 | Data validation/contracts | `pip install pydantic` |
| Chroma | Local vector store for policy RAG | `pip install chromadb` |
| SQLite (built-in) / SQLAlchemy | Audit persistence | `pip install sqlalchemy` |
| pytesseract + Pillow (optional, for scanned docs) | OCR fallback | `pip install pytesseract pillow` + system `tesseract-ocr` |
| PyYAML | Load versioned policy files | `pip install pyyaml` |
| React + Vite | Frontend | `npm create vite@latest` |
| Tailwind CSS | Styling per `UI_UX_DESIGN.md` | `npm install -D tailwindcss` |
| Recharts | Score bars / gauges | `npm install recharts` |
| pytest | Test suite for the 10 scenarios | `pip install pytest` |

---

## 2. Using a GitHub PAT as your model API key (GitHub Models)

GitHub Models exposes hosted LLMs (e.g., GPT and Llama-family models) through an **OpenAI-compatible endpoint**, authenticated with a **GitHub Personal Access Token** instead of a separate provider API key. This is the right fit for a workshop build since it avoids provisioning a new key from a third-party provider.

### 2.1 Create the PAT
1. GitHub → **Settings → Developer settings → Personal access tokens → Fine-grained tokens** (or classic tokens).
2. Scope: a token with **`models: read`** permission is sufficient for calling GitHub Models. Do not grant repo/write scopes you don't need — least privilege, same governance instinct as the project itself.
3. Copy the token once — it will not be shown again.

### 2.2 Store it safely
Never hardcode the PAT. Use a `.env` file (git-ignored) at the project root:

```
# .env  (add this file to .gitignore immediately)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_MODELS_ENDPOINT=https://models.github.ai/inference
PRIMARY_MODEL=openai/gpt-4o-mini
CHALLENGER_MODEL=meta/llama-3.1-70b-instruct
```

Load it in Python with `python-dotenv`:

```python
from dotenv import load_dotenv
import os

load_dotenv()
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
ENDPOINT = os.environ["GITHUB_MODELS_ENDPOINT"]
```

**Add `.env` to `.gitignore` before your first commit.** This is the single most common way workshop teams leak a token into a public repo.

### 2.3 Point the OpenAI-compatible client at GitHub Models

```python
from openai import OpenAI

client = OpenAI(
    base_url=os.environ["GITHUB_MODELS_ENDPOINT"],
    api_key=os.environ["GITHUB_TOKEN"],   # PAT goes here, not a separate provider key
)

response = client.chat.completions.create(
    model=os.environ["PRIMARY_MODEL"],
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ],
    temperature=0,
)
```

If using LangChain instead of the raw SDK:

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model=os.environ["PRIMARY_MODEL"],
    base_url=os.environ["GITHUB_MODELS_ENDPOINT"],
    api_key=os.environ["GITHUB_TOKEN"],
    temperature=0,
)
```

### 2.4 Rate limits
GitHub Models has request/token rate limits tied to your GitHub plan (free tier is lower than Copilot Enterprise, etc.) — check your current limits on the GitHub Models page before running large batch evaluation suites, and add basic retry/backoff around calls so a rate-limit hit doesn't crash a demo mid-run.

### 2.5 Swapping models
Because the base URL and auth are identical across models on the endpoint, changing `PRIMARY_MODEL` / `CHALLENGER_MODEL` in `.env` is enough to try a different model for either role — no code changes needed. This is what makes the "challenger model comparison" stretch goal cheap to implement: it's a second client call with a different `model=` string, same token.

---

## 3. Environment setup — step by step

```bash
# 1. Clone/create your repo
git init loan-agent && cd loan-agent

# 2. Backend
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn langgraph langchain langchain-openai \
            pydantic chromadb sqlalchemy pyyaml python-dotenv \
            pytesseract pillow pytest openai

# 3. Frontend
npm create vite@latest frontend -- --template react
cd frontend && npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install recharts
cd ..

# 4. Environment file
cp .env.example .env   # then fill in GITHUB_TOKEN
echo ".env" >> .gitignore

# 5. Run backend
uvicorn app.main:app --reload --port 8000

# 6. Run frontend (separate terminal)
cd frontend && npm run dev
```

---

## 4. Running the evaluation suite

```bash
pytest tests/ -v
```

Each of the 10 test scenarios (5 original + 5 added, see `spec.md` Section 5) should map to one `pytest` test function, using fixture applications under `tests/fixtures/`. Structure assertions around the `DecisionRecord` object, not around LLM text — e.g., assert `record.score_breakdown.band == "refer"`, assert `record.fairness_check.match is True`, assert `"[DTI-01]"` appears in citations — not string-matching the LLM's prose, since that's brittle.

---

## 5. Suggested `.env.example` (commit this, not `.env`)

```
GITHUB_TOKEN=
GITHUB_MODELS_ENDPOINT=https://models.github.ai/inference
PRIMARY_MODEL=openai/gpt-4o-mini
CHALLENGER_MODEL=meta/llama-3.1-70b-instruct
DATABASE_URL=sqlite:///./audit.db
POLICY_PATH=./policy/policy_v1.yaml
```

---

## 6. Common pitfalls (worth flagging before Day 8 demo)

- **Committing the PAT** — double check `git status` before every push; rotate the token immediately if it leaks.
- **Letting the LLM compute the score** — if your composite score ever comes back slightly different for identical inputs across two runs, the arithmetic has leaked into the LLM call somewhere; move it back into the pure-Python scorer.
- **Treating uploaded document text as trusted** — always wrap OCR/extracted text in a clearly delimited untrusted-content block in your prompts (scenario 5 / scenario 9 depend on this).
- **Rate limit surprises mid-demo** — test your exact demo script once end-to-end beforehand, not just individual pieces, so you know your token budget holds for a live run.
