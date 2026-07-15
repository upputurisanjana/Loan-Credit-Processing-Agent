"""
Queue router — read-only endpoint for the Case Queue UI.

GET /queue
    Returns all applications in summary form for the queue table.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from app.models.decision import DecisionRecord
from app.routers.intake import get_store

log = logging.getLogger(__name__)

router = APIRouter(tags=["queue"])


@router.get("/queue", summary="List all applications for the case queue")
async def list_queue() -> list[dict]:
    """
    Return a summary of every stored application, suitable for the Case Queue
    table in the frontend.

    Shape per item:
        application_id, agent_recommendation, status, created_at,
        composite_score, band, policy_version,
        fairness_match, challenger_disagreement, human_decision
    """
    store = get_store()
    items: list[dict] = []

    for record in store.values():
        if isinstance(record, DecisionRecord):
            sb = record.score_breakdown
            items.append({
                "application_id":       record.application_id,
                "applicant_name":       record.applicant_name,
                "loan_amount_requested": record.loan_amount_requested,
                "agent_recommendation": record.agent_recommendation,
                "status":               record.status,
                "created_at":           record.created_at.isoformat(),
                "composite_score":      sb.composite_score,
                "band":                 sb.band,
                "policy_version":       record.policy_version,
                "human_decision":       record.human_decision,
                "human_reviewer":       record.human_reviewer,
            })
        else:
            items.append({
                "application_id":       record.get("application_id", "unknown"),
                "applicant_name":       record.get("applicant_name", ""),
                "loan_amount_requested": record.get("loan_amount_requested", 0),
                "agent_recommendation": None,
                "status":               record.get("status", "error"),
                "created_at":           record.get("submitted_at", datetime.now(timezone.utc).isoformat()),
                "composite_score":      None,
                "band":                 None,
                "policy_version":       "-",
                "human_decision":       None,
                "human_reviewer":       None,
            })

    # Sort oldest-first; REFER-first sort is handled client-side
    items.sort(key=lambda x: x["created_at"])
    return items
