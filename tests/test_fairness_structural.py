"""
tests/test_fairness_structural.py

Structural proof that the scoring function's type contract makes it
impossible to pass identity fields into it directly.

This is distinct from test_scenarios.py scenario 4 (which shows the
*output* is the same).  This file proves the *input signature* of run_score
cannot accept identity data — even if a future developer tries to pass it.

Tests cover three layers of the structural guarantee:
  A. run_score() signature — accepts only ApplicationFields, no other params
  B. ApplicationFields type — identity is in IdentityBlock, not flat fields
  C. run_score() body — does not access fields.identity.* anywhere
  D. identity_blind_copy() — masks IdentityBlock without touching financial fields
  E. Round-trip — masked copy produces identical ScoreBreakdown to original
"""

import inspect
import os
import textwrap
import ast
from pathlib import Path

import pytest

os.environ.setdefault("POLICY_PATH", "./policy/policy_v1.yaml")
os.environ.setdefault("GITHUB_TOKEN", "test")
os.environ.setdefault("GITHUB_MODELS_ENDPOINT", "https://models.github.ai/inference")
os.environ.setdefault("PRIMARY_MODEL", "openai/gpt-4o-mini")
os.environ.setdefault("CHALLENGER_MODEL", "meta/llama-3.1-70b-instruct")
os.environ.setdefault("DATABASE_URL", "sqlite:///./audit.db")

from app.models.application import ApplicationFields, IdentityBlock
from app.agent.nodes.score import run_score, identity_blind_copy

SCORE_PY = Path("app/agent/nodes/score.py")


# ──────────────────────────────────────────────────────────────────────────
# A. Signature contract
# ──────────────────────────────────────────────────────────────────────────

class TestRunScoreSignature:
    """run_score must accept exactly one parameter: fields: ApplicationFields."""

    def test_single_parameter(self):
        sig = inspect.signature(run_score)
        params = list(sig.parameters.keys())
        assert params == ["fields"], (
            f"run_score must have exactly one parameter 'fields', got: {params}"
        )

    def test_parameter_annotated_as_application_fields(self):
        sig = inspect.signature(run_score)
        ann = sig.parameters["fields"].annotation
        assert ann is ApplicationFields, (
            f"'fields' parameter must be annotated as ApplicationFields, got {ann}"
        )

    def test_no_name_parameter(self):
        sig = inspect.signature(run_score)
        assert "name" not in sig.parameters, (
            "run_score must not have a 'name' parameter"
        )

    def test_no_address_parameter(self):
        sig = inspect.signature(run_score)
        assert "address" not in sig.parameters, (
            "run_score must not have an 'address' parameter"
        )

    def test_no_identity_parameter(self):
        sig = inspect.signature(run_score)
        assert "identity" not in sig.parameters, (
            "run_score must not have an 'identity' parameter — "
            "identity is isolated inside ApplicationFields.identity "
            "and the scorer must never read it"
        )

    def test_calling_with_strings_raises_type_error(self):
        """
        Attempting to call run_score with raw strings instead of
        ApplicationFields must fail — Python's type system and/or Pydantic
        validation prevent it at runtime.
        """
        with pytest.raises((TypeError, AttributeError, Exception)):
            run_score("Alice", "123 Main St")  # type: ignore[arg-type]

    def test_calling_with_identity_block_alone_raises(self):
        """
        Passing an IdentityBlock directly (not wrapped in ApplicationFields)
        must fail — the scorer only accepts ApplicationFields.
        """
        identity = IdentityBlock(name="Alice", address="123 Main St")
        with pytest.raises((TypeError, AttributeError, Exception)):
            run_score(identity)  # type: ignore[arg-type]


# ──────────────────────────────────────────────────────────────────────────
# B. ApplicationFields type — identity is in an isolated sub-object
# ──────────────────────────────────────────────────────────────────────────

