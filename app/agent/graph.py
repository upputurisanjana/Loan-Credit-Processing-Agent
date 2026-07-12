"""
LangGraph decisioning agent — wires all Phase 1 nodes into a single pipeline.

Pipeline:
    INTAKE → VERIFY → (hold | EXTRACT → SCORE → FAIRNESS_RECHECK → RECOMMEND → HUMAN_GATE)

Each state transition is explicit.  The graph terminates at HUMAN_GATE with
status "pending_human_review" — no decision is ever auto-finalised.

Usage
-----
    from app.agent.graph import build_graph, run_pipeline

    record = run_pipeline(raw_application)
    # record.human_decision is None until an underwriter acts
"""

import logging
from datetime import datetime
from typing import Any, Literal, TypedDict

from langgraph.graph import StateGraph, END

from app.models.application import ApplicationRaw, ApplicationFields
from app.models.verification import VerifyResult
from app.models.scoring import ScoreBreakdown
from app.models.fairness import FairnessCheck
from app.models.decision import DecisionRecord
from app.agent.nodes.verify import run_verify
from app.agent.nodes.extract import run_extract
from app.agent.nodes.score import run_score, identity_blind_copy
from app.agent.nodes.recommend import run_recommend

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared agent state — passed between every node
# ---------------------------------------------------------------------------

class AgentState(TypedDict, total=False):
    # Inputs
    raw: ApplicationRaw

    # Node outputs
    verify_result: VerifyResult
    fields: ApplicationFields
    score_breakdown: ScoreBreakdown
    fairness_check: FairnessCheck
    agent_recommendation: str
    rationale: str

    # Control / metadata
    status: str          # "ok" | "hold_for_document" | "pending_human_review" | "error"
    error_message: str | None
    pipeline_trace: list[dict]   # one entry per node for the audit log


# ---------------------------------------------------------------------------
# Node wrappers — each receives and returns AgentState
# ---------------------------------------------------------------------------

def node_verify(state: AgentState) -> AgentState:
    raw: ApplicationRaw = state["raw"]
    log.info("node=VERIFY app=%s", raw.application_id)
    _trace(state, "VERIFY", {"app_id": raw.application_id})

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


def node_fairness_recheck(state: AgentState) -> AgentState:
    fields: ApplicationFields = state["fields"]
    breakdown: ScoreBreakdown = state["score_breakdown"]
    log.info("node=FAIRNESS_RECHECK app=%s", fields.application_id)

    masked = identity_blind_copy(fields)
    masked_breakdown = run_score(masked)

    match = (
        breakdown.band == masked_breakdown.band
        and abs(breakdown.composite_score - masked_breakdown.composite_score) < 1e-9
    )

    fairness = FairnessCheck(
        original_band=breakdown.band,
        masked_band=masked_breakdown.band,
        original_composite=breakdown.composite_score,
        masked_composite=masked_breakdown.composite_score,
        match=match,
    )
    state["fairness_check"] = fairness

    if not match:
        log.error(
            "node=FAIRNESS_RECHECK app=%s MISMATCH original_band=%s masked_band=%s",
            fields.application_id,
            breakdown.band,
            masked_breakdown.band,
        )

    _trace(state, "FAIRNESS_RECHECK", {
        "original_band": fairness.original_band,
        "masked_band": fairness.masked_band,
        "match": fairness.match,
    })
    return state


def node_recommend(state: AgentState) -> AgentState:
    fields: ApplicationFields = state["fields"]
    breakdown: ScoreBreakdown = state["score_breakdown"]
    fairness: FairnessCheck = state["fairness_check"]
    log.info("node=RECOMMEND app=%s", fields.application_id)

    recommendation, rationale = run_recommend(breakdown, fairness, fields.application_id)
    state["agent_recommendation"] = recommendation
    state["rationale"] = rationale
    _trace(state, "RECOMMEND", {"recommendation": recommendation})
    return state


def node_human_gate(state: AgentState) -> AgentState:
    """
    Terminal node — application waits here for an underwriter action.

    This node sets status = "pending_human_review" and does NOT finalise
    the decision.  The DecisionRecord is assembled here but human_decision
    remains None until the underwriter calls the /decision endpoint.
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
    if state.get("status") == "ok":
        return "extract"
    return "hold"


def route_after_extract(state: AgentState) -> Literal["score", "human_gate"]:
    if state.get("status") == "error":
        return "human_gate"
    return "score"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph() -> Any:
    """Build and compile the LangGraph state machine."""
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("verify", node_verify)
    graph.add_node("hold", node_hold)
    graph.add_node("extract", node_extract)
    graph.add_node("score", node_score)
    graph.add_node("fairness_recheck", node_fairness_recheck)
    graph.add_node("recommend", node_recommend)
    graph.add_node("human_gate", node_human_gate)

    # Entry point
    graph.set_entry_point("verify")

    # Edges
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
    graph.add_edge("score", "fairness_recheck")
    graph.add_edge("fairness_recheck", "recommend")
    graph.add_edge("recommend", "human_gate")
    graph.add_edge("human_gate", END)

    return graph.compile()


# Singleton compiled graph — importable by routers
_compiled_graph: Any = None


def get_graph() -> Any:
    global _compiled_graph  # noqa: PLW0603
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


# ---------------------------------------------------------------------------
# High-level pipeline runner
# ---------------------------------------------------------------------------

def run_pipeline(raw: ApplicationRaw) -> DecisionRecord | dict:
    """
    Run the full agent pipeline for one ApplicationRaw.

    Returns a DecisionRecord with human_decision=None (pending gate) on
    success, or a dict with 'status' and 'message' for hold/error states.
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
            "missing_docs": final_state["verify_result"].missing_docs,
            "consistency_flags": final_state["verify_result"].consistency_flags,
        }

    if status == "error":
        return {
            "status": "error",
            "application_id": raw.application_id,
            "message": final_state.get("error_message", "Unknown error"),
        }

    # Build the DecisionRecord (human fields start None — pending gate)
    record = DecisionRecord(
        application_id=raw.application_id,
        policy_version=final_state["score_breakdown"].policy_version,
        score_breakdown=final_state["score_breakdown"],
        fairness_check=final_state["fairness_check"],
        challenger_result=None,  # Phase 2
        agent_recommendation=final_state["agent_recommendation"],
        rationale=final_state["rationale"],
        adverse_action_draft=None,  # Phase 2
        human_decision=None,
        human_reviewer=None,
        override_reason=None,
        decided_at=None,
        created_at=datetime.utcnow(),
    )
    return record


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _trace(state: AgentState, node: str, data: dict) -> None:
    """Append a trace entry to pipeline_trace for the audit log."""
    if "pipeline_trace" not in state:
        state["pipeline_trace"] = []
    state["pipeline_trace"].append({
        "node": node,
        "timestamp": datetime.utcnow().isoformat(),
        **data,
    })
