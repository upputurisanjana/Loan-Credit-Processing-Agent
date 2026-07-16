# Frontend

The project includes two frontend options: a **Streamlit** app (primary, quick to iterate) and a **React** app (production-quality underwriter UI).

---

## Streamlit UI (`app.py`)

### Running

```bash
# Backend must be running first
uvicorn app.main:app --reload --port 8000

# In a separate terminal
streamlit run app.py --server.port 8501

# Or via start script
./start.sh demo          # Linux/macOS
.\start.ps1 streamlit    # Windows PowerShell
```

### Design

- **Palette:** Dark slate-900 sidebar (`#0F172A`), white content cards, blue-700 accent (`#1D4ED8`), slate-50 page background (`#F8FAFC`)
- **Font:** Inter (Google Fonts)
- **Brand:** "LoanApply — Applicant Portal"

### Pages

#### 1. Submit Application (Tab 1)

- Upload an `application.json` file (parsed and previewed live)
- Upload supporting documents: ID, pay stub, bank statement (required), additional doc (optional)
- Auto-generates application ID (`APP-XXXXXX`)
- Runs the full pipeline on submit
- Shows success screen with reference number

#### 2. Check Application Status (Tab 2)

- Enter application ID to check outcome
- Shows: pending review, approved, declined (with adverse action notice), or referred
- Displays formal notice (approved version if available, else draft)

### Key Components

| Component | Purpose |
|-----------|---------|
| `_pill()` | Status pill badges (approve/refer/decline/pending) |
| `_card()` | Reusable card containers with accent variants |
| `_score_bar()` | Horizontal score bars with weight display |
| `_composite_gauge()` | Large composite score display with threshold ruler |
| `_fairness_card()` | Fairness check result with comparison grid |
| `_challenger_card()` | Challenger model result with comparison grid |
| `_counterfactual()` | "What would need to change" explanation |
| `_fmt_ts()` | ISO timestamp formatting |

---

## React UI (`frontend/`)

### Running

```bash
cd frontend
npm install        # first time only
npm run dev        # starts Vite dev server on :5173
```

Or via start scripts:
```bash
./start.sh frontend          # Linux/macOS
.\start.ps1 frontend         # Windows PowerShell
.\start.ps1                  # starts both backend + React
```

### Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 19.x | UI framework |
| TypeScript | 6.x | Type safety |
| Vite | 8.x | Build tool / dev server |
| Tailwind CSS | 3.x | Utility-first styling |
| Recharts | 3.x | Score bars / gauges |
| React Router | 7.x | Client-side routing |
| oxlint | 1.x | Linting |

### Design System

Based on `docs/UI_UX_DESIGN.md` — "Ledger, not dashboard" concept:

- **Palette:** Deep ink navy (`#12213A`), warm off-white paper (`#FAF8F3`), amber/gold accent (`#C48A2A`)
- **Status colors:** Approve = muted forest green (`#3A6B4C`), Refer = amber accent, Decline = muted brick red (`#8C3B2E`)
- **Typography:** Serif/slab-serif for headings + numbers, Inter for body text, tabular figures everywhere money/scores appear

### Screens

1. **Case Queue** — Sortable table with applicant (masked by default), score, band, age, status
2. **Application Detail** — Full decision workspace with score breakdown, recommendation, fairness/challenger panels
3. **Score Breakdown Panel** — Three horizontal stacked bars + composite gauge with threshold ruler
4. **Fairness & Challenger Panel** — Side-by-side cards showing match/disagree status
5. **Human Gate** — Sticky action bar: Approve / Override / Request Info
6. **Decision Modal** — Approve (confirm) / Override (reason required, min 20 chars) / Request Info (checklist)
7. **Adverse Action Notice Editor** — Editable draft with "must include" checklist
8. **Audit Trail** — Vertical timeline, one entry per node, expandable JSON
9. **Policy Version History** — Diff view between policy YAML versions

### API Connection

The React frontend connects to the backend via `VITE_API_URL` environment variable (default: `http://localhost:8000`).

API client: `frontend/src/api/client.ts` — thin fetch wrapper with error handling.

---

## Running Both UIs

```bash
# Windows PowerShell
.\start.ps1 all    # backend + React + Streamlit

# Both UIs share the same backend store
# Backend:  http://localhost:8000/docs
# React:    http://localhost:5173
# Streamlit: http://localhost:8501
```

---

## UI Architecture Notes

- Streamlit handles applicant-facing flows (submit + check status)
- React handles underwriter-facing flows (queue + decision workspace)
- Both share the same FastAPI backend and in-memory store
- The React UI strips internal fields (`fairness_check`, `challenger_result`, `pipeline_trace`) from displayed data via `_public_payload()`
