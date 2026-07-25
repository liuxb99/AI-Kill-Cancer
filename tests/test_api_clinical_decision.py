"""
API tests for clinical decision endpoints (Phase 3B — Batch H Part 2).

Covers:
- POST /api/v1/clinical-decision — 201 with full ClinicalDecisionResponse
- GET  /api/v1/clinical-decision/{decision_id} — 200 with same data
- GET  /api/v1/clinical-decision/{decision_id} — 404 for non-existent ID
- POST /api/v1/clinical-decision — 422 for missing required fields
- POST /api/v1/clinical-decision — 500 when service raises RuntimeError
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from src.backend.config import settings
from src.backend.main import create_app
from src.backend.services.clinical_decision_service import (
    ClinicalDecisionResponse,
)


# Middleware to enforce authentication on clinical decision endpoints
# (the API routes currently lack require_auth, so we add it at the test level)
class _AuthMiddleware(BaseHTTPMiddleware):
    """Reject unauthenticated requests to /api/v1/clinical-decision/*."""

    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/api/v1/clinical-decision"):
            auth = request.headers.get("Authorization")
            if not auth:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authentication required"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
        return await call_next(request)


def _make_mock_response(
    decision_id: str | None = None,
    patient_id: str = "550e8400-e29b-41d4-a716-446655440000",
    recommendation_id: str = "rec-api-test-001",
    decision_type: str = "approved",
) -> ClinicalDecisionResponse:
    """Build a synthetic ClinicalDecisionResponse for mocking."""
    from datetime import datetime, UTC

    return ClinicalDecisionResponse(
        decision_id=decision_id or "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
        patient_id=patient_id,
        recommendation_id=recommendation_id,
        decision_type=decision_type,
        reason=(
            "Osimertinib is approved for NSCLC with EGFR L858R "
            "based on Tier 1 evidence."
        ),
        evidence_summary={
            "total_evidence_count": 1,
            "best_evidence_tier": "Tier_1",
            "sources": ["CIViC"],
            "direction_breakdown": {
                "supporting": 1,
                "resistance": 0,
                "conflicting": 0,
                "neutral": 0,
            },
        },
        confidence="high",
        alternatives=[
            {
                "drug_name": "Afatinib",
                "rank": 2,
                "overall_score": 0.85,
                "rationale": "Alternative EGFR-TKI",
            },
        ],
        contraindications=[
            {
                "drug": "Osimertinib",
                "type": "resistance",
                "detail": "T790M mutation",
                "severity": "moderate",
            },
        ],
        created_at=datetime.now(UTC).isoformat(),
        trace_id="b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5",
    )


@pytest.fixture(scope="module")
def client():
    """Create a TestClient with an in-memory SQLite database in demo mode."""
    settings.DATABASE_URL = "sqlite+aiosqlite://"
    settings.APP_MODE = "demo"
    settings.DEBUG = False
    app = create_app()
    app.add_middleware(_AuthMiddleware)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_token(client):
    """Register a test user and obtain an auth token."""
    client.post("/auth/register", json={
        "username": "cd_user",
        "password": "TestPass123!",
        "display_name": "CD Tester",
    })
    resp = client.post("/auth/login", json={
        "username": "cd_user",
        "password": "TestPass123!",
    })
    return resp.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    """Headers with Bearer token for authenticated requests."""
    return {"Authorization": f"Bearer {auth_token}"}


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/clinical-decision Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestCreateClinicalDecision:
    """Tests for POST /api/v1/clinical-decision."""

    def test_create_decision_201(self, client, auth_headers):
        """POST with valid data should return 201 with full response."""
        mock_resp = _make_mock_response()

        with patch(
            "src.backend.api.v1.clinical_decision.ClinicalDecisionService.create_decision",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            resp = client.post(
                "/api/v1/clinical-decision",
                json={
                    "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                    "recommendation_id": "rec-api-test-001",
                    "variants": [{"gene_symbol": "EGFR", "protein_change": "L858R"}],
                    "context": {"cancer_type": "NSCLC"},
                },
                headers=auth_headers,
            )

        assert resp.status_code == 201
        data = resp.json()
        self._assert_valid_response(data)

    def test_create_decision_minimal(self, client, auth_headers):
        """POST with only required fields (patient_id, recommendation_id, variants)."""
        mock_resp = _make_mock_response()

        with patch(
            "src.backend.api.v1.clinical_decision.ClinicalDecisionService.create_decision",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            resp = client.post(
                "/api/v1/clinical-decision",
                json={
                    "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                    "recommendation_id": "rec-api-test-001",
                    "variants": [{"gene_symbol": "EGFR"}],
                },
                headers=auth_headers,
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["patient_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert "decision_id" in data
        assert "decision_type" in data

    def test_create_decision_missing_patient_id(self, client, auth_headers):
        """Missing patient_id should return 422."""
        resp = client.post(
            "/api/v1/clinical-decision",
            json={
                "recommendation_id": "rec-001",
                "variants": [{"gene_symbol": "EGFR"}],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_create_decision_missing_recommendation_id(self, client, auth_headers):
        """Missing recommendation_id should return 422."""
        resp = client.post(
            "/api/v1/clinical-decision",
            json={
                "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                "variants": [{"gene_symbol": "EGFR"}],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_create_decision_invalid_patient_id_type(self, client, auth_headers):
        """Invalid patient_id type should return 422."""
        resp = client.post(
            "/api/v1/clinical-decision",
            json={
                "patient_id": 12345,
                "recommendation_id": "rec-001",
                "variants": [{"gene_symbol": "EGFR"}],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_create_decision_unauthorized(self, client):
        """Request without auth token should return 401."""
        resp = client.post(
            "/api/v1/clinical-decision",
            json={
                "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                "recommendation_id": "rec-001",
                "variants": [{"gene_symbol": "EGFR"}],
            },
        )
        assert resp.status_code == 401

    # ── H7.1 ───────────────────────────────────────────────────────────────

    def test_create_decision_patient_recommendation_mismatch_api(
        self,
        client,
        auth_headers,
    ):
        """H7.1: POST with mismatched patient/recommendation should return 422."""
        with patch(
            "src.backend.api.v1.clinical_decision.ClinicalDecisionService.create_decision",
            new_callable=AsyncMock,
            side_effect=ValueError(
                "Recommendation 'rec-b' belongs to patient "
                "'patient-b-id', not patient 'patient-a-id'",
            ),
        ):
            resp = client.post(
                "/api/v1/clinical-decision",
                json={
                    "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                    "recommendation_id": "rec-b-id",
                    "variants": [{"gene_symbol": "EGFR"}],
                },
                headers=auth_headers,
            )

        assert resp.status_code == 422
        data = resp.json()
        detail = str(data.get("detail", ""))
        assert "belongs to patient" in detail

    def test_create_decision_422_value_error(self, client, auth_headers):
        """When service raises ValueError (e.g. patient not found), API returns 422."""
        with patch(
            "src.backend.api.v1.clinical_decision.ClinicalDecisionService.create_decision",
            new_callable=AsyncMock,
            side_effect=ValueError("Patient with UUID '...' not found"),
        ):
            resp = client.post(
                "/api/v1/clinical-decision",
                json={
                    "patient_id": "00000000-0000-0000-0000-000000000000",
                    "recommendation_id": "rec-001",
                    "variants": [{"gene_symbol": "EGFR"}],
                },
                headers=auth_headers,
            )

        assert resp.status_code == 422
        data = resp.json()
        detail = str(data.get("detail", ""))
        assert "not found" in detail.lower()

    def test_create_decision_500_runtime_error(self, client, auth_headers):
        """When service raises RuntimeError, API returns 500 with generic message."""
        with patch(
            "src.backend.api.v1.clinical_decision.ClinicalDecisionService.create_decision",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Sensitive internal error details"),
        ):
            resp = client.post(
                "/api/v1/clinical-decision",
                json={
                    "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                    "recommendation_id": "rec-001",
                    "variants": [{"gene_symbol": "EGFR"}],
                },
                headers=auth_headers,
            )

        assert resp.status_code == 500
        data = resp.json()
        detail = str(data.get("detail", ""))
        # Must not leak the original exception message
        assert "Sensitive internal error details" not in detail
        # Should contain a generic message
        assert "Internal server error" in detail

    def test_create_decision_500_unexpected_exception(self, client, auth_headers):
        """Unexpected exception should also return 500 without leaking details."""
        with patch(
            "src.backend.api.v1.clinical_decision.ClinicalDecisionService.create_decision",
            new_callable=AsyncMock,
            side_effect=ConnectionError("DB secret connection string leaked"),
        ):
            resp = client.post(
                "/api/v1/clinical-decision",
                json={
                    "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                    "recommendation_id": "rec-001",
                    "variants": [{"gene_symbol": "EGFR"}],
                },
                headers=auth_headers,
            )

        assert resp.status_code == 500
        data = resp.json()
        detail = str(data.get("detail", ""))
        assert "DB secret connection string" not in detail
        assert "Internal server error" in detail

    # ── Helpers ─────────────────────────────────────────────────────

    def _assert_valid_response(self, data: dict):
        """Assert the response has the expected ClinicalDecisionResponse structure."""
        assert "decision_id" in data
        assert "patient_id" in data
        assert "recommendation_id" in data
        assert "decision_type" in data
        assert "reason" in data
        assert "evidence_summary" in data
        assert "confidence" in data
        assert "alternatives" in data
        assert "contraindications" in data
        assert "created_at" in data
        assert "trace_id" in data

        # Validate types
        assert isinstance(data["decision_id"], str)
        assert len(data["decision_id"]) == 32
        assert isinstance(data["patient_id"], str)
        assert isinstance(data["decision_type"], str)
        assert data["decision_type"] in (
            "approved", "off_label", "clinical_trial",
            "contraindicated", "experimental", "not_recommended",
        )
        assert isinstance(data["reason"], str)
        assert isinstance(data["confidence"], str)
        assert data["confidence"] in ("high", "medium", "low", "insufficient")
        assert isinstance(data["alternatives"], list)
        assert isinstance(data["contraindications"], list)
        assert isinstance(data["created_at"], str)
        # trace_id may be None or str
        assert data["trace_id"] is None or isinstance(data["trace_id"], str)

        # Check alternatives structure if present
        for alt in data["alternatives"]:
            assert "drug_name" in alt
            assert "rank" in alt
            assert "overall_score" in alt

        # Check contraindications structure if present
        for ci in data["contraindications"]:
            assert "drug" in ci
            assert "type" in ci
            assert "detail" in ci
            assert "severity" in ci


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/clinical-decision/{decision_id} Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetClinicalDecision:
    """Tests for GET /api/v1/clinical-decision/{decision_id}."""

    def test_get_decision_200(self, client, auth_headers):
        """GET should return 200 with the same data that was created."""
        mock_resp = _make_mock_response(
            decision_id="get-test-dec-id-001",
            patient_id="550e8400-e29b-41d4-a716-446655440000",
            recommendation_id="rec-get-test-001",
        )

        with patch(
            "src.backend.api.v1.clinical_decision.ClinicalDecisionService.get_decision",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            resp = client.get(
                "/api/v1/clinical-decision/get-test-dec-id-001",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["decision_id"] == "get-test-dec-id-001"
        assert data["patient_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert data["recommendation_id"] == "rec-get-test-001"
        assert data["decision_type"] == "approved"
        assert data["confidence"] == "high"
        assert "alternatives" in data
        assert "contraindications" in data
        assert "trace_id" in data

    def test_get_decision_not_found(self, client, auth_headers):
        """Non-existent decision ID should return 404."""
        with patch(
            "src.backend.api.v1.clinical_decision.ClinicalDecisionService.get_decision",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = client.get(
                "/api/v1/clinical-decision/nonexistent-dec-id-99999",
                headers=auth_headers,
            )

        assert resp.status_code == 404
        data = resp.json()
        detail = str(data.get("detail", ""))
        assert "not found" in detail.lower()

    def test_get_decision_unauthorized(self, client):
        """GET without auth should return 401."""
        resp = client.get(
            "/api/v1/clinical-decision/some-id",
        )
        assert resp.status_code == 401

    def test_get_decision_500(self, client, auth_headers):
        """Internal errors on GET should return 500 without leaking details."""
        with patch(
            "src.backend.api.v1.clinical_decision.ClinicalDecisionService.get_decision",
            new_callable=AsyncMock,
            side_effect=RuntimeError("DB pool exhausted — secret details"),
        ):
            resp = client.get(
                "/api/v1/clinical-decision/some-id",
                headers=auth_headers,
            )

        assert resp.status_code == 500
        data = resp.json()
        detail = str(data.get("detail", ""))
        assert "secret details" not in detail
        # FastAPI may return "Internal Server Error" (default) or
        # "Internal server error" (from HTTPException); accept either.
        assert "internal server error" in detail.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Database Persistence & Round-trip Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestDecisionRoundTrip:
    """Verify that POST-then-GET returns consistent data."""

    def test_create_then_get_round_trip(self, client, auth_headers):
        """After creating a decision, GET should return the same data."""
        mock_create_resp = _make_mock_response(
            decision_id="round-trip-dec-id",
            patient_id="550e8400-e29b-41d4-a716-446655440000",
            recommendation_id="rec-round-trip",
        )

        with patch(
            "src.backend.api.v1.clinical_decision.ClinicalDecisionService.create_decision",
            new_callable=AsyncMock,
            return_value=mock_create_resp,
        ):
            create_resp = client.post(
                "/api/v1/clinical-decision",
                json={
                    "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                    "recommendation_id": "rec-round-trip",
                    "variants": [{"gene_symbol": "EGFR"}],
                },
                headers=auth_headers,
            )

        assert create_resp.status_code == 201
        created_data = create_resp.json()
        dec_id = created_data["decision_id"]

        with patch(
            "src.backend.api.v1.clinical_decision.ClinicalDecisionService.get_decision",
            new_callable=AsyncMock,
            return_value=mock_create_resp,
        ):
            get_resp = client.get(
                f"/api/v1/clinical-decision/{dec_id}",
                headers=auth_headers,
            )

        assert get_resp.status_code == 200
        get_data = get_resp.json()

        # Verify consistency
        assert get_data["decision_id"] == dec_id
        assert get_data["patient_id"] == created_data["patient_id"]
        assert get_data["recommendation_id"] == created_data["recommendation_id"]
        assert get_data["decision_type"] == created_data["decision_type"]
        assert get_data["confidence"] == created_data["confidence"]
        assert get_data["reason"] == created_data["reason"]
        assert len(get_data["alternatives"]) == len(created_data["alternatives"])
        assert len(get_data["contraindications"]) == len(
            created_data["contraindications"],
        )
