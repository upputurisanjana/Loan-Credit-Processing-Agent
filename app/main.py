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

# CORS — permit local frontend dev server (adjust origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(intake_router)
app.include_router(decisions_router)
app.include_router(queue_router)
app.include_router(audit_router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {
        "status": "ok",
        "version": settings.app_version,
        "primary_model": settings.primary_model,
        "policy_path": settings.policy_path,
    }


log.info("Credit Decisioning Agent starting — model=%s", settings.primary_model)
