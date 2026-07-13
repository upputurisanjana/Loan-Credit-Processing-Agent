"""
Amendments router — post-hoc corrections to decided applications.

Endpoints
---------
POST /applications/{application_id}/amendments
    Record a correction linked to an existing DecisionRecord.
    The original record is NEVER modified — the amendment is a new linked row.

GET /applications/{application_id}/amendments
    Return all amendments for a given application.

Design note: amendments require the application to have a completed human
decision first. You cannot amend a pending case — use the /decision endpoint.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.models.decision import DecisionAmendment, DecisionRecord
from app.routers.intake import get_store
from app.db.database import get_db, insert_amendment, fetch_amendments

log = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["amendments"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class AmendmentRequest(BaseModel):
    """Body for submitting a post-hoc correction."""

    amended_by: str = Field(..., min_length=1, description="Username of the person making the amendment")
    amendment_reason: str = Field(
        ...,
        min_length=20,
        description="Plain-English reason for the correction (min 20 chars)",
    )
    field_changes: dict = Field(
        ...,
        description=(
            "Key/value pairs describing what changed and the corrected values. "
            "Example: {\"human_decision\": \"refer\", \"override_reason\": \"New evidence submitted\"}"
        ),
    )


class AmendmentResponse(BaseModel):
    amendment_id: str
    original_application_id: str
    amended_by: str
    amendment_reason: str
    field_changes: dict
    amended_at: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/{application_id}/amendments",
    status_code=status.HTTP_201_CREATED,
    summary="Record a post-hoc correction to a decided application",
)
async def create_amendment(
    application_id: str,
    body: AmendmentRequest,
) -> AmendmentResponse:
    """
    Append a correction linked to an existing decided DecisionRecord.

    Rules:
    1. The application must exist and must already have a human decision.
       Pending cases must use POST /decision, not amendments.
    2. The original DecisionRecord is never modified — this creates a new
       linked amendment row in the database.
    3. amendment_reason must be at least 20 characters.
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
            detail=(
                f"Application {application_id!r} is in state "
                f"'{record.get('status')}' — amendments only apply to decided cases."
            ),
        )

    if record.human_decision is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Application {application_id!r} has not yet been decided. "
                "Use POST /applications/{id}/decision to record the human decision first."
            ),
        )

    amendment = DecisionAmendment(
        amendment_id=str(uuid.uuid4()),
        original_application_id=application_id,
        amended_by=body.amended_by,
        amendment_reason=body.amendment_reason,
        amended_at=datetime.now(timezone.utc),
        field_changes=body.field_changes,
    )

    try:
        db = get_db()
        insert_amendment(db, amendment)
    except Exception as exc:  # noqa: BLE001
        log.error(
            "amendments: DB insert failed for app_id=%s — %s",
            application_id, exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist amendment. Please try again.",
        ) from exc

    log.info(
        "amendments: created amendment_id=%s for app_id=%s by=%s",
        amendment.amendment_id, application_id, body.amended_by,
    )

    return AmendmentResponse(
        amendment_id=amendment.amendment_id,
        original_application_id=amendment.original_application_id,
        amended_by=amendment.amended_by,
        amendment_reason=amendment.amendment_reason,
        field_changes=amendment.field_changes,
        amended_at=amendment.amended_at.isoformat(),
    )


@router.get(
    "/{application_id}/amendments",
    summary="List all amendments for an application",
)
async def list_amendments(application_id: str) -> list[AmendmentResponse]:
    """Return all post-hoc corrections linked to a given application."""
    store = get_store()
    if application_id not in store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id!r} not found.",
        )

    try:
        db = get_db()
        rows = fetch_amendments(db, application_id)
    except Exception as exc:  # noqa: BLE001
        log.error("amendments: DB fetch failed for app_id=%s — %s", application_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch amendments.",
        ) from exc

    import json
    return [
        AmendmentResponse(
            amendment_id=row["amendment_id"],
            original_application_id=row["original_application_id"],
            amended_by=row["amended_by"],
            amendment_reason=row["amendment_reason"],
            field_changes=json.loads(row["field_changes_json"]),
            amended_at=row["amended_at"],
        )
        for row in rows
    ]
