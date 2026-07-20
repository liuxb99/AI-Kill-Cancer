"""
Specimen domain model — links a cancer case to a biological specimen.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Column, String, Date, DateTime, Boolean, Float, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship

from src.backend.database.models import CompatUUID, Base as DBBase
from src.backend.domain.enums import SpecimenTypeEnum


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class SpecimenModel(DBBase):
    __tablename__ = "domain_specimens"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    case_id = Column(CompatUUID, ForeignKey("domain_cancer_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    specimen_type = Column(SAEnum(SpecimenTypeEnum), nullable=False)
    collection_site = Column(String(256), nullable=True)
    collection_date = Column(Date, nullable=True)
    tumor_purity = Column(Float, nullable=True, comment="Estimated tumor purity (0.0–1.0)")
    matched_normal_available = Column(Boolean, default=False)
    storage_reference = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    cancer_case = relationship("CancerCaseModel", back_populates="specimens")
    sequencing_tests = relationship("SequencingTestModel", back_populates="specimen", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SpecimenModel(id={self.id}, type={self.specimen_type})>"


class SpecimenCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    case_id: str
    specimen_type: SpecimenTypeEnum
    collection_site: Optional[str] = Field(None, max_length=256)
    collection_date: Optional[date] = None
    tumor_purity: Optional[float] = Field(None, ge=0.0, le=1.0)
    matched_normal_available: bool = False
    storage_reference: Optional[str] = Field(None, max_length=256)


class SpecimenUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    specimen_type: Optional[SpecimenTypeEnum] = None
    collection_site: Optional[str] = Field(None, max_length=256)
    collection_date: Optional[date] = None
    tumor_purity: Optional[float] = Field(None, ge=0.0, le=1.0)
    matched_normal_available: Optional[bool] = None
    storage_reference: Optional[str] = Field(None, max_length=256)


class SpecimenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    case_id: str
    specimen_type: str
    collection_site: Optional[str] = None
    collection_date: Optional[date] = None
    tumor_purity: Optional[float] = None
    matched_normal_available: bool = False
    storage_reference: Optional[str] = None
    created_at: datetime
    updated_at: datetime
