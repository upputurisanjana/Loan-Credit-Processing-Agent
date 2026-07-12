"""Scoring data models — output of the pure-Python policy engine."""

from typing import Literal

from pydantic import BaseModel, Field


class ClauseCitation(BaseModel):
    """
    A reference to a specific policy clause that contributed to the score.
    Every factor in the breakdown must cite the clause ID from policy_v1.yaml
    so the recommendation is traceable.
    """

    clause_id: str = Field(..., description="e.g. 'DTI-01', 'CH-01', 'INC-01'")
    clause_text: str = Field(..., description="Exact clause text from the policy YAML")
    factor: str = Field(..., description="Which sub-score this clause supports: dti | credit_history | income_stability")


class ScoreBreakdown(BaseModel):
    """
    The output of the deterministic policy scoring step.
    This object is computed entirely in pure Python — the LLM never
    writes or modifies these numeric fields.  The LLM only reads this
    object to compose a plain-English explanation for the underwriter.
    """

    policy_version: str = Field(..., description="Policy version active at time of scoring, e.g. 'v1.2'")

    # Raw inputs preserved for auditability
    dti_ratio: float = Field(..., description="Debt-to-income ratio as a decimal (0.43 = 43%)")

    # Sub-scores: each in [0.0, 1.0] where 1.0 is best
    dti_subscore: float = Field(..., ge=0.0, le=1.0)
    credit_history_subscore: float = Field(..., ge=0.0, le=1.0)
    income_stability_subscore: float = Field(..., ge=0.0, le=1.0)

    # Weights applied (snapshot from policy at scoring time)
    weights: dict[str, float] = Field(
        ..., description="e.g. {'dti': 0.4, 'credit_history': 0.35, 'income_stability': 0.25}"
    )

    # Final result
    composite_score: float = Field(..., ge=0.0, le=1.0)
    band: Literal["approve", "refer", "decline"]

    # Policy clauses that were triggered / applied
    clause_citations: list[ClauseCitation] = Field(default_factory=list)