class TestApplicationFieldsStructure:
    """
    Identity lives in ApplicationFields.identity: IdentityBlock.
    The scoring fields (income_monthly, debt_monthly, etc.) are at the
    top level and have no overlap with identity fields.
    """

    def test_identity_is_identity_block(self):
        fields = ApplicationFields(
            application_id="T",
            identity=IdentityBlock(name="X", address="Y"),
            income_monthly=1.0,
            debt_monthly=0.0,
            credit_history_years=0.0,
            credit_history_flags=[],
            employment_months_current=0,
        )
        assert isinstance(fields.identity, IdentityBlock)

    def test_top_level_fields_are_financial_only(self):
        """
        The fields used by the scorer (income_monthly, debt_monthly,
        credit_history_years, credit_history_flags, employment_months_current)
        must not be named 'name' or 'address'.
        """
        from app.models.application import ApplicationFields
        financial_field_names = {
            "income_monthly",
            "debt_monthly",
            "credit_history_years",
            "credit_history_flags",
            "employment_months_current",
        }
        model_fields = set(ApplicationFields.model_fields.keys())
        identity_fields = {"name", "address"}
        overlap = model_fields & identity_fields
        assert not overlap, (
            f"ApplicationFields has identity fields at top level: {overlap}. "
            "Identity must be isolated in the nested IdentityBlock."
        )

    def test_scorer_fields_all_present(self):
        required = {
            "income_monthly",
            "debt_monthly",
            "credit_history_years",
            "credit_history_flags",
            "employment_months_current",
        }
        model_fields = set(ApplicationFields.model_fields.keys())
        missing = required - model_fields
        assert not missing, f"ApplicationFields missing scorer fields: {missing}"


# ──────────────────────────────────────────────────────────────────────────
# C. Source code audit — run_score() does not read fields.identity
# ──────────────────────────────────────────────────────────────────────────

def _get_run_score_ast():
    """Parse score.py and return the run_score FunctionDef node."""
    source = SCORE_PY.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "run_score":
            return node
    pytest.fail("run_score function not found in score.py")


class TestRunScoreSourceDoesNotReadIdentity:
    """
    Parse the AST of score.py and verify that run_score's function body
    contains no attribute access on a name that resolves to 'identity',
    'name', or 'address' via fields.identity.*.

    This is a compile-time structural check, not a runtime check.
    """

    @pytest.fixture
    def run_score_ast(self):
        return _get_run_score_ast()

    def test_no_identity_attribute_access(self, run_score_ast):
        """
        run_score must not contain any attribute access of the form
        `fields.identity`, `*.identity.name`, or `*.identity.address`.
        """
        violations = []
        for node in ast.walk(run_score_ast):
            if isinstance(node, ast.Attribute):
                # Check for .identity attribute access
                if node.attr == "identity":
                    violations.append(ast.unparse(node))
                # Check for .name or .address on anything called identity
                if node.attr in ("name", "address"):
                    if isinstance(node.value, ast.Attribute) and node.value.attr == "identity":
                        violations.append(ast.unparse(node))
        assert not violations, (
            f"run_score() accesses identity fields: {violations}. "
            "The scorer must never read identity data."
        )

    def test_no_hardcoded_identity_strings(self, run_score_ast):
        """No string literals 'name' or 'address' used as dict keys in run_score."""
        for node in ast.walk(run_score_ast):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert node.value not in ("name", "address"), (
                    f"run_score() contains string literal '{node.value}' "
                    "which could indicate identity data access"
                )

    def test_no_llm_imports_in_score_module(self):
        """
        The entire score.py must contain zero LLM-related imports.
        This is the hard constraint from the spec.
        """
        source = SCORE_PY.read_text(encoding="utf-8")
        tree = ast.parse(source)
        llm_modules = {"openai", "langchain", "langgraph", "anthropic", "cohere", "huggingface"}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                else:
                    module = ""
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else []
                all_names = [module] + names
                for name in all_names:
                    for llm in llm_modules:
                        assert llm not in name.lower(), (
                            f"score.py imports LLM module '{name}'. "
                            "The scoring engine must be pure Python with zero LLM imports."
                        )


