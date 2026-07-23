from __future__ import annotations

import logging
import os
import time
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from src.backend.config import settings
from src.backend.models import (
    CancerStatsResponse,
    DashboardKPI,
    DashboardKPIResponse,
    DataProvenance,
    DependencyStatus,
    HealthDetailResponse,
    HealthResponse,
    InfoResponse,
    PredictionResultsResponse,
    PredictRequest,
    PredictResponse,
    RecommendRequest,
    RecommendResponse,
    ResearchTrendsResponse,
    TreatmentOption,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["api"])

# ─── Startup timestamp ───────────────────────────────────────────────────────
_STARTED_AT = time.monotonic()

# ─── ML Model attempt ────────────────────────────────────────────────────────

_MODEL = None
_MODEL_LABELS = ["Lung Cancer", "Breast Cancer", "Prostate Cancer"]
_MODEL_VERSION: str | None = None
_LOAD_ERROR: str | None = None


def _synthetic_prov() -> DataProvenance:
    """Return provenance for demo/synthetic data."""
    now = datetime.now(UTC).isoformat()
    return DataProvenance(
        data_mode="synthetic",
        source="Simulated data for demonstration purposes only",
        source_url=None,
        retrieved_at=now,
        model_version=None,
        disclaimer=(
            "This is simulated data for demonstration purposes only. "
            "Do NOT use for diagnosis, treatment, or any clinical decision."
        ),
    )


def _model_unavailable_prov() -> DataProvenance:
    now = datetime.now(UTC).isoformat()
    return DataProvenance(
        data_mode="synthetic",
        source="Model unavailable — no checkpoint loaded",
        source_url=None,
        retrieved_at=now,
        model_version=None,
        disclaimer=(
            "Model checkpoint is not available. "
            "Results are synthetic and must NOT be used for clinical purposes."
        ),
    )


def _load_model() -> bool:
    """Load model checkpoint safely.

    Returns True if a REAL checkpoint was loaded successfully.
    The loaded model must never be a randomly-initialised model.
    """
    global _MODEL, _MODEL_VERSION, _LOAD_ERROR

    if _MODEL is not None:
        return True

    model_path = settings.MODEL_PATH
    if not model_path or not os.path.isfile(model_path):
        _LOAD_ERROR = f"Checkpoint not found at {model_path}"
        logger.warning(_LOAD_ERROR)
        return False

    try:
        import torch

        from src.models.cancer_classifier import CancerClassifier, CancerClassifierConfig

        # 1. Load checkpoint safely
        logger.info("Loading checkpoint from %s", model_path)
        ckpt = torch.load(model_path, map_location="cpu", weights_only=True)

        # 2. Determine config from checkpoint
        if isinstance(ckpt, dict) and "config" in ckpt:
            cfg_dict = ckpt["config"]
            cfg = CancerClassifierConfig(**cfg_dict)
            _MODEL_VERSION = ckpt.get("model_version", f"checkpoint@{os.path.getmtime(model_path)}")
        else:
            # Use default config
            cfg = CancerClassifierConfig()
            _MODEL_VERSION = f"unknown@{os.path.getmtime(model_path):.0f}"

        # 3. Instantiate and load state
        model = CancerClassifier(cfg)
        state_dict = ckpt if not isinstance(ckpt, dict) else ckpt.get("model_state_dict", ckpt)
        if isinstance(state_dict, dict) and "model_state_dict" in state_dict:
            state_dict = state_dict["model_state_dict"]

        model.load_state_dict(state_dict)
        model.eval()

        # 4. Verify compatibility
        if cfg.input_dim != CancerClassifierConfig().input_dim:
            logger.warning(
                "Checkpoint input_dim=%d differs from default %d",
                cfg.input_dim, CancerClassifierConfig().input_dim,
            )

        _MODEL = model
        logger.info(
            "Model loaded successfully from %s (version=%s)",
            model_path, _MODEL_VERSION,
        )
        return True

    except Exception as exc:
        _LOAD_ERROR = f"Failed to load checkpoint: {exc}"
        logger.exception("Model loading failed")
        return False


