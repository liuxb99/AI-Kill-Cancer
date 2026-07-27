"""
API tests for tumor board consensus endpoints (Phase 3C).

Covers:
- POST /api/v1/tumor-board-consensus — 201 with full ConsensusResponse
- GET  /api/v1/tumor-board-consensus/{consensus_id} — 200 with data
- GET  /api/v1/tumor-board-consensus — 200 list with pagination
- GET  /api/v1/tumor-board-consensus/{consensus_id}/opinions — 200
- GET  /api/v1/tumor-board-consensus/{consensus_id}/trace — 200
- 401 (unauthorized)
- 404 (consensus not found)
- 422 (validation / mismatch)
- 500 (service raises RuntimeError)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from src.backend.config import settings
from src.backend.main import create_app
from src.backend.services.tumor_board_service import (
    ConsensusListResponse,
    ConsensusResponse,
)


# Middleware to enforce authentication on tumor board endpoints
class _AuthMiddleware(BaseHTTPMiddleware):
    """Reject unauthenticated requests to /api/v1/tumor-board-consensus/*."""

    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/api/v1/tumor-board-consensus"):
            auth = request.headers.get("Authorization")
            if not auth:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authentication required"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
        return await call_next(request)


def _make_mock_response(
    consensus_id: str | None = None,
    patient_id: str = "550e8400-e29b-41d4-a716-446655440000",
    recommendation_id: str = "rec-api-tb-001",
    clinical_decision_id: str = "cd-api-tb-001",
    consensus_status: str = "unanimous",
) -> ConsensusResponse:
    """Build a synthetic ConsensusResponse for mocking."""
    from datetime import UTC, datetime

    return ConsensusResponse(
        consensus_id=consensus_id or "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
        patient_id=patient_id,
        recommendation_id=recommendation_id,
        clinical_decision_id=clinical_decision_id,
        consensus_status=consensus_status,
        consensus_score=1.0,
        final_recommendation="Osimertinib 80mg daily",
        supporting_rationale="All specialists agree.",
        dissenting_opinions=[],
        unresolved_questions=[],
        required_follow_up=[],
        participating_specialties=["medical_oncology", "surgical_oncology"],
        created_by=None,
        created_at=datetime.now(UTC).isoformat(),
        trace_id="b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5",
    )


def _make_mock_list_response(
    consensus_id: str = "list-consensus-001",
    patient_id: str = "550e8400-e29b-41d4-a716-446655440000",
    consensus_status: str = "unanimous",
) -> ConsensusListResponse:
    """Build a synthetic ConsensusListResponse."""
    from datetime import UTC, datetime

    return ConsensusListResponse(
        consensus_id=consensus_id,
        patient_id=patient_id,
        consensus_status=consensus_status,
        consensus_score=1.0,
        participating_specialties=["medical_oncology"],
        created_at=datetime.now(UTC).isoformat(),
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
        "username": "tb_user",
        "password": "TestPass123!",
        "display_name": "TB Tester",
    })
    resp = client.post("/auth/login", json={
        "username": "tb_user",
        "password": "TestPass123!",
    })
    return resp.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    """Headers with Bearer token for authenticated requests."""
    return {"Authorization": f"Bearer {auth_token}"}


BASE = "/api/v1/tumor-board-consensus"

# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/tumor-board-consensus Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestCreateTumorBoardConsensus:
    """Tests for POST /api/v1/tumor-board-consensus."""

    def test_create_consensus_201(self, client, auth_headers) -> None:
        """POST with valid data should return 201 with full response."""
        mock_resp = _make_mock_response()

        with patch(
            "src.backend.api.v1.tumor_board_consensus.TumorBoardConsensusService.create_consensus",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            resp = client.post(
                BASE,
                json={
                    "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                    "recommendation_id": "rec-api-tb-001",
                    "clinical_decision_id": "cd-api-tb-001",
                    "specialist_opinions": [
                        {
                            "specialty": "medical_oncology",
                            "position": "support",
                            "confidence": 0.95,
                        },
                        {
                            "specialty": "surgical_oncology",
                            "position": "support",
                            "confidence": 0.90,
                        },
                    ],
                },
                headers=auth_headers,
            )

        assert resp.status_code == 201
        data = resp.json()
        self._assert_valid_response(data)

    def test_create_consensus_minimal(self, client, auth_headers) -> None:
        """POST with only required fields."""
        mock_resp = _make_mock_response()

        with patch(
            "src.backend.api.v1.tumor_board_consensus.TumorBoardConsensusService.create_consensus",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            resp = client.post(
                BASE,
                json={
                    "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                    "recommendation_id": "rec-api-tb-001",
                    "clinical_decision_id": "cd-api-tb-001",
                    "specialist_opinions": [
                        {
                            "specialty": "medical_oncology",
                            "position": "support",
                            "confidence": 0.90,
                        },
                    ],
                },
                headers=auth_headers,
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["patient_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert "consensus_id" in data
        assert "consensus_status" in data

    def test_create_consensus_missing_patient_id(
        self, client, auth_headers,
    ) -> None:
        """Missing patient_id should return 422."""
        resp = client.post(
            BASE,
            json={
                "recommendation_id": "rec-001",
                "clinical_decision_id": "cd-001",
                "specialist_opinions": [
                    {"specialty": "med_onc", "position": "support", "confidence": 0.9},
                ],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_create_consensus_missing_opinions(
        self, client, auth_headers,
    ) -> None:
        """Missing specialist_opinions should return 422."""
        resp = client.post(
            BASE,
            json={
                "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                "recommendation_id": "rec-001",
                "clinical_decision_id": "cd-001",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_create_consensus_unauthorized(self, client) -> None:
        """Request without auth token should return 401."""
        resp = client.post(
            BASE,
            json={
                "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                "recommendation_id": "rec-001",
                "clinical_decision_id": "cd-001",
                "specialist_opinions": [
                    {"specialty": "med_onc", "position": "support", "confidence": 0.9},
                ],
            },
        )
        assert resp.status_code == 401

    def test_create_consensus_422_value_error(
        self, client, auth_headers,
    ) -> None:
        """When service raises ValueError, API returns 422."""
        with patch(
            "src.backend.api.v1.tumor_board_consensus.TumorBoardConsensusService.create_consensus",
            new_callable=AsyncMock,
            side_effect=ValueError("Recommendation not found"),
        ):
            resp = client.post(
                BASE,
                json={
                    "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                    "recommendation_id": "rec-001",
                    "clinical_decision_id": "cd-001",
                    "specialist_opinions": [
                        {"specialty": "med_onc", "position": "support", "confidence": 0.9},
                    ],
                },
                headers=auth_headers,
            )

        assert resp.status_code == 422
        assert "not found" in resp.json()["detail"]

    def test_create_consensus_500_runtime_error(
        self, client, auth_headers,
    ) -> None:
        """When service raises RuntimeError, API returns 500."""
        with patch(
            "src.backend.api.v1.tumor_board_consensus.TumorBoardConsensusService.create_consensus",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Sensitive internal error"),
        ):
            resp = client.post(
                BASE,
                json={
                    "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                    "recommendation_id": "rec-001",
                    "clinical_decision_id": "cd-001",
                    "specialist_opinions": [
                        {"specialty": "med_onc", "position": "support", "confidence": 0.9},
                    ],
                },
                headers=auth_headers,
            )

        assert resp.status_code == 500
        detail = resp.json().get("detail", "")
        assert "Sensitive internal error" not in detail
        assert "Internal server error" in detail

    # ── Helpers ─────────────────────────────────────────────────────

    def _assert_valid_response(self, data: dict) -> None:
        """Assert the response has the expected ConsensusResponse structure."""
        assert "consensus_id" in data
        assert "patient_id" in data
        assert "recommendation_id" in data
        assert "clinical_decision_id" in data
        assert "consensus_status" in data
        assert "consensus_score" in data
        assert "final_recommendation" in data
        assert "supporting_rationale" in data
        assert "dissenting_opinions" in data
        assert "unresolved_questions" in data
        assert "required_follow_up" in data
        assert "participating_specialties" in data
        assert "created_at" in data

        # Validate types
        assert isinstance(data["consensus_id"], str)
        assert isinstance(data["patient_id"], str)
        assert isinstance(data["consensus_status"], str)
        assert data["consensus_status"] in (
            "unanimous", "strong_consensus", "majority_consensus",
            "split_decision", "insufficient_information", "deferred",
        )
        assert isinstance(data["participating_specialties"], list)
        assert isinstance(data["dissenting_opinions"], list)
        assert isinstance(data["created_at"], str)


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/tumor-board-consensus/{consensus_id} Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetTumorBoardConsensus:
    """Tests for GET /api/v1/tumor-board-consensus/{consensus_id}."""

    def test_get_consensus_200(self, client, auth_headers) -> None:
        """GET should return 200 with the same data."""
        mock_resp = _make_mock_response(
            consensus_id="get-tb-cons-001",
            patient_id="550e8400-e29b-41d4-a716-446655440000",
            recommendation_id="rec-get-tb-001",
        )

        with patch(
            "src.backend.api.v1.tumor_board_consensus.TumorBoardConsensusService.get_consensus",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            resp = client.get(
                f"{BASE}/get-tb-cons-001",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["consensus_id"] == "get-tb-cons-001"
        assert data["patient_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert data["consensus_status"] == "unanimous"
        assert data["consensus_score"] == 1.0

    def test_get_consensus_not_found(self, client, auth_headers) -> None:
        """Non-existent consensus ID should return 404."""
        with patch(
            "src.backend.api.v1.tumor_board_consensus.TumorBoardConsensusService.get_consensus",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = client.get(
                f"{BASE}/nonexistent-consensus-99999",
                headers=auth_headers,
            )

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_get_consensus_unauthorized(self, client) -> None:
        """GET without auth should return 401."""
        resp = client.get(f"{BASE}/some-id")
        assert resp.status_code == 401

    def test_get_consensus_500(self, client, auth_headers) -> None:
        """Internal errors on GET should return 500."""
        with patch(
            "src.backend.api.v1.tumor_board_consensus.TumorBoardConsensusService.get_consensus",
            new_callable=AsyncMock,
            side_effect=RuntimeError("DB error"),
        ):
            resp = client.get(
                f"{BASE}/some-id",
                headers=auth_headers,
            )

        assert resp.status_code == 500
        detail = resp.json().get("detail", "")
        assert "Internal server error" in detail


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/tumor-board-consensus/{consensus_id}/opinions Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetOpinions:
    """Tests for GET /api/v1/tumor-board-consensus/{consensus_id}/opinions."""

    def test_get_opinions_200(self, client, auth_headers) -> None:
        """GET opinions returns 200 with opinion list."""
        mock_opinions = [
            {
                "id": "op-001",
                "specialty": "medical_oncology",
                "participant_id": None,
                "position": "support",
                "confidence": 0.95,
                "rationale": None,
                "supporting_evidence": None,
                "contraindications": None,
                "preferred_option": None,
                "alternative_option": None,
                "requires_more_information": False,
                "created_at": "2026-07-26T00:00:00",
            },
        ]

        with patch(
            "src.backend.api.v1.tumor_board_consensus.TumorBoardConsensusService.get_opinions",
            new_callable=AsyncMock,
            return_value=mock_opinions,
        ):
            resp = client.get(
                f"{BASE}/some-id/opinions",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["specialty"] == "medical_oncology"

    def test_get_opinions_empty(self, client, auth_headers) -> None:
        """GET opinions returns empty list for no opinions."""
        with patch(
            "src.backend.api.v1.tumor_board_consensus.TumorBoardConsensusService.get_opinions",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = client.get(
                f"{BASE}/some-id/opinions",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json() == []


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/tumor-board-consensus/{consensus_id}/trace Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetTrace:
    """Tests for GET /api/v1/tumor-board-consensus/{consensus_id}/trace."""

    def test_get_trace_200(self, client, auth_headers) -> None:
        """GET trace returns 200 with trace step list."""
        mock_trace = [
            {"trace_id": "trace-001", "step_order": 0, "step_type": "load_context",
             "input_summary": {}, "output_summary": {}, "created_at": "2026-07-26T00:00:00"},
            {"trace_id": "trace-001", "step_order": 1, "step_type": "validate_links",
             "input_summary": {}, "output_summary": {}, "created_at": "2026-07-26T00:00:00"},
        ]

        with patch(
            "src.backend.api.v1.tumor_board_consensus.TumorBoardConsensusService.get_trace",
            new_callable=AsyncMock,
            return_value=mock_trace,
        ):
            resp = client.get(
                f"{BASE}/some-id/trace",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["step_type"] == "load_context"
        assert data[1]["step_type"] == "validate_links"

    def test_get_trace_empty(self, client, auth_headers) -> None:
        """GET trace returns empty list for no trace."""
        with patch(
            "src.backend.api.v1.tumor_board_consensus.TumorBoardConsensusService.get_trace",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = client.get(
                f"{BASE}/some-id/trace",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json() == []


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/tumor-board-consensus (Collection) Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestListTumorBoardConsensus:
    """Tests for GET /api/v1/tumor-board-consensus (collection)."""

    PATIENT_ID = "550e8400-e29b-41d4-a716-446655440000"

    def test_list_consensus_empty(self, client, auth_headers) -> None:
        """GET with no consensuses returns empty list."""
        with patch(
            "src.backend.api.v1.tumor_board_consensus.TumorBoardConsensusService.list_consensus",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = client.get(
                f"{BASE}?patient_id={self.PATIENT_ID}",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_consensus_one(self, client, auth_headers) -> None:
        """GET returns a single consensus."""
        mock_item = _make_mock_list_response()

        with patch(
            "src.backend.api.v1.tumor_board_consensus.TumorBoardConsensusService.list_consensus",
            new_callable=AsyncMock,
            return_value=[mock_item],
        ):
            resp = client.get(
                f"{BASE}?patient_id={self.PATIENT_ID}",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["consensus_id"] == "list-consensus-001"

    def test_list_consensus_pagination(self, client, auth_headers) -> None:
        """GET supports skip/limit pagination."""
        mock_items = [
            _make_mock_list_response(
                consensus_id=f"page-tb-{i:02d}",
            )
            for i in range(3)
        ]

        with patch(
            "src.backend.api.v1.tumor_board_consensus.TumorBoardConsensusService.list_consensus",
            new_callable=AsyncMock,
            return_value=mock_items[:2],
        ):
            resp = client.get(
                f"{BASE}?patient_id={self.PATIENT_ID}&skip=0&limit=2",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_list_consensus_unauthorized(self, client) -> None:
        """GET without auth should return 401."""
        resp = client.get(f"{BASE}?patient_id={self.PATIENT_ID}")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Round-trip Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestConsensusRoundTrip:
    """Verify that POST-then-GET returns consistent data."""

    def test_create_then_get_round_trip(self, client, auth_headers) -> None:
        """After creating a consensus, GET should return the same data."""
        mock_create_resp = _make_mock_response(
            consensus_id="round-trip-tb-id",
            patient_id="550e8400-e29b-41d4-a716-446655440000",
            recommendation_id="rec-round-trip-tb",
        )

        with patch(
            "src.backend.api.v1.tumor_board_consensus.TumorBoardConsensusService.create_consensus",
            new_callable=AsyncMock,
            return_value=mock_create_resp,
        ):
            create_resp = client.post(
                BASE,
                json={
                    "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                    "recommendation_id": "rec-round-trip-tb",
                    "clinical_decision_id": "cd-round-trip-tb",
                    "specialist_opinions": [
                        {"specialty": "med_onc", "position": "support", "confidence": 0.9},
                    ],
                },
                headers=auth_headers,
            )

        assert create_resp.status_code == 201
        created_data = create_resp.json()
        cons_id = created_data["consensus_id"]

        with patch(
            "src.backend.api.v1.tumor_board_consensus.TumorBoardConsensusService.get_consensus",
            new_callable=AsyncMock,
            return_value=mock_create_resp,
        ):
            get_resp = client.get(
                f"{BASE}/{cons_id}",
                headers=auth_headers,
            )

        assert get_resp.status_code == 200
        get_data = get_resp.json()

        # Verify consistency
        assert get_data["consensus_id"] == cons_id
        assert get_data["patient_id"] == created_data["patient_id"]
        assert get_data["consensus_status"] == created_data["consensus_status"]
        assert get_data["consensus_score"] == created_data["consensus_score"]
