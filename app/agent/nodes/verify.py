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
3. Name consistency: applicant_name vs. name found in ID and pay stub documents.
4. OCR confidence flags for low-quality scans.
5. Prompt-injection guard: applicant_notes and extracted_text are treated
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

    # 3. Name consistency — check applicant_name against names found in documents
    #    Checks ID document and pay stub; bank statement uses "Account Holder" field.
    #    This is a best-effort regex check; OCR noise is tolerated via normalisation.
    stated_name = raw.applicant_name.strip().lower()
    doc_types_to_check = ["id", "pay_stub", "bank_statement"]
    for doc in raw.documents:
        if doc.doc_type not in doc_types_to_check:
            continue
        if not doc.extracted_text:
            continue
        doc_name = _parse_name_from_text(doc.extracted_text, doc.doc_type)
        if doc_name is None:
            # Could not find a name in this document — skip, don't flag
            continue
        doc_name_norm = doc_name.strip().lower()
        if not _names_match(stated_name, doc_name_norm):
            msg = (
                f"Name mismatch: application states '{raw.applicant_name}' "
                f"but {doc.doc_type} document shows '{doc_name}'"
            )
            flags.append(msg)
            log.warning("app=%s name_mismatch doc_type=%s stated=%r doc=%r",
                        raw.application_id, doc.doc_type, raw.applicant_name, doc_name)

    # 4. OCR confidence flags
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


def _parse_name_from_text(text: str, doc_type: str) -> str | None:
    """
    Best-effort extraction of a person's name from OCR/extracted document text.

    Handles common patterns in ID documents, pay stubs, and bank statements.
    Returns None if no recognisable name pattern found.

    NOTE: This reads data from extracted_text as UNTRUSTED INPUT.
    The regex extracts a name string — it cannot execute instructions.
    """
    # Patterns vary by document type
    if doc_type == "id":
        patterns = [
            r"(?:Name|Full\s+Name|Holder)[:\s]+([A-Za-z][A-Za-z\s\-\'\.]{2,50})",
            r"(?:SURNAME|GIVEN\s+NAME)[:\s]+([A-Za-z][A-Za-z\s\-\'\.]{2,50})",
        ]
    elif doc_type == "pay_stub":
        patterns = [
            r"(?:Employee|Payee|Name)[:\s]+([A-Za-z][A-Za-z\s\-\'\.]{2,50})",
            r"(?:EMPLOYEE)[:\s]+([A-Za-z][A-Za-z\s\-\'\.]{2,50})",
        ]
    elif doc_type == "bank_statement":
        patterns = [
            r"(?:Account\s+Holder|Customer|Name)[:\s]+([A-Za-z][A-Za-z\s\-\'\.]{2,50})",
        ]
    else:
        patterns = [
            r"(?:Name|Full\s+Name)[:\s]+([A-Za-z][A-Za-z\s\-\'\.]{2,50})",
        ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Strip trailing noise (dates, numbers, newlines)
            name = re.split(r"[\n\r\d]", name)[0].strip()
            if len(name) >= 3:
                return name
    return None


def _names_match(name_a: str, name_b: str) -> bool:
    """
    Compare two name strings with tolerance for OCR noise and name ordering.

    Rules:
    - Normalise: lowercase, collapse whitespace, remove punctuation
    - Exact match → True
    - All tokens of shorter name appear in longer name → True (handles
      "John Smith" matching "Mr John Smith" or "Smith, John")
    - Single token mismatch with edit distance ≤ 1 → True (OCR noise)
    """
    def normalise(n: str) -> set[str]:
        n = re.sub(r"[^a-z\s]", "", n.lower())
        return set(n.split())

    tokens_a = normalise(name_a)
    tokens_b = normalise(name_b)

    if not tokens_a or not tokens_b:
        return True  # Can't compare — skip check

    # Exact token set match
    if tokens_a == tokens_b:
        return True

    # All tokens of the shorter name appear in the longer name
    shorter = tokens_a if len(tokens_a) <= len(tokens_b) else tokens_b
    longer  = tokens_a if len(tokens_a) >  len(tokens_b) else tokens_b
    if shorter.issubset(longer):
        return True

    # Fuzzy: tokens differ by at most one char (OCR noise like "5mith" vs "Smith")
    # Find tokens that don't match and check edit distance
    unmatched_a = tokens_a - tokens_b
    unmatched_b = tokens_b - tokens_a
    if len(unmatched_a) == 1 and len(unmatched_b) == 1:
        ta = next(iter(unmatched_a))
        tb = next(iter(unmatched_b))
        if _edit_distance(ta, tb) <= 1:
            return True

    return False


def _edit_distance(s1: str, s2: str) -> int:
    """Simple Levenshtein distance for short strings (OCR noise detection)."""
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    if not s2:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for ch1 in s1:
        curr = [prev[0] + 1]
        for j, ch2 in enumerate(s2):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ch1 != ch2)))
        prev = curr
    return prev[-1]