def _model_predict(body: PredictRequest) -> tuple[str, float, str | None]:
    """Run prediction using loaded model or return synthetic fallback.

    Returns (cancer_type, probability, model_version_or_None).
    """
    mode = settings.APP_MODE

    # Try real model first
    if mode in ("research", "production"):
        if not _load_model() or _MODEL is None:
            # In research/production mode, no model = no prediction
            _raise_model_unavailable()

        return _do_model_inference(body, _MODEL)

    # Demo mode: try model if available, else synthetic
    if _load_model() and _MODEL is not None:
        return _do_model_inference(body, _MODEL)

    return _synthetic_predict(body)


def _do_model_inference(body: PredictRequest, model) -> tuple[str, float, str]:
    """Run inference on a loaded model."""
    import torch

    features = [0.0] * model.config.input_dim
    for i, (k, v) in enumerate(body.biomarkers.items()):
        if i < model.config.input_dim:
            features[i] = v / 100.0
    features[model.config.input_dim - 5] = body.age / 120.0
    features[model.config.input_dim - 4] = 1.0 if body.gender == "M" else 0.0
    features[model.config.input_dim - 3] = 1.0 if body.smoking_history == "current" else 0.0
    features[model.config.input_dim - 2] = 1.0 if body.family_history else 0.0

    x = torch.tensor([features], dtype=torch.float32)
    with torch.no_grad():
        probs = model.predict_proba(x)
    type_probs = probs["cancer_type"][0].tolist()
    max_idx = type_probs.index(max(type_probs))
    predicted = _MODEL_LABELS[max_idx] if max_idx < len(_MODEL_LABELS) else "Unknown"
    prob = max(type_probs)
    logger.info("Model inference: %s (%.4f)", predicted, prob)
    return predicted, prob, _MODEL_VERSION


def _synthetic_predict(body: PredictRequest) -> tuple[str, float, None]:
    """Synthetic prediction for demo mode — no clinical value."""
    cancer_type = "Lung Cancer"
    probability = 0.0
    if any(v > 50.0 for v in body.biomarkers.values()):
        cancer_type = "Breast Cancer"
        probability = 0.87
    elif body.age > 60 and body.smoking_history == "current":
        cancer_type = "Lung Cancer"
        probability = 0.76
    elif body.family_history:
        cancer_type = body.family_history[0]
        probability = 0.62
    else:
        probability = 0.12
    return cancer_type, probability, None


def _raise_model_unavailable():
    raise HTTPException(
        status_code=503,
        detail={
            "error": "model_unavailable",
            "message": "No trained model checkpoint is loaded. "
                       "Model predictions cannot be provided in the current mode.",
            "mode": settings.APP_MODE,
            "load_error": _LOAD_ERROR or "unknown",
        },
    )


# ─── Predict Endpoint ────────────────────────────────────────────────────────


