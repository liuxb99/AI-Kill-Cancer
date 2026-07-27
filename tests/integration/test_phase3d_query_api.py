"""Phase 3D — Graph Query API Tests."""

import pytest
from fastapi.testclient import TestClient

from src.backend.config import settings
from src.backend.main import create_app


@pytest.fixture(scope="module")
def client():
    """Create a TestClient with in-memory SQLite database in demo mode."""
    settings.DATABASE_URL = "sqlite+aiosqlite://"
    settings.APP_MODE = "demo"
    settings.DEBUG = False
    app = create_app()
    with TestClient(app) as c:
        yield c


class TestGraphAPI:
    """Graph API 端点测试。"""

    def test_status_endpoint_requires_auth(self, client):
        """GET /api/v1/clinical-graph/status 需要认证。"""
        resp = client.get("/api/v1/clinical-graph/status")
        assert resp.status_code in (401, 403)

    def test_failed_events_endpoint_requires_auth(self, client):
        """GET /api/v1/clinical-graph/failed-events 需要认证。"""
        resp = client.get("/api/v1/clinical-graph/failed-events")
        assert resp.status_code in (401, 403)

    def test_patient_thread_requires_auth(self, client):
        """GET /api/v1/clinical-graph/patient/{id}/thread 需要认证。"""
        resp = client.get("/api/v1/clinical-graph/patient/nonexistent/thread")
        assert resp.status_code in (401, 403)

    def test_recommendation_explain_requires_auth(self, client):
        """GET /api/v1/clinical-graph/recommendation/{id}/explain 需要认证。"""
        resp = client.get("/api/v1/clinical-graph/recommendation/nonexistent/explain")
        assert resp.status_code in (401, 403)

    def test_consensus_explain_requires_auth(self, client):
        """GET /api/v1/clinical-graph/consensus/{id}/explain 需要认证。"""
        resp = client.get("/api/v1/clinical-graph/consensus/nonexistent/explain")
        assert resp.status_code in (401, 403)

    def test_retry_event_requires_auth(self, client):
        """POST /api/v1/clinical-graph/retry/{id} 需要认证。"""
        resp = client.post("/api/v1/clinical-graph/retry/nonexistent")
        assert resp.status_code in (401, 403)
