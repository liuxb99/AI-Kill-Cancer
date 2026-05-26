import pytest
from fastapi.testclient import TestClient

from src.backend.main import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


class TestHealth:

    def test_health_endpoint(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_info_endpoint(self, client):
        resp = client.get("/api/v1/info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["app_name"] == "AI Kill Cancer API"
        assert len(data["endpoints"]) > 0


class TestPredict:

    def test_predict_low_risk(self, client):
        payload = {
            "age": 30,
            "gender": "F",
            "biomarkers": {"CA125": 10.0, "CEA": 2.0},
            "family_history": None,
            "smoking_history": "never",
        }
        resp = client.post("/api/v1/predict", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "patient_id" in data
        assert "cancer_type" in data
        assert "risk_level" in data
        assert "probability" in data

    def test_predict_high_biomarker(self, client):
        payload = {
            "age": 45,
            "gender": "F",
            "biomarkers": {"BRCA1": 85.0, "CA125": 90.0},
            "family_history": None,
            "smoking_history": "never",
        }
        resp = client.post("/api/v1/predict", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["risk_level"] == "High"

    def test_predict_smoking_risk(self, client):
        payload = {
            "age": 65,
            "gender": "M",
            "biomarkers": {"CEA": 5.0},
            "family_history": None,
            "smoking_history": "current",
        }
        resp = client.post("/api/v1/predict", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["probability"] == 0.76

    def test_predict_family_history(self, client):
        payload = {
            "age": 50,
            "gender": "F",
            "biomarkers": {"CA125": 15.0},
            "family_history": ["Breast Cancer"],
            "smoking_history": "former",
        }
        resp = client.post("/api/v1/predict", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["cancer_type"] == "Breast Cancer"

    def test_predict_invalid_age(self, client):
        payload = {
            "age": -1,
            "gender": "M",
            "biomarkers": {"CEA": 1.0},
        }
        resp = client.post("/api/v1/predict", json=payload)
        assert resp.status_code == 422

    def test_predict_invalid_gender(self, client):
        payload = {
            "age": 30,
            "gender": "X",
            "biomarkers": {"CEA": 1.0},
        }
        resp = client.post("/api/v1/predict", json=payload)
        assert resp.status_code == 422


class TestRecommend:

    def test_recommend_early_stage(self, client):
        payload = {
            "cancer_type": "Lung Cancer",
            "stage": "1",
            "biomarkers": {"EGFR": 0.5},
            "age": 60,
            "prior_treatments": None,
        }
        resp = client.post("/api/v1/recommend", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "primary_option" in data
        assert "alternative_options" in data
        assert data["primary_option"]["success_rate"] == 0.85

    def test_recommend_late_stage(self, client):
        payload = {
            "cancer_type": "Lung Cancer",
            "stage": "4",
            "biomarkers": {"EGFR": 0.8},
            "age": 70,
            "prior_treatments": ["Chemotherapy"],
        }
        resp = client.post("/api/v1/recommend", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["primary_option"]["success_rate"] == 0.55
        assert len(data["alternative_options"]) == 2

    def test_recommend_invalid_stage(self, client):
        payload = {
            "cancer_type": "Lung Cancer",
            "stage": "5",
            "biomarkers": {"EGFR": 0.5},
            "age": 60,
        }
        resp = client.post("/api/v1/recommend", json=payload)
        assert resp.status_code == 422

    def test_recommend_edge_stage_2(self, client):
        payload = {
            "cancer_type": "Breast Cancer",
            "stage": "2",
            "biomarkers": {"HER2": 3.0},
            "age": 50,
        }
        resp = client.post("/api/v1/recommend", json=payload)
        assert resp.status_code == 200
        assert resp.json()["primary_option"]["success_rate"] == 0.85


class TestResearchAPI:

    def test_research_health(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
