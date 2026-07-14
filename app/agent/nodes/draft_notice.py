"""
DRAFT_NOTICE node — LLM drafts an adverse-action notice for DECLINE cases.

Per spec / UI_UX_DESIGN.md §3.6:
- Only runs on DECLINE path (agent_recommendation == "decline" after human gate).
- The draft must reference the ACTUAL score factors from ScoreBreakdown —
  not generic boilerplate.
- Held for human edit / approval before any send.  No real send integration.
- The draft is stored in DecisionRecord.adverse_action_draft.
- Lender name and contact are injected from LENDER_NAME / LENDER_CONTACT
  environment variables (set in .env) so placeholders are filled automatically.

Called from graph.py AFTER human_gate when decision == "decline", or can be
called on-demand via the adverse-action endpoint.
"""

import logging
import os

from app.models.scoring import ScoreBreakdown
from app.tools.github_models_client import call_model, get_primary_model

log = logging.getLogger(__name__)

_SYSTEM_PROMPT_TEMPLATE = """\
You are a compliance officer drafting an adverse-action notice for a declined
credit application on behalf of {lender_name}.

The notice must:
1. Open with a formal salutation addressed to "Dear Applicant," and clearly
   state that the application has been declined by {lender_name}.
2. List the specific reasons for decline, each tied directly to a scoring
   factor (DTI, credit history, or income stability) from the provided
   ScoreBreakdown.  Reference the exact policy clause IDs (e.g. [DTI-01]).
3. State the applicant's right to request a free copy of their credit report
   and to dispute inaccurate information.
4. State the right to request a reconsideration with supporting documentation.
5. Close with the lender's contact details: {lender_contact}
6. Sign off with "Sincerely, {lender_name}"

Rules:
- Use the ACTUAL numeric values from the breakdown (DTI ratio, sub-scores,
  composite score). Do NOT invent or approximate numbers.
- Write in plain English suitable for a regulated consumer notice.
- Do NOT include any meta-commentary, markdown, or section headers beyond
  natural letter formatting.
- Length: 200–350 words.
"""


def _get_lender_details() -> tuple[str, str]:
    """Read lender name and contact from environment (set via config.py)."""
    name    = os.environ.get("LENDER_NAME", "Credit Decisioning Ltd")
    contact = os.environ.get("LENDER_CONTACT", "Please contact us for further information.")
    return name, contact


def _build_messages(breakdown: ScoreBreakdown) -> list[dict[str, str]]:
    """Build the message list for the adverse-action notice draft."""
    lender_name, lender_contact = _get_lender_details()

    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        lender_name=lender_name,
        lender_contact=lender_contact,
    )

    score_summary = (
        f"Policy version: {breakdown.policy_version}\n"
        f"Composite score: {breakdown.composite_score:.3f} (band: {breakdown.band})\n"
        f"DTI ratio: {breakdown.dti_ratio:.3f} ({breakdown.dti_ratio * 100:.1f}%) — "
        f"sub-score: {breakdown.dti_subscore:.3f}\n"
        f"Credit history sub-score: {breakdown.credit_history_subscore:.3f}\n"
        f"Income stability sub-score: {breakdown.income_stability_subscore:.3f}\n"
        f"\nPolicy clauses cited:\n"
    )
    for c in breakdown.clause_citations:
        score_summary += f"  [{c.clause_id}] ({c.factor}): {c.clause_text}\n"

    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                "Draft the adverse-action notice based on the following score breakdown.\n\n"
                f"<score_breakdown>\n{score_summary}\n</score_breakdown>"
            ),
        },
    ]


def _fallback_draft() -> str:
    """Return a fallback draft with real lender details when the LLM is unavailable."""
    lender_name, lender_contact = _get_lender_details()
    return f"""\
[DRAFT — LLM UNAVAILABLE — UNDERWRITER MUST COMPLETE THIS NOTICE BEFORE SENDING]

Dear Applicant,

We regret to inform you that your credit application has been declined by {lender_name}.

Reasons: Please refer to the Score Breakdown panel for the specific factors
that contributed to this decision, including your Debt-to-Income ratio,
credit history score, and income stability assessment.

You have the right to request a free copy of your credit report from the
reporting agency used in this decision. You may also request a reconsideration
by submitting updated financial documentation.

For questions, please contact us at: {lender_contact}

Sincerely,
{lender_name}
"""


def run_draft_notice(breakdown: ScoreBreakdown, application_id: str) -> str:
    """
    Generate an adverse-action notice draft for a DECLINE decision.

    Returns the draft text (may be a fallback if the LLM call fails).
    The returned text is NOT final — it must be reviewed and approved by
    the underwriter via NoticeEditor before any send.
    """
    if breakdown.band != "decline":
        log.warning(
            "app=%s draft_notice called for non-DECLINE band=%s — skipping",
            application_id,
            breakdown.band,
        )
        return ""

    log.info("app=%s requesting adverse-action notice draft", application_id)

    try:
        messages = _build_messages(breakdown)
        draft = call_model(
            model=get_primary_model(),
            messages=messages,
            temperature=0.1,
            max_tokens=600,
        )
        draft = draft.strip()
        if not draft:
            raise ValueError("empty LLM response")
        log.info("app=%s adverse-action draft generated (%d chars)", application_id, len(draft))
        return draft
    except Exception as exc:  # noqa: BLE001
        log.error("app=%s draft_notice LLM call failed: %s", application_id, exc)
        return _fallback_draft()
