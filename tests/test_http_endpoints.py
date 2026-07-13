"""
tests/test_http_endpoints.py — FastAPI TestClient integration tests.

Coverage
--------
POST /applications
  - 202 on valid application (pipeline mocked to return a DecisionRecord)
  - 409 on duplicate application_id
  - 422 on invalid body (missing required fields)

GET /applications/{id}
  - 200 for known application
  - 404 for unknown application

GET /queue
  - 200 returns list with expected shape

POST /applications/{id}/decision
  - 200 on valid underwriter approval
  - 409 if application not in decidable state
  - 409 if already decided
  - 422 if override_reason missing when overriding
  - 422 if override_reason too short

GET /applications/{id}/trace
  - 200 returns trace list
  - 404 for unknown application

POST /applications/{id}/amendments
  - 201 on valid amendment for a decided application
  - 409 if application is not yet decided
  - 404 if application not found

The pipeline is mocked so no LLM calls are made.
"""

import os
import pytest
from datetime import datetime, timezone
from unittest.mock import patch

os.environ.setdefault("POLICY_PATH", "./policy/policy_v1.yaml")
os.environ.setdefault("GITHUB_TOKEN", "test-token")
os.environ.setdefault("GITHUB_MODELS_ENDPOINT", "https://models.github.ai/inference")
os.environ.setdefault("PRIMARY_MODEL", "openai/gpt-4o-mini")
os.environ.setdefault("CHALLENGER_MODEL", "meta/llama-3.1-70b-instruct")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient

from app.models.application import ApplicationFields, IdentityBlock
from app.models.fairness import FairnessCheck, ChallengerResult
from app.agent.nodes.score import run_score


# ── Build a deterministic DecisionRecord for mocking ─────────────────────

def _make_decision_record(app_id: str = "HTTP-TEST-001"):
    from app.models.decision import DecisionRecord

    fields = ApplicationFields(
        application_id=app_id,
        identity=IdentityBlock(name="Test User", address="1 Test St"),
        income_monthly=5000.0,
        debt_monthly=1000.0,
        credit_history_years=6.0,
        credit_history_flags=[],
        employment_months_current=36,
    )
    breakdown = run_score(fields)
    fairness = FairnessCheck(
        original_band=breakdown.band,
        masked_band=breakdown.band,
        original_composite=breakdown.composite_score,
        masked_composite=breakdown.composite_score,
        match=True,
    )
    challenger = ChallengerResult(
        primary_band=breakdown.band,
        challenger_band=breakdown.band,
        bands_agree=True,
        delta=0.0,
    )
    return DecisionRecord(
        application_id=app_id,
        policy_version=breakdown.policy_version,
        score_breakdown=breakdown,
        fairness_check=fairness,
        challenger_result=challenger,
        agent_recommendation=breakdown.band,
        rationale="Test rationale from mock.",
        adverse_action_draft=None,
        human_decision=None,
        human_reviewer=None,
        override_reason=None,
        decided_at=None,
        created_at=datetime.now(timezone.utc),
        pipeline_trace=[{"node": "VERIFY", "timestamp": datetime.now(timezone.utc).isoformat(), "status": "ok"}],
        missing_docs=[],
        consistency_flags=[],
    )


VALID_APP_BODY = {
    "application_id": "HTTP-TEST-001",
    "applicant_name": "Test User",
    "applicant_address": "1 Test St",
    "stated_income": 5000.0,
    "stated_monthly_debt": 1000.0,
    "loan_amount_requested": 20000.0,
    "documents": [],
}


@pytest.fixture(autouse=True)
def reset_store():
    """Clear the in-memory store before each test."""
    from app.routers.intake import _store
    _store.clear()
    yield
    _store.clear()


@pytest.fixture
def client():
    # Patch DB writes so tests don't touch the filesystem
    with patch("app.routers.intake.get_db"), \
         patch("app.routers.intake.insert_decision"), \
         patch("app.routers.decisions.get_db"), \
         patch("app.routers.decisions.db_record_human_decision"):
        from app.main import app
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


