"""
LangGraph decisioning agent — single pipeline with explicit conditional edges.

Pipeline
--------
INTAKE → VERIFY → (hold | EXTRACT → SCORE → FAIRNESS_RECHECK
                                            ├─ mismatch → FLAG_FAIRNESS_FAIL → HUMAN_GATE
                                            └─ match    → RECOMMEND → HUMAN_GATE)

Every path terminates at HUMAN_GATE with status "pending_human_review".
No decision is ever auto-finalised.

Usage
-----
    from app.agent.graph import run_pipeline
    result = run_pipeline(raw_application)
    # result is DecisionRecord (human_decision=None) or a hold/error dict
"""

import logging
from datetime import datetime, timezone
from typing import Any, Literal, TypedDict

from langgraph.graph import StateGraph, END

from app.models.application import ApplicationRaw, ApplicationFields
from app.models.verification import VerifyResult
from app.models.scoring import ScoreBreakdown
from app.models.fairness import FairnessCheck, ChallengerResult
from app.models.decision import DecisionRecord
from app.agent.nodes.verify import run_verify
from app.agent.nodes.extract import run_extract
from app.agent.nodes.score import run_score
from app.agent.nodes.fairness_recheck import run_fairness_recheck
from app.agent.nodes.recommend import run_recommend
from app.agent.nodes.challenger_compare import run_challenger_compare
from app.agent.nodes.draft_notice import run_draft_notice

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared agent state
# ---------------------------------------------------------------------------

class AgentState(TypedDict, total=False):
    raw: ApplicationRaw
    verify_result: VerifyResult
    fields: ApplicationFields
    score_breakdown: ScoreBreakdown
    fairness_check: FairnessCheck
    challenger_result: "ChallengerResult | None"
    agent_recommendation: str
    rationale: str
    adverse_action_draft: str
    status: str          # "ok" | "hold_for_document" | "pending_human_review" | "flag_fairness_fail" | "error"
    error_message: str | None
    pipeline_trace: list[dict]


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------

def node_verify(state: AgentState) -> AgentState:
    raw: ApplicationRaw = state["raw"]
    log.info("node=VERIFY app=%s", raw.application_id)
    result = run_verify(raw)
    state["verify_result"] = result
    state["status"] = result.status
    _trace(state, "VERIFY", {
        "status": result.status,
        "missing_docs": result.missing_docs,
        "consistency_flags": result.consistency_flags,
    })
    return state


def node_hold(state: AgentState) -> AgentState:
    raw: ApplicationRaw = state["raw"]
    log.info("node=HOLD app=%s missing=%s", raw.application_id, state["verify_result"].missing_docs)
    state["status"] = "hold_for_document"
    _trace(state, "HOLD_FOR_DOCUMENT", {"missing_docs": state["verify_result"].missing_docs})
    return state


def node_extract(state: AgentState) -> AgentState:
    raw: ApplicationRaw = state["raw"]
    log.info("node=EXTRACT app=%s", raw.application_id)
    try:
        fields = run_extract(raw)
        state["fields"] = fields
        _trace(state, "EXTRACT", {
            "income_monthly": fields.income_monthly,
            "debt_monthly": fields.debt_monthly,
            "credit_history_years": fields.credit_history_years,
            "employment_months_current": fields.employment_months_current,
        })
    except Exception as exc:  # noqa: BLE001
        log.error("node=EXTRACT app=%s error=%s", raw.application_id, exc)
        state["status"] = "error"
        state["error_message"] = f"Extraction failed: {exc}"
        _trace(state, "EXTRACT", {"error": str(exc)})
    return state


def node_score(state: AgentState) -> AgentState:
    fields: ApplicationFields = state["fields"]
    log.info("node=SCORE app=%s", fields.application_id)
    breakdown = run_score(fields)
    state["score_breakdown"] = breakdown
    _trace(state, "SCORE", {
        "composite_score": breakdown.composite_score,
        "band": breakdown.band,
        "policy_version": breakdown.policy_version,
    })
    return state


