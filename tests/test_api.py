from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient

from src.backend.config import settings
from src.backend.main import create_app


@pytest.fixture(scope="module")
def client():
    settings.DATABASE_URL = "sqlite+aiosqlite:///./test.db"
    settings.DEBUG = False
    settings.APP_MODE = "demo"
    app = create_app()
    with TestClient(app) as c:
        yield c


class TestHealth:

    def test_health_endpoint(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["mode"] == "demo"
        assert "version" in data

    def test_health_live(self, client):
        resp = client.get("/api/v1/health/live")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_ready(self, client):
        resp = client.get("/api/v1/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert "dependencies" in data
        assert data["mode"] == "demo"
        assert "uptime_seconds" in data

    def test_health_dependencies(self, client):
        resp = client.get("/api/v1/health/dependencies")
        assert resp.status_code == 200
        data = resp.json()
        assert "dependencies" in data

    def test_info_endpoint(self, client):
        resp = client.get("/api/v1/info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["app_name"] == "AI Kill Cancer API"
        assert data["mode"] == "demo"
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
        # Provenance must be present
        assert "provenance" in data
        assert data["provenance"]["data_mode"] == "synthetic"

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
        assert isinstance(data["risk_level"], str)
        assert data["cancer_type"] == "Breast Cancer"

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
        assert isinstance(data["probability"], float)
        assert data["cancer_type"] is not None

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
        assert isinstance(data["cancer_type"], str)

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


class TestPredictResearchMode:

    def test_predict_without_model_returns_503(self, client):
        """In research mode without a checkpoint, predict must fail."""
        from src.backend.config import settings as s
        original = s.APP_MODE
        s.APP_MODE = "research"
        try:
            payload = {
                "age": 45,
                "gender": "M",
                "biomarkers": {"CEA": 5.0},
            }
            resp = client.post("/api/v1/predict", json=payload)
            assert resp.status_code == 503
            detail = resp.json()["detail"]
            assert "model_unavailable" in str(detail) or "model_unavailable" in detail.get("error", "")
        finally:
            s.APP_MODE = original

    def test_predict_production_without_model(self, client):
        """In production mode without a checkpoint, predict must fail."""
        from src.backend.config import settings as s
        original = s.APP_MODE
        s.APP_MODE = "production"
        try:
            payload = {
                "age": 45,
                "gender": "M",
                "biomarkers": {"CEA": 5.0},
            }
            resp = client.post("/api/v1/predict", json=payload)
            assert resp.status_code == 503
        finally:
            s.APP_MODE = original


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
        # Provenance
        assert data["primary_option"].get("provenance") is not None
        assert data["provenance"]["data_mode"] == "synthetic"

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

    def test_recommend_research_mode_fails(self, client):
        """In research mode, recommend must fail (no model)."""
        from src.backend.config import settings as s
        original = s.APP_MODE
        s.APP_MODE = "research"
        try:
            payload = {
                "cancer_type": "Lung Cancer",
                "stage": "2",
                "biomarkers": {"EGFR": 0.5},
                "age": 60,
            }
            resp = client.post("/api/v1/recommend", json=payload)
            assert resp.status_code == 503
        finally:
            s.APP_MODE = original


class TestChartsAPI:

    def test_cancer_stats_endpoint(self, client):
        resp = client.get("/api/v1/charts/cancer-stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "incidence" in data
        assert "mortality" in data
        assert isinstance(data["incidence"], list)
        assert len(data["incidence"]) > 0
        assert "name" in data["incidence"][0]
        assert "male" in data["incidence"][0]
        # Provenance
        assert data.get("provenance") is not None
        assert data["provenance"]["data_mode"] == "synthetic"

    def test_research_trends_endpoint(self, client):
        resp = client.get("/api/v1/charts/research-trends")
        assert resp.status_code == 200
        data = resp.json()
        assert "publications" in data
        assert "funding" in data
        assert len(data["publications"]) > 0
        assert "year" in data["publications"][0]
        assert "deepLearning" in data["publications"][0]

    def test_prediction_results_endpoint(self, client):
        resp = client.get("/api/v1/charts/prediction-results")
        assert resp.status_code == 200
        data = resp.json()
        assert "accuracy" in data
        assert "roc" in data
        assert isinstance(data["accuracy"], list)
        assert len(data["accuracy"]) > 0
        assert "precision" in data["accuracy"][0]
        assert "recall" in data["accuracy"][0]
        assert "f1" in data["accuracy"][0]

    def test_dashboard_kpis_endpoint(self, client):
        resp = client.get("/api/v1/dashboard/kpis")
        assert resp.status_code == 200
        data = resp.json()
        assert "kpis" in data
        assert isinstance(data["kpis"], list)
        assert len(data["kpis"]) > 0
        assert "label" in data["kpis"][0]
        assert "value" in data["kpis"][0]
        assert "unit" in data["kpis"][0]


class TestResearchAPI:

    def test_research_health(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    @pytest.mark.skip(reason="需要 PostgreSQL 環境，僅在整合測試中執行")
    def test_submit_paper(self, client):
        payload = {
            "title": "Deep Learning for Early Cancer Detection",
            "authors": "Chen X., Wang L.",
            "journal": "Nature Medicine",
            "year": 2026,
            "doi": "10.1234/test.2026",
            "abstract": "A deep learning model for early cancer detection.",
            "keywords": "deep learning, cancer, early detection",
        }
        resp = client.post("/api/v1/research/papers", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == payload["title"]

    @pytest.mark.skip(reason="需要 PostgreSQL 環境，僅在整合測試中執行")
    def test_list_papers(self, client):
        resp = client.get("/api/v1/research/papers")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestAPPModeDemo:

    def test_provenance_has_disclaimer(self, client):
        """In demo mode, all responses must carry a disclaimer."""
        resp = client.post("/api/v1/predict", json={
            "age": 30, "gender": "F",
            "biomarkers": {"CA125": 10.0},
        })
        data = resp.json()
        assert data["provenance"]["data_mode"] == "synthetic"
        assert "disclaimer" in data["provenance"]


class TestCheckpointLoading:

    def test_load_model_no_checkpoint(self, client):
        """_load_model should return False when checkpoint doesn't exist."""
        from src.backend.api.routes import _load_model
        original = settings.MODEL_PATH
        settings.MODEL_PATH = "/nonexistent/path.pt"
        # Reset module-level model cache
        import src.backend.api.routes as routes
        routes._MODEL = None
        routes._LOAD_ERROR = None
        result = _load_model()
        settings.MODEL_PATH = original
        assert result is False

    def test_load_model_bad_checkpoint(self, tmp_path):
        """_load_model should handle corrupted checkpoint gracefully."""
        import torch
        from src.backend.api.routes import _load_model
        import src.backend.api.routes as routes

        # Create a corrupted file
        bad_ckpt = tmp_path / "bad_model.pt"
        bad_ckpt.write_text("this is not a torch checkpoint")

        original = settings.MODEL_PATH
        settings.MODEL_PATH = str(bad_ckpt)
        routes._MODEL = None
        routes._LOAD_ERROR = None
        result = _load_model()
        settings.MODEL_PATH = original
        assert result is False

    def test_load_model_valid_checkpoint(self, tmp_path):
        """_load_model should load a valid minimal checkpoint."""
        import torch
        from src.backend.api.routes import _load_model
        import src.backend.api.routes as routes
        from src.models.cancer_classifier import CancerClassifier, CancerClassifierConfig

        # Create a real (minimal) checkpoint
        cfg = CancerClassifierConfig(
            input_dim=100, hidden_dims=(64, 32), use_batch_norm=False,
        )
        model = CancerClassifier(cfg)
        model.eval()

        ckpt_path = tmp_path / "minimal_model.pt"
        torch.save({
            "config": {
                "input_dim": 100,
                "hidden_dims": (64, 32),
                "dropout": 0.1,
                "num_cancer_types": 3,
                "num_subtypes": 6,
                "num_stages": 4,
                "use_batch_norm": False,
            },
            "model_state_dict": model.state_dict(),
            "model_version": "test-v1",
        }, ckpt_path)

        original_path = settings.MODEL_PATH
        settings.MODEL_PATH = str(ckpt_path)
        routes._MODEL = None
        routes._LOAD_ERROR = None
        result = _load_model()
        settings.MODEL_PATH = original_path

        assert result is True

    def test_empty_checkpoint_rejected(self, tmp_path):
        """Empty or meaningless checkpoint should not load."""
        import torch
        from src.backend.api.routes import _load_model
        import src.backend.api.routes as routes

        empty_ckpt = tmp_path / "empty.pt"
        torch.save({}, empty_ckpt)

        original = settings.MODEL_PATH
        settings.MODEL_PATH = str(empty_ckpt)
        routes._MODEL = None
        routes._LOAD_ERROR = None
        result = _load_model()
        settings.MODEL_PATH = original
        # Should fail because empty dict has no model_state_dict
        assert result is False

    def test_random_init_never_used_for_inference(self, client):
        """A randomly initialised model must not be used for real predictions.
        In demo mode with no checkpoint, synthetic fallback is used instead."""
        from src.backend.api.routes import _MODEL as current_model
        # When no checkpoint is loaded, _MODEL stays None
        assert current_model is None
