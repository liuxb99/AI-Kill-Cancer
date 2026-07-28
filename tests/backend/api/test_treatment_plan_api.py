"""
API tests for treatment plan endpoints (Phase 3E Batch 3).

Covers:
- POST   /api/v1/treatment-plans              — 201 (create)
- GET    /api/v1/treatment-plans/{plan_id}     — 200 (get by id)
- GET    /api/v1/treatment-plans               — 200 (list pagination)
- GET    /api/v1/treatment-plans/{plan_id}/versions — 200 (versions)
- GET    /api/v1/treatment-plans/{plan_id}/trace    — 200 (trace)
- POST   /api/v1/treatment-plans/{plan_id}/submit   — 200 (draft → proposed)
- POST   /api/v1/treatment-plans/{plan_id}/approve  — 200 (under_review → approved)
- POST   /api/v1/treatment-plans/{plan_id}/activate — 200 (approved → active)
- POST   /api/v1/treatment-plans/{plan_id}/pause    — 200 (active → paused)
- POST   /api/v1/treatment-plans/{plan_id}/complete — 200 (active → completed)
- POST   /api/v1/treatment-plans/{plan_id}/cancel   — 200 (any → cancelled)
- POST   /api/v1/treatment-plans/{plan_id}/revise   — 200 (superseded + new version)
- 401 (unauthorized)
- 403 (forbidden — role insufficient)
- 404 (plan not found)
- 409 (illegal transition)
- 422 (validation error)
- 500 (internal server error)
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Depends
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from src.backend.config import settings
from src.backend.domain.enums import Role
from src.backend.domain.user import UserModel
from src.backend.main import create_app
from src.backend.services.treatment_plan_service import (
    TreatmentPlanListItem,
    TreatmentPlanResponse,
)

# ─── Constants ─────────────────────────────────────────────────────────────────

BASE = "/api/v1/treatment-plans"
TEST_PATIENT = "550e8400-e29b-41d4-a716-446655440000"
TEST_PLAN_ID = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
CREATED_AT = datetime.now(UTC).isoformat()


# ─── Auth middleware ───────────────────────────────────────────────────────────


class _AuthMiddleware(BaseHTTPMiddleware):
    """Reject unauthenticated requests to treatment plan endpoints."""

    async def dispatch(self, request, call_next):
        if request.url.path.startswith(BASE):
            auth = request.headers.get("Authorization")
            if not auth:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authentication required"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
        return await call_next(request)


# ─── Mock user for dependency override ─────────────────────────────────────────


class _MockUser:
    """Minimal mock user that satisfies role checks."""
    def __init__(self, user_id: str = "admin-user", role: Role = Role.ADMIN):
        self.id = user_id
        self.role = role


async def _override_auth_with_admin() -> _MockUser:
    """Override require_auth to return an admin user (bypasses role checks)."""
    return _MockUser()


# ─── Mock builders ─────────────────────────────────────────────────────────────


def _make_response(
    plan_id: str = TEST_PLAN_ID,
    patient_id: str = TEST_PATIENT,
    plan_status: str = "draft",
    version: int = 1,
) -> TreatmentPlanResponse:
    """Build a synthetic TreatmentPlanResponse."""
    return TreatmentPlanResponse(
        plan_id=plan_id,
        version=version,
        patient_id=patient_id,
        recommendation_id="rec-001",
        clinical_decision_id="cd-001",
        consensus_id="con-001",
        plan_status=plan_status,
        plan_intent="curative",
        treatment_goals=["Reduce tumor burden"],
        summary="Treatment plan summary",
        clinical_rationale="Based on clinical evidence.",
        phases=[
            {
                "phase_id": "ph-001",
                "phase_order": 0,
                "phase_type": "induction",
                "name": "Induction",
                "description": "Initial treatment phase",
                "duration_days": 28,
                "status": "planned",
            },
        ],
        items=[
            {
                "item_id": "it-001",
                "item_order": 0,
                "item_type": "medication",
                "name": "Osimertinib",
                "description": "80mg daily",
                "priority": 1,
                "status": "planned",
                "rationale": "Targeted therapy",
            },
        ],
        monitoring=[
            {
                "monitoring_id": "mo-001",
                "monitoring_type": "lab_test",
                "name": "CBC",
                "schedule": "weekly",
                "baseline_required": True,
                "repeat_interval": 7,
            },
        ],
        safety_rules=[
            {
                "rule_id": "sr-001",
                "rule_type": "dose_adjustment",
                "condition": "neutrophils < 1.0",
                "severity": "high",
                "recommended_action": "Hold dose",
                "requires_review": True,
            },
        ],
        alternatives=[],
        trace=[
            {
                "trace_id": "tr-001",
                "step_order": 0,
                "step_type": "load_context",
                "input_summary": {},
                "output_summary": {},
            },
        ],
        is_current=True,
        previous_plan_id=None,
        supersedes_plan_id=None,
        revision_reason=None,
        created_by="user-001",
        approved_by=None,
        approved_at=None,
        activated_at=None,
        created_at=CREATED_AT,
    )


def _make_list_item() -> TreatmentPlanListItem:
    """Build a synthetic TreatmentPlanListItem."""
    return TreatmentPlanListItem(
        plan_id=TEST_PLAN_ID,
        version=1,
        patient_id=TEST_PATIENT,
        plan_status="draft",
        plan_intent="curative",
        is_current=True,
        created_at=CREATED_AT,
    )


# ─── Fixtures ──────────────────────────────────────────────────────────────────


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
        "username": "tp_user",
        "password": "TestPass123!",
        "display_name": "TP Tester",
    })
    resp = client.post("/auth/login", json={
        "username": "tp_user",
        "password": "TestPass123!",
    })
    return resp.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    """Headers with Bearer token for authenticated requests."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def admin_override_client(client):
    """Return the client with require_auth overridden to return admin user.

    This bypasses role checks so write-operation tests can focus on
    service-level behaviour.
    """
    from src.backend.auth.dependencies import require_auth
    client.app.dependency_overrides[require_auth] = _override_auth_with_admin
    yield client
    client.app.dependency_overrides.pop(require_auth, None)


