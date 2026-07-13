"""Fairness check and challenger model result models."""

from pydantic import BaseModel, Field


class FairnessCheck(BaseModel):
    """
    Result of the identity-blind re-score.

    The fairness recheck runs the same deterministic scorer against a copy
    of ApplicationFields where IdentityBlock is masked to '[REDACTED]'.
    Because the scorer never uses identity fields in its arithmetic, the
    two runs should always match — any mismatch indicates a regression
    (e.g. identity data accidentally wired into a future scoring feature).
    """

    original_band: str
    masked_band: str
    original_composite: float
    masked_composite: float
    match: bool = Field(
        ...,
        description=(
            "True if both bands are identical. "
            "False triggers FLAG_FAIRNESS_FAIL and forces human review."
        ),
    )


class ChallengerResult(BaseModel):
    """
    Comparison between the primary model's rationale and the challenger
    model's independent read of the application.

    Note: the *band assignment* still comes from the deterministic policy
    engine for both roles.  The 'challenger' checks whether an independent
    LLM's policy read would suggest a materially different band — if so,
    that's a signal worth flagging to the underwriter, not an automatic
    override.
    """

    primary_band: str
    challenger_band: str
    bands_agree: bool
    delta: float = Field(
        ...,
        description=(
            "Integer band distance between primary and challenger bands: "
            "0 = same band, 1 = one tier apart (approve↔refer or refer↔decline), "
            "2 = two tiers apart (approve↔decline). Stored as float for model compatibility."
        ),
    )