# ── POST /applications ────────────────────────────────────────────────────

class TestSubmitApplication:

    def test_202_on_valid_application(self, client):
        record = _make_decision_record("HTTP-TEST-001")
        with patch("app.routers.intake.run_pipeline", return_value=record):
            resp = client.post("/applications", json=VALID_APP_BODY)
        assert resp.status_code == 202
        data = resp.json()
        assert data["application_id"] == "HTTP-TEST-001"
        assert data["status"] == "pending_human_review"
        assert "score_breakdown" in data

    def test_409_on_duplicate_application_id(self, client):
        record = _make_decision_record("HTTP-TEST-001")
        with patch("app.routers.intake.run_pipeline", return_value=record):
            client.post("/applications", json=VALID_APP_BODY)
            resp = client.post("/applications", json=VALID_APP_BODY)
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    def test_422_on_missing_required_fields(self, client):
        resp = client.post("/applications", json={"application_id": "X"})
        assert resp.status_code == 422

    def test_hold_response_passthrough(self, client):
        hold = {
            "status": "hold_for_document",
            "application_id": "HTTP-TEST-001",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "missing_docs": ["pay_stub"],
            "consistency_flags": [],
            "pipeline_trace": [],
        }
        with patch("app.routers.intake.run_pipeline", return_value=hold):
            resp = client.post("/applications", json=VALID_APP_BODY)
        assert resp.status_code == 202
        assert resp.json()["status"] == "hold_for_document"


# ── GET /applications/{id} ────────────────────────────────────────────────

class TestGetApplication:

    def test_200_for_known_application(self, client):
        record = _make_decision_record("HTTP-TEST-001")
        with patch("app.routers.intake.run_pipeline", return_value=record):
            client.post("/applications", json=VALID_APP_BODY)

        resp = client.get("/applications/HTTP-TEST-001")
        assert resp.status_code == 200
        assert resp.json()["application_id"] == "HTTP-TEST-001"

    def test_404_for_unknown_application(self, client):
        resp = client.get("/applications/DOES-NOT-EXIST")
        assert resp.status_code == 404


# ── GET /queue ────────────────────────────────────────────────────────────

class TestGetQueue:

    def test_200_returns_list(self, client):
        resp = client.get("/queue")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_queue_includes_submitted_application(self, client):
        record = _make_decision_record("HTTP-TEST-001")
        with patch("app.routers.intake.run_pipeline", return_value=record):
            client.post("/applications", json=VALID_APP_BODY)

        queue = client.get("/queue").json()
        ids = [item["application_id"] for item in queue]
        assert "HTTP-TEST-001" in ids

    def test_queue_item_has_required_fields(self, client):
        record = _make_decision_record("HTTP-TEST-001")
        with patch("app.routers.intake.run_pipeline", return_value=record):
            client.post("/applications", json=VALID_APP_BODY)

        item = client.get("/queue").json()[0]
        for field in ("application_id", "status", "created_at", "band", "human_decision"):
            assert field in item, f"Missing field: {field}"


# ── POST /applications/{id}/decision ─────────────────────────────────────