@router.post("/predict", response_model=PredictResponse)
async def predict(body: PredictRequest):
    try:
        logger.info("Predict request (mode=%s): age=%s, gender=%s", settings.APP_MODE, body.age, body.gender)
        cancer_type, probability, model_ver = _model_predict(body)

        risk_level: str
        if probability >= 0.8:
            risk_level = "High"
        elif probability >= 0.4:
            risk_level = "Moderate"
        else:
            risk_level = "Low"

        recommendations = [
            f"Recommended screening: {cancer_type} panel",
            "Consult with oncologist for further evaluation",
            "Maintain regular follow-up schedule",
        ]

        prov: DataProvenance
        if model_ver:
            now = datetime.now(UTC).isoformat()
            prov = DataProvenance(
                data_mode=settings.APP_MODE,
                source=f"CancerClassifier model checkpoint ({model_ver})",
                source_url=None,
                retrieved_at=now,
                model_version=model_ver,
                disclaimer=None if settings.APP_MODE == "production" else
                "This prediction is for research purposes only. Not for clinical use.",
            )
        else:
            prov = _synthetic_prov()

        return PredictResponse(
            patient_id=str(uuid.uuid4()),
            cancer_type=cancer_type,
            probability=round(probability, 4),
            risk_level=risk_level,
            recommendations=recommendations,
            provenance=prov,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ─── Recommend Endpoint ──────────────────────────────────────────────────────


@router.post("/recommend", response_model=RecommendResponse)
async def recommend(body: RecommendRequest):
    try:
        logger.info(
            "Recommend request (mode=%s): cancer_type=%s, stage=%s",
            settings.APP_MODE, body.cancer_type, body.stage,
        )

        if settings.APP_MODE in ("research", "production"):
            _raise_model_unavailable()

        # Demo mode: synthetic recommendations
        stage_int = int(body.stage)

        primary = TreatmentOption(
            name=f"{body.cancer_type} — Stage {body.stage} Standard Protocol",
            description="First-line treatment based on simulated data",
            success_rate=0.0,
            side_effects=[],
            estimated_cost="$50,000 – $120,000",
            provenance=_synthetic_prov(),
        )

        alternatives: list[TreatmentOption] = []

        if stage_int <= 2:
            primary.success_rate = 0.85
            primary.side_effects = ["Fatigue", "Nausea", "Hair loss"]
            alternatives.append(
                TreatmentOption(
                    name="Targeted Therapy",
                    description="Precision medicine — simulated data",
                    success_rate=0.72,
                    side_effects=["Skin rash", "Diarrhea", "Liver enzyme elevation"],
                    estimated_cost="$80,000 – $200,000",
                    provenance=_synthetic_prov(),
                )
            )
        else:
            primary.success_rate = 0.55
            primary.side_effects = [
                "Severe fatigue",
                "Immunosuppression",
                "Organ toxicity",
            ]
            alternatives.append(
                TreatmentOption(
                    name="Immunotherapy (PD-1/PD-L1)",
                    description="Checkpoint inhibitor therapy — simulated data",
                    success_rate=0.48,
                    side_effects=["Immune-related adverse events", "Fatigue", "Rash"],
                    estimated_cost="$100,000 – $250,000",
                    provenance=_synthetic_prov(),
                )
            )
            alternatives.append(
                TreatmentOption(
                    name="Clinical Trial",
                    description="Experimental therapy — simulated data",
                    success_rate=0.35,
                    side_effects=["Varies by protocol", "Unknown long-term effects"],
                    estimated_cost="$0 (sponsored)",
                    provenance=_synthetic_prov(),
                )
            )

        return RecommendResponse(
            patient_id=str(uuid.uuid4()),
            cancer_type=body.cancer_type,
            stage=body.stage,
            primary_option=primary,
            alternative_options=alternatives,
            provenance=_synthetic_prov(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Recommendation failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ─── Chart Data Endpoints (synthetic) ────────────────────────────────────────


_SYNTHETIC_SOURCE = DataProvenance(
    data_mode="synthetic",
    source="Simulated statistical data for demonstration. Not based on real cancer registry data.",
    source_url=None,
    retrieved_at=datetime.now(UTC).isoformat(),
    model_version=None,
    disclaimer="These charts display simulated data. Do NOT use for clinical or research conclusions.",
)


@router.get("/charts/cancer-stats", response_model=CancerStatsResponse)
async def cancer_stats():
    return CancerStatsResponse(
        incidence=[
            {"name": "肺癌", "male": 58.2, "female": 32.4},
            {"name": "乳癌", "male": 0.5, "female": 88.2},
            {"name": "大腸癌", "male": 42.3, "female": 32.1},
            {"name": "肝癌", "male": 38.7, "female": 15.2},
            {"name": "胃癌", "male": 28.1, "female": 14.3},
            {"name": "攝護腺癌", "male": 45.6, "female": 0},
            {"name": "甲狀腺癌", "male": 8.5, "female": 24.6},
        ],
        mortality=[
            {"name": "肺癌", "value": 38},
            {"name": "肝癌", "value": 22},
            {"name": "大腸癌", "value": 18},
            {"name": "胃癌", "value": 13},
            {"name": "乳癌", "value": 9},
        ],
        mortality_colors=["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6"],
        provenance=_SYNTHETIC_SOURCE,
    )


@router.get("/charts/research-trends", response_model=ResearchTrendsResponse)
async def research_trends():
    return ResearchTrendsResponse(
        publications=[
            {"year": "2016", "deepLearning": 120, "genomics": 340, "immunotherapy": 280, "radiomics": 90},
            {"year": "2017", "deepLearning": 210, "genomics": 390, "immunotherapy": 350, "radiomics": 140},
            {"year": "2018", "deepLearning": 380, "genomics": 420, "immunotherapy": 440, "radiomics": 210},
            {"year": "2019", "deepLearning": 620, "genomics": 460, "immunotherapy": 530, "radiomics": 340},
            {"year": "2020", "deepLearning": 950, "genomics": 510, "immunotherapy": 620, "radiomics": 510},
            {"year": "2021", "deepLearning": 1420, "genomics": 540, "immunotherapy": 710, "radiomics": 730},
            {"year": "2022", "deepLearning": 2180, "genomics": 580, "immunotherapy": 780, "radiomics": 1020},
            {"year": "2023", "deepLearning": 3150, "genomics": 610, "immunotherapy": 840, "radiomics": 1380},
            {"year": "2024", "deepLearning": 4280, "genomics": 650, "immunotherapy": 910, "radiomics": 1790},
        ],
        funding=[
            {"year": "2020", "government": 4.2, "private": 2.8},
            {"year": "2021", "government": 5.1, "private": 3.5},
            {"year": "2022", "government": 6.3, "private": 4.7},
            {"year": "2023", "government": 7.8, "private": 6.2},
            {"year": "2024", "government": 9.5, "private": 8.1},
        ],
        provenance=_SYNTHETIC_SOURCE,
    )


@router.get("/charts/prediction-results", response_model=PredictionResultsResponse)
async def prediction_results():
    return PredictionResultsResponse(
        accuracy=[
            {"model": "CNN", "accuracy": 94.2, "precision": 93.8, "recall": 92.5, "f1": 93.1},
            {"model": "ResNet50", "accuracy": 96.7, "precision": 95.9, "recall": 95.2, "f1": 95.5},
            {"model": "ViT", "accuracy": 97.1, "precision": 96.8, "recall": 96.3, "f1": 96.5},
            {"model": "EfficientNet", "accuracy": 95.8, "precision": 95.1, "recall": 94.6, "f1": 94.8},
            {"model": "TransUNet", "accuracy": 97.8, "precision": 97.3, "recall": 97.0, "f1": 97.1},
        ],
        roc=[
            {"fpr": 0, "tpr1": 0, "tpr2": 0, "tpr3": 0},
            {"fpr": 0.1, "tpr1": 0.72, "tpr2": 0.68, "tpr3": 0.75},
            {"fpr": 0.2, "tpr1": 0.85, "tpr2": 0.81, "tpr3": 0.87},
            {"fpr": 0.3, "tpr1": 0.91, "tpr2": 0.88, "tpr3": 0.93},
            {"fpr": 0.4, "tpr1": 0.94, "tpr2": 0.92, "tpr3": 0.96},
            {"fpr": 0.5, "tpr1": 0.96, "tpr2": 0.94, "tpr3": 0.97},
            {"fpr": 0.6, "tpr1": 0.97, "tpr2": 0.96, "tpr3": 0.98},
            {"fpr": 0.7, "tpr1": 0.98, "tpr2": 0.97, "tpr3": 0.99},
            {"fpr": 0.8, "tpr1": 0.99, "tpr2": 0.98, "tpr3": 0.99},
            {"fpr": 0.9, "tpr1": 0.99, "tpr2": 0.99, "tpr3": 1.0},
            {"fpr": 1.0, "tpr1": 1.0, "tpr2": 1.0, "tpr3": 1.0},
        ],
        provenance=_SYNTHETIC_SOURCE,
    )


@router.get("/dashboard/kpis", response_model=DashboardKPIResponse)
async def dashboard_kpis():
    return DashboardKPIResponse(
        kpis=[
            DashboardKPI(label="涵蓋癌症種類 (模擬)", value="12", unit="種"),
            DashboardKPI(label="AI 模型準確率 (模擬)", value="97.8", unit="% (模擬)"),
            DashboardKPI(label="研究論文數 (模擬)", value="8,640", unit="篇"),
            DashboardKPI(label="臨床試驗 (模擬)", value="342", unit="項"),
        ],
        provenance=_SYNTHETIC_SOURCE,
    )


# ─── Health Endpoints ────────────────────────────────────────────────────────


@router.get("/health", response_model=HealthResponse)
async def health():
    """Simple health check (legacy)."""
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        mode=settings.APP_MODE,
        model_loaded=_MODEL is not None,
        database_connected=True,
    )


@router.get("/health/live", response_model=HealthResponse)
async def health_live():
    """Liveness probe — always returns ok if the service is running."""
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        mode=settings.APP_MODE,
        model_loaded=_MODEL is not None,
        database_connected=True,
    )


@router.get("/health/ready", response_model=HealthDetailResponse)
async def health_ready():
    """Readiness probe — reflects dependency status."""
    deps: list[DependencyStatus] = []

    # Model check
    if _MODEL is not None:
        deps.append(DependencyStatus(name="model", status="ok", detail=_MODEL_VERSION))
    elif settings.APP_MODE == "demo":
        deps.append(DependencyStatus(
            name="model", status="degraded",
            detail="Model checkpoint not loaded (expected in demo mode)",
        ))
    else:
        deps.append(DependencyStatus(
            name="model", status="unavailable",
            detail=_LOAD_ERROR or "Model checkpoint not found",
        ))

    # Database check (simplified — would need actual connection check)
    db_url = settings.DATABASE_URL
    if db_url:
        deps.append(DependencyStatus(name="database", status="degraded",
                                      detail="Connection not verified in this request"))
    else:
        deps.append(DependencyStatus(name="database", status="unavailable",
                                      detail="DATABASE_URL not configured"))

    overall_status = "ok"
    for d in deps:
        if d.status == "unavailable":
            overall_status = "degraded"
        elif d.status == "degraded" and overall_status == "ok":
            overall_status = "degraded"

    return HealthDetailResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        mode=settings.APP_MODE,
        uptime_seconds=time.monotonic() - _STARTED_AT,
        dependencies=deps,
    )


