"""
SCORE node — pure-Python deterministic policy scoring engine.

HARD CONSTRAINT: This file must NEVER import or call any LLM.
The scoring arithmetic is deterministic: same inputs always produce the
same output, making it unit-testable and audit-reproducible.

The LLM is used in the RECOMMEND node only — to compose a plain-English
explanation FROM this already-computed ScoreBreakdown.

Policy is loaded from the YAML file referenced by POLICY_PATH in env
(default: ./policy/policy_v1.yaml).
"""

import logging
import os
from functools import lru_cache
from typing import Any

import yaml

from app.models.application import ApplicationFields, IdentityBlock
from app.models.scoring import ClauseCitation, ScoreBreakdown

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Policy loading (cached per process)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=4)
def _load_policy(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        policy = yaml.safe_load(fh)
    log.info("Loaded policy version=%s from %s", policy.get("version"), path)
    return policy


def get_policy() -> dict[str, Any]:
    path = os.environ.get("POLICY_PATH", "./policy/policy_v1.yaml")
    return _load_policy(path)


# ---------------------------------------------------------------------------
# Sub-scorers — each returns a float in [0.0, 1.0]
# ---------------------------------------------------------------------------

def _score_dti(dti_ratio: float, cfg: dict) -> tuple[float, list[str]]:
    """
    DTI sub-score and applicable clause IDs.

    cfg keys: excellent_max, acceptable_max, poor_max
    """
    excellent = cfg.get("excellent_max", 0.30)
    acceptable = cfg.get("acceptable_max", 0.43)
    poor_max = cfg.get("poor_max", 0.55)
    clauses: list[str] = []

    if dti_ratio <= excellent:
        score = 1.0
        clauses.append("DTI-02")
    elif dti_ratio <= acceptable:
        # Linear interpolation from 1.0 (at excellent) down to 0.5 (at acceptable)
        t = (dti_ratio - excellent) / (acceptable - excellent)
        score = 1.0 - 0.5 * t
        clauses.append("DTI-01")
    elif dti_ratio <= poor_max:
        # Linear interpolation from 0.5 down to 0.0
        t = (dti_ratio - acceptable) / (poor_max - acceptable)
        score = 0.5 - 0.5 * t
        clauses.append("DTI-01")
    else:
        score = 0.0
        clauses.append("DTI-01")

    return round(score, 6), clauses


def _score_credit_history(
    years: float,
    flags: list[str],
    cfg: dict,
) -> tuple[float, list[str]]:
    """
    Credit history sub-score and applicable clause IDs.

    cfg keys: min_years_full_credit, min_years_any_credit,
              late_payment_12m_penalty, default_penalty
    """
    min_any = cfg.get("min_years_any_credit", 2.0)
    min_full = cfg.get("min_years_full_credit", 5.0)
    late_penalty = cfg.get("late_payment_12m_penalty", 0.30)
    default_penalty = cfg.get("default_penalty", 0.50)
    clauses: list[str] = []

    if years < min_any:
        # CH-01: less than minimum — hard zero
        clauses.append("CH-01")
        return 0.0, clauses

    clauses.append("CH-01")

    # Base score from history length: interpolate between min_any and min_full
    if years >= min_full:
        base = 1.0
    else:
        t = (years - min_any) / (min_full - min_any)
        base = t  # 0.0–1.0

    # Apply penalties
    deductions = 0.0
    if "late_payment_12m" in flags:
        deductions += late_penalty
        clauses.append("CH-02")
    elif "late_payment_36m" in flags:
        deductions += late_penalty * 0.5  # smaller penalty for older event
        clauses.append("CH-02")

    if "default_36m" in flags or "default_older" in flags:
        deductions += default_penalty
        clauses.append("CH-03")

    score = max(0.0, base - deductions)
    return round(score, 6), clauses


def _score_income_stability(months: int, cfg: dict) -> tuple[float, list[str]]:
    """
    Income stability sub-score and applicable clause IDs.

    cfg keys: min_months_any_credit, min_months_full_credit
    """
    min_any = cfg.get("min_months_any_credit", 6)
    min_full = cfg.get("min_months_full_credit", 24)
    clauses: list[str] = []

    if months < min_any:
        clauses.append("INC-01")
        return 0.0, clauses

    clauses.append("INC-01")

    if months >= min_full:
        clauses.append("INC-02")
        return 1.0, clauses

    # Linear interpolation
    t = (months - min_any) / (min_full - min_any)
    score = round(t, 6)
    return score, clauses


# ---------------------------------------------------------------------------
# Public scoring function
# ---------------------------------------------------------------------------

def run_score(fields: ApplicationFields) -> ScoreBreakdown:
    """
    Compute the full ScoreBreakdown for ApplicationFields.

    This function:
    - Uses ONLY the financial/credit fields from ApplicationFields
    - Does NOT read identity (name/address) — by design
    - Loads policy weights and thresholds from YAML
    - Performs all arithmetic in pure Python
    - Returns a fully populated ScoreBreakdown ready for the RECOMMEND node

    The LLM never calls this function or modifies its output.
    """
    policy = get_policy()
    version = policy["version"]
    weights = policy["weights"]  # {dti, credit_history, income_stability}
    bands = policy["bands"]
    dti_cfg = policy.get("dti_scoring", {})
    ch_cfg = policy.get("credit_history_scoring", {})
    inc_cfg = policy.get("income_stability_scoring", {})
    clause_defs = policy.get("clauses", {})

    # Compute DTI ratio from extracted fields
    dti_ratio = fields.debt_monthly / max(fields.income_monthly, 1)

    # Sub-scores
    dti_sub, dti_clause_ids = _score_dti(dti_ratio, dti_cfg)
    ch_sub, ch_clause_ids = _score_credit_history(
        fields.credit_history_years,
        fields.credit_history_flags,
        ch_cfg,
    )
    inc_sub, inc_clause_ids = _score_income_stability(
        fields.employment_months_current,
        inc_cfg,
    )

    # Weighted composite
    w_dti = weights.get("dti", 0.40)
    w_ch = weights.get("credit_history", 0.35)
    w_inc = weights.get("income_stability", 0.25)

    composite = round(
        dti_sub * w_dti + ch_sub * w_ch + inc_sub * w_inc,
        6,
    )

    # Band assignment
    approve_min = bands.get("approve_min", 0.75)
    refer_min = bands.get("refer_min", 0.65)

    if composite >= approve_min:
        band = "approve"
    elif composite >= refer_min:
        band = "refer"
    else:
        band = "decline"

    # Build clause citation objects for every clause that was triggered
    all_clause_ids: list[str] = list(dict.fromkeys(dti_clause_ids + ch_clause_ids + inc_clause_ids))
    citations: list[ClauseCitation] = []
    for cid in all_clause_ids:
        clause_data = clause_defs.get(cid)
        if clause_data:
            citations.append(
                ClauseCitation(
                    clause_id=cid,
                    clause_text=clause_data["text"].strip(),
                    factor=clause_data["factor"],
                )
            )
        else:
            log.warning("score: clause_id=%s not found in policy YAML", cid)

    log.info(
        "app=%s scored version=%s dti_ratio=%.3f composite=%.4f band=%s",
        fields.application_id,
        version,
        dti_ratio,
        composite,
        band,
    )

    return ScoreBreakdown(
        policy_version=version,
        dti_ratio=round(dti_ratio, 6),
        dti_subscore=dti_sub,
        credit_history_subscore=ch_sub,
        income_stability_subscore=inc_sub,
        weights={"dti": w_dti, "credit_history": w_ch, "income_stability": w_inc},
        composite_score=composite,
        band=band,
        clause_citations=citations,
    )


# ---------------------------------------------------------------------------
# Fairness helper — structural identity-blind copy
# ---------------------------------------------------------------------------

def identity_blind_copy(fields: ApplicationFields) -> ApplicationFields:
    """
    Return a deep copy of ApplicationFields with identity fields masked.

    The scorer only ever receives ApplicationFields; it has no path through
    which identity can influence the score.  Masking and re-running score()
    is therefore a true structural test — not a prompt instruction to "ignore".
    """
    masked = fields.model_copy(deep=True)
    masked.identity = IdentityBlock(name="[REDACTED]", address="[REDACTED]")
    return masked
