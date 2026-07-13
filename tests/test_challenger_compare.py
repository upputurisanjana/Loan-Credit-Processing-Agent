"""
tests/test_challenger_compare.py — unit tests for the CHALLENGER node.

Coverage
--------
- employment_status regression: ApplicationFields has no such field; accessing
  it would raise AttributeError before this fix.
- _parse_band: valid bands, fuzzy match, unrecognised input defaults to "refer".
- _bands_differ_by_more_than_one: approve↔decline is >1, approve↔refer is not.
- run_challenger_compare: LLM failure path falls back to agreeing with primary.
- run_challenger_compare: delta and bands_agree are computed correctly.

All tests mock the LLM call so no real network requests are made.
"""

import os
import pytest
from unittest.mock import patch

os.environ.setdefault("POLICY_PATH", "./policy/policy_v1.yaml")
os.environ.setdefault("GITHUB_TOKEN", "test-token")
os.environ.setdefault("GITHUB_MODELS_ENDPOINT", "https://models.github.ai/inference")
os.environ.setdefault("PRIMARY_MODEL", "openai/gpt-4o-mini")
os.environ.setdefault("CHALLENGER_MODEL", "meta/llama-3.1-70b-instruct")
os.environ.setdefault("DATABASE_URL", "sqlite:///./audit.db")

from app.models.application import ApplicationFields, IdentityBlock
from app.models.scoring import ScoreBreakdown
from app.agent.nodes.challenger_compare import (
    _parse_band,
    _bands_differ_by_more_than_one,
    run_challenger_compare,
)
from app.agent.nodes.score import run_score


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def strong_fields() -> ApplicationFields:
    return ApplicationFields(
        application_id="TEST-CHALLENGER",
        identity=IdentityBlock(name="Alice Example", address="1 Test Lane"),
        income_monthly=6000.0,
        debt_monthly=1200.0,
        credit_history_years=8.0,
        credit_history_flags=[],
        employment_months_current=48,
    )


@pytest.fixture
def strong_breakdown(strong_fields: ApplicationFields) -> ScoreBreakdown:
    return run_score(strong_fields)


# ── Regression: employment_status field no longer accessed ────────────────

class TestEmploymentStatusRegression:
    """
    Before the fix, _build_messages accessed fields.employment_status which
    does not exist on ApplicationFields, raising AttributeError at runtime.
    This test ensures the node runs without error.
    """

    def test_build_messages_does_not_raise(
        self, strong_fields: ApplicationFields, strong_breakdown: ScoreBreakdown
    ):
        from app.agent.nodes.challenger_compare import _build_messages
        # Must not raise AttributeError
        messages = _build_messages(strong_fields, strong_breakdown)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_no_employment_status_in_prompt(
        self, strong_fields: ApplicationFields, strong_breakdown: ScoreBreakdown
    ):
        from app.agent.nodes.challenger_compare import _build_messages
        messages = _build_messages(strong_fields, strong_breakdown)
        user_content = messages[1]["content"]
        assert "employment_status" not in user_content.lower()

    def test_employment_months_in_prompt(
        self, strong_fields: ApplicationFields, strong_breakdown: ScoreBreakdown
    ):
        from app.agent.nodes.challenger_compare import _build_messages
        messages = _build_messages(strong_fields, strong_breakdown)
        user_content = messages[1]["content"]
        assert "48" in user_content  # employment_months_current value


# ── _parse_band ───────────────────────────────────────────────────────────

class TestParseBand:

    @pytest.mark.parametrize("raw,expected", [
        ("approve",  "approve"),
        ("refer",    "refer"),
        ("decline",  "decline"),
        ("APPROVE",  "approve"),
        ("DECLINE\n","decline"),
        ("  refer  ","refer"),
    ])
    def test_valid_bands(self, raw: str, expected: str):
        assert _parse_band(raw) == expected

    @pytest.mark.parametrize("raw,expected", [
        ("approved", "approve"),      # partial match
        ("declined", "decline"),      # partial match
        ("referral", "refer"),        # partial match
    ])
    def test_fuzzy_match(self, raw: str, expected: str):
        assert _parse_band(raw) == expected

    @pytest.mark.parametrize("raw", [
        "maybe",
        "unknown",
        "yes",
        "",
        "   ",
    ])
    def test_unrecognised_defaults_to_refer(self, raw: str):
        assert _parse_band(raw) == "refer"


