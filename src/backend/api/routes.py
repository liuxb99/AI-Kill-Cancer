import logging
import uuid

from fastapi import APIRouter, HTTPException

from src.backend.config import settings
from src.backend.models import (
    HealthResponse,
    InfoResponse,
    PredictRequest,
    PredictResponse,
    RecommendRequest,
    RecommendResponse,
    TreatmentOption,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["api"])


@router.post("/predict", response_model=PredictResponse)
async def predict(body: PredictRequest):
    try:
        logger.info("Predict request received: age=%s, gender=%s", body.age, body.gender)

        # Mock prediction logic — replace with actual ML model inference
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

        return PredictResponse(
            patient_id=str(uuid.uuid4()),
            cancer_type=cancer_type,
            probability=round(probability, 4),
            risk_level=risk_level,
            recommendations=recommendations,
        )
    except Exception as e:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/recommend", response_model=RecommendResponse)
async def recommend(body: RecommendRequest):
    try:
        logger.info(
            "Recommend request received: cancer_type=%s, stage=%s",
            body.cancer_type,
            body.stage,
        )

        stage_int = int(body.stage)

        primary = TreatmentOption(
            name=f"{body.cancer_type} — Stage {body.stage} Standard Protocol",
            description="First-line treatment based on NCCN guidelines",
            success_rate=0.0,
            side_effects=[],
            estimated_cost="$50,000 – $120,000",
        )

        alternatives: list[TreatmentOption] = []

        if stage_int <= 2:
            primary.success_rate = 0.85
            primary.side_effects = ["Fatigue", "Nausea", "Hair loss"]
            alternatives.append(
                TreatmentOption(
                    name="Targeted Therapy",
                    description="Precision medicine based on genetic markers",
                    success_rate=0.72,
                    side_effects=["Skin rash", "Diarrhea", "Liver enzyme elevation"],
                    estimated_cost="$80,000 – $200,000",
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
                    description="Checkpoint inhibitor therapy",
                    success_rate=0.48,
                    side_effects=["Immune-related adverse events", "Fatigue", "Rash"],
                    estimated_cost="$100,000 – $250,000",
                )
            )
            alternatives.append(
                TreatmentOption(
                    name="Clinical Trial",
                    description="Experimental therapy with novel mechanism",
                    success_rate=0.35,
                    side_effects=["Varies by protocol", "Unknown long-term effects"],
                    estimated_cost="$0 (sponsored)",
                )
            )

        return RecommendResponse(
            patient_id=str(uuid.uuid4()),
            cancer_type=body.cancer_type,
            stage=body.stage,
            primary_option=primary,
            alternative_options=alternatives,
        )
    except Exception as e:
        logger.exception("Recommendation failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        model_loaded=settings.MODEL_ENABLED,
        database_connected=True,
    )


@router.get("/info", response_model=InfoResponse)
async def info():
    return InfoResponse(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        endpoints=[
            {"path": "/api/v1/predict", "method": "POST", "description": "Cancer diagnosis prediction"},
            {"path": "/api/v1/recommend", "method": "POST", "description": "Treatment recommendation"},
            {"path": "/api/v1/health", "method": "GET", "description": "Health check"},
            {"path": "/api/v1/info", "method": "GET", "description": "System information"},
        ],
    )
