"""Verification result data models."""

from typing import Literal

from pydantic import BaseModel, Field


class VerifyResult(BaseModel):
    """
    Output of the VERIFY node.
    Signals whether all required documents are present and internally
    consistent, or whether the application must be held pending more docs.
    """

    all_required_present: bool
    missing_docs: list[str] = Field(
        default_factory=list,
        description="Doc types that are absent but required (e.g. 'pay_stub')",
    )
    consistency_flags: list[str] = Field(
        default_factory=list,
        description=(
            "Cross-document inconsistencies found, e.g. "
            "'stated_income does not match pay stub by >10%'"
        ),
    )
    status: Literal["ok", "hold_for_document"]
