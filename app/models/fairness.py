"""Fairness check and challenger model result models."""

from pydantic import BaseModel, Field


class FairnessCheck(BaseModel):
    """
    Result of both fairness checks:

    1. Structural (Python): re-runs the scorer with identity masked.
       Proves the *score* is not influenced by name/address.

    2. LLM language review: asks an LLM to scan the rationale text for
       any identity-proxy or bias language.
       Proves the *explanation* is also free from bias.

    Both must pass for the application to proceed normally.
    Either failure forces REFER and mandatory human review.
    """

    # ── Structural recheck ────────────────────────────────────────────
    original_band: str
    masked_band: str
    original_composite: float
    masked_composite: float
    match: bool = Field(
        ...,
        description=(
            "True if both bands and composite scores are identical. "
            "False triggers FLAG_FAIRNESS_FAIL and forces human review."
        ),
    )

    # ── LLM language review ───────────────────────────────────────────
    llm_review_flag: bool = Field(
        default=False,
        description=(
            "True if the LLM found potential identity-bias language "
            "in the rationale. Forces REFER when True."
        ),
    )
    llm_review_note: str = Field(
        default="",
        description="LLM's one-sentence explanation of its fairness finding.",
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
    bands_agree: bool = Field(
        ...,
        description=(
            "True when the band difference is within the acceptable tolerance "
            "(0 or 1 tier apart). False only when the gap is 2 tiers "
            "(approve vs decline), which forces a REFER. "
            "A 1-tier difference (approve vs refer, or refer vs decline) "
            "is flagged in the UI but does NOT force REFER."
        ),
    )
    delta: float = Field(
        ...,
        description=(
            "Integer band distance between primary and challenger bands: "
            "0 = same band, 1 = one tier apart (approve/refer or refer/decline), "
            "2 = two tiers apart (approve/decline). Stored as float for model compatibility."
        ),
    )