def node_challenger(state: AgentState) -> AgentState:
    """
    Run the challenger model comparison.

    Per ARCHITECTURE.md §6: the challenger does NOT replace the band from
    the deterministic scorer.  It only checks whether an independent model
    would suggest a different band, as a sanity check.  Disagreement > 1
    band forces REFER (handled in node_fairness_recheck routing).
    """
    fields: ApplicationFields = state["fields"]
    breakdown: ScoreBreakdown = state["score_breakdown"]
    log.info("node=CHALLENGER app=%s", fields.application_id)

    challenger_result = run_challenger_compare(fields, breakdown)
    state["challenger_result"] = challenger_result

    # If challenger disagrees by > 1 band, force a refer via status
    if not challenger_result.bands_agree:
        log.warning(
            "app=%s challenger_disagree primary=%s challenger=%s — forcing REFER",
            fields.application_id,
            challenger_result.primary_band,
            challenger_result.challenger_band,
        )
        # Don't set flag_fairness_fail here — keep it as a separate signal
        # The band in score_breakdown stays; REFER is enforced at recommend time
        state["status"] = state.get("status", "ok")  # preserve existing status

    _trace(state, "CHALLENGER", {
        "primary_band":     challenger_result.primary_band,
        "challenger_band":  challenger_result.challenger_band,
        "bands_agree":      challenger_result.bands_agree,
        "delta":            challenger_result.delta,
    })
    return state


def node_fairness_recheck(state: AgentState) -> AgentState:
    """
    Calls run_fairness_recheck from the standalone fairness_recheck module.
    Sets status to "flag_fairness_fail" on mismatch so the conditional
    edge can route to FLAG_FAIRNESS_FAIL node.
    """
    fields: ApplicationFields = state["fields"]
    breakdown: ScoreBreakdown = state["score_breakdown"]
    log.info("node=FAIRNESS_RECHECK app=%s", fields.application_id)

    fairness = run_fairness_recheck(fields, breakdown)
    state["fairness_check"] = fairness

    if not fairness.match:
        state["status"] = "flag_fairness_fail"

    _trace(state, "FAIRNESS_RECHECK", {
        "original_band": fairness.original_band,
        "masked_band": fairness.masked_band,
        "match": fairness.match,
    })
    return state


def node_flag_fairness_fail(state: AgentState) -> AgentState:
    """
    Entered when the fairness re-score produced a different band.
    Forces the recommendation to 'refer' and marks the record so the
    underwriter sees a hard-stop warning.  No auto-anything happens here —
    the application still waits at HUMAN_GATE.
    """
    fields: ApplicationFields = state["fields"]
    fairness: FairnessCheck = state["fairness_check"]
    log.error(
        "node=FLAG_FAIRNESS_FAIL app=%s — forced REFER, original=%s masked=%s",
        fields.application_id,
        fairness.original_band,
        fairness.masked_band,
    )
    # Override recommendation to refer; rationale explains the flag
    state["agent_recommendation"] = "refer"
    state["rationale"] = (
        f"FAIRNESS FLAG: identity-masked re-score produced band '{fairness.masked_band}' "
        f"vs original '{fairness.original_band}'. Application forced to REFER for mandatory "
        "human review. Do not approve without investigating the disparity."
    )
    state["status"] = "flag_fairness_fail"
    _trace(state, "FLAG_FAIRNESS_FAIL", {
        "original_band": fairness.original_band,
        "masked_band": fairness.masked_band,
    })
    return state


