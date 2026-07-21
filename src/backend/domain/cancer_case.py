"""
CancerCase domain model — links a patient to a specific thyroid cancer diagnosis.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, model_validator
from sqlalchemy import Column, String, Text, Date, DateTime, Enum as SAEnum, ForeignKey, JSON
from sqlalchemy.orm import relationship

from src.backend.database.models import CompatUUID, Base as DBBase
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
    oncotree_code: Optional[str] = Field(None, max_length=32)
    cancer_type: CancerTypeEnum
    histology: Optional[str] = Field(None, max_length=256)
    stage: Optional[str] = Field(None, max_length=32)
    diagnosis_date: Optional[date] = None
    radioiodine_status: Optional[str] = Field(None, max_length=64)
    recurrence_status: Optional[str] = Field(None, max_length=64)
    metastatic_sites: Optional[list[str]] = None
    treatment_history: Optional[list[dict]] = None
    current_medications: Optional[list[dict]] = None
    clinical_notes: Optional[str] = None


class CancerCaseUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    oncotree_code: Optional[str] = Field(None, max_length=32)
    cancer_type: Optional[CancerTypeEnum] = None
    histology: Optional[str] = Field(None, max_length=256)
    stage: Optional[str] = Field(None, max_length=32)
    diagnosis_date: Optional[date] = None
    radioiodine_status: Optional[str] = Field(None, max_length=64)
    recurrence_status: Optional[str] = Field(None, max_length=64)
    metastatic_sites: Optional[list[str]] = None
    treatment_history: Optional[list[dict]] = None
    current_medications: Optional[list[dict]] = None
    clinical_notes: Optional[str] = None


class CancerCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    patient_id: str
    oncotree_code: Optional[str] = None
    cancer_type: str
    histology: Optional[str] = None
    stage: Optional[str] = None
    diagnosis_date: Optional[date] = None
    radioiodine_status: Optional[str] = None
    recurrence_status: Optional[str] = None
    metastatic_sites: list = []
    treatment_history: list = []
    current_medications: list = []
    clinical_notes: Optional[str] = None
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
