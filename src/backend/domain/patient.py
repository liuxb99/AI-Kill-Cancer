"""
Patient domain model.

Patients are de-identified research subjects. Avoid storing full names,
government IDs, or other highly sensitive identifiers unless strictly
necessary for clinical matching.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

from src.backend.database.models import Base as DBBase
from src.backend.database.models import CompatUUID
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

    external_id: str | None = Field(None, max_length=128)
    display_name: str | None = Field(None, max_length=128)
    birth_year: int | None = Field(None, ge=1900, le=2100)
    age_range: str | None = Field(None, max_length=32)
    sex: SexEnum | None = None
    consent_status: ConsentStatusEnum = ConsentStatusEnum.PENDING


class PatientUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    external_id: str | None = Field(None, max_length=128)
    display_name: str | None = Field(None, max_length=128)
    birth_year: int | None = Field(None, ge=1900, le=2100)
    age_range: str | None = Field(None, max_length=32)
    sex: SexEnum | None = None
    consent_status: ConsentStatusEnum | None = None


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str = Field(..., description="Patient UUID as string")
    external_id: str | None = None
    display_name: str | None = None
    birth_year: int | None = None
    age_range: str | None = None
    sex: str | None = None
    consent_status: str
    created_at: datetime
    updated_at: datetime

    @field_serializer("id")
    @classmethod
    def serialize_id(cls, v: Any) -> str:
        if isinstance(v, uuid.UUID):
            return str(v)
        return v

    @field_validator("id", mode="before")
    @classmethod
    def validate_id(cls, v: Any) -> str:
        if isinstance(v, uuid.UUID):
            return str(v)
        return v


class PatientListResponse(BaseModel):
    items: list[PatientResponse]
    total: int
    skip: int
    limit: int
