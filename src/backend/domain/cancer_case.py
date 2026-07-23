"""
CancerCase domain model — links a patient to a specific thyroid cancer diagnosis.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import JSON, Column, Date, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

from src.backend.database.models import Base as DBBase
from src.backend.database.models import CompatUUID
from src.backend.domain.enums import CancerTypeEnum


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class CancerCaseModel(DBBase):
    __tablename__ = "domain_cancer_cases"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    patient_id = Column(CompatUUID, ForeignKey("domain_patients.id", ondelete="CASCADE"), nullable=False, index=True)
    oncotree_code = Column(String(32), nullable=True, index=True)
    cancer_type = Column(SAEnum(CancerTypeEnum), nullable=False, index=True)
    histology = Column(String(256), nullable=True)
    stage = Column(String(32), nullable=True)
    diagnosis_date = Column(Date, nullable=True)
    radioiodine_status = Column(String(64), nullable=True)
    recurrence_status = Column(String(64), nullable=True)
    metastatic_sites = Column(JSON, default=list)
    treatment_history = Column(JSON, default=list)
    current_medications = Column(JSON, default=list)
    clinical_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient = relationship("PatientModel", back_populates="cancer_cases")
    specimens = relationship("SpecimenModel", back_populates="cancer_case", cascade="all, delete-orphan")
    analysis_runs = relationship("AnalysisRunModel", back_populates="cancer_case", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CancerCaseModel(id={self.id}, cancer_type={self.cancer_type})>"


class CancerCaseCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    patient_id: str
    oncotree_code: str | None = Field(None, max_length=32)
    cancer_type: CancerTypeEnum
    histology: str | None = Field(None, max_length=256)
    stage: str | None = Field(None, max_length=32)
    diagnosis_date: date | None = None
    radioiodine_status: str | None = Field(None, max_length=64)
    recurrence_status: str | None = Field(None, max_length=64)
    metastatic_sites: list[str] | None = None
    treatment_history: list[dict] | None = None
    current_medications: list[dict] | None = None
    clinical_notes: str | None = None


class CancerCaseUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    oncotree_code: str | None = Field(None, max_length=32)
    cancer_type: CancerTypeEnum | None = None
    histology: str | None = Field(None, max_length=256)
    stage: str | None = Field(None, max_length=32)
    diagnosis_date: date | None = None
    radioiodine_status: str | None = Field(None, max_length=64)
    recurrence_status: str | None = Field(None, max_length=64)
    metastatic_sites: list[str] | None = None
    treatment_history: list[dict] | None = None
    current_medications: list[dict] | None = None
    clinical_notes: str | None = None


class CancerCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    patient_id: str
    oncotree_code: str | None = None
    cancer_type: str
    histology: str | None = None
    stage: str | None = None
    diagnosis_date: date | None = None
    radioiodine_status: str | None = None
    recurrence_status: str | None = None
    metastatic_sites: list = []
    treatment_history: list = []
    current_medications: list = []
    clinical_notes: str | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _convert_uuids(cls, data):
        """Convert UUID fields to strings when using from_attributes."""
        if hasattr(data, "id") and not isinstance(data.id, str):
            data.id = str(data.id)
        if hasattr(data, "patient_id") and not isinstance(data.patient_id, str):
            data.patient_id = str(data.patient_id)
        return data


class CancerCaseListResponse(BaseModel):
    items: list[CancerCaseResponse]
    total: int
    skip: int
    limit: int
