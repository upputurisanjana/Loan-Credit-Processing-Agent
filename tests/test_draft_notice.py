"""
tests/test_draft_notice.py — unit tests for the DRAFT_NOTICE node.

Coverage
--------
- Band guard: run_draft_notice returns "" for non-DECLINE bands.
- LLM success path: returns the LLM's draft text.
- LLM failure path: returns the _FALLBACK_DRAFT constant.
- LLM returns empty string: falls back rather than storing an empty notice.
- Fallback draft contains required regulatory placeholders.
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
from app.agent.nodes.score import run_score
from app.agent.nodes.draft_notice import run_draft_notice, _FALLBACK_DRAFT


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def decline_breakdown():
    """A ScoreBreakdown that lands in the DECLINE band."""
    fields = ApplicationFields(
        application_id="TEST-DECLINE",
        identity=IdentityBlock(name="Bob Example", address="2 Test Lane"),
        income_monthly=2000.0,
        debt_monthly=1400.0,   # DTI 70% — very high
        credit_history_years=0.5,  # below 2yr minimum
        credit_history_flags=["default_36m"],
        employment_months_current=2,  # below 6m minimum
    )
    breakdown = run_score(fields)
    assert breakdown.band == "decline", (
        f"Fixture must produce decline band, got {breakdown.band!r} "
        f"(composite={breakdown.composite_score:.4f})"
    )
    return breakdown


@pytest.fixture
def approve_breakdown():
    """A ScoreBreakdown that lands in the APPROVE band."""
    fields = ApplicationFields(
        application_id="TEST-APPROVE",
        identity=IdentityBlock(name="Carol Example", address="3 Test Lane"),
        income_monthly=6000.0,
        debt_monthly=1200.0,
        credit_history_years=8.0,
        credit_history_flags=[],
        employment_months_current=60,
    )
    breakdown = run_score(fields)
    assert breakdown.band == "approve"
    return breakdown


@pytest.fixture
def refer_breakdown():
    """A ScoreBreakdown that lands in the REFER band (0.65 ≤ composite < 0.75)."""
    fields = ApplicationFields(
        application_id="TEST-REFER",
        identity=IdentityBlock(name="Dave Example", address="4 Test Lane"),
        income_monthly=4000.0,
        debt_monthly=1400.0,   # DTI 35% — acceptable range
        credit_history_years=4.0,   # between 2yr and 5yr
        credit_history_flags=[],
        employment_months_current=18,   # between 6m and 24m
    )
    breakdown = run_score(fields)
    assert breakdown.band == "refer", (
        f"Fixture must produce refer band, got {breakdown.band!r} "
        f"(composite={breakdown.composite_score:.4f})"
    )
    return breakdown


# ── Band guard ────────────────────────────────────────────────────────────

class TestBandGuard:

    def test_returns_empty_for_approve(self, approve_breakdown):
        """No LLM call should be made; returns empty string."""
        with patch("app.agent.nodes.draft_notice.call_model") as mock_llm:
            result = run_draft_notice(approve_breakdown, "TEST-APPROVE", agent_recommendation="approve")
        assert result == ""
        mock_llm.assert_not_called()

    def test_returns_empty_for_refer(self, refer_breakdown):
        """No LLM call should be made; returns empty string."""
        with patch("app.agent.nodes.draft_notice.call_model") as mock_llm:
            result = run_draft_notice(refer_breakdown, "TEST-REFER", agent_recommendation="refer")
        assert result == ""
        mock_llm.assert_not_called()


# ── Success path ──────────────────────────────────────────────────────────

class TestSuccessPath:

    def test_returns_llm_draft_on_decline(self, decline_breakdown):
        """LLM response is returned as-is (stripped)."""
        fake_draft = "Dear Applicant, your application has been declined due to high DTI."
        with patch(
            "app.agent.nodes.draft_notice.call_model",
            return_value=f"  {fake_draft}  ",
        ):
            result = run_draft_notice(decline_breakdown, "TEST-DECLINE", agent_recommendation="decline")
        assert result == fake_draft

    def test_llm_called_with_decline_band_context(self, decline_breakdown):
        """The score breakdown data is included in the LLM messages."""
        with patch("app.agent.nodes.draft_notice.call_model", return_value="Draft text.") as mock_llm:
            run_draft_notice(decline_breakdown, "TEST-DECLINE", agent_recommendation="decline")

        assert mock_llm.called
        call_args = mock_llm.call_args
        messages = call_args.kwargs.get("messages") or call_args.args[1]
        user_msg = next(m["content"] for m in messages if m["role"] == "user")

        # Numeric values from the breakdown must appear in the prompt
        assert str(round(decline_breakdown.composite_score, 3)) in user_msg
        assert decline_breakdown.band in user_msg


# ── Fallback path ─────────────────────────────────────────────────────────

class TestFallbackPath:

    def test_llm_exception_returns_fallback(self, decline_breakdown):
        with patch(
            "app.agent.nodes.draft_notice.call_model",
            side_effect=RuntimeError("LLM unavailable"),
        ):
            result = run_draft_notice(decline_breakdown, "TEST-DECLINE", agent_recommendation="decline")
        assert result == _FALLBACK_DRAFT
        assert len(result) > 0

    def test_llm_empty_response_returns_fallback(self, decline_breakdown):
        """An empty string from the LLM should also trigger the fallback."""
        with patch(
            "app.agent.nodes.draft_notice.call_model",
            return_value="",
        ):
            result = run_draft_notice(decline_breakdown, "TEST-DECLINE", agent_recommendation="decline")
        assert result == _FALLBACK_DRAFT

    def test_llm_whitespace_only_returns_fallback(self, decline_breakdown):
        with patch(
            "app.agent.nodes.draft_notice.call_model",
            return_value="   \n  ",
        ):
            result = run_draft_notice(decline_breakdown, "TEST-DECLINE", agent_recommendation="decline")
        assert result == _FALLBACK_DRAFT


# ── Fallback draft content ────────────────────────────────────────────────

class TestFallbackDraftContent:
    """The fallback must still contain minimum regulatory placeholders."""

    def test_fallback_mentions_decline(self):
        assert "decline" in _FALLBACK_DRAFT.lower() or "declined" in _FALLBACK_DRAFT.lower()

    def test_fallback_mentions_credit_report(self):
        assert "credit report" in _FALLBACK_DRAFT.lower()

    def test_fallback_mentions_reconsideration(self):
        text = _FALLBACK_DRAFT.lower()
        assert "reconsider" in text or "appeal" in text or "documentation" in text

    def test_fallback_contains_lender_contact_placeholder(self):
        # The fallback now uses the actual default lender contact string
        # rather than a bracket placeholder.
        assert "contact" in _FALLBACK_DRAFT.lower()

    def test_fallback_is_not_empty(self):
        assert len(_FALLBACK_DRAFT.strip()) > 50
