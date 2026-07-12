"""
FAIRNESS_RECHECK node — structural identity-blind re-score.

Design guarantee (from ARCHITECTURE.md §4–5)
---------------------------------------------
The scorer (run_score) accepts ApplicationFields.  ApplicationFields holds
identity in an isolated IdentityBlock sub-object.  The scorer reads ONLY
the financial/credit fields — it never touches .identity.

This means:
  - Pass 1 (original):  run_score(fields)          — identity present but ignored
  - Pass 2 (masked):    run_score(identity_blind_copy(fields))  — identity replaced with [REDACTED]

Both passes call the **exact same** run_score function.  There is no separate
masked-pass code path.  The two results should be bit-for-bit identical
because identity was never a scoring input.

Any mismatch means a regression has introduced identity into a scoring path
and MUST block auto-anything — the application is forced to FLAG_FAIRNESS_FAIL
for mandatory human review.

Imports
-------
identity_blind_copy is intentionally kept in score.py (not here) so the
structural proof in test_fairness_structural.py can import it alongside
run_score and verify that both operate on ApplicationFields — never on
raw identity strings.
"""

import logging

from app.models.application import ApplicationFields
from app.models.scoring import ScoreBreakdown
from app.models.fairness import FairnessCheck
from app.agent.nodes.score import run_score, identity_blind_copy

log = logging.getLogger(__name__)


def run_fairness_recheck(
    fields: ApplicationFields,
    original_breakdown: ScoreBreakdown,
) -> FairnessCheck:
    """
    Re-run the scorer with identity masked and compare against the original.

    Parameters
    ----------
    fields:             The extracted ApplicationFields (identity still present).
    original_breakdown: The ScoreBreakdown already produced in the SCORE node.

    Returns
    -------
    FairnessCheck with match=True if bands and composite scores are identical,
    match=False otherwise (triggers FLAG_FAIRNESS_FAIL in the graph).
    """
    masked_fields = identity_blind_copy(fields)

    # Both passes use the same run_score — there is no alternative path.
    masked_breakdown = run_score(masked_fields)

    band_match = original_breakdown.band == masked_breakdown.band
    # Composite scores must be exactly equal (scorer is deterministic pure Python)
    composite_match = (
        abs(original_breakdown.composite_score - masked_breakdown.composite_score) < 1e-9
    )
    match = band_match and composite_match

    if not match:
        log.error(
            "FAIRNESS MISMATCH app=%s  "
            "original_band=%s masked_band=%s  "
            "original_composite=%.6f masked_composite=%.6f",
            fields.application_id,
            original_breakdown.band,
            masked_breakdown.band,
            original_breakdown.composite_score,
            masked_breakdown.composite_score,
        )
    else:
        log.info(
            "fairness_recheck app=%s MATCH band=%s composite=%.6f",
            fields.application_id,
            original_breakdown.band,
            original_breakdown.composite_score,
        )

    return FairnessCheck(
        original_band=original_breakdown.band,
        masked_band=masked_breakdown.band,
        original_composite=original_breakdown.composite_score,
        masked_composite=masked_breakdown.composite_score,
        match=match,
    )