@router.get("/health/dependencies", response_model=HealthDetailResponse)
async def health_dependencies():
    """Detailed dependency status — alias for /health/ready."""
    return await health_ready()


@router.get("/info", response_model=InfoResponse)
async def info():
    return InfoResponse(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        mode=settings.APP_MODE,
        endpoints=[
            {"path": "/api/v1/predict", "method": "POST", "description": "Cancer diagnosis prediction"},
            {"path": "/api/v1/recommend", "method": "POST", "description": "Treatment recommendation"},
            {"path": "/api/v1/charts/cancer-stats", "method": "GET", "description": "Cancer statistics data"},
            {"path": "/api/v1/charts/research-trends", "method": "GET", "description": "Research trend data"},
            {"path": "/api/v1/charts/prediction-results", "method": "GET", "description": "Model prediction results"},
            {"path": "/api/v1/dashboard/kpis", "method": "GET", "description": "Dashboard KPI data"},
            {"path": "/api/v1/health", "method": "GET", "description": "Simple health check"},
            {"path": "/api/v1/health/live", "method": "GET", "description": "Liveness probe"},
            {"path": "/api/v1/health/ready", "method": "GET", "description": "Readiness probe"},
            {"path": "/api/v1/health/dependencies", "method": "GET", "description": "Dependency details"},
            {"path": "/api/v1/info", "method": "GET", "description": "System information"},
        ],
    )
