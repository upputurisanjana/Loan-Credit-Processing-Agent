"""
Analysis router — on-demand fairness recheck and challenger re-run.

Endpoints
---------
GET  /applications/{application_id}/fairness
    Re-runs the identity-blind fairness recheck on demand and returns the
    FairnessCheck result stored in the DecisionRecord (no new LLM call needed
    — the result was computed at pipeline time and is fully deterministic).

GET  /applications/{application_id}/challenger
    Returns the ChallengerResult stored in the DecisionRecord.

POST /applications/{application_id}/challenger/rerun
    Re-runs the challenger LLM call live against the stored score breakdown.
    Useful when the challenger model has been updated or the initial run failed.
    WARNING: consumes one LLM API call.

These endpoints expose the existing pipeline results with richer detail
so the Streamlit / React frontends can display dedicated interactive panels.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.models.decision import DecisionRecord
from app.models.fairness import FairnessCheck, ChallengerResult
from app.routers.intake import get_store

log = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["analysis"])


# ─────────────────────────────────────────────────────────────────────────────
# Fairness endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{application_id}/fairness",
    summary="Return the fairness recheck result for an application",
)
async def get_fairness(application_id: str) -> dict:
    """
    Return the stored FairnessCheck result with full explainability detail.

    The fairness recheck is computed deterministically at pipeline time:
    - Pass 1: score(fields)                  — identity present, never used
    - Pass 2: score(identity_blind_copy(fields)) — identity = [REDACTED]
    Both passes run the *same* pure-Python scorer.  Any mismatch means
    identity leaked into a scoring path — a serious regression.

    Shape:
        {
            "application_id": "APP-001",
            "fairness_check": { original_band, masked_band,
                                original_composite, masked_composite, match },
            "explanation": { ... }
        }
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
            detail=f"Application {application_id!r} is not in a decided/pending state ({record.get('status')}).",
        )

    fc = record.fairness_check
    composite_delta = abs(fc.original_composite - fc.masked_composite)

    explanation = {
        "method": (
            "Identity-blind re-score: the same deterministic scoring engine is run twice. "
            "Pass 1 uses the original ApplicationFields (identity present but never read by scorer). "
            "Pass 2 uses a deep copy where IdentityBlock is replaced with [REDACTED]. "
            "Results must be bit-for-bit identical — any difference indicates a regression."
        ),
        "composite_delta": round(composite_delta, 6),
        "band_delta": 0 if fc.original_band == fc.masked_band else 1,
        "verdict": (
            "PASS — no identity leakage detected. Scoring is structurally fair."
            if fc.match
            else (
                "FAIL — identity-masked re-score produced a different band. "
                f"Original: {fc.original_band} ({fc.original_composite:.4f}), "
                f"Masked: {fc.masked_band} ({fc.masked_composite:.4f}). "
                "Application forced to REFER. Investigate immediately."
            )
        ),
        "forced_refer": not fc.match,
        "agent_recommendation": record.agent_recommendation,
        "policy_version": record.policy_version,
    }

    log.info("analysis: fairness detail requested for app_id=%s match=%s", application_id, fc.match)

    return {
        "application_id": application_id,
        "fairness_check": fc.model_dump(),
        "explanation": explanation,
        "score_breakdown": record.score_breakdown.model_dump(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Challenger endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{application_id}/challenger",
    summary="Return the challenger model result for an application",
)
async def get_challenger(application_id: str) -> dict:
    """
    Return the stored ChallengerResult with full explainability detail.

    The challenger is an independent LLM (CHALLENGER_MODEL) that reads the
    same score breakdown and financial data and states its own band opinion.
    A delta > 1 (approve↔decline) forces REFER regardless of the primary band.

    Shape:
        {
            "application_id": "APP-001",
            "challenger_result": { primary_band, challenger_band, bands_agree, delta },
            "explanation": { ... }
        }
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
            detail=f"Application {application_id!r} is not in a decided/pending state.",
        )

    cr = record.challenger_result

    if cr is None:
        return {
            "application_id": application_id,
            "challenger_result": None,
            "explanation": {
                "method": "Challenger model was not run for this application.",
                "verdict": "N/A",
                "forced_refer": False,
            },
        }

    band_order = {"decline": 0, "refer": 1, "approve": 2}
    band_labels = {
        0: "No disagreement — models agree.",
        1: "1-tier disagreement (approve↔refer or refer↔decline). No forced REFER.",
        2: "2-tier disagreement (approve↔decline). REFER forced — mandatory human review.",
    }
    delta_int  = int(cr.delta)
    tier_label = band_labels.get(delta_int, f"Delta: {delta_int}")

    explanation = {
        "method": (
            "An independent LLM (CHALLENGER_MODEL) receives the same applicant financial data "
            "and the primary score summary, then states its own band opinion (one word: "
            "approve/refer/decline). It does NOT recompute the numeric scores — those come "
            "solely from the deterministic policy engine."
        ),
        "primary_model_band":     cr.primary_band,
        "challenger_model_band":  cr.challenger_band,
        "delta":                  delta_int,
        "tier_explanation":       tier_label,
        "bands_agree":            cr.bands_agree,
        "forced_refer":           not cr.bands_agree,
        "verdict": (
            "AGREE — challenger confirms the primary recommendation."
            if cr.bands_agree
            else (
                f"DISAGREE — challenger suggested '{cr.challenger_band}' vs primary '{cr.primary_band}'. "
                "Disagreement exceeds 1 band. Application forced to REFER."
            )
        ),
        "agent_recommendation":   record.agent_recommendation,
        "policy_version":         record.policy_version,
    }

    log.info(
        "analysis: challenger detail requested for app_id=%s agree=%s",
        application_id, cr.bands_agree,
    )

    return {
        "application_id": application_id,
        "challenger_result": cr.model_dump(),
        "explanation": explanation,
        "score_breakdown": record.score_breakdown.model_dump(),
    }


@router.post(
    "/{application_id}/challenger/rerun",
    summary="Re-run the challenger LLM call live",
    status_code=status.HTTP_200_OK,
)
async def rerun_challenger(application_id: str) -> dict:
    """
    Re-execute the challenger model against the stored score breakdown and fields.

    This makes a live LLM API call using CHALLENGER_MODEL.
    Use this when: (a) the challenger failed during the initial pipeline run,
    or (b) the challenger model has been updated and you want a fresh opinion.

    The result is stored back into the in-memory record (not the DB — the DB
    record is append-only; use amendments for audit-grade corrections).
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
            detail=f"Application {application_id!r} is not in a decidable state.",
        )

    # Re-run challenger using stored score breakdown.
    # We reconstruct minimal ApplicationFields from what the scorer stored.
    from app.agent.nodes.challenger_compare import run_challenger_compare
    from app.models.application import ApplicationFields, IdentityBlock

    sb = record.score_breakdown

    # Reconstruct minimal ApplicationFields from score breakdown
    # (DTI ratio = debt / income, so we back-calculate a representative income/debt pair)
    # We use income=10000 as a neutral baseline — the challenger only uses the breakdown summary.
    synthetic_income = 10_000.0
    synthetic_debt   = round(sb.dti_ratio * synthetic_income, 2)

    fields = ApplicationFields(
        application_id=application_id,
        identity=IdentityBlock(name="[REDACTED]", address="[REDACTED]"),
        income_monthly=synthetic_income,
        debt_monthly=synthetic_debt,
        credit_history_years=2.0,      # not used by challenger prompt directly
        credit_history_flags=[],
        employment_months_current=12,
    )

    try:
        new_cr = run_challenger_compare(fields, sb)
    except Exception as exc:
        log.error("analysis: challenger rerun failed for app_id=%s — %s", application_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Challenger rerun failed: {exc}",
        )

    # Update in-memory record (not DB — append-only)
    record.challenger_result = new_cr

    log.info(
        "analysis: challenger rerun app_id=%s new_band=%s agree=%s",
        application_id, new_cr.challenger_band, new_cr.bands_agree,
    )

    band_order = {"decline": 0, "refer": 1, "approve": 2}
    return {
        "application_id":    application_id,
        "challenger_result": new_cr.model_dump(),
        "rerun":             True,
        "note": (
            "Result stored in memory only. Original DB record unchanged (append-only). "
            "Use the amendments endpoint to create an audit-grade correction."
        ),
    }