@pytest.fixture
def admin_auth_headers(admin_override_client, auth_token):
    """Headers for admin-override requests."""
    return {"Authorization": f"Bearer {auth_token}"}


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/treatment-plans (A-01)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCreateTreatmentPlan:
    """Tests for POST /api/v1/treatment-plans."""

    CREATE_BODY = {
        "patient_id": TEST_PATIENT,
        "recommendation_id": "rec-001",
        "clinical_decision_id": "cd-001",
        "consensus_id": "con-001",
        "plan_intent": "curative",
        "treatment_goals": ["Reduce tumor burden"],
        "clinical_context": {"cancer_type": "NSCLC", "stage": "IV"},
        "monitoring_requirements": [],
    }

    def test_create_201(self, admin_override_client, admin_auth_headers) -> None:
        """POST with valid data should return 201."""
        mock_resp = _make_response()

        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.create_plan",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            resp = admin_override_client.post(
                BASE,
                json=self.CREATE_BODY,
                headers=admin_auth_headers,
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["plan_id"] == TEST_PLAN_ID
        assert data["patient_id"] == TEST_PATIENT
        assert data["plan_status"] == "draft"

    def test_create_unauthorized(self, client) -> None:
        """Request without auth token should return 401."""
        resp = client.post(BASE, json=self.CREATE_BODY)
        assert resp.status_code == 401

    def test_create_forbidden_for_viewer(self, client, auth_headers) -> None:
        """Viewer role should not be able to create (403)."""
        resp = client.post(
            BASE,
            json=self.CREATE_BODY,
            headers=auth_headers,
        )
        assert resp.status_code == 403

    def test_create_422_value_error(self, admin_override_client, admin_auth_headers) -> None:
        """Service ValueError should produce 422."""
        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.create_plan",
            new_callable=AsyncMock,
            side_effect=ValueError("Recommendation not found"),
        ):
            resp = admin_override_client.post(
                BASE,
                json=self.CREATE_BODY,
                headers=admin_auth_headers,
            )

        assert resp.status_code == 422
        assert "not found" in resp.json()["detail"]

    def test_create_500_runtime_error(self, admin_override_client, admin_auth_headers) -> None:
        """Service RuntimeError should produce 500 (detail hidden)."""
        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.create_plan",
            new_callable=AsyncMock,
            side_effect=RuntimeError("DB failure"),
        ):
            resp = admin_override_client.post(
                BASE,
                json=self.CREATE_BODY,
                headers=admin_auth_headers,
            )

        assert resp.status_code == 500
        detail = resp.json().get("detail", "")
        assert "Internal server error" in detail

    def test_create_500_generic_exception(self, admin_override_client, admin_auth_headers) -> None:
        """Unexpected exception should return 500 (detail hidden)."""
        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.create_plan",
            new_callable=AsyncMock,
            side_effect=Exception("Something unexpected"),
        ):
            resp = admin_override_client.post(
                BASE,
                json=self.CREATE_BODY,
                headers=admin_auth_headers,
            )

        assert resp.status_code == 500
        detail = resp.json().get("detail", "")
        assert "Internal server error" in detail


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/treatment-plans/{plan_id} (A-02)
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetTreatmentPlan:
    """Tests for GET /api/v1/treatment-plans/{plan_id}."""

    def test_get_200(self, client, auth_headers) -> None:
        """GET should return 200 with plan data."""
        mock_resp = _make_response()

        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.get_plan",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            resp = client.get(
                f"{BASE}/{TEST_PLAN_ID}",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["plan_id"] == TEST_PLAN_ID
        assert data["patient_id"] == TEST_PATIENT
        assert data["plan_status"] == "draft"

    def test_get_not_found(self, client, auth_headers) -> None:
        """Non-existent plan ID should return 404."""
        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.get_plan",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = client.get(
                f"{BASE}/nonexistent",
                headers=auth_headers,
            )

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_get_unauthorized(self, client) -> None:
        """GET without auth should return 401."""
        resp = client.get(f"{BASE}/{TEST_PLAN_ID}")
        assert resp.status_code == 401

    def test_get_500(self, client, auth_headers) -> None:
        """Internal errors on GET should return 500."""
        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.get_plan",
            new_callable=AsyncMock,
            side_effect=RuntimeError("DB error"),
        ):
            resp = client.get(
                f"{BASE}/{TEST_PLAN_ID}",
                headers=auth_headers,
            )

        assert resp.status_code == 500


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/treatment-plans (A-03)
# ═══════════════════════════════════════════════════════════════════════════════


