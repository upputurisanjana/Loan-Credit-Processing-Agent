"""
Audit router — read-only access to the full pipeline trace per application.

Endpoints
---------
GET /applications/{application_id}/trace
    Returns the ordered node-by-node trace for a given application.
    The trace is embedded in the DecisionRecord and stored at pipeline run time.
"""
import logging

from fastapi import APIRouter, HTTPException, status

from app.models.decision import DecisionRecord
from app.routers.intake import get_store

log = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["audit"])


@router.get(
    "/{application_id}/trace",
    summary="Full pipeline trace for an application",
)
async def get_trace(application_id: str) -> dict:
    """
    Return the ordered list of trace entries produced by the agent pipeline.
    Each entry contains the node name, timestamp, and the key inputs/outputs
    logged at that node.

    Shape:
        {
            "application_id": "APP-001",
            "trace": [
                { "node": "VERIFY",  "timestamp": "...", "status": "ok", ... },
                { "node": "EXTRACT", "timestamp": "...", "income_monthly": 5000, ... },
                ...
            ]
        }
    """
    store = get_store()
    record = store.get(application_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id!r} not found.",
        )

    if isinstance(record, DecisionRecord):
        trace = record.pipeline_trace
    else:
        # Hold / error — return whatever partial trace was stored
        trace = record.get("pipeline_trace", [])

    log.info("audit: trace requested for app_id=%s nodes=%d", application_id, len(trace))

    return {
        "application_id": application_id,
        "trace": trace,
    }
