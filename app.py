"""
app.py — Streamlit frontend for the Credit Decisioning Agent.

Matches the React UI design: dark slate-900 sidebar, white content cards,
blue-700 accent, slate-50 page background, Inter font.

Run with:
    streamlit run app.py
Backend must be running at http://localhost:8000
"""

# ─────────────────────────────────────────────────────────────────────────────
# Imports
# ─────────────────────────────────────────────────────────────────────────────
import json
import random
import string
from datetime import datetime, timezone
from typing import Any

import requests
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Page config  (MUST be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LoanApply — Submit Your Application",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS — matches the React design tokens exactly
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* ── Google font ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Root resets ── */
html, body, [class*="css"] {
    font-family: "Inter", system-ui, -apple-system, sans-serif;
    -webkit-font-smoothing: antialiased;
}

/* Page background: slate-50 */
.stApp { background-color: #F8FAFC; }

/* Sidebar: slate-900 */
[data-testid="stSidebar"] {
    background-color: #0F172A !important;
    border-right: 1px solid #1E293B;
}
[data-testid="stSidebar"] * { color: #94A3B8; }
[data-testid="stSidebar"] .sidebar-brand { color: #FFFFFF !important; }

/* Remove default sidebar header padding */
[data-testid="stSidebar"] > div:first-child { padding-top: 0 !important; }

/* Main content padding */
.main .block-container { padding: 1.5rem 2rem 4rem 2rem; max-width: 900px; }

/* ── Card component ── */
.card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 0.5rem;
    box-shadow: 0 1px 3px 0 rgba(0,0,0,.04), 0 1px 2px -1px rgba(0,0,0,.04);
    overflow: hidden;
    margin-bottom: 1rem;
}
.card-header {
    padding: 0.75rem 1.25rem;
    border-bottom: 1px solid #F1F5F9;
    background: #F8FAFC;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #64748B;
}
.card-header.danger  { background:#FFF1F2; border-color:#FECDD3; color:#DC2626; }
.card-header.warning { background:#FFFBEB; border-color:#FDE68A; color:#B45309; }
.card-header.success { background:#F0FDF4; border-color:#BBF7D0; color:#15803D; }
.card-body { padding: 1rem 1.25rem; }

/* ── Stat card ── */
.stat-card {
    background:#FFFFFF;
    border:1px solid #E2E8F0;
    border-radius:0.5rem;
    padding:1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
.stat-label {
    font-size:0.65rem; font-weight:600;
    text-transform:uppercase; letter-spacing:0.08em;
    color:#64748B; margin-bottom:0.4rem;
}
.stat-value { font-size:1.875rem; font-weight:700; line-height:1; font-variant-numeric:tabular-nums; }
.stat-value.default { color:#0F172A; }
.stat-value.warning { color:#D97706; }
.stat-value.success { color:#16A34A; }
.stat-value.danger  { color:#DC2626; }
.stat-sub { font-size:0.7rem; color:#94A3B8; margin-top:0.35rem; }

/* ── Status pill / badge ── */
.pill {
    display:inline-flex; align-items:center; gap:4px;
    padding:2px 8px; border-radius:4px;
    font-size:0.7rem; font-weight:600; border:1px solid;
    white-space:nowrap;
}
.pill-approve  { background:#F0FDF4; color:#15803D; border-color:#BBF7D0; }
.pill-refer    { background:#FFFBEB; color:#B45309; border-color:#FDE68A; }
.pill-decline  { background:#FFF1F2; color:#DC2626; border-color:#FECDD3; }
.pill-pending  { background:#EFF6FF; color:#1D4ED8; border-color:#BFDBFE; }
.pill-decided  { background:#F0FDF4; color:#15803D; border-color:#BBF7D0; }
.pill-fairness { background:#FFF1F2; color:#DC2626; border-color:#FECDD3; }
.pill-hold     { background:#F8FAFC; color:#475569; border-color:#CBD5E1; }

/* ── Score bar ── */
.score-bar-wrap { display:flex; align-items:center; gap:10px; margin-bottom:0.5rem; }
.score-bar-label { font-size:0.75rem; color:#64748B; width:130px; flex-shrink:0; }
.score-bar-track {
    flex:1; height:6px; background:#E2E8F0;
    border-radius:3px; overflow:hidden;
}
.score-bar-fill { height:100%; border-radius:3px; transition:width .4s ease; }
.score-bar-num { font-size:0.7rem; font-variant-numeric:tabular-nums; color:#475569; width:50px; text-align:right; }

/* ── Comparison grid ── */
.compare-grid { display:grid; grid-template-columns:1fr 1fr; gap:0.75rem; }
.compare-cell {
    background:#F8FAFC; border:1px solid #E2E8F0;
    border-radius:0.375rem; padding:0.75rem;
}
.compare-cell.mismatch { background:#FFF1F2; border-color:#FECDD3; }
.compare-cell.warn     { background:#FFFBEB; border-color:#FDE68A; }
.compare-cell-lbl { font-size:0.6rem; text-transform:uppercase; letter-spacing:0.08em; color:#94A3B8; margin-bottom:0.25rem; }
.compare-cell-val { font-size:0.875rem; font-weight:700; text-transform:capitalize; color:#0F172A; }
.compare-cell-val.red   { color:#DC2626; }
.compare-cell-val.amber { color:#B45309; }
.compare-cell-sub { font-size:0.65rem; color:#94A3B8; font-variant-numeric:tabular-nums; }

/* ── Pipeline trace node ── */
.trace-node {
    display:flex; gap:12px; position:relative; padding-bottom:1.25rem;
}
.trace-node::before {
    content:"";
    position:absolute; left:14px; top:30px; bottom:0;
    width:1px; background:#E2E8F0;
}
.trace-node:last-child::before { display:none; }
.trace-dot {
    width:28px; height:28px; border-radius:50%;
    background:#EFF6FF; border:1.5px solid #BFDBFE;
    display:flex; align-items:center; justify-content:center;
    flex-shrink:0; font-size:0.6rem; font-weight:700; color:#1D4ED8;
}
.trace-dot.error  { background:#FFF1F2; border-color:#FECDD3; color:#DC2626; }
.trace-dot.ok     { background:#F0FDF4; border-color:#BBF7D0; color:#15803D; }
.trace-content { flex:1; min-width:0; }
.trace-node-name { font-size:0.75rem; font-weight:600; color:#0F172A; }
.trace-ts { font-size:0.65rem; color:#94A3B8; }

/* ── Document chip ── */
.doc-chip {
    display:inline-flex; align-items:center; gap:6px;
    background:#F8FAFC; border:1px solid #E2E8F0; border-radius:0.375rem;
    padding:6px 10px; font-size:0.75rem; color:#475569;
}

/* ── Amendment row ── */
.amendment-row {
    border-left:3px solid #BFDBFE; padding-left:12px;
    margin-bottom:0.75rem;
}

/* ── Clause chip ── */
.clause-chip {
    display:inline-flex; align-items:center;
    background:#EFF6FF; border:1px solid #BFDBFE; border-radius:4px;
    padding:2px 7px; font-size:0.65rem; font-weight:600;
    font-family:monospace; color:#1D4ED8;
    margin:2px;
}

/* ── Headings ── */
h1,h2,h3 { font-weight:600; letter-spacing:-0.01em; color:#0F172A; }

/* ── Streamlit widget overrides ── */
div[data-testid="stForm"] { border:none; padding:0; }
div.stButton > button {
    background:#1D4ED8; color:#FFFFFF; border:none;
    font-weight:500; font-size:0.8125rem; border-radius:0.375rem;
    padding:0.45rem 1rem; transition:background .15s;
}
div.stButton > button:hover { background:#1E40AF; }
div[data-baseweb="select"] > div { border-color:#E2E8F0 !important; border-radius:0.375rem !important; }
div[data-baseweb="input"] > div  { border-color:#E2E8F0 !important; border-radius:0.375rem !important; }
textarea { border-color:#E2E8F0 !important; border-radius:0.375rem !important; font-size:0.8125rem !important; }

/* ── Section divider ── */
hr { border:none; border-top:1px solid #F1F5F9; margin:0.75rem 0; }

/* ── Shrink expander header ── */
details > summary { font-size:0.8125rem; font-weight:500; color:#475569; }
</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"
TIMEOUT  = 30   # seconds

# ─────────────────────────────────────────────────────────────────────────────
# API helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get(path: str) -> Any:
    r = requests.get(f"{API_BASE}{path}", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def _post(path: str, payload: dict) -> Any:
    r = requests.post(f"{API_BASE}{path}", json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def api_health() -> dict:
    return _get("/health")

def api_queue() -> list:
    return _get("/queue")

def api_get_application(app_id: str) -> dict:
    return _get(f"/applications/{app_id}")

def api_submit_application(payload: dict) -> dict:
    return _post("/applications", payload)

def api_get_trace(app_id: str) -> dict:
    return _get(f"/applications/{app_id}/trace")

def api_post_decision(app_id: str, payload: dict) -> dict:
    return _post(f"/applications/{app_id}/decision", payload)

def api_get_amendments(app_id: str) -> list:
    return _get(f"/applications/{app_id}/amendments")

def api_post_amendment(app_id: str, payload: dict) -> dict:
    return _post(f"/applications/{app_id}/amendments", payload)

def api_get_decision(app_id: str) -> dict:
    return _get(f"/applications/{app_id}/decision")

# ─────────────────────────────────────────────────────────────────────────────
# UI helper components
# ─────────────────────────────────────────────────────────────────────────────

def _pill(value: str) -> str:
    """Return an HTML status pill matching the React StatusPill component."""
    if not value:
        return '<span class="pill pill-hold">—</span>'
    mapping = {
        "approve":              ("pill-approve",  "● Approve"),
        "refer":                ("pill-refer",    "● Refer"),
        "decline":              ("pill-decline",  "● Decline"),
        "pending_human_review": ("pill-pending",  "⏳ Pending Review"),
        "awaiting_information": ("pill-refer",    "⏳ Awaiting Info"),
        "decided":              ("pill-decided",  "✓ Decided"),
        "flag_fairness_fail":   ("pill-fairness", "⚠ Fairness Flag"),
        "hold_for_document":    ("pill-hold",     "📄 Hold – Docs"),
        "error":                ("pill-decline",  "✕ Error"),
    }
    cls, label = mapping.get(value.lower(), ("pill-hold", value))
    return f'<span class="pill {cls}">{label}</span>'


def _card(header: str, body_html: str, accent: str = "") -> str:
    """Return a card HTML block."""
    return (
        f'<div class="card">'
        f'<div class="card-header {accent}">{header}</div>'
        f'<div class="card-body">{body_html}</div>'
        f'</div>'
    )


def _score_bar(label: str, subscore: float, weight: float) -> str:
    pct = round(subscore * 100)
    if pct >= 75:
        color = "#16A34A"
    elif pct >= 50:
        color = "#D97706"
    else:
        color = "#DC2626"
    return (
        f'<div class="score-bar-wrap">'
        f'<div class="score-bar-label">{label}</div>'
        f'<div class="score-bar-track">'
        f'  <div class="score-bar-fill" style="width:{pct}%;background:{color}"></div>'
        f'</div>'
        f'<div class="score-bar-num">{pct}/100 <span style="color:#CBD5E1">×{weight:.0%}</span></div>'
        f'</div>'
    )


def _composite_gauge(composite: float, band: str) -> str:
    pct = round(composite * 100)
    bar_color = {"approve": "#16A34A", "refer": "#D97706", "decline": "#DC2626"}.get(band, "#94A3B8")
    band_html = _pill(band)
    return (
        f'<div style="display:flex;align-items:center;gap:1.25rem;padding-bottom:0.75rem;">'
        f'  <div style="text-align:center;min-width:80px;">'
        f'    <div style="font-size:2.5rem;font-weight:700;line-height:1;color:{bar_color};'
        f'         font-variant-numeric:tabular-nums;">{pct}</div>'
        f'    <div style="font-size:0.65rem;color:#94A3B8;text-transform:uppercase;'
        f'         letter-spacing:.06em;margin-top:2px;">/ 100</div>'
        f'  </div>'
        f'  <div style="flex:1;">'
        f'    <div style="height:10px;background:#E2E8F0;border-radius:5px;overflow:hidden;">'
        f'      <div style="height:100%;width:{pct}%;background:{bar_color};'
        f'           border-radius:5px;transition:width .4s ease;"></div>'
        f'    </div>'
        f'    <div style="display:flex;justify-content:space-between;'
        f'         font-size:0.6rem;color:#94A3B8;margin-top:4px;">'
        f'      <span>0</span><span style="color:#D97706;">65 Refer</span>'
        f'      <span style="color:#16A34A;">75 Approve</span><span>100</span>'
        f'    </div>'
        f'  </div>'
        f'  <div>{band_html}</div>'
        f'</div>'
    )


def _fairness_card(fc: dict) -> str:
    ok = fc.get("match", True)
    accent = "" if ok else "danger"
    orig_band   = fc.get("original_band", "—")
    masked_band = fc.get("masked_band", "—")
    orig_comp   = round(fc.get("original_composite", 0) * 100, 1)
    mask_comp   = round(fc.get("masked_composite", 0) * 100, 1)
    if ok:
        status_html = (
            '<div style="display:flex;align-items:center;gap:6px;color:#16A34A;margin-bottom:.75rem;">'
            '<span style="font-size:1rem;">✓</span>'
            '<span style="font-size:.8125rem;font-weight:600;">Masked re-score matched</span>'
            '</div>'
        )
    else:
        status_html = (
            '<div style="display:flex;align-items:flex-start;gap:6px;color:#DC2626;margin-bottom:.75rem;">'
            '<span style="font-size:1rem;flex-shrink:0;">⚠</span>'
            '<div><div style="font-size:.8125rem;font-weight:700;">Mismatch — forced to REFER</div>'
            '<div style="font-size:.7rem;margin-top:2px;color:#EF4444;">Investigate disparity before approving.</div></div>'
            '</div>'
        )
    masked_cls = "mismatch" if not ok else ""
    body = (
        f'{status_html}'
        f'<div class="compare-grid">'
        f'  <div class="compare-cell">'
        f'    <div class="compare-cell-lbl">Original</div>'
        f'    <div class="compare-cell-val">{orig_band}</div>'
        f'    <div class="compare-cell-sub">{orig_comp} pts</div>'
        f'  </div>'
        f'  <div class="compare-cell {masked_cls}">'
        f'    <div class="compare-cell-lbl">Masked</div>'
        f'    <div class="compare-cell-val{"" if ok else " red"}">{masked_band}</div>'
        f'    <div class="compare-cell-sub">{mask_comp} pts</div>'
        f'  </div>'
        f'</div>'
    )
    return _card("Fairness Check", body, accent)


def _challenger_card(cr: dict | None) -> str:
    if not cr:
        return _card("Challenger Model", '<p style="font-size:.8125rem;color:#94A3B8;">Not run for this application.</p>')
    agree        = cr.get("bands_agree", True)
    primary_band = cr.get("primary_band", "—")
    chall_band   = cr.get("challenger_band", "—")
    delta        = cr.get("delta", 0)
    accent       = "" if agree else "warning"
    if not agree:
        alert_html = (
            '<div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:.375rem;'
            'padding:.6rem .75rem;margin-bottom:.75rem;">'
            '<div style="font-size:.8125rem;font-weight:600;color:#92400E;">⚠ Models disagree — REFER enforced</div>'
            '<div style="font-size:.7rem;color:#B45309;margin-top:2px;">Band delta exceeds threshold. Cannot be auto-approved.</div>'
            '</div>'
        )
    else:
        alert_html = ""
    chall_cls  = "warn" if not agree else ""
    chall_vcls = " amber" if not agree else ""
    agree_row  = (
        '<div style="margin-top:.6rem;font-size:.7rem;color:#16A34A;">✓ Models agree</div>'
        if agree else
        f'<div style="margin-top:.6rem;font-size:.7rem;color:#94A3B8;">Band delta: <b>{int(delta)}</b></div>'
    )
    body = (
        f'{alert_html}'
        f'<div class="compare-grid">'
        f'  <div class="compare-cell">'
        f'    <div class="compare-cell-lbl">Primary</div>'
        f'    <div class="compare-cell-val">{primary_band}</div>'
        f'  </div>'
        f'  <div class="compare-cell {chall_cls}">'
        f'    <div class="compare-cell-lbl">Challenger</div>'
        f'    <div class="compare-cell-val{chall_vcls}">{chall_band}</div>'
        f'  </div>'
        f'</div>'
        f'{agree_row}'
    )
    return _card("Challenger Model", body, accent)


def _fmt_ts(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y, %H:%M UTC")
    except Exception:
        return iso


def _counterfactual(sb: dict) -> str:
    band      = sb.get("band", "")
    composite = sb.get("composite_score", 0)
    pct       = round(composite * 100)
    if band == "approve":
        return "Score is already in the approve band — no further action required."
    if band == "refer":
        gap = 75 - pct
        return (
            f"Composite score needs to rise by {gap} points ({pct} → 75) to reach APPROVE."
            if gap > 0
            else "Score is at the approve threshold — a minor improvement would clear it."
        )
    gap = 65 - pct
    return f"Composite score needs to rise by {gap} points ({pct} → 65) to reach REFER."


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — dark slate-900, matches React aside
# ─────────────────────────────────────────────────────────────────────────────

def render_sidebar() -> str:
    """Render applicant-facing sidebar brand + nav; return the selected page key."""
    with st.sidebar:
        # Brand header
        st.markdown(
            """
<div style="padding:1.25rem 1rem 1rem;border-bottom:1px solid #1E293B;margin-bottom:.5rem;">
  <div style="display:flex;align-items:center;gap:10px;">
    <div style="width:28px;height:28px;background:#1D4ED8;border-radius:6px;
         display:flex;align-items:center;justify-content:center;flex-shrink:0;">
      <span style="color:#FFF;font-size:14px;">◆</span>
    </div>
    <div>
      <div class="sidebar-brand" style="font-size:.875rem;font-weight:600;color:#FFFFFF;
           line-height:1.2;letter-spacing:-.01em;">LoanApply</div>
      <div style="font-size:.6rem;color:#475569;text-transform:uppercase;
           letter-spacing:.1em;margin-top:2px;">Applicant Portal</div>
    </div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown(
            '<p style="padding:0 .75rem;margin:.5rem 0 .35rem;font-size:.6rem;'
            'font-weight:600;text-transform:uppercase;letter-spacing:.12em;color:#334155;">'
            "MENU</p>",
            unsafe_allow_html=True,
        )

        # Applicant-only pages
        pages = {
            "📝  Apply for a Loan":        "submit",
        }

        if "page" not in st.session_state:
            st.session_state.page = "submit"

        for label, key in pages.items():
            active = st.session_state.page == key
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.page = key
                st.rerun()

        # Backend health
        st.markdown(
            '<div style="margin-top:1rem;padding:0 .75rem;">'
            '<div style="display:flex;align-items:center;gap:.375rem;">'
            '<div style="width:6px;height:6px;border-radius:50%;background:#22C55E;flex-shrink:0;"></div>'
            '<span style="font-size:.6875rem;color:#475569;">Secure &amp; encrypted</span>'
            '</div></div>',
            unsafe_allow_html=True,
        )

    return st.session_state.get("page", "submit")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Submit Application
# ─────────────────────────────────────────────────────────────────────────────

def _upload_files_to_backend(app_id: str, files: list) -> None:
    """Upload files to POST /applications/{id}/documents using multipart."""
    if not files:
        return
    multipart_files = [("files", (f.name, f.getvalue(), f.type or "application/octet-stream")) for f in files]
    try:
        r = requests.post(
            f"{API_BASE}/applications/{app_id}/documents",
            files=multipart_files,
            timeout=60,
        )
        r.raise_for_status()
    except requests.HTTPError as exc:
        st.warning(f"Application submitted but document upload failed: {exc}")
    except Exception as exc:
        st.warning(f"Application submitted but document upload failed: {exc}")


def page_submit() -> None:
    # ── Tab selector: New Application vs Check Status ─────────────────
    tab_new, tab_check = st.tabs(["📝 New Application", "🔍 Check Application Status"])

    # ─────────────────────────────────────────────────────────────────
    # TAB 1 — Submit a new application
    # ─────────────────────────────────────────────────────────────────
    with tab_new:
        st.markdown("### Submit New Application")
        st.markdown(
            '<p style="font-size:.8125rem;color:#64748B;margin-top:-.25rem;margin-bottom:1.25rem;">'
            "Fill in your details, upload your supporting documents, and run the pipeline.</p>",
            unsafe_allow_html=True,
        )

        # Auto-generate a unique application ID once per session (immutable to applicant)
        if "draft_app_id" not in st.session_state:
            import random, string
            suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            st.session_state.draft_app_id = f"APP-{suffix}"

        st.markdown(
            f'<div style="display:flex;align-items:center;gap:.75rem;padding:.6rem 1rem;'
            f'background:#EFF6FF;border:1px solid #BFDBFE;border-radius:.5rem;margin-bottom:1rem;">'
            f'<div style="font-size:.75rem;color:#1D4ED8;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:.07em;">Your Reference Number</div>'
            f'<div style="font-size:1rem;font-weight:700;color:#1E3A8A;font-family:monospace;">'
            f'{st.session_state.draft_app_id}</div>'
            f'<div style="font-size:.7rem;color:#6B7280;margin-left:auto;">'
            f'Save this — you will need it to check your status</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        with st.form("submit_form", clear_on_submit=False):
            # ── Application identity ──────────────────────────────────
            st.markdown(
                '<div class="card-header" style="border-radius:.5rem .5rem 0 0;">Your Details</div>',
                unsafe_allow_html=True,
            )
            name    = st.text_input("Full Name *", placeholder="Jane Smith")
            address = st.text_input("Address *", placeholder="42 Maple Street, London, EC1A 1BB")
            notes   = st.text_area("Additional Notes (optional)", placeholder="Any context the reviewer should know…", height=70)

            st.divider()

            # ── Financials ────────────────────────────────────────────
            st.markdown(
                '<div style="font-size:.7rem;font-weight:600;text-transform:uppercase;'
                'letter-spacing:.08em;color:#64748B;margin-bottom:.5rem;">Financial Details</div>',
                unsafe_allow_html=True,
            )
            col3, col4, col5 = st.columns(3)
            with col3:
                income       = st.number_input("Monthly Income (£) *", min_value=0.01, value=5000.0, step=100.0)
            with col4:
                monthly_debt = st.number_input("Monthly Debt (£) *",   min_value=0.0,  value=1200.0, step=50.0)
            with col5:
                loan_amount  = st.number_input("Loan Requested (£) *", min_value=0.01, value=20000.0, step=500.0)

            st.divider()

            # ── Document uploads ──────────────────────────────────────
            st.markdown(
                '<div style="font-size:.7rem;font-weight:600;text-transform:uppercase;'
                'letter-spacing:.08em;color:#64748B;margin-bottom:.3rem;">Supporting Documents</div>'
                '<p style="font-size:.75rem;color:#94A3B8;margin-bottom:.75rem;">'
                "Upload your ID, pay stub, and bank statement. Accepted: PDF, PNG, JPG, TIFF (max 20 MB each).</p>",
                unsafe_allow_html=True,
            )

            id_file   = st.file_uploader(
                "ID Document *  (passport, driving licence, national ID)",
                type=["pdf", "png", "jpg", "jpeg", "tiff"],
                key="id_file",
            )
            ps_file   = st.file_uploader(
                "Pay Stub *  (most recent payslip)",
                type=["pdf", "png", "jpg", "jpeg", "tiff"],
                key="ps_file",
            )
            bs_file   = st.file_uploader(
                "Bank Statement *  (last 3 months)",
                type=["pdf", "png", "jpg", "jpeg", "tiff"],
                key="bs_file",
            )
            other_file = st.file_uploader(
                "Additional Document (optional)",
                type=["pdf", "png", "jpg", "jpeg", "tiff"],
                key="other_file",
            )

            submitted = st.form_submit_button("🚀  Submit Application", use_container_width=True)

        # ── Handle submission ─────────────────────────────────────────
        if submitted:
            errors = []
            if not name.strip():
                errors.append("Full name is required.")
            if not address.strip():
                errors.append("Address is required.")
            if not id_file:
                errors.append("ID document is required.")
            if not ps_file:
                errors.append("Pay stub is required.")
            if not bs_file:
                errors.append("Bank statement is required.")
            if errors:
                for e in errors:
                    st.error(e)
            else:
                # Build pipeline payload — documents carry minimal metadata;
                # the actual files are uploaded separately after pipeline success.
                docs = [
                    {"doc_type": "id",             "file_path": id_file.name,   "ocr_confidence": 0.95, "extracted_text": f"Uploaded file: {id_file.name}"},
                    {"doc_type": "pay_stub",        "file_path": ps_file.name,   "ocr_confidence": 0.95, "extracted_text": f"Uploaded file: {ps_file.name}"},
                    {"doc_type": "bank_statement",  "file_path": bs_file.name,   "ocr_confidence": 0.95, "extracted_text": f"Uploaded file: {bs_file.name}"},
                ]
                if other_file:
                    docs.append({"doc_type": "other", "file_path": other_file.name, "ocr_confidence": 0.90, "extracted_text": f"Uploaded file: {other_file.name}"})

                payload = {
                    "application_id":        st.session_state.get("draft_app_id", "APP-UNKNOWN"),
                    "submitted_at":          datetime.now(timezone.utc).isoformat(),
                    "applicant_name":        name.strip(),
                    "applicant_address":     address.strip(),
                    "stated_income":         income,
                    "stated_monthly_debt":   monthly_debt,
                    "loan_amount_requested": loan_amount,
                    "applicant_notes":       notes.strip() or None,
                    "documents":             docs,
                }

                with st.spinner("Running pipeline: VERIFY → EXTRACT → SCORE → RECOMMEND …"):
                    try:
                        result = api_submit_application(payload)
                    except requests.HTTPError as exc:
                        try:
                            detail = exc.response.json().get("detail", str(exc))
                        except Exception:
                            detail = str(exc)
                        st.error(f"Submission failed: {detail}")
                        result = None
                    except requests.ConnectionError:
                        st.error("Cannot reach the processing server. Please try again later.")
                        result = None

                if result is not None:
                    status = result.get("status", "")

                    if status == "hold_for_document":
                        st.warning("⚠ Your application is on hold — some required documents could not be verified:")
                        for d in result.get("missing_docs", []):
                            st.markdown(f"- Missing: `{d}`")
                        for f in result.get("consistency_flags", []):
                            st.markdown(f"- ⚠ {f}")

                    elif status == "error":
                        st.error(f"Processing error: {result.get('message', 'Unknown error')}")

                    else:
                        app_result_id = result.get("application_id", "")
                        st.session_state.last_submitted = app_result_id
                        # Reset so next form submission gets a fresh reference number
                        if "draft_app_id" in st.session_state:
                            del st.session_state["draft_app_id"]

                        # Upload the actual files to the documents endpoint
                        files_to_upload = [f for f in [id_file, ps_file, bs_file, other_file] if f is not None]
                        with st.spinner("Uploading your documents…"):
                            _upload_files_to_backend(app_result_id, files_to_upload)

                        st.success(f"✅ Application **{app_result_id}** submitted successfully and is now awaiting reviewer decision.")
                        st.markdown(
                            f'<div class="card"><div class="card-body">'
                            f'<p style="font-size:.8125rem;color:#374151;margin:0;">'
                            f'Your documents have been uploaded. You will be notified once a reviewer has made a decision. '
                            f'Use the <b>Check Application Status</b> tab above to see your outcome at any time.</p>'
                            f'</div></div>',
                            unsafe_allow_html=True,
                        )

    # ─────────────────────────────────────────────────────────────────
    # TAB 2 — Check outcome of a submitted application
    # ─────────────────────────────────────────────────────────────────
    with tab_check:
        st.markdown("### Check Application Status")
        st.markdown(
            '<p style="font-size:.8125rem;color:#64748B;margin-top:-.25rem;margin-bottom:1rem;">'
            "Enter your Application ID to see whether your application has been approved or declined.</p>",
            unsafe_allow_html=True,
        )

        col_id, col_btn = st.columns([3, 1])
        with col_id:
            lookup_id = st.text_input(
                "Application ID",
                value=st.session_state.get("last_submitted", ""),
                placeholder="APP-001",
                key="status_lookup_id",
                label_visibility="collapsed",
            )
        with col_btn:
            check_btn = st.button("Check Status", key="status_check_btn", use_container_width=True)

        if check_btn and lookup_id.strip():
            try:
                rec = api_get_application(lookup_id.strip())
            except requests.HTTPError:
                st.error(f"Application **{lookup_id.strip()}** not found. Check your Application ID.")
                rec = None
            except requests.ConnectionError:
                st.error("Cannot reach the processing server. Please try again later.")
                rec = None

            if rec:
                human_decision = rec.get("human_decision")
                status         = rec.get("status", "")
                app_id_display = rec.get("application_id", lookup_id.strip())

                if not human_decision:
                    # Still pending
                    st.markdown(
                        f'<div class="card"><div class="card-body">'
                        f'<div style="display:flex;align-items:center;gap:.75rem;">'
                        f'  <div style="font-size:1.5rem;">⏳</div>'
                        f'  <div>'
                        f'    <div style="font-size:.9375rem;font-weight:600;color:#0F172A;">{app_id_display}</div>'
                        f'    <div style="font-size:.8125rem;color:#64748B;margin-top:2px;">'
                        f'      Your application is currently <b>under review</b>. '
                        f'      Please check back later.</div>'
                        f'  </div>'
                        f'</div></div></div>',
                        unsafe_allow_html=True,
                    )

                elif human_decision == "approve":
                    decided_at = _fmt_ts(rec.get("decided_at"))
                    reviewer   = rec.get("human_reviewer", "—")
                    loan_amt   = ""
                    st.markdown(
                        f'<div class="card" style="border-color:#BBF7D0;">'
                        f'<div class="card-header success">✅ Application Approved</div>'
                        f'<div class="card-body">'
                        f'  <div style="font-size:1rem;font-weight:600;color:#15803D;margin-bottom:.5rem;">'
                        f'    Congratulations! Your credit application has been <b>approved</b>.</div>'
                        f'  <div style="font-size:.8125rem;color:#374151;margin-bottom:.75rem;">'
                        f'    Application <b>{app_id_display}</b> was reviewed and approved on {decided_at}.</div>'
                        f'  <div style="font-size:.75rem;color:#64748B;">'
                        f'    Reviewed by: {reviewer}</div>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )

                elif human_decision in ("decline", "refer"):
                    # Show the adverse action / rejection letter
                    decided_at   = _fmt_ts(rec.get("decided_at"))
                    reviewer     = rec.get("human_reviewer", "—")
                    # Prefer reviewer-approved notice; fall back to raw draft
                    adv_draft    = rec.get("approved_notice_text") or rec.get("adverse_action_draft") or ""
                    notice_label = (
                        "Formal Notice from Reviewer (Approved)"
                        if rec.get("approved_notice_text")
                        else "Formal Notice (Draft)"
                    )
                    override_rsn = rec.get("override_reason") or ""
                    rationale    = rec.get("rationale", "")

                    label  = "Declined" if human_decision == "decline" else "Referred for Further Review"
                    accent = "danger"   if human_decision == "decline" else "warning"
                    icon   = "❌"        if human_decision == "decline" else "⚠"

                    st.markdown(
                        f'<div class="card" style="border-color:{"#FECDD3" if human_decision=="decline" else "#FDE68A"};">'
                        f'<div class="card-header {accent}">{icon} Application {label}</div>'
                        f'<div class="card-body">'
                        f'  <div style="font-size:.8125rem;color:#374151;margin-bottom:.75rem;">'
                        f'    Application <b>{app_id_display}</b> was reviewed on {decided_at} by {reviewer}.</div>',
                        unsafe_allow_html=True,
                    )

                    # Adverse action letter (the reviewer's formal notice)
                    if adv_draft:
                        st.markdown(
                            f'<div style="font-size:.7rem;font-weight:600;text-transform:uppercase;'
                            f'letter-spacing:.08em;color:#64748B;margin-bottom:.4rem;">{notice_label}</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<div style="background:#FFF8F8;border:1px solid #FECDD3;border-radius:.375rem;'
                            f'padding:1rem;font-size:.8125rem;color:#374151;line-height:1.7;'
                            f'white-space:pre-wrap;">{adv_draft}</div>',
                            unsafe_allow_html=True,
                        )
                    elif rationale:
                        # Fallback: show the agent rationale if no formal notice yet
                        st.markdown(
                            '<div style="font-size:.7rem;font-weight:600;text-transform:uppercase;'
                            'letter-spacing:.08em;color:#64748B;margin-bottom:.4rem;">Reason for Decision</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:.375rem;'
                            f'padding:1rem;font-size:.8125rem;color:#374151;line-height:1.7;">{rationale}</div>',
                            unsafe_allow_html=True,
                        )

                    if override_rsn:
                        st.markdown(
                            f'<div style="margin-top:.75rem;padding:.6rem .75rem;background:#FFFBEB;'
                            f'border:1px solid #FDE68A;border-radius:.375rem;">'
                            f'<b style="font-size:.7rem;text-transform:uppercase;color:#B45309;">Additional Notes</b>'
                            f'<p style="font-size:.8rem;color:#78350F;margin:.2rem 0 0 0;">{override_rsn}</p>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                    st.markdown("</div></div>", unsafe_allow_html=True)

        elif check_btn and not lookup_id.strip():
            st.warning("Please enter your Application ID.")



# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Case Queue
# ─────────────────────────────────────────────────────────────────────────────

def page_queue() -> None:
    # Page header
    col_h, col_r = st.columns([6, 1])
    with col_h:
        st.markdown("## Application Queue")
        st.markdown(
            '<p style="font-size:.8125rem;color:#64748B;margin-top:-.25rem;">Human-gated credit decisioning · every application requires underwriter review</p>',
            unsafe_allow_html=True,
        )
    with col_r:
        if st.button("↻ Refresh", key="queue_refresh"):
            st.rerun()

    # Banner if we just submitted something
    last = st.session_state.get("last_submitted")
    if last:
        st.markdown(
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'padding:.6rem 1rem;background:#F0FDF4;border:1px solid #BBF7D0;'
            f'border-radius:.5rem;margin-bottom:.75rem;">'
            f'  <span style="font-size:.8125rem;color:#15803D;">✅ <b>{last}</b> just submitted — visible in queue below</span>'
            f'  <button onclick="this.parentElement.style.display=\'none\'" '
            f'style="background:none;border:none;color:#64748B;cursor:pointer;font-size:.8rem;">✕</button>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Fetch queue
    try:
        items = api_queue()
    except requests.ConnectionError:
        st.error("Cannot reach backend at http://localhost:8000 — is it running?")
        return
    except Exception as exc:
        st.error(f"Failed to load queue: {exc}")
        return

    if not items:
        st.markdown(
            '<div class="card"><div class="card-body" style="text-align:center;padding:2rem;">'
            '<div style="font-size:2rem;margin-bottom:.5rem;opacity:.15;">📋</div>'
            '<p style="font-size:.8125rem;color:#94A3B8;">No applications in queue. Submit one using the sidebar.</p>'
            '</div></div>',
            unsafe_allow_html=True,
        )
        return

    # ── Stat cards ────────────────────────────────────────────────────
    total      = len(items)
    pending    = sum(1 for i in items if i.get("status") in ("pending_human_review", "flag_fairness_fail", "awaiting_information"))
    decided    = sum(1 for i in items if i.get("status") == "decided")

    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.markdown(
            f'<div class="stat-card"><div class="stat-label">Total</div>'
            f'<div class="stat-value default">{total}</div>'
            f'<div class="stat-sub">all applications</div></div>',
            unsafe_allow_html=True,
        )
    with sc2:
        st.markdown(
            f'<div class="stat-card"><div class="stat-label">Pending Review</div>'
            f'<div class="stat-value warning">{pending}</div>'
            f'<div class="stat-sub">awaiting underwriter</div></div>',
            unsafe_allow_html=True,
        )
    with sc3:
        st.markdown(
            f'<div class="stat-card"><div class="stat-label">Decided</div>'
            f'<div class="stat-value success">{decided}</div>'
            f'<div class="stat-sub">completed</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top:1.25rem;'></div>", unsafe_allow_html=True)

    # ── Queue table card ──────────────────────────────────────────────
    st.markdown(
        '<div class="card"><div class="card-header">Applications</div><div class="card-body" style="padding:0;">',
        unsafe_allow_html=True,
    )

    # Build table rows HTML
    rows_html = ""
    for item in items:
        aid       = item.get("application_id", "—")
        status    = item.get("status", "")
        rec       = item.get("agent_recommendation") or "—"
        human     = item.get("human_decision") or "—"
        score     = item.get("composite_score", 0)
        band      = item.get("band", "—")
        created   = _fmt_ts(item.get("created_at"))
        pct       = round(score * 100)
        bar_color = {"approve": "#16A34A", "refer": "#D97706", "decline": "#DC2626"}.get(band, "#94A3B8")

        score_bar = (
            f'<div style="display:flex;align-items:center;gap:6px;">'
            f'  <div style="width:60px;height:4px;background:#E2E8F0;border-radius:2px;overflow:hidden;">'
            f'    <div style="height:100%;width:{pct}%;background:{bar_color};border-radius:2px;"></div>'
            f'  </div>'
            f'  <span style="font-size:.7rem;color:#475569;font-variant-numeric:tabular-nums;">{pct}</span>'
            f'</div>'
        )

        rows_html += (
            f'<tr style="border-bottom:1px solid #F1F5F9;cursor:pointer;'
            f'{"background:#FFFBEB;" if aid == last else ""}" >'
            f'<td style="padding:.75rem .75rem;font-size:.8125rem;font-weight:500;color:#0F172A;'
            f'{"border-left:3px solid #F59E0B;" if aid == last else ""}">{aid}'
            f'{"<span style=\'font-size:.6rem;color:#B45309;margin-left:4px;\'>NEW</span>" if aid == last else ""}'
            f'</td>'
            f'<td style="padding:.75rem .5rem;">{_pill(status)}</td>'
            f'<td style="padding:.75rem .5rem;">{_pill(rec) if rec != "—" else "—"}</td>'
            f'<td style="padding:.75rem .5rem;">{score_bar}</td>'
            f'<td style="padding:.75rem .5rem;font-size:.75rem;color:#64748B;">{human}</td>'
            f'<td style="padding:.75rem .5rem;font-size:.7rem;color:#94A3B8;white-space:nowrap;">{created}</td>'
            f'</tr>'
        )

    table_html = (
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr style="border-bottom:1px solid #E2E8F0;">'
        f'<th style="padding:.6rem .75rem;font-size:.7rem;font-weight:500;color:#64748B;text-align:left;">App ID</th>'
        f'<th style="padding:.6rem .5rem;font-size:.7rem;font-weight:500;color:#64748B;text-align:left;">Status</th>'
        f'<th style="padding:.6rem .5rem;font-size:.7rem;font-weight:500;color:#64748B;text-align:left;">Recommendation</th>'
        f'<th style="padding:.6rem .5rem;font-size:.7rem;font-weight:500;color:#64748B;text-align:left;">Score</th>'
        f'<th style="padding:.6rem .5rem;font-size:.7rem;font-weight:500;color:#64748B;text-align:left;">Human Decision</th>'
        f'<th style="padding:.6rem .5rem;font-size:.7rem;font-weight:500;color:#64748B;text-align:left;">Submitted</th>'
        f'</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table>'
    )
    st.markdown(table_html, unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)

    # ── Per-row open buttons ──────────────────────────────────────────
    st.markdown("<div style='margin-top:.75rem;'></div>", unsafe_allow_html=True)
    btn_cols = st.columns(min(len(items), 4))
    for i, item in enumerate(items):
        aid = item.get("application_id", "")
        col = btn_cols[i % len(btn_cols)]
        with col:
            if st.button(
                f"🔍 {aid}",
                key=f"queue_open_{aid}",
                use_container_width=True,
                help=f"Open detail for {aid}",
            ):
                st.session_state.detail_app_id = aid
                st.session_state.page = "detail"
                st.rerun()



# ─────────────────────────────────────────────────────────────────────────────
# Rich Fairness + Challenger card helpers (used on Submit preview + Detail page)
# ─────────────────────────────────────────────────────────────────────────────

def _fairness_card_rich(fc: dict) -> str:
    """
    Extended fairness card matching the React FairnessCard component.
    Shows original vs masked bands, composite scores, and a colour-coded verdict.
    """
    ok          = fc.get("match", True)
    orig_band   = fc.get("original_band", "—")
    masked_band = fc.get("masked_band", "—")
    orig_comp   = round(fc.get("original_composite", 0) * 100, 1)
    mask_comp   = round(fc.get("masked_composite", 0) * 100, 1)
    delta       = round(abs(fc.get("original_composite", 0) - fc.get("masked_composite", 0)) * 100, 3)

    verdict_html = (
        '<div style="display:flex;align-items:center;gap:6px;color:#16A34A;margin-bottom:.75rem;">'
        '<span>✓</span><span style="font-size:.8125rem;font-weight:600;">Masked re-score matched — no identity leakage</span>'
        '</div>'
        if ok else
        '<div style="display:flex;align-items:flex-start;gap:6px;color:#DC2626;margin-bottom:.75rem;">'
        '<span style="flex-shrink:0;margin-top:1px;">⚠</span>'
        '<div><div style="font-size:.8125rem;font-weight:700;">Mismatch — forced to REFER</div>'
        '<div style="font-size:.7rem;margin-top:2px;color:#EF4444;">Identity may have leaked into a scoring path. Investigate before approving.</div>'
        '</div></div>'
    )

    masked_cls = "mismatch" if not ok else ""
    masked_vcls = ' style="color:#DC2626;"' if not ok else ""
    delta_row = (
        f'<div style="margin-top:.6rem;font-size:.7rem;color:#94A3B8;">'
        f'Composite delta: <b style="color:{"#DC2626" if not ok else "#16A34A"};">{delta} pts</b>'
        f'{"  ·  regression detected" if not ok else "  ·  identical (expected)"}'
        f'</div>'
    )
    method_row = (
        '<div style="margin-top:.6rem;padding:.5rem .6rem;background:#F8FAFC;'
        'border:1px solid #E2E8F0;border-radius:.375rem;font-size:.7rem;color:#64748B;">'
        '<b>Method:</b> Same deterministic scorer, two passes — Pass 1: identity present '
        '(never read); Pass 2: identity = [REDACTED]. Results must match bit-for-bit.'
        '</div>'
    )

    body = (
        f'{verdict_html}'
        f'<div class="compare-grid">'
        f'  <div class="compare-cell">'
        f'    <div class="compare-cell-lbl">Original</div>'
        f'    <div class="compare-cell-val">{orig_band}</div>'
        f'    <div class="compare-cell-sub">{orig_comp} pts</div>'
        f'  </div>'
        f'  <div class="compare-cell {masked_cls}">'
        f'    <div class="compare-cell-lbl">Masked</div>'
        f'    <div class="compare-cell-val"{masked_vcls}>{masked_band}</div>'
        f'    <div class="compare-cell-sub">{mask_comp} pts</div>'
        f'  </div>'
        f'</div>'
        f'{delta_row}'
        f'{method_row}'
    )
    accent = "" if ok else "danger"
    return _card("Fairness Check", body, accent)


def _challenger_card_rich(cr: dict | None) -> str:
    """
    Extended challenger card matching the React ChallengerCard component.
    Shows primary vs challenger bands, delta tier, forced-REFER logic, and method note.
    """
    if not cr:
        return _card(
            "Challenger Model",
            '<p style="font-size:.8125rem;color:#94A3B8;">Not run for this application.</p>',
        )

    agree        = cr.get("bands_agree", True)
    primary_band = cr.get("primary_band", "—")
    chall_band   = cr.get("challenger_band", "—")
    delta        = int(cr.get("delta", 0))

    tier_labels = {
        0: ("No disagreement", "#16A34A"),
        1: ("1-tier apart (approve↔refer or refer↔decline) — no forced REFER", "#D97706"),
        2: ("2-tier apart (approve↔decline) — REFER forced", "#DC2626"),
    }
    tier_text, tier_color = tier_labels.get(delta, (f"Delta {delta}", "#94A3B8"))

    if not agree:
        alert_html = (
            '<div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:.375rem;'
            'padding:.6rem .75rem;margin-bottom:.75rem;">'
            '<div style="font-size:.8125rem;font-weight:600;color:#92400E;">⚠ Models disagree — REFER enforced</div>'
            '<div style="font-size:.7rem;color:#B45309;margin-top:2px;">'
            'Band delta exceeds 1 tier. Application cannot be auto-approved.</div>'
            '</div>'
        )
    else:
        alert_html = (
            '<div style="display:flex;align-items:center;gap:6px;color:#16A34A;margin-bottom:.75rem;">'
            '<span>✓</span><span style="font-size:.8125rem;font-weight:600;">Models agree — challenger confirms primary</span>'
            '</div>'
        )

    chall_cls  = "warn" if not agree else ""
    chall_vcls = ' style="color:#B45309;"' if not agree else ""

    method_row = (
        '<div style="margin-top:.6rem;padding:.5rem .6rem;background:#F8FAFC;'
        'border:1px solid #E2E8F0;border-radius:.375rem;font-size:.7rem;color:#64748B;">'
        '<b>Method:</b> Independent LLM (CHALLENGER_MODEL) reads the same financial data '
        'and score summary, then states its own band opinion. Does NOT recompute numeric scores.'
        '</div>'
    )

    delta_row = (
        f'<div style="margin-top:.6rem;font-size:.7rem;" style="color:{tier_color};">'
        f'Band delta: <b>{delta}</b> — <span style="color:{tier_color};">{tier_text}</span>'
        f'</div>'
    )

    body = (
        f'{alert_html}'
        f'<div class="compare-grid">'
        f'  <div class="compare-cell">'
        f'    <div class="compare-cell-lbl">Primary Model</div>'
        f'    <div class="compare-cell-val">{primary_band}</div>'
        f'  </div>'
        f'  <div class="compare-cell {chall_cls}">'
        f'    <div class="compare-cell-lbl">Challenger Model</div>'
        f'    <div class="compare-cell-val"{chall_vcls}>{chall_band}</div>'
        f'  </div>'
        f'</div>'
        f'{delta_row}'
        f'{method_row}'
    )
    accent = "" if agree else "warning"
    return _card("Challenger Model", body, accent)


def _render_fairness_panel(app_id: str, fc: dict) -> None:
    """
    Full interactive fairness panel for the Application Detail page.
    Fetches deep explainability from GET /applications/{id}/fairness,
    renders the card, and shows the explanation in an expander.
    """
    if not fc:
        st.markdown(
            _card("Fairness Check", '<p style="font-size:.8125rem;color:#94A3B8;">No fairness data available.</p>'),
            unsafe_allow_html=True,
        )
        return

    # Render the rich card using stored fc data (always available, no extra API call)
    st.markdown(_fairness_card_rich(fc), unsafe_allow_html=True)

    # Deep-dive expander — fetches the explainability endpoint
    with st.expander("🔬 Fairness Explainability Detail"):
        if st.button("Load fairness explanation", key=f"fairness_explain_{app_id}"):
            st.session_state[f"fairness_detail_{app_id}"] = None
            try:
                data = requests.get(f"{API_BASE}/applications/{app_id}/fairness", timeout=TIMEOUT)
                data.raise_for_status()
                st.session_state[f"fairness_detail_{app_id}"] = data.json()
            except requests.HTTPError as exc:
                st.error(f"Could not fetch fairness detail: {exc}")
            except requests.ConnectionError:
                st.error("Backend offline.")

        detail = st.session_state.get(f"fairness_detail_{app_id}")
        if detail:
            exp   = detail.get("explanation", {})
            match = fc.get("match", True)

            # Verdict banner
            verdict_color = "#16A34A" if match else "#DC2626"
            st.markdown(
                f'<div style="padding:.6rem .75rem;background:{"#F0FDF4" if match else "#FFF1F2"};'
                f'border:1px solid {"#BBF7D0" if match else "#FECDD3"};border-radius:.375rem;'
                f'margin-bottom:.75rem;">'
                f'<b style="color:{verdict_color};">{exp.get("verdict","")}</b>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Key metrics grid
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Composite Delta", f'{exp.get("composite_delta", 0):.4f}')
            with col2:
                st.metric("Band Delta", exp.get("band_delta", 0))
            with col3:
                forced = exp.get("forced_refer", False)
                st.metric("Forced REFER", "Yes ⚠" if forced else "No ✓")

            # Method explanation
            st.markdown(
                f'<div style="padding:.6rem .75rem;background:#F8FAFC;border:1px solid #E2E8F0;'
                f'border-radius:.375rem;font-size:.8rem;color:#475569;line-height:1.6;">'
                f'<b>Method:</b> {exp.get("method","")}'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Score comparison
            sb = detail.get("score_breakdown", {})
            if sb:
                st.markdown("**Score Breakdown (stored at pipeline time):**")
                scol1, scol2, scol3, scol4 = st.columns(4)
                scol1.metric("Composite", f'{sb.get("composite_score",0):.3f}')
                scol2.metric("DTI Sub", f'{sb.get("dti_subscore",0):.3f}')
                scol3.metric("Credit Sub", f'{sb.get("credit_history_subscore",0):.3f}')
                scol4.metric("Income Sub", f'{sb.get("income_stability_subscore",0):.3f}')


def _render_challenger_panel(app_id: str, cr: dict | None) -> None:
    """
    Full interactive challenger panel for the Application Detail page.
    Fetches deep explainability from GET /applications/{id}/challenger,
    and supports live re-run via POST /applications/{id}/challenger/rerun.
    """
    # Render the rich card using stored cr data
    st.markdown(_challenger_card_rich(cr), unsafe_allow_html=True)

    with st.expander("🤖 Challenger Model Detail & Re-Run"):
        # Load explanation
        if st.button("Load challenger explanation", key=f"chal_explain_{app_id}"):
            st.session_state[f"chal_detail_{app_id}"] = None
            try:
                data = requests.get(f"{API_BASE}/applications/{app_id}/challenger", timeout=TIMEOUT)
                data.raise_for_status()
                st.session_state[f"chal_detail_{app_id}"] = data.json()
            except requests.HTTPError as exc:
                st.error(f"Could not fetch challenger detail: {exc}")
            except requests.ConnectionError:
                st.error("Backend offline.")

        detail = st.session_state.get(f"chal_detail_{app_id}")
        if detail:
            exp = detail.get("explanation", {})
            cr_stored = detail.get("challenger_result")
            agree = exp.get("bands_agree", True)

            # Verdict banner
            verdict_color = "#16A34A" if agree else "#B45309"
            st.markdown(
                f'<div style="padding:.6rem .75rem;background:{"#F0FDF4" if agree else "#FFFBEB"};'
                f'border:1px solid {"#BBF7D0" if agree else "#FDE68A"};border-radius:.375rem;'
                f'margin-bottom:.75rem;">'
                f'<b style="color:{verdict_color};">{exp.get("verdict","")}</b>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Metrics
            if cr_stored:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Primary Band",     cr_stored.get("primary_band", "—").title())
                col2.metric("Challenger Band",  cr_stored.get("challenger_band", "—").title())
                col3.metric("Band Delta",       int(cr_stored.get("delta", 0)))
                col4.metric("Forced REFER",     "Yes ⚠" if exp.get("forced_refer") else "No ✓")

            # Tier explanation
            tier = exp.get("tier_explanation", "")
            if tier:
                st.markdown(
                    f'<div style="font-size:.8rem;color:#64748B;padding:.5rem;'
                    f'background:#F8FAFC;border:1px solid #E2E8F0;border-radius:.375rem;">'
                    f'<b>Tier:</b> {tier}</div>',
                    unsafe_allow_html=True,
                )

            # Method
            st.markdown(
                f'<div style="margin-top:.5rem;padding:.6rem .75rem;background:#F8FAFC;'
                f'border:1px solid #E2E8F0;border-radius:.375rem;font-size:.8rem;'
                f'color:#475569;line-height:1.6;">'
                f'<b>Method:</b> {exp.get("method","")}'
                f'</div>',
                unsafe_allow_html=True,
            )

        # ── Live re-run ───────────────────────────────────────────────
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:.75rem;font-weight:600;color:#64748B;margin-bottom:.35rem;">'
            '🔄 Re-run Challenger Live</div>'
            '<div style="font-size:.75rem;color:#94A3B8;margin-bottom:.6rem;">'
            'Makes a live LLM API call using CHALLENGER_MODEL. Use when the initial run '
            'failed or the model has been updated. <b>Consumes one API call.</b></div>',
            unsafe_allow_html=True,
        )
        if st.button("⚡ Re-run Challenger Model Now", key=f"chal_rerun_{app_id}"):
            with st.spinner("Calling challenger model…"):
                try:
                    resp = requests.post(
                        f"{API_BASE}/applications/{app_id}/challenger/rerun",
                        timeout=TIMEOUT,
                    )
                    resp.raise_for_status()
                    rerun_data = resp.json()
                    new_cr = rerun_data.get("challenger_result", {})
                    agree  = new_cr.get("bands_agree", True)
                    st.success(
                        f"✅ Re-run complete. Challenger band: **{new_cr.get('challenger_band','—')}** "
                        f"vs primary: **{new_cr.get('primary_band','—')}** — "
                        f"{'✓ Agree' if agree else '⚠ Disagree (REFER enforced)'}"
                    )
                    # Update cached detail
                    st.session_state[f"chal_detail_{app_id}"] = None
                    st.markdown(
                        f'<div style="font-size:.7rem;color:#94A3B8;margin-top:.4rem;">'
                        f'{rerun_data.get("note","")}</div>',
                        unsafe_allow_html=True,
                    )
                    # Re-render immediately
                    st.markdown(_challenger_card_rich(new_cr), unsafe_allow_html=True)
                except requests.HTTPError as exc:
                    try:
                        detail_msg = exc.response.json().get("detail", str(exc))
                    except Exception:
                        detail_msg = str(exc)
                    st.error(f"Re-run failed: {detail_msg}")
                except requests.ConnectionError:
                    st.error("Backend offline.")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Application Detail
# ─────────────────────────────────────────────────────────────────────────────

def page_detail() -> None:
    # ── App ID picker ─────────────────────────────────────────────────
    app_id = st.session_state.get("detail_app_id", "")

    col_back, col_id = st.columns([1, 4])
    with col_back:
        if st.button("← Queue", key="detail_back"):
            st.session_state.page = "queue"
            st.rerun()
    with col_id:
        app_id_input = st.text_input(
            "Application ID",
            value=app_id,
            placeholder="APP-001",
            key="detail_app_id_input",
            label_visibility="collapsed",
        )
        if app_id_input:
            app_id = app_id_input
            st.session_state.detail_app_id = app_id

    if not app_id:
        st.info("Enter an application ID above, or open one from the Case Queue.")
        return

    # ── Fetch record ──────────────────────────────────────────────────
    try:
        rec = api_get_application(app_id)
    except requests.HTTPError as exc:
        st.error(f"Application not found: {exc}")
        return
    except requests.ConnectionError:
        st.error("Cannot reach backend at http://localhost:8000 — is it running?")
        return

    status = rec.get("status", "")
    sb     = rec.get("score_breakdown", {})

    # ── Header ────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="display:flex;align-items:flex-start;justify-content:space-between;'
        f'flex-wrap:wrap;gap:.75rem;margin-bottom:1rem;">'
        f'  <div>'
        f'    <h1 style="font-size:1.5rem;font-weight:600;letter-spacing:-.01em;'
        f'         color:#0F172A;margin:0;">{app_id}</h1>'
        f'    <p style="font-size:.7rem;color:#94A3B8;margin-top:4px;">'
        f'      Submitted {_fmt_ts(rec.get("created_at"))}</p>'
        f'  </div>'
        f'  <div style="display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;">'
        f'    <span style="font-family:monospace;font-size:.7rem;color:#64748B;'
        f'          background:#F1F5F9;border:1px solid #E2E8F0;padding:2px 8px;border-radius:4px;">'
        f'      {rec.get("policy_version","—")}</span>'
        f'    {_pill(status)}'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Verification strip ────────────────────────────────────────────
    missing   = rec.get("missing_docs", [])
    con_flags = rec.get("consistency_flags", [])
    if missing or con_flags:
        parts = []
        for d in missing:
            parts.append(f'<span class="doc-chip" style="border-color:#FECDD3;background:#FFF1F2;color:#DC2626;">✕ {d}</span>')
        for f in con_flags:
            parts.append(f'<span class="doc-chip" style="border-color:#FDE68A;background:#FFFBEB;color:#B45309;">⚠ {f}</span>')
        st.markdown(
            f'<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:.75rem;">{"".join(parts)}</div>',
            unsafe_allow_html=True,
        )

    # ── 0. Applicant Details ──────────────────────────────────────────
    applicant_name    = rec.get("applicant_name", "")
    applicant_address = rec.get("applicant_address", "")
    loan_amount       = rec.get("loan_amount_requested", 0)
    applicant_notes   = rec.get("applicant_notes")

    if applicant_name or applicant_address:
        def _kv_row(label: str, value: str) -> str:
            return (
                f'<div style="display:flex;gap:.75rem;padding:.4rem 0;border-bottom:1px solid #F8FAFC;">'
                f'  <span style="font-size:.75rem;color:#94A3B8;width:130px;flex-shrink:0;">{label}</span>'
                f'  <span style="font-size:.8125rem;color:#0F172A;">{value}</span>'
                f'</div>'
            )
        appl_body = ""
        if applicant_name:
            appl_body += _kv_row("Full Name", applicant_name)
        if applicant_address:
            appl_body += _kv_row("Address", applicant_address)
        if loan_amount and loan_amount > 0:
            appl_body += _kv_row("Loan Requested", f"£{loan_amount:,.2f}")
        if applicant_notes:
            appl_body += _kv_row("Applicant Notes", applicant_notes)
        st.markdown(_card("Applicant Details", appl_body), unsafe_allow_html=True)

    # ── Awaiting information banner ───────────────────────────────────
    if status == "awaiting_information":
        awaiting_items = rec.get("awaiting_info_items", [])
        if awaiting_items:
            items_html = "".join(
                f'<li style="font-size:.8rem;color:#B45309;">· {item}</li>'
                for item in awaiting_items
            )
            st.markdown(
                f'<div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:.5rem;'
                f'padding:.75rem 1rem;margin-bottom:.75rem;">'
                f'<div style="font-size:.75rem;font-weight:600;color:#B45309;margin-bottom:.4rem;">'
                f'⏳ Awaiting information from applicant:</div>'
                f'<ul style="margin:0;padding:0;list-style:none;">{items_html}</ul>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── 1. Score Breakdown ────────────────────────────────────────────
    if sb:
        dti_ratio = sb.get("dti_ratio", 0)
        dti_warn  = " · <span style='color:#EF4444;'>above 43% acceptable threshold</span>" if dti_ratio > 0.43 else ""
        clauses   = sb.get("clause_citations", [])
        clause_chips = "".join(
            f'<span class="clause-chip">[{c["clause_id"]}]</span>' for c in clauses
        )
        body = (
            _composite_gauge(sb.get("composite_score", 0), sb.get("band", "")) +
            "<hr>" +
            _score_bar("Debt-to-Income",   sb.get("dti_subscore", 0),              sb.get("weights", {}).get("dti", 0.4)) +
            _score_bar("Credit History",   sb.get("credit_history_subscore", 0),   sb.get("weights", {}).get("credit_history", 0.35)) +
            _score_bar("Income Stability", sb.get("income_stability_subscore", 0), sb.get("weights", {}).get("income_stability", 0.25)) +
            f'<div style="margin-top:.6rem;padding-top:.6rem;border-top:1px solid #F1F5F9;'
            f'font-size:.75rem;color:#64748B;font-variant-numeric:tabular-nums;">'
            f'DTI ratio: <b style="color:#0F172A;">{dti_ratio*100:.1f}%</b>{dti_warn}</div>'
        )
        if clause_chips:
            body += (
                f'<div style="margin-top:.75rem;padding-top:.6rem;border-top:1px solid #F1F5F9;">'
                f'<span style="font-size:.7rem;color:#94A3B8;margin-right:4px;">Policy clauses:</span>'
                f'{clause_chips}'
                f'</div>'
            )
        st.markdown(_card("Score Breakdown", body), unsafe_allow_html=True)

        # Clause text expander
        if clauses:
            with st.expander("📖 Policy Clause Details"):
                for c in clauses:
                    st.markdown(
                        f'<div style="margin-bottom:.6rem;">'
                        f'<span class="clause-chip">[{c["clause_id"]}]</span> '
                        f'<span style="font-size:.7rem;font-weight:500;color:#475569;">{c.get("factor","").replace("_"," ").title()}</span>'
                        f'<p style="font-size:.8rem;color:#64748B;margin:.25rem 0 0 0;'
                        f'padding-left:.5rem;border-left:2px solid #BFDBFE;">{c.get("clause_text","")}</p>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

    # ── 2. Agent Recommendation ───────────────────────────────────────
    rationale = rec.get("rationale", "")
    if rationale or sb:
        agent_rec = rec.get("agent_recommendation", "")
        comp_pct  = round(sb.get("composite_score", 0) * 100) if sb else 0
        body = (
            f'<div style="display:flex;align-items:center;gap:1rem;margin-bottom:.75rem;">'
            f'  {_pill(agent_rec)}'
            f'  <span style="font-size:.8125rem;color:#64748B;font-variant-numeric:tabular-nums;">'
            f'    Composite score: <b style="color:#0F172A;">{comp_pct}/100</b></span>'
            f'</div>'
            f'<p style="font-size:.8125rem;line-height:1.6;color:#374151;">{rationale}</p>'
        )
        # Counterfactual
        if sb:
            cf_text = _counterfactual(sb)
            body += (
                f'<div style="margin-top:.75rem;padding:.6rem .75rem;background:#F8FAFC;'
                f'border:1px solid #E2E8F0;border-radius:.375rem;">'
                f'<div style="font-size:.65rem;font-weight:600;text-transform:uppercase;'
                f'letter-spacing:.08em;color:#94A3B8;margin-bottom:.2rem;">What would change this</div>'
                f'<p style="font-size:.8rem;color:#475569;margin:0;">{cf_text}</p>'
                f'</div>'
            )
        accent = "danger" if agent_rec == "decline" else "warning" if agent_rec == "refer" else "success"
        st.markdown(_card("Agent Recommendation", body, accent), unsafe_allow_html=True)

    # ── 3. Uploaded Documents ─────────────────────────────────────────
    try:
        docs_resp = requests.get(f"{API_BASE}/applications/{app_id}/documents", timeout=TIMEOUT)
        docs_resp.raise_for_status()
        docs_list = docs_resp.json().get("documents", [])
    except Exception:
        docs_list = []

    def _fmt_bytes(n: int) -> str:
        if n < 1024: return f"{n} B"
        if n < 1024 * 1024: return f"{n/1024:.1f} KB"
        return f"{n/1024/1024:.1f} MB"

    if docs_list:
        doc_rows = "".join(
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'padding:.6rem 0;border-bottom:1px solid #F1F5F9;">'
            f'  <div style="display:flex;align-items:center;gap:.6rem;">'
            f'    <span style="font-size:.875rem;">📄</span>'
            f'    <div>'
            f'      <div style="font-size:.8125rem;font-weight:500;color:#0F172A;">{d["filename"]}</div>'
            f'      <div style="font-size:.65rem;color:#94A3B8;">'
            f'        <span style="background:#EFF6FF;color:#1D4ED8;border:1px solid #BFDBFE;'
            f'        border-radius:3px;padding:1px 5px;margin-right:4px;font-size:.6rem;">'
            f'        {d.get("doc_type_label", d.get("doc_type","other").replace("_"," ").title())}</span>'
            f'        {_fmt_bytes(d["size_bytes"])} · {d.get("uploaded_at","")[:19].replace("T"," ")} UTC'
            f'      </div>'
            f'    </div>'
            f'  </div>'
            f'  <div style="display:flex;align-items:center;gap:.5rem;">'
            + (
                f'<span style="font-size:.65rem;font-weight:600;padding:2px 6px;border-radius:3px;'
                f'background:{"#F0FDF4" if d.get("verification_status")=="verified" else "#FFF1F2" if d.get("verification_status")=="rejected" else "#FFFBEB"};'
                f'color:{"#15803D" if d.get("verification_status")=="verified" else "#DC2626" if d.get("verification_status")=="rejected" else "#B45309"};'
                f'border:1px solid {"#BBF7D0" if d.get("verification_status")=="verified" else "#FECDD3" if d.get("verification_status")=="rejected" else "#FDE68A"};">'
                f'{"✓ Verified" if d.get("verification_status")=="verified" else "✗ Rejected" if d.get("verification_status")=="rejected" else "? Pending"}'
                f'</span>'
            ) +
            f'  <a href="{API_BASE}{d["url"]}" target="_blank" download="{d["filename"]}" '
            f'     style="font-size:.75rem;color:#1D4ED8;text-decoration:none;'
            f'     padding:3px 10px;border:1px solid #BFDBFE;border-radius:4px;background:#EFF6FF;">'
            f'     ⬇ Download</a>'
            f'  </div>'
            f'</div>'
            for d in docs_list
        )
        docs_body = doc_rows
    else:
        docs_body = '<p style="font-size:.8125rem;color:#94A3B8;text-align:center;padding:1rem 0;">No documents uploaded for this application.</p>'

    # PDF report download link
    pdf_url = f"{API_BASE}/applications/{app_id}/pdf"
    docs_body += (
        f'<div style="margin-top:.75rem;padding-top:.75rem;border-top:1px solid #F1F5F9;">'
        f'  <a href="{pdf_url}" target="_blank" download="application_{app_id}.pdf" '
        f'     style="display:inline-flex;align-items:center;gap:.4rem;'
        f'     background:#1D4ED8;color:#fff;font-size:.8125rem;font-weight:500;'
        f'     padding:.45rem 1rem;border-radius:.375rem;text-decoration:none;">'
        f'     📥 Download Full Application Report (PDF)</a>'
        f'  <p style="font-size:.7rem;color:#94A3B8;margin-top:.4rem;">'
        f'     Includes scores, rationale, policy clauses, and document list.</p>'
        f'</div>'
    )
    st.markdown(_card("Supporting Documents", docs_body), unsafe_allow_html=True)

    # ── 4. Adverse Action Notice ──────────────────────────────────────
    adv_draft = rec.get("adverse_action_draft")
    if adv_draft:
        with st.expander("📄 Adverse-Action Notice Draft", expanded=True):
            edited = st.text_area(
                "Edit before sending (held for human approval — never auto-sent)",
                value=adv_draft,
                height=280,
                key="adv_edit",
            )
            st.caption("This draft is NOT sent automatically. Copy, review, and send manually after underwriter approval.")

    # ── 5. Human Gate ─────────────────────────────────────────────────
    human_decision = rec.get("human_decision")
    agent_rec      = rec.get("agent_recommendation", "")

    st.markdown("<div style='margin-top:.5rem;'></div>", unsafe_allow_html=True)

    if human_decision:
        # Already decided
        body = (
            f'<div style="display:flex;flex-wrap:wrap;gap:1.25rem;">'
            f'  <div><div class="compare-cell-lbl">Decision</div>'
            f'       <div style="margin-top:3px;">{_pill(human_decision)}</div></div>'
            f'  <div><div class="compare-cell-lbl">Reviewer</div>'
            f'       <div style="font-size:.875rem;font-weight:600;color:#0F172A;margin-top:3px;">'
            f'       {rec.get("human_reviewer","—")}</div></div>'
            f'  <div><div class="compare-cell-lbl">Decided At</div>'
            f'       <div style="font-size:.8rem;color:#475569;margin-top:3px;">'
            f'       {_fmt_ts(rec.get("decided_at"))}</div></div>'
            f'</div>'
        )
        override = rec.get("override_reason")
        if override:
            body += (
                f'<div style="margin-top:.75rem;padding:.6rem .75rem;background:#FFFBEB;'
                f'border:1px solid #FDE68A;border-radius:.375rem;">'
                f'<b style="font-size:.7rem;text-transform:uppercase;color:#B45309;">Override Reason</b>'
                f'<p style="font-size:.8rem;color:#78350F;margin:.2rem 0 0 0;">{override}</p>'
                f'</div>'
            )
        body += (
            f'<div style="margin-top:.6rem;">'
            f'  <span style="font-size:.75rem;color:#64748B;">To correct this decision, use the Amendments section (Phase 2 feature).</span>'
            f'</div>'
        )
        st.markdown(_card("Human Gate — Decided ✓", body, "success"), unsafe_allow_html=True)
        if st.button("📑 Go to Amendments", key="detail_goto_amd"):
            st.session_state.amend_app_id = app_id
            st.session_state.page = "amendments"
            st.rerun()

    else:
        # Pending — show decision form
        st.markdown(
            '<div class="card-header warning" style="border-radius:.5rem .5rem 0 0;">'
            '⏳ Human Gate — Pending Underwriter Decision</div>',
            unsafe_allow_html=True,
        )

        # ── Request-info tab ─────────────────────────────────────────
        tab_decide, tab_info = st.tabs(["✅ Record Decision", "⏳ Request More Information"])

        with tab_decide:
            with st.form("decision_form"):
                col_dec, col_rev = st.columns(2)
                with col_dec:
                    decision = st.selectbox(
                        "Decision *",
                        ["approve", "refer", "decline"],
                        index=["approve", "refer", "decline"].index(agent_rec)
                        if agent_rec in ["approve", "refer", "decline"] else 0,
                    )
                with col_rev:
                    reviewer = st.text_input("Reviewer ID *", placeholder="underwriter_1")
                is_override = (decision != agent_rec)
                override_reason = st.text_area(
                    f"Override Reason {'(required — decision differs from agent recommendation)' if is_override else '(optional)'}",
                    height=90,
                    placeholder="Minimum 20 characters when overriding the agent recommendation…",
                    key="override_reason_input",
                )
                submitted_dec = st.form_submit_button("✅  Record Decision", use_container_width=True)

            if submitted_dec:
                if not reviewer.strip():
                    st.error("Reviewer ID is required.")
                elif is_override and len(override_reason.strip()) < 20:
                    st.error("Override reason must be at least 20 characters when overriding the agent recommendation.")
                else:
                    payload = {
                        "human_decision": decision,
                        "human_reviewer": reviewer.strip(),
                        "override_reason": override_reason.strip() or None,
                    }
                    try:
                        result = api_post_decision(app_id, payload)
                        st.success(f"✅ Decision recorded: **{decision}** by {reviewer.strip()}")
                        st.rerun()
                    except requests.HTTPError as exc:
                        try:
                            detail = exc.response.json().get("detail", str(exc))
                        except Exception:
                            detail = str(exc)
                        st.error(f"API error: {detail}")

        with tab_info:
            st.markdown(
                '<p style="font-size:.8125rem;color:#64748B;margin-bottom:.75rem;">'
                "Request specific information from the applicant without finalising the decision. "
                "The application remains open and reviewable once the applicant responds.</p>",
                unsafe_allow_html=True,
            )
            # Show current awaiting items if any
            current_items = rec.get("awaiting_info_items", [])
            if current_items:
                st.markdown(
                    '<div style="font-size:.75rem;color:#B45309;margin-bottom:.5rem;font-weight:600;">'
                    'Currently requested:</div>',
                    unsafe_allow_html=True,
                )
                for item in current_items:
                    st.markdown(f"- {item}")

            with st.form("request_info_form"):
                info_reviewer = st.text_input("Reviewer ID *", placeholder="underwriter_1", key="info_reviewer")
                # Pre-populate with known issues
                missing  = rec.get("missing_docs", [])
                con_flags = rec.get("consistency_flags", [])
                known = [f"Missing document: {d.replace('_',' ')}" for d in missing] + con_flags
                selected_known = []
                if known:
                    st.markdown("**Outstanding issues (check to request):**")
                    for item in known:
                        if st.checkbox(item, value=item in current_items, key=f"chk_{item}"):
                            selected_known.append(item)
                custom_item = st.text_area(
                    "Additional request (optional)",
                    placeholder="e.g. Updated bank statements for last 6 months",
                    height=60,
                    key="custom_info_item",
                )
                submitted_info = st.form_submit_button("⏳  Send Information Request", use_container_width=True)

            if submitted_info:
                if not info_reviewer.strip():
                    st.error("Reviewer ID is required.")
                else:
                    items = selected_known + ([custom_item.strip()] if custom_item.strip() else [])
                    if not items:
                        st.error("Please select at least one item to request.")
                    else:
                        try:
                            r = requests.post(
                                f"{API_BASE}/applications/{app_id}/request-info",
                                json={"requested_items": items, "reviewer": info_reviewer.strip()},
                                timeout=TIMEOUT,
                            )
                            r.raise_for_status()
                            st.success(f"✅ Information request sent. Application is now awaiting a response.")
                            st.rerun()
                        except requests.HTTPError as exc:
                            try:
                                detail = exc.response.json().get("detail", str(exc))
                            except Exception:
                                detail = str(exc)
                            st.error(f"API error: {detail}")

    # ── Audit trace link ──────────────────────────────────────────────
    st.markdown(
        f'<div style="text-align:right;margin-top:.5rem;">'
        f'  <span style="font-size:.75rem;color:#64748B;">→ </span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("🕵️ View Full Pipeline Trace", key="detail_trace_btn"):
        st.session_state.trace_app_id = app_id
        st.session_state.page = "audit"
        st.rerun()



# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Audit Trace
# ─────────────────────────────────────────────────────────────────────────────

def page_audit() -> None:
    st.markdown("## Audit Trace")
    st.markdown(
        '<p style="font-size:.8125rem;color:#64748B;margin-top:-.25rem;margin-bottom:1rem;">'
        "Node-by-node pipeline trace for any application in the store.</p>",
        unsafe_allow_html=True,
    )

    # App ID selector
    col_a, col_b = st.columns([3, 1])
    with col_a:
        default_id = st.session_state.get("trace_app_id", "")
        app_id = st.text_input(
            "Application ID",
            value=default_id,
            placeholder="APP-001",
            key="audit_app_id",
        )
    with col_b:
        st.markdown("<div style='height:1.75rem;'></div>", unsafe_allow_html=True)
        load_btn = st.button("Load Trace", key="audit_load")

    if not app_id:
        st.info("Enter an application ID to view its pipeline trace.")
        return

    # Auto-load: trigger on button OR when arriving with a pre-set ID
    should_load = load_btn or bool(app_id)
    if should_load:
        st.session_state.trace_app_id = app_id
        try:
            data = api_get_trace(app_id)
        except requests.HTTPError as exc:
            st.error(f"Application not found: {exc}")
            return
        except requests.ConnectionError:
            st.error("Cannot reach backend at http://localhost:8000 — is it running?")
            return

        trace = data.get("trace", [])
        if not trace:
            st.warning("No trace entries found for this application.")
            return

        # Summary header
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:.75rem;margin-bottom:1rem;">'
            f'  <span style="font-size:.875rem;font-weight:600;color:#0F172A;">{app_id}</span>'
            f'  <span style="font-size:.7rem;color:#94A3B8;">{len(trace)} pipeline node{"s" if len(trace)!=1 else ""}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Color mapping for nodes
        node_colors = {
            "VERIFY":            ("#EFF6FF", "#BFDBFE", "#1D4ED8"),
            "EXTRACT":           ("#F0FDF4", "#BBF7D0", "#15803D"),
            "SCORE":             ("#EFF6FF", "#BFDBFE", "#1D4ED8"),
            "CHALLENGER":        ("#FFFBEB", "#FDE68A", "#B45309"),
            "FAIRNESS_RECHECK":  ("#F0FDF4", "#BBF7D0", "#15803D"),
            "FLAG_FAIRNESS_FAIL":("#FFF1F2", "#FECDD3", "#DC2626"),
            "RECOMMEND":         ("#EFF6FF", "#BFDBFE", "#1D4ED8"),
            "DRAFT_NOTICE":      ("#F5F3FF", "#DDD6FE", "#7C3AED"),
            "HUMAN_GATE":        ("#F0FDF4", "#BBF7D0", "#15803D"),
            "HOLD_FOR_DOCUMENT": ("#FFFBEB", "#FDE68A", "#B45309"),
        }

        # Build trace HTML
        trace_html = ""
        for i, entry in enumerate(trace):
            node     = entry.get("node", "?")
            ts       = _fmt_ts(entry.get("timestamp"))
            is_last  = i == len(trace) - 1

            bg, border, text = node_colors.get(node, ("#F8FAFC", "#E2E8F0", "#475569"))
            abbr = node[:2].upper()

            # Key/value pairs (exclude node and timestamp)
            kv_pairs = {k: v for k, v in entry.items() if k not in ("node", "timestamp")}
            kv_html = ""
            for k, v in kv_pairs.items():
                if isinstance(v, float):
                    v_str = f"{v:.4f}"
                elif isinstance(v, list):
                    v_str = ", ".join(str(x) for x in v) if v else "—"
                elif isinstance(v, bool):
                    v_str = "✓ True" if v else "✕ False"
                else:
                    v_str = str(v)
                kv_html += (
                    f'<span style="display:inline-block;background:#F8FAFC;border:1px solid #E2E8F0;'
                    f'border-radius:4px;padding:1px 7px;font-size:.7rem;color:#475569;margin:2px;">'
                    f'<b style="color:#64748B;">{k}:</b> {v_str}</span>'
                )

            connector = "" if is_last else (
                '<div style="width:1px;height:20px;background:#E2E8F0;'
                'margin-left:13px;margin-top:2px;margin-bottom:2px;"></div>'
            )
            trace_html += (
                f'<div style="display:flex;gap:12px;align-items:flex-start;">'
                f'  <div style="display:flex;flex-direction:column;align-items:center;flex-shrink:0;">'
                f'    <div style="width:28px;height:28px;border-radius:50%;background:{bg};'
                f'         border:1.5px solid {border};display:flex;align-items:center;'
                f'         justify-content:center;font-size:.6rem;font-weight:700;color:{text};">'
                f'      {abbr}</div>'
                f'    {connector}'
                f'  </div>'
                f'  <div style="flex:1;padding-bottom:.75rem;">'
                f'    <div style="font-size:.8125rem;font-weight:600;color:#0F172A;">{node}</div>'
                f'    <div style="font-size:.65rem;color:#94A3B8;margin-bottom:4px;">{ts}</div>'
                f'    <div style="display:flex;flex-wrap:wrap;gap:2px;">{kv_html}</div>'
                f'  </div>'
                f'</div>'
            )

        st.markdown(
            _card("Pipeline Trace", trace_html),
            unsafe_allow_html=True,
        )

        # Also show full JSON
        with st.expander("🗂 Raw Trace JSON"):
            st.json(trace)

        # Link to detail
        if st.button("← Back to Application Detail", key="audit_back_detail"):
            st.session_state.detail_app_id = app_id
            st.session_state.page = "detail"
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Amendments
# ─────────────────────────────────────────────────────────────────────────────

def page_amendments() -> None:
    st.markdown("## Amendments")
    st.markdown(
        '<p style="font-size:.8125rem;color:#64748B;margin-top:-.25rem;margin-bottom:1rem;">'
        "Post-hoc corrections to decided applications. The original record is never modified — "
        "amendments are a new linked row.</p>",
        unsafe_allow_html=True,
    )

    default_id = st.session_state.get("amend_app_id", "")
    col_a, col_b = st.columns([3, 1])
    with col_a:
        app_id = st.text_input(
            "Application ID",
            value=default_id,
            placeholder="APP-001",
            key="amd_app_id",
        )
    with col_b:
        st.markdown("<div style='height:1.75rem;'></div>", unsafe_allow_html=True)
        load_btn = st.button("Load", key="amd_load")

    if not app_id:
        st.info("Enter an application ID to view or submit amendments.")
        return

    # Always update session state when app_id is present
    st.session_state.amend_app_id = app_id

    # Verify application is decided
    try:
        rec = api_get_application(app_id)
    except requests.HTTPError as exc:
        st.error(f"Application not found: {exc}")
        return
    except requests.ConnectionError:
        st.error("Cannot reach backend at http://localhost:8000 — is it running?")
        return

    human_decision = rec.get("human_decision")
    if not human_decision:
        st.warning(
            "This application has not yet been decided. "
            "Use the Application Detail page to record the human decision first."
        )
        if st.button("Go to Detail →", key="amd_goto_detail"):
            st.session_state.detail_app_id = app_id
            st.session_state.page = "detail"
            st.rerun()
        return

    # Show current decision
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:.75rem;margin-bottom:1rem;">'
        f'  <span style="font-size:.875rem;color:#64748B;">Current decision:</span>'
        f'  {_pill(human_decision)}'
        f'  <span style="font-size:.75rem;color:#94A3B8;">by {rec.get("human_reviewer","—")}'
        f'  · {_fmt_ts(rec.get("decided_at"))}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Existing amendments ───────────────────────────────────────────
    try:
        amendments = api_get_amendments(app_id)
    except Exception:
        amendments = []

    if amendments:
        st.markdown(
            f'<div class="card-header" style="border-radius:.5rem .5rem 0 0;">Existing Amendments ({len(amendments)})</div>',
            unsafe_allow_html=True,
        )
        for amd in amendments:
            fc_html = "".join(
                f'<div style="font-size:.75rem;color:#475569;">'
                f'  <b style="color:#64748B;">{k}:</b> {v}</div>'
                for k, v in amd.get("field_changes", {}).items()
            )
            st.markdown(
                f'<div class="amendment-row">'
                f'  <div style="font-size:.8rem;font-weight:600;color:#0F172A;">'
                f'    {amd.get("amended_by","—")}</div>'
                f'  <div style="font-size:.7rem;color:#94A3B8;margin-bottom:4px;">'
                f'    {_fmt_ts(amd.get("amended_at"))} · ID: <code style="font-size:.65rem;">{amd.get("amendment_id","—")[:12]}…</code></div>'
                f'  <p style="font-size:.8rem;color:#374151;margin:.2rem 0;">{amd.get("amendment_reason","")}</p>'
                f'  {fc_html}'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<p style="font-size:.8rem;color:#94A3B8;margin-bottom:.75rem;">No amendments on record.</p>',
            unsafe_allow_html=True,
        )

    # ── New amendment form ────────────────────────────────────────────
    st.markdown(
        '<div class="card-header" style="border-radius:.5rem .5rem 0 0;margin-top:.75rem;">Submit New Amendment</div>',
        unsafe_allow_html=True,
    )
    with st.form("amendment_form"):
        amended_by = st.text_input("Your Reviewer ID *", placeholder="reviewer_2")
        reason     = st.text_area(
            "Amendment Reason * (min 20 chars)",
            height=80,
            placeholder="Describe why this correction is needed…",
        )
        st.markdown(
            '<div style="font-size:.75rem;color:#64748B;margin-bottom:.5rem;">'
            "Field Changes (key → new value). Each row: <code>field_name = new_value</code>",
            unsafe_allow_html=True,
        )
        changes_text = st.text_area(
            "Field changes",
            height=100,
            placeholder="human_decision = refer\noverride_reason = New evidence of income submitted",
            label_visibility="collapsed",
        )
        sub_amd = st.form_submit_button("📑  Submit Amendment", use_container_width=True)

    if sub_amd:
        errors = []
        if not amended_by.strip():
            errors.append("Reviewer ID is required.")
        if len(reason.strip()) < 20:
            errors.append("Amendment reason must be at least 20 characters.")
        if not changes_text.strip():
            errors.append("At least one field change is required.")
        if errors:
            for e in errors:
                st.error(e)
        else:
            # Parse field changes
            field_changes: dict = {}
            for line in changes_text.strip().splitlines():
                if "=" in line:
                    k, _, v = line.partition("=")
                    field_changes[k.strip()] = v.strip()

            if not field_changes:
                st.error("Could not parse any field changes. Use format: key = value")
            else:
                payload = {
                    "amended_by":       amended_by.strip(),
                    "amendment_reason": reason.strip(),
                    "field_changes":    field_changes,
                }
                try:
                    result = api_post_amendment(app_id, payload)
                    st.success(f"✅ Amendment recorded: `{result.get('amendment_id','')[:12]}…`")
                    st.session_state.amend_app_id = app_id
                    st.rerun()
                except requests.HTTPError as exc:
                    try:
                        detail = exc.response.json().get("detail", str(exc))
                    except Exception:
                        detail = str(exc)
                    st.error(f"API error: {detail}")


# ─────────────────────────────────────────────────────────────────────────────
# Main router
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    page = render_sidebar()
    # Applicant portal — only one page
    page_submit()


# Streamlit executes this module at top-level (not via __main__), so always call main().
main()
