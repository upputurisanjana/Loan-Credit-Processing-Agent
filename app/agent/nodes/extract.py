"""
EXTRACT node — LLM-assisted structured field extraction.

Inputs (from AgentState):
    raw: ApplicationRaw

Outputs (mutates AgentState):
    fields: ApplicationFields

The LLM parses OCR'd / form-submitted text and returns a structured JSON
object.  All content from applicant documents is wrapped in <applicant_data>
tags and treated as UNTRUSTED INPUT — the system prompt explicitly instructs
the model not to follow any embedded instructions (prompt-injection defence).

After extraction the result is Pydantic-validated; any field the LLM cannot
reliably extract comes back as None and is handled by falling back to the
stated values from ApplicationRaw.
"""

import json
import logging

from app.models.application import ApplicationFields, ApplicationRaw, IdentityBlock
from app.agent.prompts.extract_prompt import build_extract_prompt
from app.tools.github_models_client import call_model, get_primary_model

log = logging.getLogger(__name__)


def run_extract(raw: ApplicationRaw) -> ApplicationFields:
    """
    Call the primary LLM to extract structured fields from ApplicationRaw.

    Falls back to ApplicationRaw.stated_* values if the LLM cannot extract
    a field or returns an invalid/null value — so the pipeline never halts
    due to a partial extraction.
    """
    # Collect available document texts
    doc_texts = [
        doc.extracted_text
        for doc in raw.documents
        if doc.extracted_text
    ]

    raw_json = raw.model_dump_json(indent=2)
    messages = build_extract_prompt(raw_json, doc_texts)

    log.info("app=%s running extract via LLM", raw.application_id)

    raw_response = call_model(
        model=get_primary_model(),
        messages=messages,
        temperature=0.0,
        max_tokens=512,
    )

    extracted = _parse_llm_response(raw_response, raw)

    log.info(
        "app=%s extract complete income_monthly=%.2f debt_monthly=%.2f",
        raw.application_id,
        extracted.income_monthly,
        extracted.debt_monthly,
    )
    return extracted


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_llm_response(response: str, raw: ApplicationRaw) -> ApplicationFields:
    """
    Parse the LLM's JSON response into ApplicationFields, falling back to
    stated values from ApplicationRaw for any missing or invalid field.
    """
    data: dict = {}
    try:
        # Strip any accidental markdown fences the model may have added
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            # Remove first and last fence lines
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as exc:
        log.warning("app=%s LLM extraction JSON parse failed (%s); using stated values", raw.application_id, exc)

    def _float(key: str, fallback: float) -> float:
        val = data.get(key)
        try:
            return float(val) if val is not None else fallback
        except (TypeError, ValueError):
            return fallback

    def _int(key: str, fallback: int) -> int:
        val = data.get(key)
        try:
            return int(val) if val is not None else fallback
        except (TypeError, ValueError):
            return fallback

    # credit_history_flags — validate against closed list
    _VALID_FLAGS = {
        "late_payment_12m",
        "late_payment_36m",
        "default_36m",
        "default_older",
        "no_history",
    }
    raw_flags = data.get("credit_history_flags", [])
    if not isinstance(raw_flags, list):
        raw_flags = []
    flags = [f for f in raw_flags if isinstance(f, str) and f in _VALID_FLAGS]

    return ApplicationFields(
        application_id=raw.application_id,
        identity=IdentityBlock(
            name=raw.applicant_name,
            address=raw.applicant_address,
        ),
        income_monthly=_float("income_monthly", raw.stated_income),
        debt_monthly=_float("debt_monthly", raw.stated_monthly_debt),
        credit_history_years=_float("credit_history_years", 0.0),
        credit_history_flags=flags,
        employment_months_current=_int("employment_months_current", 0),
    )
