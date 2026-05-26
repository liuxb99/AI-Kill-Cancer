from pydantic import BaseModel, Field
from typing import Optional


class PredictRequest(BaseModel):
    age: int = Field(..., ge=0, le=120, description="Patient age")
    gender: str = Field(..., pattern="^(M|F)$", description="Patient gender (M/F)")
    biomarkers: dict[str, float] = Field(
        ..., description="Biomarker values keyed by name"
    )
    family_history: Optional[list[str]] = Field(
        None, description="List of family cancer types"
    )
    smoking_history: Optional[str] = Field(
        None, pattern="^(never|former|current)$"
    )


class PredictResponse(BaseModel):
    patient_id: str
    cancer_type: str
    probability: float
    risk_level: str
    recommendations: list[str]


class RecommendRequest(BaseModel):
    cancer_type: str = Field(..., description="Diagnosed cancer type")
    stage: str = Field(..., pattern="^[0-4]$", description="Cancer stage (0-4)")
    biomarkers: dict[str, float] = Field(
        ..., description="Current biomarker values"
    )
    age: int = Field(..., ge=0, le=120)
    prior_treatments: Optional[list[str]] = Field(
        None, description="Previous treatments received"
    )


class TreatmentOption(BaseModel):
    name: str
    description: str
    success_rate: float
    side_effects: list[str]
    estimated_cost: Optional[str] = None


class RecommendResponse(BaseModel):
    patient_id: str
    cancer_type: str
    stage: str
    primary_option: TreatmentOption
    alternative_options: list[TreatmentOption]


class HealthResponse(BaseModel):
    status: str
    version: str
    model_loaded: bool
    database_connected: bool


class InfoResponse(BaseModel):
    app_name: str
    version: str
    endpoints: list[dict[str, str]]
