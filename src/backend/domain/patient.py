"""
Patient domain model.

Patients are de-identified research subjects. Avoid storing full names,
government IDs, or other highly sensitive identifiers unless strictly
necessary for clinical matching.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Column, String, Integer, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship

from src.backend.database.models import CompatUUID, Base as DBBase
from src.backend.domain.enums import ConsentStatusEnum, SexEnum


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


# ─── SQLAlchemy Model ─────────────────────────────────────────────────────────

class PatientModel(DBBase):
    __tablename__ = "domain_patients"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    external_id = Column(String(128), unique=True, nullable=True, index=True)
    display_name = Column(String(128), nullable=True, comment="Anonymous display code")
    birth_year = Column(Integer, nullable=True)
    age_range = Column(String(32), nullable=True)
    sex = Column(SAEnum(SexEnum), nullable=True)
    consent_status = Column(SAEnum(ConsentStatusEnum), default=ConsentStatusEnum.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    cancer_cases = relationship("CancerCaseModel", back_populates="patient", cascade="all, delete-orphan")
    consents = relationship("ConsentModel", back_populates="patient", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PatientModel(id={self.id}, display_name={self.display_name!r})>"


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────


class PatientCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    external_id: Optional[str] = Field(None, max_length=128)
    display_name: Optional[str] = Field(None, max_length=128)
    birth_year: Optional[int] = Field(None, ge=1900, le=2100)
    age_range: Optional[str] = Field(None, max_length=32)
    sex: Optional[SexEnum] = None
    consent_status: ConsentStatusEnum = ConsentStatusEnum.PENDING


class PatientUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    external_id: Optional[str] = Field(None, max_length=128)
    display_name: Optional[str] = Field(None, max_length=128)
    birth_year: Optional[int] = Field(None, ge=1900, le=2100)
    age_range: Optional[str] = Field(None, max_length=32)
    sex: Optional[SexEnum] = None
    consent_status: Optional[ConsentStatusEnum] = None


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str = Field(..., description="Patient UUID as string")
    external_id: Optional[str] = None
    display_name: Optional[str] = None
    birth_year: Optional[int] = None
    age_range: Optional[str] = None
    sex: Optional[str] = None
    consent_status: str
    created_at: datetime
    updated_at: datetime


class PatientListResponse(BaseModel):
    items: list[PatientResponse]
    total: int
    skip: int
    limit: int