def node_recommend(state: AgentState) -> AgentState:
    fields: ApplicationFields = state.get("fields")
    breakdown: ScoreBreakdown = state.get("score_breakdown")
    fairness: FairnessCheck = state.get("fairness_check")

    if fields is None or breakdown is None or fairness is None:
        log.error(
            "node=RECOMMEND missing required state keys — fields=%s breakdown=%s fairness=%s",
            fields is not None, breakdown is not None, fairness is not None,
        )
        state["status"] = "error"
        state["error_message"] = "RECOMMEND node reached with incomplete state (missing fields/breakdown/fairness)"
        return state

    log.info("node=RECOMMEND app=%s", fields.application_id)
    recommendation, rationale = run_recommend(breakdown, fairness, fields.application_id)

    # Challenger disagreement (>1 band) forces REFER regardless of primary
    cr = state.get("challenger_result")
    if cr is not None and not cr.bands_agree and recommendation != "refer":
        log.warning(
            "app=%s challenger_disagree forcing recommendation from %s → refer",
            fields.application_id, recommendation,
        )
        recommendation = "refer"
        rationale = (
            f"CHALLENGER FLAG: Primary model suggested '{breakdown.band}' but the "
            f"challenger model suggested '{cr.challenger_band}' — disagreement exceeds "
            "1 band. Recommendation forced to REFER for mandatory human review.\n\n"
            + rationale
        )

    state["agent_recommendation"] = recommendation
    state["rationale"] = rationale
    _trace(state, "RECOMMEND", {"recommendation": recommendation})
    return state


def node_draft_notice(state: AgentState) -> AgentState:
    """
    Generate an adverse-action notice draft for DECLINE recommendations.
    Only runs when agent_recommendation == "decline".
    Uses agent_recommendation (not breakdown.band) as the single source of
    truth — these can differ when challenger or fairness overrides the band.
    The draft is stored in the state and later written to DecisionRecord.adverse_action_draft.
    """
    recommendation = state.get("agent_recommendation", "")
    if recommendation != "decline":
        _trace(state, "DRAFT_NOTICE", {"skipped": True, "reason": f"recommendation={recommendation}"})
        return state

    fields: ApplicationFields = state.get("fields")
    breakdown: ScoreBreakdown = state.get("score_breakdown")

    if fields is None or breakdown is None:
        log.error("node=DRAFT_NOTICE missing fields or breakdown — skipping notice generation")
        _trace(state, "DRAFT_NOTICE", {"skipped": True, "reason": "missing state keys"})
        return state

    log.info("node=DRAFT_NOTICE app=%s generating adverse-action draft", fields.application_id)
    draft = run_draft_notice(breakdown, fields.application_id, recommendation)
    state["adverse_action_draft"] = draft
    _trace(state, "DRAFT_NOTICE", {"draft_length": len(draft)})
    return state


def node_human_gate(state: AgentState) -> AgentState:
    """
    Terminal node — all paths converge here.
    Sets status = "pending_human_review"; human_decision stays None
    until the underwriter POSTs to /decision.
    """
    raw: ApplicationRaw = state["raw"]
    log.info("node=HUMAN_GATE app=%s — awaiting underwriter", raw.application_id)
    state["status"] = "pending_human_review"
    _trace(state, "HUMAN_GATE", {"status": "pending_human_review"})
    return state


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------

def route_after_verify(state: AgentState) -> Literal["extract", "hold"]:
    return "extract" if state.get("status") == "ok" else "hold"


def route_after_extract(state: AgentState) -> Literal["score", "human_gate"]:
    return "human_gate" if state.get("status") == "error" else "score"


