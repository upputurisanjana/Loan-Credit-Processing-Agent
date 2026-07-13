"""
CHALLENGER node — second independent LLM call using the CHALLENGER_MODEL.

Per ARCHITECTURE.md §6 and UI_UX_DESIGN.md §3.4:
- The challenger does NOT recompute or replace the band from the
  deterministic scorer.
- It independently reads the policy and the application fields and states
  which band it would recommend.
- If its suggested band differs from the primary band by more than 1 tier
  (approve/refer/decline), that forces a REFER regardless of primary result.
- "More than 1 band" here means primary=approve + challenger=decline (or
  vice versa). Primary=approve + challenger=refer, or primary=refer +
  challenger=decline, count as a 1-band difference and do NOT force REFER.

Inputs:  ApplicationFields, ScoreBreakdown (for context)
Outputs: ChallengerResult
"""

import logging

from app.models.application import ApplicationFields
from app.models.fairness import ChallengerResult
from app.models.scoring import ScoreBreakdown
from app.tools.github_models_client import call_model, get_challenger_model

log = logging.getLogger(__name__)

# Band ordering — used to compute integer distance between bands
_BAND_ORDER: dict[str, int] = {"decline": 0, "refer": 1, "approve": 2}

_SYSTEM_PROMPT = """\
You are an independent credit policy analyst performing a second-opinion review.
You will be given an applicant's financial data and a score summary computed by a
deterministic policy engine.

Your task is ONLY to state which band you believe the application falls into:
  approve  — strong application, meets all key criteria
  refer    — borderline or incomplete, warrants manual review
  decline  — clear policy violations, does not meet minimum thresholds

Rules you must follow:
1. Reply with exactly ONE word: approve, refer, or decline. No other text.
2. Use the provided score summary as context, but apply your own independent
   read of the applicant's financial health.
3. Do NOT explain your reasoning. One word only.
"""

def _build_messages(fields: ApplicationFields, breakdown: ScoreBreakdown) -> list[dict]:
    applicant_summary = (
        f"Monthly income: {fields.income_monthly}\n"
        f"Monthly debt payments: {fields.debt_monthly}\n"
        f"DTI ratio: {breakdown.dti_ratio:.3f} ({breakdown.dti_ratio * 100:.1f}%)\n"
        f"Credit history: {fields.credit_history_years} years\n"
        f"Credit history flags: {', '.join(fields.credit_history_flags) or 'none'}\n"
        f"Employment tenure: {fields.employment_months_current} months at current employer\n"
        f"\nPrimary model summary:\n"
        f"  Composite score: {breakdown.composite_score:.3f} (band: {breakdown.band})\n"
        f"  DTI sub-score: {breakdown.dti_subscore:.3f}\n"
        f"  Credit history sub-score: {breakdown.credit_history_subscore:.3f}\n"
        f"  Income stability sub-score: {breakdown.income_stability_subscore:.3f}\n"
    )
    return [
        {"role": "system",  "content": _SYSTEM_PROMPT},
        {"role": "user",    "content": f"Applicant data:\n{applicant_summary}\nYour band assessment (one word):"},
    ]


def _parse_band(raw: str) -> str:
    """Parse the LLM's single-word response into a valid band."""
    cleaned = raw.strip().lower().split()[0] if raw.strip() else "refer"
    if cleaned in _BAND_ORDER:
        return cleaned
    # Fuzzy match for typos / decorated responses
    for band in ("approve", "refer", "decline"):
        if band in cleaned:
            return band
    log.warning("challenger returned unrecognised band %r — defaulting to refer", raw)
    return "refer"


def _bands_differ_by_more_than_one(band_a: str, band_b: str) -> bool:
    """True if the two bands are more than 1 tier apart (approve vs decline)."""
    return abs(_BAND_ORDER.get(band_a, 1) - _BAND_ORDER.get(band_b, 1)) > 1


def run_challenger_compare(
    fields: ApplicationFields,
    breakdown: ScoreBreakdown,
) -> ChallengerResult:
    """
    Run the challenger model and return a ChallengerResult.

    On any LLM failure the challenger defaults to agreeing with the primary
    (bands_agree=True, delta=0) so a single-model outage does not block all
    applications — but the failure is logged as a warning.
    """
    primary_band = breakdown.band

    try:
        messages = _build_messages(fields, breakdown)
        raw = call_model(
            model=get_challenger_model(),
            messages=messages,
            temperature=0.0,
            max_tokens=10,
        )
        challenger_band = _parse_band(raw)
        log.info(
            "app=%s challenger_band=%s primary_band=%s",
            fields.application_id,
            challenger_band,
            primary_band,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "app=%s challenger LLM call failed (%s) — treating as agree",
            fields.application_id,
            exc,
        )
        challenger_band = primary_band

    primary_val     = _BAND_ORDER.get(primary_band, 1)
    challenger_val  = _BAND_ORDER.get(challenger_band, 1)
    delta           = float(abs(primary_val - challenger_val))
    bands_agree     = not _bands_differ_by_more_than_one(primary_band, challenger_band)

    return ChallengerResult(
        primary_band=primary_band,
        challenger_band=challenger_band,
        bands_agree=bands_agree,
        delta=delta,
    )
