"""
RECOMMEND node — LLM composes plain-English rationale from ScoreBreakdown.

Inputs (from AgentState):
    fields: ApplicationFields
    score_breakdown: ScoreBreakdown
    fairness_check: FairnessCheck

Outputs (mutates AgentState):
    agent_recommendation: "approve" | "refer" | "decline"
    rationale: str
    next_step: "human_gate"

The band (approve/refer/decline) is READ from ScoreBreakdown — the LLM
does not assign or alter it.  The LLM writes only the explanatory text.
"""

import logging

from app.models.scoring import ScoreBreakdown
from app.models.fairness import FairnessCheck
from app.agent.prompts.recommend_prompt import build_recommend_prompt
from app.tools.github_models_client import call_model, get_primary_model

log = logging.getLogger(__name__)

# Fallback rationale if the LLM call fails — keeps the pipeline alive
_FALLBACK_RATIONALE_TEMPLATE = (
    "Agent recommendation: {band_upper}. Composite score: {composite:.3f} "
    "(policy version {version}). LLM rationale unavailable — "
    "underwriter should review score breakdown directly."
)


def run_recommend(
    score_breakdown: ScoreBreakdown,
    fairness_check: FairnessCheck,
    application_id: str,
) -> tuple[str, str]:
    """
    Compose an LLM rationale for the underwriter.

    Returns (recommendation, rationale) where recommendation is the band
    from score_breakdown (never invented by the LLM).

    NOTE: fairness mismatch cases are routed away from this node entirely
    by the graph (via FLAG_FAIRNESS_FAIL).  This function is only called
    when fairness_check.match is True, so no guard is needed here.
    The fairness_check parameter is retained for context passed to the LLM
    prompt if needed in future.
    """
    band: str = score_breakdown.band

    # Ask the LLM to explain the already-computed scores
    score_json = score_breakdown.model_dump_json(indent=2)
    messages = build_recommend_prompt(score_json)

    log.info("app=%s requesting rationale from LLM (band=%s)", application_id, band)

    try:
        rationale = call_model(
            model=get_primary_model(),
            messages=messages,
            temperature=0.0,
            max_tokens=400,
        )
        rationale = rationale.strip()
        if not rationale:
            raise ValueError("empty LLM response")
    except Exception as exc:  # noqa: BLE001
        log.error("app=%s recommend LLM call failed: %s", application_id, exc)
        rationale = _FALLBACK_RATIONALE_TEMPLATE.format(
            band_upper=band.upper(),
            composite=score_breakdown.composite_score,
            version=score_breakdown.policy_version,
        )

    log.info("app=%s recommendation=%s", application_id, band)
    return band, rationale
