"""
Decisions router — human gate approval for pending applications.

Endpoints
---------
POST /applications/{application_id}/decision
    Underwriter approve, override, or (via amendments) decline.
    This is the ONLY path through which a final decision (approve/refer/decline)
    becomes recorded. No auto-finalisation.

POST /applications/{application_id}/request-info
    Reviewer requests additional information from the applicant.
    Sets status to awaiting_information without finalising the decision.
    The application remains open for further review once info is received.

PATCH /applications/{application_id}/notice
    Save the reviewer-edited adverse action notice text.
    Must be called before the final decision so the applicant receives
    the edited version, not the raw LLM draft.

Design notes:
- override_reason is REQUIRED when the human decision differs from
  agent_recommendation.
- The original agent_recommendation is preserved unmodified.
- Once decided, the record cannot be re-decided via this endpoint
  (amendments go via the /amendments endpoint).
- request-info does NOT set human_decision — it sets awaiting_info_items
  and status becomes awaiting_information.
"""

import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, model_validator

from app.models.decision import DecisionRecord
from app.routers.intake import get_store, _public_payload
from app.db.database import (
    get_db,
    record_human_decision as db_record_human_decision,
    update_approved_notice as db_update_approved_notice,
    update_awaiting_info as db_update_awaiting_info,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["decisions"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class HumanDecisionRequest(BaseModel):
    """Body for the underwriter's final decision action."""

    human_decision: Literal["approve", "refer", "decline"]
    human_reviewer: str = Field(..., min_length=1)
    override_reason: str | None = Field(
        None,
        description=(
            "Required (min 20 chars) when human_decision differs from "
            "the agent_recommendation."
        ),
    )

    @model_validator(mode="after")
    def validate_override_reason(self) -> "HumanDecisionRequest":
        if self.override_reason is not None and len(self.override_reason.strip()) < 20:
            raise ValueError("override_reason must be at least 20 characters")
        return self


class RequestInfoRequest(BaseModel):
    """Body for the reviewer requesting additional information."""

    requested_items: list[str] = Field(
        ...,
        min_length=1,
        description="List of specific items being requested from the applicant.",
    )
    reviewer: str = Field(..., min_length=1, description="Reviewer identifier")


class NoticeUpdateRequest(BaseModel):
    """Body for saving the reviewer-edited notice text."""

    notice_text: str = Field(
        ...,
        min_length=10,
        description="The final, edited adverse action notice text.",
    )
    reviewer: str = Field(..., min_length=1, description="Reviewer identifier")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/{application_id}/decision",
    summary="Underwriter records final decision (approve / refer / decline)",
    status_code=status.HTTP_200_OK,
)
async def record_human_decision(
    application_id: str,
    body: HumanDecisionRequest,
) -> dict:
    """
    Record the underwriter's final decision for a pending application.

    Rules:
    1. Application must exist and be in pending_human_review or
       awaiting_information state (not already decided, not hold/error).
    2. If human_decision differs from agent_recommendation, override_reason
       is required (min 20 chars).
    3. The original agent_recommendation is NEVER overwritten.
    4. Once decided, the record cannot be re-decided here.
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

    is_override = body.human_decision != record.agent_recommendation
    if is_override and not body.override_reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"override_reason is required when the human decision ({body.human_decision!r}) "
                f"differs from the agent recommendation ({record.agent_recommendation!r})."
            ),
        )

    # DecisionRecord is frozen — create a new instance with updated fields
    # and replace the store entry. Never mutate the original object.
    updated = record.model_copy(update={
        "human_decision": body.human_decision,
        "human_reviewer": body.human_reviewer,
        "override_reason": body.override_reason,
        "decided_at": datetime.now(timezone.utc),
        "awaiting_info_items": [],
    })
    store[application_id] = updated

    try:
        db = get_db()
        db_record_human_decision(
            db,
            application_id,
            body.human_decision,
            body.human_reviewer,
            body.override_reason,
        )
    except Exception as exc:  # noqa: BLE001
        log.error("decision: DB update failed for app_id=%s — %s", application_id, exc)

    log.info(
        "decision: app_id=%s agent_rec=%s human_decision=%s reviewer=%s override=%s",
        application_id,
        record.agent_recommendation,
        body.human_decision,
        body.human_reviewer,
        is_override,
    )

    return _public_payload(updated)


@router.post(
    "/{application_id}/request-info",
    summary="Reviewer requests additional information without finalising decision",
    status_code=status.HTTP_200_OK,
)
async def request_more_info(
    application_id: str,
    body: RequestInfoRequest,
) -> dict:
    """
    Reviewer flags the application as awaiting information from the applicant.

    This does NOT set human_decision — it sets awaiting_info_items and moves
    the status to awaiting_information. The application remains open.
    The reviewer can later call POST /decision once the info is received.

    To clear the awaiting state (resume review), call this endpoint with
    an empty requested_items list — or simply POST /decision when ready.
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
            detail=f"Application {application_id!r} is not in a reviewable state.",
        )

    if record.human_decision is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Application {application_id!r} is already decided.",
        )

    updated = record.model_copy(update={"awaiting_info_items": body.requested_items})
    store[application_id] = updated

    try:
        db = get_db()
        db_update_awaiting_info(db, application_id, body.requested_items)
    except Exception as exc:  # noqa: BLE001
        log.error("decision: DB awaiting_info update failed for app_id=%s — %s", application_id, exc)

    log.info(
        "decision: app_id=%s request-info by %s — %d items",
        application_id, body.reviewer, len(body.requested_items),
    )

    return _public_payload(updated)


@router.patch(
    "/{application_id}/notice",
    summary="Save the reviewer-edited adverse action notice text",
    status_code=status.HTTP_200_OK,
)
async def update_notice(
    application_id: str,
    body: NoticeUpdateRequest,
) -> dict:
    """
    Save the reviewer-edited version of the adverse action notice.

    The edited text is stored in approved_notice_text.  When the applicant
    checks their status, they will see this approved version instead of the
    raw LLM draft.

    This can be called before or after POST /decision.
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
            detail=f"Application {application_id!r} is not in a valid state for notice editing.",
        )

    updated = record.model_copy(update={"approved_notice_text": body.notice_text})
    store[application_id] = updated

    try:
        db = get_db()
        db_update_approved_notice(db, application_id, body.notice_text)
    except Exception as exc:  # noqa: BLE001
        log.error("decision: DB notice update failed for app_id=%s — %s", application_id, exc)

    log.info(
        "decision: approved_notice_text saved for app_id=%s by %s (%d chars)",
        application_id, body.reviewer, len(body.notice_text),
    )

    return _public_payload(updated)
