"""Decision record and amendment models — the append-only audit store contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.scoring import ScoreBreakdown
from app.models.fairness import FairnessCheck, ChallengerResult


class DecisionRecord(BaseModel):
    """
    The full, immutable record of a decisioning run.

    Written once when the agent completes its pipeline and the application
    enters HUMAN_GATE state.  Human decisions (approve/override/etc.) are
    recorded in the same row via the human_decision / override_reason fields
    once the underwriter acts.

    Records are append-only: corrections are made via DecisionAmendment
    linked to this record — the original row is never mutated.
    """

    application_id: str
    policy_version: str

    # Agent pipeline outputs
    score_breakdown: ScoreBreakdown
    fairness_check: FairnessCheck
    challenger_result: ChallengerResult | None = None
    agent_recommendation: Literal["approve", "refer", "decline"]
    rationale: str = Field(..., description="Plain-English rationale composed by the LLM from ScoreBreakdown")
    adverse_action_draft: str | None = Field(
        None,
        description="LLM-drafted adverse-action notice, held for human edit. Only set on DECLINE.",
    )

    # Human gate — these fields start None and are filled by the underwriter
    human_decision: Literal["approve", "refer", "decline"] | None = None
    human_reviewer: str | None = None
    override_reason: str | None = Field(
        None,
        description=(
            "Required (non-empty) if human_decision differs from agent_recommendation. "
            "Stored alongside original recommendation — never silently overwrites it."
        ),
    )
    decided_at: datetime | None = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    immutable: bool = Field(
        True,
        description="Enforced at the storage layer.  This field is a documentary marker.",
    )

    # Full node-by-node pipeline trace for audit trail
    pipeline_trace: list[dict] = Field(
        default_factory=list,
        description="Ordered list of trace entries, one per graph node execution.",
    )

    # Hold / verification state — populated for non-DecisionRecord paths but
    # included here for convenience on the detail endpoint
    missing_docs: list[str] = Field(default_factory=list)
    consistency_flags: list[str] = Field(default_factory=list)


class DecisionAmendment(BaseModel):
    """
    A post-hoc correction linked to an existing DecisionRecord.
    The original record is never modified; amendments are a new linked row.
    """

    amendment_id: str
    original_application_id: str
    amended_by: str
    amendment_reason: str
    amended_at: datetime = Field(default_factory=datetime.utcnow)
    field_changes: dict = Field(
        default_factory=dict,
        description="Key/value pairs of what changed and what the corrected values are",
    )
