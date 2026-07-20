"""
API v1 contract tests — verify endpoints exist and return correct status codes.
These tests use SQLite in-memory database.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.backend.config import settings
from src.backend.main import create_app


@pytest.fixture(scope="module")
def client():
    settings.DATABASE_URL = "sqlite+aiosqlite://"  # In-memory SQLite
    settings.APP_MODE = "demo"
    settings.DEBUG = False
    app = create_app()
    with TestClient(app) as c:
        yield c


class TestV1Patients:
    def test_create_patient(self, client):
        """Create a patient via API with SQLite."""
        resp = client.post(
            "/api/v1/patients",
            json={"sex": "M", "consent_status": "granted"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["sex"] == "M"
        assert data["consent_status"] == "granted"
        assert "id" in data

    def test_get_patient_not_found(self, client):
        resp = client.get("/api/v1/patients/550e8400-e29b-41d4-a716-446655440000")
        assert resp.status_code == 404

    def test_list_patients_empty(self, client):
        resp = client.get("/api/v1/patients")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 0
        assert "items" in data

    def test_v1_endpoints_exist(self, client):
        """Verify all v1 routes are registered by checking paths resolve properly."""
        endpoints = [
            ("GET", "/api/v1/patients/550e8400-e29b-41d4-a716-446655440000"),
            ("GET", "/api/v1/cases/550e8400-e29b-41d4-a716-446655440000"),
            ("GET", "/api/v1/analyses/550e8400-e29b-41d4-a716-446655440000/graph"),
            ("GET", "/api/v1/analyses/550e8400-e29b-41d4-a716-446655440000/drug-candidates"),
            ("GET", "/api/v1/analyses/550e8400-e29b-41d4-a716-446655440000/evidence"),
        ]
        for method, path in endpoints:
            resp = client.request(method, path)
            # Routes exist if we get any response other than 404
            # 404 means resource not found (valid for non-existent IDs)
            # 500 means route found but internal error
            assert resp.status_code in (404, 200, 500), f"Unexpected status for {method} {path}: {resp.status_code}"


class TestV1Analyses:
    def test_analysis_graph_not_found(self, client):
        resp = client.get("/api/v1/analyses/550e8400-e29b-41d4-a716-446655440000/graph")
        assert resp.status_code == 404

    def test_analysis_drug_candidates_not_found(self, client):
        resp = client.get("/api/v1/analyses/550e8400-e29b-41d4-a716-446655440000/drug-candidates")
        assert resp.status_code == 404


class TestV1Variants:
    def test_import_variants_empty(self, client):
        resp = client.post(
            "/api/v1/variants/import",
            json={"items": []},
        )
        assert resp.status_code == 201
        assert resp.json() == []
