#!/usr/bin/env bash
# start.sh — Start the Credit Decisioning Agent (backend + frontend)
# Usage:
#   ./start.sh           # start both servers
#   ./start.sh backend   # backend only
#   ./start.sh frontend  # frontend only

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-5173}
VENV="$ROOT/.venv"
FRONTEND="$ROOT/frontend"

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[info]${RESET}  $*"; }
success() { echo -e "${GREEN}[ok]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[warn]${RESET}  $*"; }
die()     { echo -e "${RED}[error]${RESET} $*" >&2; exit 1; }

# ── Pre-flight checks ─────────────────────────────────────────────────────────
check_env() {
    info "Checking environment…"

    # .env must exist
    [[ -f "$ROOT/.env" ]] || die ".env not found. Run: cp .env.example .env && fill in GITHUB_TOKEN"

    # GITHUB_TOKEN must not be empty
    local token
    token=$(grep -E '^GITHUB_TOKEN=' "$ROOT/.env" | cut -d= -f2- | tr -d '[:space:]')
    [[ -n "$token" ]] || die "GITHUB_TOKEN is empty in .env — add your GitHub PAT (models:read scope)"

    # Python venv
    [[ -d "$VENV" ]] || die "Virtual env not found. Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    [[ -f "$VENV/bin/uvicorn" ]] || die "uvicorn not installed. Run: source .venv/bin/activate && pip install -r requirements.txt"

    # Node / npm
    command -v node >/dev/null 2>&1 || die "node not found — install Node.js 18+"
    command -v npm  >/dev/null 2>&1 || die "npm not found"

    # Frontend node_modules
    [[ -d "$FRONTEND/node_modules" ]] || {
        warn "node_modules missing — running npm install…"
        npm --prefix "$FRONTEND" install --silent
    }

    success "Environment OK"
}

# ── Backend ───────────────────────────────────────────────────────────────────
start_backend() {
    info "Starting FastAPI backend on http://localhost:${BACKEND_PORT} …"

    # Activate venv inline for this sub-shell
    # shellcheck source=/dev/null
    source "$VENV/bin/activate"

    uvicorn app.main:app \
        --reload \
        --port "$BACKEND_PORT" \
        --log-level info \
        --host 0.0.0.0 &

    BACKEND_PID=$!
    echo "$BACKEND_PID" > "$ROOT/.backend.pid"
    success "Backend started (PID $BACKEND_PID) — docs at http://localhost:${BACKEND_PORT}/docs"
}

# ── Frontend ──────────────────────────────────────────────────────────────────
start_frontend() {
    info "Starting Vite frontend on http://localhost:${FRONTEND_PORT} …"

    VITE_API_URL="http://localhost:${BACKEND_PORT}" \
    npm --prefix "$FRONTEND" run dev -- --port "$FRONTEND_PORT" &

    FRONTEND_PID=$!
    echo "$FRONTEND_PID" > "$ROOT/.frontend.pid"
    success "Frontend started (PID $FRONTEND_PID) — open http://localhost:${FRONTEND_PORT}"
}

# ── Teardown on Ctrl-C ────────────────────────────────────────────────────────
cleanup() {
    echo ""
    info "Shutting down…"
    [[ -f "$ROOT/.backend.pid"  ]] && kill "$(cat "$ROOT/.backend.pid")"  2>/dev/null || true
    [[ -f "$ROOT/.frontend.pid" ]] && kill "$(cat "$ROOT/.frontend.pid")" 2>/dev/null || true
    rm -f "$ROOT/.backend.pid" "$ROOT/.frontend.pid"
    success "Stopped."
}
trap cleanup EXIT INT TERM

# ── Quick test with fixture ───────────────────────────────────────────────────
demo_submit() {
    local fixture="${1:-$ROOT/tests/fixtures/clear_approve.json}"
    [[ -f "$fixture" ]] || { warn "Fixture not found: $fixture"; return; }

    info "Waiting for backend to be ready…"
    local attempts=0
    until curl -sf "http://localhost:${BACKEND_PORT}/health" >/dev/null; do
        sleep 1
        (( attempts++ ))
        [[ $attempts -gt 20 ]] && { warn "Backend didn't start in time — skipping demo submit"; return; }
    done

    echo ""
    info "Submitting demo application from $fixture …"
    curl -s -X POST "http://localhost:${BACKEND_PORT}/applications" \
         -H "Content-Type: application/json" \
         -d @"$fixture" | python3 -m json.tool
    echo ""
    success "Demo app submitted — open http://localhost:${FRONTEND_PORT} to see the queue."
}

# ── Main ──────────────────────────────────────────────────────────────────────
MODE="${1:-both}"

check_env

case "$MODE" in
    backend)
        start_backend
        info "Backend running. Press Ctrl-C to stop."
        wait
        ;;
    frontend)
        start_frontend
        info "Frontend running. Press Ctrl-C to stop."
        wait
        ;;
    demo)
        # Start both + auto-submit the clear_approve fixture
        start_backend
        start_frontend
        demo_submit "${2:-}"
        info "Both servers running. Press Ctrl-C to stop."
        wait
        ;;
    both|"")
        start_backend
        start_frontend
        echo ""
        echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
        echo -e "  ${GREEN}Backend  ${RESET}→  http://localhost:${BACKEND_PORT}/docs"
        echo -e "  ${GREEN}Frontend ${RESET}→  http://localhost:${FRONTEND_PORT}"
        echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
        echo -e "  Press ${BOLD}Ctrl-C${RESET} to stop both servers."
        echo ""
        wait
        ;;
    *)
        die "Unknown mode '$MODE'. Usage: ./start.sh [both|backend|frontend|demo]"
        ;;
esac
