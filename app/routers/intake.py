"""
Intake router — accepts new credit applications and runs the decisioning pipeline.

Endpoints
---------
POST /applications
    Submit a new application; runs the full agent pipeline.
    Returns a pending DecisionRecord (human_decision=None) or a hold/error response.

GET /applications/{application_id}
    Retrieve the stored decision record for an application.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.models.application import ApplicationRaw
from app.models.decision import DecisionRecord
from app.agent.graph import run_pipeline

log = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["intake"])

# ---------------------------------------------------------------------------
# In-memory store — sufficient for Phase 1 demo.
# Replace with SQLAlchemy DB layer (app/db/) for production.
# ---------------------------------------------------------------------------
_store: dict[str, Any] = {}  # application_id → DecisionRecord | dict


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a new credit application",
    response_description=(
        "Application accepted and processed. "
        "Returns a DecisionRecord with pending human review, "
        "or a hold/error object if the pipeline could not complete."
    ),
)
async def submit_application(body: ApplicationRaw) -> dict:
    """
    Run the full credit-decisioning pipeline on the submitted application.

    The pipeline terminates at the HUMAN_GATE node — every application
    requires explicit underwriter approval before a decision takes effect.

    Possible outcomes:
    - `pending_human_review` — pipeline completed; awaiting underwriter.
    - `hold_for_document` — required documents are missing.
    - `error` — pipeline failed; details in `message`.
    """
    app_id = body.application_id

    if app_id in _store:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Application {app_id!r} already exists.",
        )

    log.info("intake: running pipeline for app_id=%s", app_id)

    result = run_pipeline(body)

    if isinstance(result, DecisionRecord):
        payload = result.model_dump(mode="json")
        payload["status"] = "pending_human_review"
        _store[app_id] = result
        log.info(
            "intake: app_id=%s band=%s status=pending_human_review",
            app_id,
            result.agent_recommendation,
        )
        return payload

    # Hold or error — also store so /decision endpoint can explain the state
    _store[app_id] = result
    log.warning("intake: app_id=%s result_status=%s", app_id, result.get("status"))
    return result


@router.get(
    "/{application_id}",
    summary="Retrieve a stored decision record",
)
async def get_application(application_id: str) -> dict:
    """Return the current state of an application by ID."""
    record = _store.get(application_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id!r} not found.",
        )
    if isinstance(record, DecisionRecord):
        return record.model_dump(mode="json")
    return record


def get_store() -> dict[str, Any]:
    """Expose the in-memory store to the decisions router."""
    return _store
