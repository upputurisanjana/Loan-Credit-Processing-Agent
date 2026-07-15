"""Application intake and extracted-field data models."""

from datetime import datetime, timezone
from typing import Literal
import re

from pydantic import BaseModel, Field, field_validator


class UploadedDocument(BaseModel):
    """A single document attached to the application."""

    doc_type: Literal["id", "pay_stub", "bank_statement", "other"]
    file_path: str
    ocr_confidence: float | None = None
    extracted_text: str | None = None


class ApplicationRaw(BaseModel):
    """
    Raw application as received from the intake form/API.
    Contains identity, stated financials, and document references.
    This is the *untrusted* input — all fields are treated as applicant
    claims until verified.
    """

    application_id: str = Field(..., description="Unique application identifier")
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    applicant_name: str = Field(..., description="Full legal name as stated by applicant")
    applicant_address: str = Field(..., description="Address as stated by applicant")
    documents: list[UploadedDocument] = Field(
        default_factory=list,
        description="ID, pay stub, bank statement, etc.",
    )
    stated_income: float = Field(
        ..., gt=0, description="Monthly gross income stated by applicant (£/$/local currency)"
    )
    stated_monthly_debt: float = Field(
        ..., ge=0, description="Total monthly debt obligations stated by applicant"
    )
    loan_amount_requested: float = Field(..., gt=0, description="Requested loan amount")
    applicant_notes: str | None = Field(
        None,
        description=(
            "Free-text note from applicant — treated as UNTRUSTED DATA, "
            "never executed as instructions."
        ),
    )

    @field_validator("application_id")
    @classmethod
    def validate_application_id(cls, v: str) -> str:
        """
        Restrict application_id to safe alphanumeric + hyphen characters.
        Prevents path-traversal and injection when used to construct file paths.
        Pattern: 3–30 characters, uppercase letters, digits, and hyphens only.
        """
        if not re.match(r"^[A-Z0-9][A-Z0-9\-]{2,29}$", v):
            raise ValueError(
                "application_id must be 3–30 characters, "
                "containing only uppercase letters, digits, and hyphens, "
                "and must start with a letter or digit. "
                f"Got: {v!r}"
            )
        return v


class IdentityBlock(BaseModel):
    """
    Identity fields kept separate so the fairness re-scorer can mask them
    without touching the financial/credit fields used for scoring.
    """

    name: str
    address: str


class ApplicationFields(BaseModel):
    """
    Extracted and validated fields ready for the policy scoring engine.
    Identity is isolated in its own block so the scorer can operate on a
    copy with IdentityBlock masked without any code path seeing name/address.
    """

    application_id: str
    identity: IdentityBlock

    # Financial fields used by the scoring engine
    income_monthly: float = Field(..., gt=0)
    debt_monthly: float = Field(..., ge=0)
    credit_history_years: float = Field(..., ge=0)
    credit_history_flags: list[str] = Field(
        default_factory=list,
        description="e.g. 'late_payment_12m', 'default_36m'",
    )
    employment_months_current: int = Field(..., ge=0)

    # Derived convenience — computed at extraction time, not by the LLM scorer
    @property
    def dti_ratio(self) -> float:
        """Debt-to-income ratio (monthly debt / monthly income)."""
        if self.income_monthly == 0:
            return 1.0
        return self.debt_monthly / self.income_monthly