def route_after_fairness(state: AgentState) -> Literal["recommend", "flag_fairness_fail"]:
    """Mismatch → FLAG_FAIRNESS_FAIL; match → RECOMMEND."""
    return "flag_fairness_fail" if state.get("status") == "flag_fairness_fail" else "recommend"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph() -> Any:
    graph = StateGraph(AgentState)

    graph.add_node("verify", node_verify)
    graph.add_node("hold", node_hold)
    graph.add_node("extract", node_extract)
    graph.add_node("score", node_score)
    graph.add_node("challenger", node_challenger)
    graph.add_node("fairness_recheck", node_fairness_recheck)
    graph.add_node("flag_fairness_fail", node_flag_fairness_fail)
    graph.add_node("recommend", node_recommend)
    graph.add_node("draft_notice", node_draft_notice)
    graph.add_node("human_gate", node_human_gate)

    graph.set_entry_point("verify")

    graph.add_conditional_edges(
        "verify",
        route_after_verify,
        {"extract": "extract", "hold": "hold"},
    )
    graph.add_edge("hold", END)

    graph.add_conditional_edges(
        "extract",
        route_after_extract,
        {"score": "score", "human_gate": "human_gate"},
    )
    # SCORE → CHALLENGER → FAIRNESS_RECHECK
    graph.add_edge("score", "challenger")
    graph.add_edge("challenger", "fairness_recheck")

    # KEY conditional edge: mismatch → flag_fairness_fail, match → recommend
    graph.add_conditional_edges(
        "fairness_recheck",
        route_after_fairness,
        {"recommend": "recommend", "flag_fairness_fail": "flag_fairness_fail"},
    )

    # Both fairness paths converge at human_gate (via draft_notice)
    graph.add_edge("flag_fairness_fail", "draft_notice")
    graph.add_edge("recommend", "draft_notice")
    graph.add_edge("draft_notice", "human_gate")
    graph.add_edge("human_gate", END)

    return graph.compile()


# Singleton compiled graph
_compiled_graph: Any = None


def get_graph() -> Any:
    global _compiled_graph  # noqa: PLW0603
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


# ---------------------------------------------------------------------------
# High-level pipeline runner
# ---------------------------------------------------------------------------

def run_pipeline(raw: ApplicationRaw) -> "DecisionRecord | dict":
    """
    Run the full pipeline for one ApplicationRaw.

    Returns DecisionRecord (human_decision=None, pending gate) on success,
    or a dict with status/message for hold and error states.
    """
    graph = get_graph()

    initial_state: AgentState = {
        "raw": raw,
        "status": "ok",
        "error_message": None,
        "pipeline_trace": [],
    }

    final_state: AgentState = graph.invoke(initial_state)
    status = final_state.get("status")

    if status == "hold_for_document":
        return {
            "status": "hold_for_document",
            "application_id": raw.application_id,
            "submitted_at": raw.submitted_at.isoformat(),
            "missing_docs": final_state["verify_result"].missing_docs,
            "consistency_flags": final_state["verify_result"].consistency_flags,
            "pipeline_trace": final_state.get("pipeline_trace", []),
        }

    if status == "error":
        return {
            "status": "error",
            "application_id": raw.application_id,
            "submitted_at": raw.submitted_at.isoformat(),
            "message": final_state.get("error_message", "Unknown error"),
            "pipeline_trace": final_state.get("pipeline_trace", []),
        }

    # Both "pending_human_review" and "flag_fairness_fail" end up here
    # (flag_fairness_fail also sets agent_recommendation="refer" before human_gate)
    verify_result = final_state.get("verify_result")
    record = DecisionRecord(
        application_id=raw.application_id,
        policy_version=final_state["score_breakdown"].policy_version,
        # Applicant details — captured at intake, surfaced to reviewers
        applicant_name=raw.applicant_name,
        applicant_address=raw.applicant_address,
        loan_amount_requested=raw.loan_amount_requested,
        applicant_notes=raw.applicant_notes,
        score_breakdown=final_state["score_breakdown"],
        fairness_check=final_state["fairness_check"],
        challenger_result=final_state.get("challenger_result"),
        agent_recommendation=final_state["agent_recommendation"],
        rationale=final_state["rationale"],
        adverse_action_draft=final_state.get("adverse_action_draft") or None,
        human_decision=None,
        human_reviewer=None,
        override_reason=None,
        decided_at=None,
        created_at=datetime.now(timezone.utc),
        pipeline_trace=final_state.get("pipeline_trace", []),
        missing_docs=verify_result.missing_docs if verify_result else [],
        consistency_flags=verify_result.consistency_flags if verify_result else [],
    )
    return record


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _trace(state: AgentState, node: str, data: dict) -> None:
    if "pipeline_trace" not in state:
        state["pipeline_trace"] = []
    state["pipeline_trace"].append({
        "node": node,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **data,
    })