class TestRecordDecision:

    @pytest.fixture
    def pending_app(self, client):
        record = _make_decision_record("HTTP-TEST-001")
        with patch("app.routers.intake.run_pipeline", return_value=record):
            client.post("/applications", json=VALID_APP_BODY)
        return record

    def test_200_on_valid_approval(self, client, pending_app):
        resp = client.post(
            "/applications/HTTP-TEST-001/decision",
            json={"human_decision": "approve", "human_reviewer": "uw_1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["human_decision"] == "approve"
        assert data["status"] == "decided"

    def test_409_on_already_decided(self, client, pending_app):
        client.post(
            "/applications/HTTP-TEST-001/decision",
            json={"human_decision": "approve", "human_reviewer": "uw_1"},
        )
        resp = client.post(
            "/applications/HTTP-TEST-001/decision",
            json={"human_decision": "approve", "human_reviewer": "uw_1"},
        )
        assert resp.status_code == 409
        assert "already has a human decision" in resp.json()["detail"]

    def test_404_for_unknown_application(self, client):
        resp = client.post(
            "/applications/DOES-NOT-EXIST/decision",
            json={"human_decision": "approve", "human_reviewer": "uw_1"},
        )
        assert resp.status_code == 404

    def test_422_override_without_reason(self, client, pending_app):
        """Human overrides agent but provides no override_reason → 422."""
        # pending_app has agent_recommendation == "approve" (strong file)
        resp = client.post(
            "/applications/HTTP-TEST-001/decision",
            json={"human_decision": "decline", "human_reviewer": "uw_1"},
        )
        assert resp.status_code == 422

    def test_422_override_reason_too_short(self, client, pending_app):
        resp = client.post(
            "/applications/HTTP-TEST-001/decision",
            json={
                "human_decision": "decline",
                "human_reviewer": "uw_1",
                "override_reason": "short",
            },
        )
        assert resp.status_code == 422

    def test_200_override_with_valid_reason(self, client, pending_app):
        resp = client.post(
            "/applications/HTTP-TEST-001/decision",
            json={
                "human_decision": "decline",
                "human_reviewer": "uw_1",
                "override_reason": "New adverse information received from credit bureau.",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["human_decision"] == "decline"


# ── GET /applications/{id}/trace ──────────────────────────────────────────

class TestGetTrace:

    def test_200_returns_trace(self, client):
        record = _make_decision_record("HTTP-TEST-001")
        with patch("app.routers.intake.run_pipeline", return_value=record):
            client.post("/applications", json=VALID_APP_BODY)

        resp = client.get("/applications/HTTP-TEST-001/trace")
        assert resp.status_code == 200
        data = resp.json()
        assert data["application_id"] == "HTTP-TEST-001"
        assert isinstance(data["trace"], list)
        assert len(data["trace"]) > 0

    def test_404_for_unknown_application(self, client):
        resp = client.get("/applications/DOES-NOT-EXIST/trace")
        assert resp.status_code == 404


# ── POST /applications/{id}/amendments ───────────────────────────────────

class TestAmendments:

    @pytest.fixture
    def decided_app(self, client):
        record = _make_decision_record("HTTP-TEST-001")
        with patch("app.routers.intake.run_pipeline", return_value=record):
            client.post("/applications", json=VALID_APP_BODY)
        client.post(
            "/applications/HTTP-TEST-001/decision",
            json={"human_decision": "approve", "human_reviewer": "uw_1"},
        )

    def test_201_on_valid_amendment(self, client, decided_app):
        with patch("app.routers.amendments.get_db"), \
             patch("app.routers.amendments.insert_amendment"):
            resp = client.post(
                "/applications/HTTP-TEST-001/amendments",
                json={
                    "amended_by": "supervisor_1",
                    "amendment_reason": "Correcting the override reason after legal review.",
                    "field_changes": {"override_reason": "Corrected reason."},
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["original_application_id"] == "HTTP-TEST-001"
        assert "amendment_id" in data

    def test_409_amendment_on_pending_app(self, client):
        record = _make_decision_record("HTTP-TEST-001")
        with patch("app.routers.intake.run_pipeline", return_value=record):
            client.post("/applications", json=VALID_APP_BODY)

        with patch("app.routers.amendments.get_db"), \
             patch("app.routers.amendments.insert_amendment"):
            resp = client.post(
                "/applications/HTTP-TEST-001/amendments",
                json={
                    "amended_by": "supervisor_1",
                    "amendment_reason": "This should fail — case not yet decided.",
                    "field_changes": {},
                },
            )
        assert resp.status_code == 409

    def test_404_amendment_on_unknown_app(self, client):
        resp = client.post(
            "/applications/DOES-NOT-EXIST/amendments",
            json={
                "amended_by": "supervisor_1",
                "amendment_reason": "This should return 404 not found.",
                "field_changes": {},
            },
        )
        assert resp.status_code == 404