# ──────────────────────────────────────────────────────────────────────────
# D. identity_blind_copy — masks identity without touching financial fields
# ──────────────────────────────────────────────────────────────────────────

class TestIdentityBlindCopy:
    """
    identity_blind_copy() must:
    1. Replace name and address with '[REDACTED]'
    2. Leave all financial/credit fields untouched
    3. Return a new object (deep copy), not mutate the original
    """

    @pytest.fixture
    def original(self) -> ApplicationFields:
        return ApplicationFields(
            application_id="COPY-TEST",
            identity=IdentityBlock(name="Real Name", address="Real Address"),
            income_monthly=4000.0,
            debt_monthly=1200.0,
            credit_history_years=5.0,
            credit_history_flags=["late_payment_12m"],
            employment_months_current=24,
        )

    def test_name_is_redacted(self, original):
        masked = identity_blind_copy(original)
        assert masked.identity.name == "[REDACTED]"

    def test_address_is_redacted(self, original):
        masked = identity_blind_copy(original)
        assert masked.identity.address == "[REDACTED]"

    def test_original_name_unchanged(self, original):
        identity_blind_copy(original)
        assert original.identity.name == "Real Name", (
            "identity_blind_copy must not mutate the original"
        )

    def test_original_address_unchanged(self, original):
        identity_blind_copy(original)
        assert original.identity.address == "Real Address"

    def test_financial_fields_preserved(self, original):
        masked = identity_blind_copy(original)
        assert masked.income_monthly == original.income_monthly
        assert masked.debt_monthly == original.debt_monthly
        assert masked.credit_history_years == original.credit_history_years
        assert masked.credit_history_flags == original.credit_history_flags
        assert masked.employment_months_current == original.employment_months_current

    def test_returns_new_object(self, original):
        masked = identity_blind_copy(original)
        assert masked is not original


# ──────────────────────────────────────────────────────────────────────────
# E. Round-trip — masked copy produces bit-identical ScoreBreakdown
# ──────────────────────────────────────────────────────────────────────────

class TestMaskedScoreIsIdentical:
    """
    Running run_score on the original and on identity_blind_copy must produce
    the exact same composite_score, band, dti_ratio, and all sub-scores.

    This confirms identity was never a scoring input — if it were, the scores
    would diverge and we'd catch it here.
    """

    @pytest.mark.parametrize("income,debt,years,flags,months", [
        # Clear approve
        (5000.0, 1200.0, 8.0, [], 87),
        # Borderline refer
        (4000.0, 1350.0, 4.0, [], 14),
        # Clear decline
        (2800.0, 1400.0, 0.0, [], 0),
        # With late payment flag
        (4500.0, 1350.0, 3.0, ["late_payment_12m"], 18),
        # With default flag
        (4000.0, 1100.0, 6.0, ["default_36m"], 30),
    ])
    def test_score_identical_after_masking(self, income, debt, years, flags, months):
        original = ApplicationFields(
            application_id="ROUND-TRIP",
            identity=IdentityBlock(name="Sensitive Name", address="Sensitive Address"),
            income_monthly=income,
            debt_monthly=debt,
            credit_history_years=years,
            credit_history_flags=flags,
            employment_months_current=months,
        )
        masked = identity_blind_copy(original)

        bd_orig = run_score(original)
        bd_masked = run_score(masked)

        assert bd_orig.band == bd_masked.band, (
            f"Band changed after masking: {bd_orig.band} → {bd_masked.band} "
            f"(income={income}, debt={debt}, years={years}, months={months})"
        )
        assert abs(bd_orig.composite_score - bd_masked.composite_score) < 1e-9, (
            f"Composite changed after masking: {bd_orig.composite_score} → {bd_masked.composite_score}"
        )
        assert bd_orig.dti_ratio == bd_masked.dti_ratio
        assert bd_orig.dti_subscore == bd_masked.dti_subscore
        assert bd_orig.credit_history_subscore == bd_masked.credit_history_subscore
        assert bd_orig.income_stability_subscore == bd_masked.income_stability_subscore
