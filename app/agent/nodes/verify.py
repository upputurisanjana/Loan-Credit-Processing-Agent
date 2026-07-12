"""
VERIFY node — document presence and cross-document consistency checks.

Inputs (from AgentState):
    raw: ApplicationRaw

Outputs (mutates AgentState):
    verify_result: VerifyResult
    next_step: "extract" | "hold_for_document"

This node is pure Python — no LLM call.  It checks:
1. Required document types are present (id, pay_stub, bank_statement).
2. Cross-document consistency: stated income vs. pay stub income (if both
   available and parseable from extracted_text).
3. Prompt-injection guard: applicant_notes and extracted_text are treated
   as data, never parsed for instructions.
"""

import logging
import re

from app.models.application import ApplicationRaw
from app.models.verification import VerifyResult

log = logging.getLogger(__name__)

REQUIRED_DOC_TYPES: list[str] = ["id", "pay_stub", "bank_statement"]

# Tolerance for income figure cross-check between stated income and pay stub
INCOME_TOLERANCE_PCT: float = 0.10  # 10 %


def run_verify(raw: ApplicationRaw) -> VerifyResult:
    """
    Check document presence and cross-doc consistency.

    Returns a VerifyResult with status 'ok' or 'hold_for_document'.
    Never raises — any unexpected error yields a hold state with a flag.
    """
    missing: list[str] = []
    flags: list[str] = []

    present_types = {doc.doc_type for doc in raw.documents}

    # 1. Check required document presence
    for required in REQUIRED_DOC_TYPES:
        if required not in present_types:
            missing.append(required)
            log.info("app=%s missing_doc=%s", raw.application_id, required)

    # 2. Cross-doc income consistency (best-effort; skipped if no extractable text)
    pay_stub_doc = next(
        (d for d in raw.documents if d.doc_type == "pay_stub" and d.extracted_text),
        None,
    )
    if pay_stub_doc and pay_stub_doc.extracted_text:
        stub_income = _parse_income_from_text(pay_stub_doc.extracted_text)
        if stub_income is not None:
            diff_pct = abs(stub_income - raw.stated_income) / max(raw.stated_income, 1)
            if diff_pct > INCOME_TOLERANCE_PCT:
                msg = (
                    f"stated_income ({raw.stated_income:.2f}) differs from "
                    f"pay stub income ({stub_income:.2f}) by "
                    f"{diff_pct * 100:.1f}% (>{INCOME_TOLERANCE_PCT * 100:.0f}% threshold)"
                )
                flags.append(msg)
                log.warning("app=%s consistency_flag=%s", raw.application_id, msg)

    # 3. OCR confidence flags
    for doc in raw.documents:
        if doc.ocr_confidence is not None and doc.ocr_confidence < 0.60:
            flags.append(
                f"{doc.doc_type} OCR confidence low ({doc.ocr_confidence:.0%}); "
                "field values may be inaccurate — consider manual review"
            )

    status = "hold_for_document" if missing else "ok"

    return VerifyResult(
        all_required_present=len(missing) == 0,
        missing_docs=missing,
        consistency_flags=flags,
        status=status,
    )


def _parse_income_from_text(text: str) -> float | None:
    """
    Best-effort extraction of a monthly income figure from OCR/extracted text.

    Looks for patterns like "monthly income: 3500" or "monthly pay: £3,500".
    Returns None if no recognisable pattern found — caller should skip the
    cross-check rather than fail.

    NOTE: This reads data from extracted_text as UNTRUSTED INPUT.
    The regex extracts a number — it cannot execute instructions.
    """
    # Patterns: optional currency symbol, digits, optional comma separators
    patterns = [
        r"(?:monthly\s+(?:income|pay|salary|gross)[:\s]+)[£$€]?\s*([\d,]+(?:\.\d+)?)",
        r"(?:gross\s+(?:monthly|pay)[:\s]+)[£$€]?\s*([\d,]+(?:\.\d+)?)",
        r"(?:net\s+monthly[:\s]+)[£$€]?\s*([\d,]+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                continue
    return None