# ── _bands_differ_by_more_than_one ────────────────────────────────────────

class TestBandDistance:

    def test_approve_vs_decline_is_more_than_one(self):
        assert _bands_differ_by_more_than_one("approve", "decline") is True
        assert _bands_differ_by_more_than_one("decline", "approve") is True

    def test_approve_vs_refer_is_not_more_than_one(self):
        assert _bands_differ_by_more_than_one("approve", "refer") is False

    def test_refer_vs_decline_is_not_more_than_one(self):
        assert _bands_differ_by_more_than_one("refer", "decline") is False

    def test_same_band_is_not_more_than_one(self):
        assert _bands_differ_by_more_than_one("approve", "approve") is False
        assert _bands_differ_by_more_than_one("refer", "refer") is False
        assert _bands_differ_by_more_than_one("decline", "decline") is False


# ── run_challenger_compare ────────────────────────────────────────────────

class TestRunChallengerCompare:

    def test_agreement_path(
        self, strong_fields: ApplicationFields, strong_breakdown: ScoreBreakdown
    ):
        """LLM agrees with primary → bands_agree=True, delta=0."""
        with patch(
            "app.agent.nodes.challenger_compare.call_model",
            return_value="approve",
        ):
            result = run_challenger_compare(strong_fields, strong_breakdown)

        assert result.primary_band == "approve"
        assert result.challenger_band == "approve"
        assert result.bands_agree is True
        assert result.delta == 0.0

    def test_minor_disagreement_still_agrees(
        self, strong_fields: ApplicationFields, strong_breakdown: ScoreBreakdown
    ):
        """Challenger says 'refer' vs primary 'approve' — 1 band, still agrees."""
        with patch(
            "app.agent.nodes.challenger_compare.call_model",
            return_value="refer",
        ):
            result = run_challenger_compare(strong_fields, strong_breakdown)

        assert result.primary_band == "approve"
        assert result.challenger_band == "refer"
        assert result.bands_agree is True
        assert result.delta == 1.0

    def test_major_disagreement_bands_disagree(
        self, strong_fields: ApplicationFields, strong_breakdown: ScoreBreakdown
    ):
        """Challenger says 'decline' vs primary 'approve' — 2 bands, disagrees."""
        with patch(
            "app.agent.nodes.challenger_compare.call_model",
            return_value="decline",
        ):
            result = run_challenger_compare(strong_fields, strong_breakdown)

        assert result.primary_band == "approve"
        assert result.challenger_band == "decline"
        assert result.bands_agree is False
        assert result.delta == 2.0

    def test_llm_failure_falls_back_to_agree(
        self, strong_fields: ApplicationFields, strong_breakdown: ScoreBreakdown
    ):
        """Any exception from the LLM defaults challenger to agreeing with primary."""
        with patch(
            "app.agent.nodes.challenger_compare.call_model",
            side_effect=RuntimeError("rate limit"),
        ):
            result = run_challenger_compare(strong_fields, strong_breakdown)

        assert result.challenger_band == result.primary_band
        assert result.bands_agree is True
        assert result.delta == 0.0

    def test_result_contains_required_fields(
        self, strong_fields: ApplicationFields, strong_breakdown: ScoreBreakdown
    ):
        with patch(
            "app.agent.nodes.challenger_compare.call_model",
            return_value="approve",
        ):
            result = run_challenger_compare(strong_fields, strong_breakdown)

        assert hasattr(result, "primary_band")
        assert hasattr(result, "challenger_band")
        assert hasattr(result, "bands_agree")
        assert hasattr(result, "delta")
        assert isinstance(result.delta, float)
