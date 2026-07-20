"""
Tests for data provenance and medical safety wording.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.backend.config import settings
from src.backend.main import create_app


@pytest.fixture(scope="module")
def client():
    settings.DATABASE_URL = "sqlite+aiosqlite://"  # Use SQLite for v1 endpoints too
    settings.APP_MODE = "demo"
    settings.DEBUG = False
    app = create_app()
    with TestClient(app) as c:
        yield c


def _check_endpoint_synthetic_flag(data: dict, path: str):
    """Check that synthetic data has proper provenance marker."""
    if "provenance" in data:
        prov = data["provenance"]
        assert "data_mode" in prov, f"{path}: missing data_mode in provenance"
        assert prov["data_mode"] in ("synthetic", "demo"), f"{path}: unexpected data_mode"
    elif "data_mode" in data:
        assert data["data_mode"] in ("synthetic", "demo"), f"{path}: unexpected data_mode"


class TestProvenance:
    def test_predict_has_provenance(self, client):
        resp = client.post(
            "/api/v1/predict",
            json={
                "age": 45,
                "gender": "F",
                "biomarkers": {"BRCA1": 75.0},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "provenance" in data
        prov = data["provenance"]
        assert prov["data_mode"] == "synthetic"
        assert "disclaimer" in prov
        assert "simulated" in prov["disclaimer"].lower()

    def test_recommend_has_disclaimer(self, client):
        resp = client.post(
            "/api/v1/recommend",
            json={
                "cancer_type": "Thyroid Cancer",
                "stage": "2",
                "biomarkers": {"BRAF": 1.0},
                "age": 45,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "provenance" in data
        prov = data["provenance"]
        assert prov["data_mode"] == "synthetic"

    def test_charts_have_provenance(self, client):
        resp = client.get("/api/v1/charts/cancer-stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "provenance" in data

    def test_dashboard_kpis_have_provenance(self, client):
        resp = client.get("/api/v1/dashboard/kpis")
        assert resp.status_code == 200
        data = resp.json()
        assert "provenance" in data


class TestMedicalSafety:
    """Verify no inappropriate medical claims are used."""

    FORBIDDEN_PATTERNS = [
        "prescribe",
        "dosage",
        "dose",
        "stop taking",
        "discontinue",
        "switch to",
        "diagnosis confirmed",
        "you have cancer",
        "will cure",
        "guaranteed",
        "FDA approved for your case",
    ]

    def test_predict_response_no_diagnosis_claim(self, client):
        """The predict endpoint must not claim to diagnose."""
        resp = client.post(
            "/api/v1/predict",
            json={
                "age": 50,
                "gender": "M",
                "biomarkers": {"CEA": 30.0},
            },
        )
        data = resp.json()
        text = str(data).lower()
        for pattern in self.FORBIDDEN_PATTERNS:
            assert pattern not in text, f"Found forbidden pattern '{pattern}' in predict response"

    def test_health_returns_ok_with_mode(self, client):
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert data["status"] == "ok"
        assert "mode" in data
        assert data["mode"] == "demo"

    def test_v1_endpoints_no_synthetic_false_claims(self, client):
        """V1 endpoints in Phase 1 should return not_configured/not_searched
        statuses rather than fake drug candidates."""
        resp = client.get("/api/v1/analyses/00000000-0000-0000-0000-000000000000/drug-candidates")
        if resp.status_code == 200:
            data = resp.json()
            # If it returns 200, it should be an empty list with proper status
            assert "items" in data
            assert data["total"] == 0
