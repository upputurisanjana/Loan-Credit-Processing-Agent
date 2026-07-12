"""
Decisions router — human gate approval for pending applications.

Endpoints
---------
GET  /applications/{application_id}/decision
    Return the current decision state (pending or decided).

POST /applications/{application_id}/decision
    Underwriter approve, override, or request-more-info.
    This is the ONLY path through which a decision becomes final.
    Every application must pass through this gate — no auto-finalisation.

Design note: override_reason is REQUIRED when the human decision differs
from agent_recommendation.  The original agent recommendation is preserved
unmodified in the record.
"""

import logging
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, model_validator

from app.models.decision import DecisionRecord
from app.routers.intake import get_store

log = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["decisions"])


# ---------------------------------------------------------------------------
# Request / response schemas for the human gate
# ---------------------------------------------------------------------------

class HumanDecisionRequest(BaseModel):
    """Body for the underwriter's decision action."""

    human_decision: Literal["approve", "refer", "decline"]
    human_reviewer: str = Field(..., min_length=1, description="Reviewer identifier / username")
    override_reason: str | None = Field(
        None,
        description=(
            "Required (min 20 chars) when human_decision differs from "
            "the agent_recommendation. Stored alongside original recommendation."
        ),
    )

    @model_validator(mode="after")
    def validate_override_reason(self) -> "HumanDecisionRequest":
        # We validate override consistency in the endpoint handler where we can
        # compare against agent_recommendation; this validator checks format only.
        if self.override_reason is not None and len(self.override_reason.strip()) < 20:
            raise ValueError("override_reason must be at least 20 characters")
        return self


class DecisionResponse(BaseModel):
    application_id: str
    agent_recommendation: str
    human_decision: str | None
    human_reviewer: str | None
    override_reason: str | None
    decided_at: str | None
    status: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/{application_id}/decision",
    summary="Get current decision state for an application",
)
async def get_decision(application_id: str) -> dict:
    """Return the pending or decided state of an application."""
    store = get_store()
    record = store.get(application_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id!r} not found.",
        )

    if not isinstance(record, DecisionRecord):
        # Hold or error state
        return record

    return DecisionResponse(
        application_id=record.application_id,
        agent_recommendation=record.agent_recommendation,
        human_decision=record.human_decision,
        human_reviewer=record.human_reviewer,
        override_reason=record.override_reason,
        decided_at=record.decided_at.isoformat() if record.decided_at else None,
        status="pending_human_review" if record.human_decision is None else "decided",
    ).model_dump()


@router.post(
    "/{application_id}/decision",
    summary="Underwriter approves, overrides, or requests more info",
    status_code=status.HTTP_200_OK,
)
async def record_human_decision(
    application_id: str,
    body: HumanDecisionRequest,
) -> dict:
    """
    Record the underwriter's decision for a pending application.

    Rules enforced here:
    1. Application must exist and be in `pending_human_review` state.
    2. If human_decision differs from agent_recommendation, override_reason
       is required (min 20 chars, validated on the request model).
    3. The original agent_recommendation is NEVER overwritten — only
       human_decision, human_reviewer, override_reason, decided_at are set.
    4. Once decided, the record cannot be re-decided via this endpoint
       (amendments go via the /amendments endpoint, Phase 2).
    """
    store = get_store()
    record = store.get(application_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id!r} not found.",
        )

    if not isinstance(record, DecisionRecord):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Application {application_id!r} is not in a decidable state ({record.get('status')}).",
        )

    if record.human_decision is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Application {application_id!r} already has a human decision "
                f"({record.human_decision}). Use the amendments endpoint to correct it."
            ),
        )

    # Enforce override_reason when human overrides the agent recommendation
    is_override = body.human_decision != record.agent_recommendation
    if is_override and not body.override_reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"override_reason is required when the human decision ({body.human_decision!r}) "
                f"differs from the agent recommendation ({record.agent_recommendation!r})."
            ),
        )

    # Apply decision — mutate the record fields (human gate only)
    record.human_decision = body.human_decision
    record.human_reviewer = body.human_reviewer
    record.override_reason = body.override_reason
    record.decided_at = datetime.utcnow()

    log.info(
        "decision: app_id=%s agent_rec=%s human_decision=%s reviewer=%s override=%s",
        application_id,
        record.agent_recommendation,
        body.human_decision,
        body.human_reviewer,
        is_override,
    )

    return DecisionResponse(
        application_id=record.application_id,
        agent_recommendation=record.agent_recommendation,
        human_decision=record.human_decision,
        human_reviewer=record.human_reviewer,
        override_reason=record.override_reason,
        decided_at=record.decided_at.isoformat(),
        status="decided",
    ).model_dump()