class TestListTreatmentPlans:
    """Tests for GET /api/v1/treatment-plans (collection)."""

    def test_list_200_empty(self, client, auth_headers) -> None:
        """GET with no plans returns empty list."""
        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.list_plans",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = client.get(
                f"{BASE}?patient_id={TEST_PATIENT}",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_200_with_data(self, client, auth_headers) -> None:
        """GET returns list of plans."""
        mock_item = _make_list_item()

        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.list_plans",
            new_callable=AsyncMock,
            return_value=[mock_item],
        ):
            resp = client.get(
                f"{BASE}?patient_id={TEST_PATIENT}",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["plan_id"] == TEST_PLAN_ID
        assert data[0]["plan_status"] == "draft"

    def test_list_pagination(self, client, auth_headers) -> None:
        """Pagination parameters should be passed to service."""
        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.list_plans",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_list:
            client.get(
                f"{BASE}?patient_id={TEST_PATIENT}&skip=10&limit=5",
                headers=auth_headers,
            )

        mock_list.assert_called_once_with(
            patient_id=TEST_PATIENT,
            skip=10,
            limit=5,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/treatment-plans/{plan_id}/versions (A-04)
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetPlanVersions:
    """Tests for GET /api/v1/treatment-plans/{plan_id}/versions."""

    def test_versions_200(self, client, auth_headers) -> None:
        """GET versions returns list of plan versions."""
        mock_v1 = _make_response(plan_id=TEST_PLAN_ID, version=1)
        mock_v2 = _make_response(plan_id=TEST_PLAN_ID, version=2)

        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.get_versions",
            new_callable=AsyncMock,
            return_value=[mock_v1, mock_v2],
        ):
            resp = client.get(
                f"{BASE}/{TEST_PLAN_ID}/versions",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["version"] == 1
        assert data[1]["version"] == 2

    def test_versions_unauthorized(self, client) -> None:
        """Versions without auth should return 401."""
        resp = client.get(f"{BASE}/{TEST_PLAN_ID}/versions")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/treatment-plans/{plan_id}/trace (A-05)
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetPlanTrace:
    """Tests for GET /api/v1/treatment-plans/{plan_id}/trace."""

    def test_trace_200(self, client, auth_headers) -> None:
        """GET trace returns trace step list."""
        mock_trace = [
            {
                "trace_id": "tr-001",
                "step_order": 0,
                "step_type": "load_context",
                "input_summary": {},
                "output_summary": {},
                "rule_ids": None,
                "evidence_ids": None,
                "created_at": CREATED_AT,
            },
        ]

        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.get_trace",
            new_callable=AsyncMock,
            return_value=mock_trace,
        ):
            resp = client.get(
                f"{BASE}/{TEST_PLAN_ID}/trace",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["step_type"] == "load_context"

    def test_trace_empty(self, client, auth_headers) -> None:
        """GET trace returns empty list for no trace."""
        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.get_trace",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = client.get(
                f"{BASE}/{TEST_PLAN_ID}/trace",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json() == []


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/treatment-plans/{plan_id}/submit (A-06)
# ═══════════════════════════════════════════════════════════════════════════════


class TestSubmitPlan:
    """Tests for POST /api/v1/treatment-plans/{plan_id}/submit."""

    def test_submit_200(self, admin_override_client, admin_auth_headers) -> None:
        """Submit should return 200 with proposed status."""
        mock_resp = _make_response(plan_status="proposed")

        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.submit_plan",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            resp = admin_override_client.post(
                f"{BASE}/{TEST_PLAN_ID}/submit",
                headers=admin_auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json()["plan_status"] == "proposed"

    def test_submit_forbidden(self, client, auth_headers) -> None:
        """Viewer role should get 403 on submit."""
        resp = client.post(
            f"{BASE}/{TEST_PLAN_ID}/submit",
            headers=auth_headers,
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/treatment-plans/{plan_id}/review (A-06b)
# ═══════════════════════════════════════════════════════════════════════════════


class TestReviewPlan:
    """Tests for POST /api/v1/treatment-plans/{plan_id}/review."""

    def test_review_plan_success(self, admin_override_client, admin_auth_headers) -> None:
        """Review should return 200 with under_review status."""
        mock_resp = _make_response(plan_status="under_review")

        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.review_plan",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            resp = admin_override_client.post(
                f"{BASE}/{TEST_PLAN_ID}/review",
                headers=admin_auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json()["plan_status"] == "under_review"

    def test_review_plan_unauthorized(self, client) -> None:
        """Request without auth token should return 401."""
        resp = client.post(f"{BASE}/{TEST_PLAN_ID}/review")
        assert resp.status_code == 401

    def test_review_plan_forbidden(self, client, auth_headers) -> None:
        """Viewer role should get 403 on review."""
        resp = client.post(
            f"{BASE}/{TEST_PLAN_ID}/review",
            headers=auth_headers,
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/treatment-plans/{plan_id}/approve (A-07)
# ═══════════════════════════════════════════════════════════════════════════════


class TestApprovePlan:
    """Tests for POST /api/v1/treatment-plans/{plan_id}/approve."""

    def test_approve_200(self, admin_override_client, admin_auth_headers) -> None:
        """Approve should return 200 with approved status."""
        mock_resp = _make_response(plan_status="approved")

        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.approve_plan",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            resp = admin_override_client.post(
                f"{BASE}/{TEST_PLAN_ID}/approve",
                headers=admin_auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json()["plan_status"] == "approved"

    def test_approve_forbidden(self, client, auth_headers) -> None:
        """Viewer role should get 403 on approve."""
        resp = client.post(
            f"{BASE}/{TEST_PLAN_ID}/approve",
            headers=auth_headers,
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/treatment-plans/{plan_id}/activate (A-08)
# ═══════════════════════════════════════════════════════════════════════════════


class TestActivatePlan:
    """Tests for POST /api/v1/treatment-plans/{plan_id}/activate."""

    def test_activate_200(self, admin_override_client, admin_auth_headers) -> None:
        """Activate should return 200 with active status."""
        mock_resp = _make_response(plan_status="active")

        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.activate_plan",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            resp = admin_override_client.post(
                f"{BASE}/{TEST_PLAN_ID}/activate",
                headers=admin_auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json()["plan_status"] == "active"


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/treatment-plans/{plan_id}/pause (A-09)
# ═══════════════════════════════════════════════════════════════════════════════


class TestPausePlan:
    """Tests for POST /api/v1/treatment-plans/{plan_id}/pause."""

    def test_pause_200(self, admin_override_client, admin_auth_headers) -> None:
        """Pause should return 200 with paused status."""
        mock_resp = _make_response(plan_status="paused")

        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.pause_plan",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            resp = admin_override_client.post(
                f"{BASE}/{TEST_PLAN_ID}/pause",
                headers=admin_auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json()["plan_status"] == "paused"


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/treatment-plans/{plan_id}/complete (A-10)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCompletePlan:
    """Tests for POST /api/v1/treatment-plans/{plan_id}/complete."""

    def test_complete_200(self, admin_override_client, admin_auth_headers) -> None:
        """Complete should return 200 with completed status."""
        mock_resp = _make_response(plan_status="completed")

        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.complete_plan",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            resp = admin_override_client.post(
                f"{BASE}/{TEST_PLAN_ID}/complete",
                headers=admin_auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json()["plan_status"] == "completed"


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/treatment-plans/{plan_id}/cancel (A-11)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCancelPlan:
    """Tests for POST /api/v1/treatment-plans/{plan_id}/cancel."""

    def test_cancel_200(self, admin_override_client, admin_auth_headers) -> None:
        """Cancel should return 200 with cancelled status."""
        mock_resp = _make_response(plan_status="cancelled")

        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.cancel_plan",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            resp = admin_override_client.post(
                f"{BASE}/{TEST_PLAN_ID}/cancel",
                headers=admin_auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json()["plan_status"] == "cancelled"


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/treatment-plans/{plan_id}/revise (A-12)
# ═══════════════════════════════════════════════════════════════════════════════


class TestRevisePlan:
    """Tests for POST /api/v1/treatment-plans/{plan_id}/revise."""

    REVISE_BODY = {
        "patient_id": TEST_PATIENT,
        "recommendation_id": "rec-001",
        "clinical_decision_id": "cd-001",
        "consensus_id": "con-001",
        "plan_intent": "curative",
        "treatment_goals": ["Reduce tumor burden", "Improve QoL"],
        "clinical_context": {"cancer_type": "NSCLC", "revision_reason": "Updated evidence"},
        "monitoring_requirements": [],
    }

    def test_revise_200(self, admin_override_client, admin_auth_headers) -> None:
        """Revise should return 200 with new version."""
        mock_resp = _make_response(
            plan_id=TEST_PLAN_ID,
            version=2,
            plan_status="draft",
        )

        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.revise_plan",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            resp = admin_override_client.post(
                f"{BASE}/{TEST_PLAN_ID}/revise",
                json=self.REVISE_BODY,
                headers=admin_auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == 2
        assert "draft" in data["plan_status"]


# ═══════════════════════════════════════════════════════════════════════════════
# Error scenario tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestErrorScenarios:
    """Cross-cutting error scenarios."""

    def test_404_not_found_on_status_op(self, admin_override_client, admin_auth_headers) -> None:
        """Status operation on non-existent plan should return 422 (ValueError)."""
        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.submit_plan",
            new_callable=AsyncMock,
            side_effect=ValueError("Treatment plan with id 'nonexistent' not found"),
        ):
            resp = admin_override_client.post(
                f"{BASE}/nonexistent/submit",
                headers=admin_auth_headers,
            )

        # ValueError from service maps to 422
        assert resp.status_code == 422
        assert "not found" in resp.json()["detail"]

    def test_409_illegal_transition(self, admin_override_client, admin_auth_headers) -> None:
        """Illegal state transition should return 409."""
        from src.backend.clinical.treatment_plan_state_machine import IllegalTransitionError

        with patch(
            "src.backend.api.v1.treatment_plans.TreatmentPlanService.approve_plan",
            new_callable=AsyncMock,
            side_effect=IllegalTransitionError(
                current="draft", target="approved",
            ),
        ):
            resp = admin_override_client.post(
                f"{BASE}/{TEST_PLAN_ID}/approve",
                headers=admin_auth_headers,
            )

        assert resp.status_code == 409
        assert "Cannot transition" in resp.json()["detail"]

    def test_422_validation_error_create(self, admin_override_client, admin_auth_headers) -> None:
        """Missing required fields should return 422."""
        resp = admin_override_client.post(
            BASE,
            json={"patient_id": TEST_PATIENT},  # Missing many required fields
            headers=admin_auth_headers,
        )

        assert resp.status_code == 422
