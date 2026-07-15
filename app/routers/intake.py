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

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.models.application import ApplicationRaw
from app.models.decision import DecisionRecord
from app.models.scoring import ScoreBreakdown
from app.models.fairness import FairnessCheck, ChallengerResult
from app.agent.graph import run_pipeline
from app.db.database import get_db, insert_decision, fetch_all_decisions

log = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["intake"])

# ---------------------------------------------------------------------------
# In-memory store — write-through cache backed by SQLite (app/db/).
# All writes go to DB first; _store is populated on insert for fast reads.
# On startup the store is rehydrated from the DB so the queue is never empty
# after a server restart.
# ---------------------------------------------------------------------------
_store: dict[str, Any] = {}  # application_id → DecisionRecord | dict


def _row_to_decision_record(row) -> DecisionRecord:
    """Reconstruct a DecisionRecord from a decision_records DB row."""
    sb_raw = json.loads(row["score_breakdown_json"])
    score_breakdown = ScoreBreakdown(**sb_raw)

    fairness_check = FairnessCheck(
        original_band=row["fairness_original_band"],
        masked_band=row["fairness_masked_band"],
        original_composite=row["fairness_original_composite"],
        masked_composite=row["fairness_masked_composite"],
        match=bool(row["fairness_match"]),
    )

    created_at = row["created_at"]
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)

    decided_at = row["decided_at"]
    if isinstance(decided_at, str) and decided_at:
        decided_at = datetime.fromisoformat(decided_at)
    else:
        decided_at = None

    # awaiting_info_items stored as JSON list; older rows may not have it
    awaiting_raw = row["awaiting_info_items"] if "awaiting_info_items" in row.keys() else "[]"
    try:
        awaiting_items = json.loads(awaiting_raw or "[]")
    except Exception:
        awaiting_items = []

    # pipeline_trace stored as JSON list; older rows may not have the column
    trace_raw = row["pipeline_trace"] if "pipeline_trace" in row.keys() else "[]"
    try:
        pipeline_trace = json.loads(trace_raw or "[]")
    except Exception:
        pipeline_trace = []

    return DecisionRecord(
        application_id=row["application_id"],
        policy_version=row["policy_version"],
        applicant_name=row["applicant_name"] if "applicant_name" in row.keys() else "",
        applicant_address=row["applicant_address"] if "applicant_address" in row.keys() else "",
        loan_amount_requested=row["loan_amount_requested"] if "loan_amount_requested" in row.keys() else 0.0,
        applicant_notes=row["applicant_notes"] if "applicant_notes" in row.keys() else None,
        score_breakdown=score_breakdown,
        fairness_check=fairness_check,
        challenger_result=None,  # not stored in DB
        agent_recommendation=row["agent_recommendation"],
        rationale=row["rationale"],
        adverse_action_draft=row["adverse_action_draft"],
        approved_notice_text=row["approved_notice_text"] if "approved_notice_text" in row.keys() else None,
        human_decision=row["human_decision"],
        human_reviewer=row["human_reviewer"],
        override_reason=row["override_reason"],
        decided_at=decided_at,
        awaiting_info_items=awaiting_items,
        pipeline_trace=pipeline_trace,
        created_at=created_at,
    )


def _load_store_from_db() -> None:
    """Populate _store from the database on startup."""
    try:
        db = get_db()
        rows = fetch_all_decisions(db)
        for row in rows:
            try:
                record = _row_to_decision_record(row)
                _store[record.application_id] = record
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "intake: failed to rehydrate app_id=%s from DB — %s",
                    row["application_id"] if row else "?", exc,
                )
        log.info("intake: rehydrated %d application(s) from DB into memory store", len(_store))
    except Exception as exc:  # noqa: BLE001
        log.warning("intake: could not load store from DB on startup — %s", exc)


# Rehydrate on module load (happens when FastAPI starts)
_load_store_from_db()


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
        # Persist to DB first — if this fails we must not serve a record
        # that only exists in memory and will vanish on restart.
        try:
            db = get_db()
            insert_decision(db, result)
        except Exception as exc:  # noqa: BLE001
            log.error("intake: DB insert failed for app_id=%s — %s", app_id, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Pipeline completed but the record could not be persisted "
                    f"for application {app_id!r}. Please retry. ({exc})"
                ),
            )
        _store[app_id] = result
        log.info(
            "intake: app_id=%s band=%s status=%s",
            app_id,
            result.agent_recommendation,
            result.status,
        )
        return _public_payload(result)

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
        return _public_payload(record)
    return record


def _public_payload(record: DecisionRecord) -> dict:
    """
    Serialise a DecisionRecord for the public API response.

    Strips internal pipeline diagnostics — fairness_check, challenger_result,
    and pipeline_trace — from the JSON sent to the browser.

    These three fields continue to:
      - run fully in the pipeline (safety guarantees unchanged)
      - be stored in the DB (audit trail intact)
      - exist in the in-memory store (available for future admin endpoints)

    They are excluded here because they are internal mechanics, not reviewer
    or applicant information. Outcomes are already communicated via
    agent_recommendation and rationale.
    """
    return record.model_dump(
        mode="json",
        exclude={"fairness_check", "challenger_result", "pipeline_trace"},
    )


def get_store() -> dict[str, Any]:
    """Expose the in-memory store to the decisions router."""
    return _store
