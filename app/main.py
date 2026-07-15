"""
FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --port 8000

Interactive docs at: http://localhost:8000/docs
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load settings first — this populates os.environ for downstream imports
from app.config import settings  # noqa: F401 (side-effect import)
from app.routers.intake import router as intake_router
from app.routers.decisions import router as decisions_router
from app.routers.queue import router as queue_router
from app.routers.audit import router as audit_router
from app.routers.amendments import router as amendments_router
from app.routers.analysis import router as analysis_router
from app.routers.documents import router as documents_router
from app.middleware.rate_limit import RateLimitMiddleware

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=(
        "Credit application decisioning agent. "
        "Pipeline: verify → extract → score (pure Python) → fairness recheck → recommend → human gate. "
        "Every decision requires explicit underwriter approval."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — origins are environment-controlled via ALLOWED_ORIGINS in .env
# Dev default: localhost ports 5173/3000/8000
# Production: set ALLOWED_ORIGINS=https://your-app.example.com
_cors_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting — protect LLM-heavy endpoints from quota exhaustion
app.add_middleware(RateLimitMiddleware)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(intake_router)
app.include_router(decisions_router)
app.include_router(queue_router)
app.include_router(audit_router)
app.include_router(amendments_router)
app.include_router(analysis_router)
app.include_router(documents_router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["meta"])
async def health() -> dict:
    """
    Returns API status, model config, and a live reachability probe for
    both the primary and challenger LLM models.
    """
    from app.tools.github_models_client import call_model

    def _probe_model(model_name: str) -> dict:
        try:
            call_model(
                model=model_name,
                messages=[{"role": "user", "content": "ping"}],
                temperature=0.0,
                max_tokens=1,
            )
            return {"status": "ok", "model": model_name}
        except Exception as exc:  # noqa: BLE001
            return {"status": "unavailable", "model": model_name, "error": str(exc)[:120]}

    primary_probe    = _probe_model(settings.primary_model)
    challenger_probe = _probe_model(settings.challenger_model)

    overall = (
        "ok"
        if primary_probe["status"] == "ok"
        else "degraded"
    )
    if challenger_probe["status"] != "ok":
        overall = "degraded"

    return {
        "status": overall,
        "version": settings.app_version,
        "primary_model":    primary_probe,
        "challenger_model": challenger_probe,
        "policy_path": settings.policy_path,
    }


log.info("Credit Decisioning Agent starting — model=%s", settings.primary_model)
