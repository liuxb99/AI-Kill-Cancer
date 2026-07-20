from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ─── Predict ─────────────────────────────────────────────────────────────────


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


class DataProvenance(BaseModel):
    """数据溯源信息"""
    model_config = ConfigDict(protected_namespaces=())

    data_mode: str = Field(..., description="synthetic | research | production")
    source: str | None = Field(None, description="数据来源说明")
    source_url: str | None = Field(None, description="来源 URL")
    retrieved_at: str | None = Field(None, description="数据获取时间")
    model_version: str | None = Field(None, description="模型版本")
    disclaimer: str | None = Field(
        None,
        description="免责声明 — 模拟数据不可用于诊断或治疗"
    )


class PredictResponse(BaseModel):
    patient_id: str
    cancer_type: str
    probability: float
    risk_level: str
    recommendations: list[str]
    provenance: DataProvenance | None = None


# ─── Recommend ───────────────────────────────────────────────────────────────


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
    provenance: DataProvenance | None = None


class RecommendResponse(BaseModel):
    patient_id: str
    cancer_type: str
    stage: str
    primary_option: TreatmentOption
    alternative_options: list[TreatmentOption]
    provenance: DataProvenance | None = None


# ─── Health ──────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: str
    version: str
    mode: str
    model_loaded: bool
    database_connected: bool


class DependencyStatus(BaseModel):
    name: str
    status: str  # ok | degraded | unavailable
    detail: str | None = None


class HealthDetailResponse(BaseModel):
    status: str
    version: str
    mode: str
    uptime_seconds: float
    dependencies: list[DependencyStatus]


# ─── Info ────────────────────────────────────────────────────────────────────


class InfoResponse(BaseModel):
    app_name: str
    version: str
    mode: str
    endpoints: list[dict[str, str]]


# ─── Charts ──────────────────────────────────────────────────────────────────


class CancerStatsResponse(BaseModel):
    incidence: list[dict]
    mortality: list[dict]
    mortality_colors: list[str]
    provenance: DataProvenance | None = None


class ResearchTrendsResponse(BaseModel):
    publications: list[dict]
    funding: list[dict]
    provenance: DataProvenance | None = None


class PredictionResultsResponse(BaseModel):
    accuracy: list[dict]
    roc: list[dict]
    provenance: DataProvenance | None = None


class DashboardKPI(BaseModel):
    label: str
    value: str
    unit: str


class DashboardKPIResponse(BaseModel):
    kpis: list[DashboardKPI]
    provenance: DataProvenance | None = None
