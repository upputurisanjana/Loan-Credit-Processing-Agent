"""
Patch app.py to auto-generate the application ID.
Uses index-based search to avoid encoding issues with special chars.
"""
from pathlib import Path

src = Path("app.py").read_text(encoding="utf-8")

# ── Markers that are definitely unique and ASCII-safe ─────────────────────
FORM_START  = 'with st.form("submit_form", clear_on_submit=False):'
COL_LINE    = '            col1, col2 = st.columns(2)\n'
APP_ID_LINE = '                app_id  = st.text_input("Application ID *"'
COL2_LINE   = '            with col2:\n'
NAME_LINE   = '                name    = st.text_input("Full Name *", placeholder="Jane Smith")\n'
ADDR_LINE   = '            address     = st.text_input("Address *"'
NOTES_LINE  = '            notes       = st.text_area("Additional Notes (optional)"'

# Find the block: from col1,col2 through end of notes line
start_idx = src.index(COL_LINE)
notes_start = src.index(NOTES_LINE)
notes_end   = src.index('\n', notes_start) + 1   # end of notes line

old_block = src[start_idx:notes_end]
print("Old block found:")
print(repr(old_block))

new_block = (
    '            name    = st.text_input("Full Name *", placeholder="Jane Smith")\n'
    '            address = st.text_input("Address *", placeholder="42 Maple Street, London, EC1A 1BB")\n'
    '            notes   = st.text_area("Additional Notes (optional)", placeholder="Any context the reviewer should know\u2026", height=70)\n'
)

src = src[:start_idx] + new_block + src[notes_end:]

# ── Add reference banner + session state BEFORE the form ─────────────────
banner = (
    '        # Auto-generate a unique application ID once per session (immutable to applicant)\n'
    '        if "draft_app_id" not in st.session_state:\n'
    '            import random, string\n'
    '            suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))\n'
    '            st.session_state.draft_app_id = f"APP-{suffix}"\n'
    '\n'
    '        st.markdown(\n'
    '            f\'<div style="display:flex;align-items:center;gap:.75rem;padding:.6rem 1rem;\'\n'
    '            f\'background:#EFF6FF;border:1px solid #BFDBFE;border-radius:.5rem;margin-bottom:1rem;">\'\n'
    '            f\'<div style="font-size:.75rem;color:#1D4ED8;font-weight:600;text-transform:uppercase;\'\n'
    '            f\'letter-spacing:.07em;">Your Reference Number</div>\'\n'
    '            f\'<div style="font-size:1rem;font-weight:700;color:#1E3A8A;font-family:monospace;">\'\n'
    '            f\'{st.session_state.draft_app_id}</div>\'\n'
    '            f\'<div style="font-size:.7rem;color:#6B7280;margin-left:auto;">\'\n'
    '            f\'Save this \u2014 you will need it to check your status</div>\'\n'
    '            f\'</div>\',\n'
    '            unsafe_allow_html=True,\n'
    '        )\n'
    '\n'
)

form_idx = src.index(FORM_START)
# Insert banner just before the "with st.form..." line
line_start = src.rindex('\n', 0, form_idx) + 1
src = src[:line_start] + banner + src[line_start:]

# ── Remove app_id validation ──────────────────────────────────────────────
old_val = (
    '            errors = []\n'
    '            if not app_id.strip():\n'
    '                errors.append("Application ID is required.")\n'
    '            if not name.strip():\n'
)
new_val = (
    '            errors = []\n'
    '            if not name.strip():\n'
)
assert old_val in src, "Validation block not found"
src = src.replace(old_val, new_val, 1)

# ── Replace app_id.strip() in payload with session_state.draft_app_id ────
old_payload = '                    "application_id":        app_id.strip(),\n'
new_payload = '                    "application_id":        st.session_state.get("draft_app_id", "APP-UNKNOWN"),\n'
assert old_payload in src, "Payload line not found"
src = src.replace(old_payload, new_payload, 1)

# ── After successful submit, reset draft_app_id ───────────────────────────
old_reset = '                        st.session_state.last_submitted = app_result_id\n'
new_reset = (
    '                        st.session_state.last_submitted = app_result_id\n'
    '                        # Reset so next form submission gets a fresh reference number\n'
    '                        if "draft_app_id" in st.session_state:\n'
    '                            del st.session_state["draft_app_id"]\n'
)
assert old_reset in src, "Success/reset line not found"
src = src.replace(old_reset, new_reset, 1)

Path("app.py").write_text(src, encoding="utf-8")
print("\nPatch applied successfully.")
