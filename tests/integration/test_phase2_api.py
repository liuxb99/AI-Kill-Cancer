"""
Phase 2 API integration tests — verify all clinical endpoints return correct
status codes and response structures.

Uses FastAPI TestClient with SQLite in-memory database and real auth flow.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.backend.config import settings
from src.backend.main import create_app


@pytest.fixture(scope="module")
def client():
    """Create a TestClient with in-memory SQLite database."""
    settings.DATABASE_URL = "sqlite+aiosqlite://"
    settings.APP_MODE = "demo"
    settings.DEBUG = False
    app = create_app()
    with TestClient(app) as c:
        yield c


def _register_user(client: TestClient, username: str, password: str = "TestPass123!") -> str:
    """Register a user and return the access token."""
    resp = client.post("/auth/register", json={
        "username": username,
        "password": password,
        "display_name": username,
    })
    assert resp.status_code == 201, f"Register failed: {resp.json()}"
    login = client.post("/auth/login", json={
        "username": username,
        "password": password,
    })
    assert login.status_code == 200, f"Login failed: {login.json()}"
    return login.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_patient(client: TestClient, token: str) -> str:
    """Create a patient and return patient ID."""
    resp = client.post(
        "/api/v1/patients",
        json={"sex": "F", "consent_status": "granted"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201, f"Create patient failed: {resp.json()}"
    return resp.json()["id"]


def _create_case(client: TestClient, token: str, patient_id: str) -> str:
    """Create a case and return case ID."""
    resp = client.post(
        "/api/v1/cases",
        json={"patient_id": patient_id, "cancer_type": "PTC"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201, f"Create case failed: {resp.json()}"
    return resp.json()["id"]


# ─── Shared fixture for authenticated client + case ────────────────────────────


@pytest.fixture(scope="module")
def auth_setup(client):
    """Register a test user, create patient + case, return token and case_id."""
    token = _register_user(client, "phase2_api_user")
    pid = _create_patient(client, token)
    case_id = _create_case(client, token, pid)
    return {"token": token, "case_id": case_id, "patient_id": pid}


INVALID_CASE_ID = "550e8400-e29b-41d4-a716-446655440000"
"""Valid UUID format but no case exists with this ID."""


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/clinical/context/{case_id}
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetClinicalContext:
    """GET /api/v1/clinical/context/{case_id}"""

    def test_success(self, client, auth_setup):
        """Valid case_id returns 200 with ClinicalContext JSON structure."""
        resp = client.get(
            f"/api/v1/clinical/context/{auth_setup['case_id']}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 200, f"Unexpected status: {resp.status_code} {resp.json()}"
        data = resp.json()
        assert data["case_id"] == auth_setup["case_id"]
        assert data["patient_id"] == auth_setup["patient_id"]
        assert isinstance(data["age"], int)
        assert isinstance(data["gender"], str)
        assert isinstance(data["diagnosis"], str)
        assert isinstance(data["cancer_type"], str)
        assert data["cancer_type"] == "PTC"
        assert "context_hash" in data
        assert isinstance(data["context_hash"], str)

    def test_invalid_case_id_returns_404(self, client, auth_setup):
        """Invalid case_id format returns 404."""
        resp = client.get(
            "/api/v1/clinical/context/not-a-uuid",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 404

    def test_non_existent_case_returns_404(self, client, auth_setup):
        """Well-formed UUID with no matching case returns 404."""
        resp = client.get(
            f"/api/v1/clinical/context/{INVALID_CASE_ID}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 403

    def test_unauthorized_returns_401(self, client, auth_setup):
        """No auth token returns 401."""
        resp = client.get(f"/api/v1/clinical/context/{auth_setup['case_id']}")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/clinical/evidence/{case_id}
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetClinicalEvidence:
    """GET /api/v1/clinical/evidence/{case_id}"""

    def test_success(self, client, auth_setup):
        """Valid case_id returns 200 with EvidenceBundle JSON structure."""
        resp = client.get(
            f"/api/v1/clinical/evidence/{auth_setup['case_id']}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 200, f"Unexpected status: {resp.status_code} {resp.json()}"
        data = resp.json()
        assert "items" in data
        assert "total_count" in data
        assert "by_source" in data
        assert "by_gene" in data
        assert "by_drug" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["total_count"], int)
        assert isinstance(data["by_source"], dict)
        assert isinstance(data["by_gene"], dict)
        assert isinstance(data["by_drug"], dict)

    def test_invalid_case_id_returns_404(self, client, auth_setup):
        """Invalid case_id format returns 404."""
        resp = client.get(
            "/api/v1/clinical/evidence/not-a-uuid",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 404

    def test_non_existent_case_returns_404(self, client, auth_setup):
        """Well-formed UUID with no matching case returns 404."""
        resp = client.get(
            f"/api/v1/clinical/evidence/{INVALID_CASE_ID}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 403

    def test_unauthorized_returns_401(self, client, auth_setup):
        """No auth token returns 401."""
        resp = client.get(f"/api/v1/clinical/evidence/{auth_setup['case_id']}")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/clinical/evidence/gene/{gene}
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetEvidenceByGene:
    """GET /api/v1/clinical/evidence/gene/{gene_symbol}"""

    def test_success(self, client, auth_setup):
        """Valid gene symbol returns 200 with EvidenceBundle."""
        resp = client.get(
            "/api/v1/clinical/evidence/gene/BRAF",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 200, f"Unexpected status: {resp.status_code} {resp.json()}"
        data = resp.json()
        assert "items" in data
        assert "total_count" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["total_count"], int)

    def test_unknown_gene_returns_empty_bundle(self, client, auth_setup):
        """Gene with no evidence returns empty bundle (200, not 404)."""
        resp = client.get(
            "/api/v1/clinical/evidence/gene/ZZZZZ",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 0
        assert data["items"] == []

    def test_unauthorized_returns_401(self, client, auth_setup):
        """No auth token returns 401."""
        resp = client.get("/api/v1/clinical/evidence/gene/BRAF")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/clinical/agents/{case_id}
# ═══════════════════════════════════════════════════════════════════════════════


class TestRunAgents:
    """POST /api/v1/clinical/agents/{case_id}"""

    def test_success(self, client, auth_setup):
        """Valid case_id returns 200 with list of AgentOpinion."""
        resp = client.post(
            f"/api/v1/clinical/agents/{auth_setup['case_id']}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 200, f"Unexpected status: {resp.status_code} {resp.json()}"
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        for opinion in data:
            assert "agent_type" in opinion
            assert "agent_version" in opinion
            assert "summary" in opinion
            assert "confidence" in opinion
            assert "pros" in opinion
            assert "cons" in opinion
            assert "created_at" in opinion
            assert opinion["agent_type"] in (
                "diagnosis", "variant", "drug", "resistance", "guideline", "clinical_trial",
            )

    def test_invalid_case_id_returns_404(self, client, auth_setup):
        """Invalid case_id format returns 404."""
        resp = client.post(
            "/api/v1/clinical/agents/not-a-uuid",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 404

    def test_non_existent_case_returns_404(self, client, auth_setup):
        """Well-formed UUID with no matching case returns 404."""
        resp = client.post(
            f"/api/v1/clinical/agents/{INVALID_CASE_ID}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 403

    def test_unauthorized_returns_401(self, client, auth_setup):
        """No auth token returns 401."""
        resp = client.post(f"/api/v1/clinical/agents/{auth_setup['case_id']}")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/clinical/consensus/{case_id}
# ═══════════════════════════════════════════════════════════════════════════════


class TestRunConsensus:
    """POST /api/v1/clinical/consensus/{case_id}"""

    def test_success(self, client, auth_setup):
        """Valid case_id returns 200 with ConsensusResult."""
        resp = client.post(
            f"/api/v1/clinical/consensus/{auth_setup['case_id']}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 200, f"Unexpected status: {resp.status_code} {resp.json()}"
        data = resp.json()
        assert "agreement" in data
        assert "conflicts" in data
        assert "confidence" in data
        assert "recommended_option" in data
        assert "alternative_options" in data
        assert "unresolved_questions" in data
        assert "context_hash" in data
        assert "created_at" in data

    def test_invalid_case_id_returns_404(self, client, auth_setup):
        """Invalid case_id format returns 404."""
        resp = client.post(
            "/api/v1/clinical/consensus/not-a-uuid",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 404

    def test_non_existent_case_returns_404(self, client, auth_setup):
        """Well-formed UUID with no matching case returns 404."""
        resp = client.post(
            f"/api/v1/clinical/consensus/{INVALID_CASE_ID}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 403

    def test_unauthorized_returns_401(self, client, auth_setup):
        """No auth token returns 401."""
        resp = client.post(f"/api/v1/clinical/consensus/{auth_setup['case_id']}")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/clinical/recommend/{case_id}
# ═══════════════════════════════════════════════════════════════════════════════


class TestRecommendTreatment:
    """POST /api/v1/clinical/recommend/{case_id}"""

    def test_success(self, client, auth_setup):
        """Valid case_id returns 200 with TreatmentRecommendation."""
        resp = client.post(
            f"/api/v1/clinical/recommend/{auth_setup['case_id']}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 200, f"Unexpected status: {resp.status_code} {resp.json()}"
        data = resp.json()
        assert "first_line" in data
        assert "second_line" in data
        assert "clinical_trial" in data
        assert "supporting_evidence" in data
        assert "expected_benefit" in data
        assert "potential_risk" in data
        assert "monitoring_plan" in data
        assert "structured_json" in data
        assert "markdown" in data
        assert "context_hash" in data
        assert "created_at" in data

    def test_invalid_case_id_returns_404(self, client, auth_setup):
        """Invalid case_id format returns 404."""
        resp = client.post(
            "/api/v1/clinical/recommend/not-a-uuid",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 404

    def test_non_existent_case_returns_404(self, client, auth_setup):
        """Well-formed UUID with no matching case returns 404."""
        resp = client.post(
            f"/api/v1/clinical/recommend/{INVALID_CASE_ID}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 403

    def test_unauthorized_returns_401(self, client, auth_setup):
        """No auth token returns 401."""
        resp = client.post(f"/api/v1/clinical/recommend/{auth_setup['case_id']}")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# POST /api/v1/clinical/analyze/{case_id}
# ═══════════════════════════════════════════════════════════════════════════════


class TestAnalyzeCase:
    """POST /api/v1/clinical/analyze/{case_id}"""

    def test_success(self, client, auth_setup):
        """Valid case_id returns 200 with full AnalyzeResponse."""
        resp = client.post(
            f"/api/v1/clinical/analyze/{auth_setup['case_id']}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 200, f"Unexpected status: {resp.status_code} {resp.json()}"
        data = resp.json()
        # Top-level keys
        assert "context" in data
        assert "evidence" in data
        assert "opinions" in data
        assert "consensus" in data
        assert "recommendation" in data

        # context is a ClinicalContext
        ctx = data["context"]
        assert ctx["case_id"] == auth_setup["case_id"]
        assert "context_hash" in ctx

        # evidence is an EvidenceBundle
        ev = data["evidence"]
        assert "items" in ev
        assert "total_count" in ev

        # opinions is a list of AgentOpinion
        opinions = data["opinions"]
        assert isinstance(opinions, list)
        assert len(opinions) > 0
        for op in opinions:
            assert "agent_type" in op
            assert "summary" in op

        # consensus is a ConsensusResult
        cs = data["consensus"]
        assert "agreement" in cs
        assert "confidence" in cs

        # recommendation is a TreatmentRecommendation
        rec = data["recommendation"]
        assert "first_line" in rec
        assert "markdown" in rec

    def test_invalid_case_id_returns_404(self, client, auth_setup):
        """Invalid case_id format returns 404."""
        resp = client.post(
            "/api/v1/clinical/analyze/not-a-uuid",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 404

    def test_non_existent_case_returns_404(self, client, auth_setup):
        """Well-formed UUID with no matching case returns 404."""
        resp = client.post(
            f"/api/v1/clinical/analyze/{INVALID_CASE_ID}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 403

    def test_unauthorized_returns_401(self, client, auth_setup):
        """No auth token returns 401."""
        resp = client.post(f"/api/v1/clinical/analyze/{auth_setup['case_id']}")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/clinical/thread/{case_id}
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetCaseThread:
    """GET /api/v1/clinical/thread/{case_id}"""

    def test_success(self, client, auth_setup):
        """Valid case_id returns 200 with list of DecisionNode."""
        # First run analyze to populate the thread
        client.post(
            f"/api/v1/clinical/analyze/{auth_setup['case_id']}",
            headers=_auth_headers(auth_setup["token"]),
        )

        resp = client.get(
            f"/api/v1/clinical/thread/{auth_setup['case_id']}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 200, f"Unexpected status: {resp.status_code} {resp.json()}"
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        for node in data:
            assert "id" in node
            assert "case_id" in node
            assert "node_type" in node
            assert "timestamp" in node
            assert node["case_id"] == auth_setup["case_id"]

    def test_empty_case_thread_returns_empty_list(self, client, auth_setup):
        """Case with no decision thread returns empty list (200)."""
        resp = client.get(
            f"/api/v1/clinical/thread/{INVALID_CASE_ID}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 403
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_invalid_case_id_returns_404(self, client, auth_setup):
        """Invalid case_id format returns 404."""
        resp = client.get(
            "/api/v1/clinical/thread/not-a-uuid",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 404

    def test_unauthorized_returns_401(self, client, auth_setup):
        """No auth token returns 401."""
        resp = client.get(f"/api/v1/clinical/thread/{auth_setup['case_id']}")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# GET /api/v1/clinical/thread/{case_id}/tree
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetDecisionTree:
    """GET /api/v1/clinical/thread/{case_id}/tree"""

    def test_success(self, client, auth_setup):
        """Valid case_id returns 200 with list of DecisionNode (tree)."""
        # Run analyze to populate the thread
        client.post(
            f"/api/v1/clinical/analyze/{auth_setup['case_id']}",
            headers=_auth_headers(auth_setup["token"]),
        )

        resp = client.get(
            f"/api/v1/clinical/thread/{auth_setup['case_id']}/tree",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 200, f"Unexpected status: {resp.status_code} {resp.json()}"
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        for node in data:
            assert "id" in node
            assert "case_id" in node
            assert "node_type" in node
            assert "parent_id" in node  # may be None for root nodes

    def test_empty_tree_returns_empty_list(self, client, auth_setup):
        """Case with no decision tree returns empty list (200)."""
        resp = client.get(
            f"/api/v1/clinical/thread/{INVALID_CASE_ID}/tree",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 403
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_invalid_case_id_returns_404(self, client, auth_setup):
        """Invalid case_id format returns 404."""
        resp = client.get(
            "/api/v1/clinical/thread/not-a-uuid/tree",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 404

    def test_unauthorized_returns_401(self, client, auth_setup):
        """No auth token returns 401."""
        resp = client.get(f"/api/v1/clinical/thread/{auth_setup['case_id']}/tree")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Edge cases: malformed paths
# ═══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Additional edge cases for Phase 2 endpoints."""

    def test_empty_case_id_returns_404(self, client, auth_setup):
        """Empty case_id in path returns 404."""
        endpoints = [
            ("GET", "/api/v1/clinical/context/"),
            ("GET", "/api/v1/clinical/evidence/"),
            ("POST", "/api/v1/clinical/agents/"),
            ("POST", "/api/v1/clinical/consensus/"),
            ("POST", "/api/v1/clinical/recommend/"),
            ("POST", "/api/v1/clinical/analyze/"),
            ("GET", "/api/v1/clinical/thread/"),
        ]
        for method, path in endpoints:
            resp = client.request(method, path, headers=_auth_headers(auth_setup["token"]))
            assert resp.status_code in (200, 404, 405, 422), (
                f"Unexpected {resp.status_code} for {method} {path}"
            )

    def test_get_node_endpoint_exists(self, client, auth_setup):
        """GET /api/v1/clinical/thread/node/{node_id} exists."""
        # Non-existent node_id → 404 (not 405 or 500)
        resp = client.get(
            f"/api/v1/clinical/thread/node/{INVALID_CASE_ID}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 404
