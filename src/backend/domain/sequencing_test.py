"""
SequencingTest domain model.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Column, String, Date, DateTime, Float, Text, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship

from src.backend.database.models import CompatUUID, Base as DBBase
from src.backend.domain.enums import AnalysisResultTypeEnum


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class SequencingTestModel(DBBase):
    __tablename__ = "domain_sequencing_tests"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    specimen_id = Column(CompatUUID, ForeignKey("domain_specimens.id", ondelete="CASCADE"), nullable=False, index=True)
    laboratory = Column(String(256), nullable=True)
    assay_name = Column(String(256), nullable=False)
    assay_version = Column(String(64), nullable=True)
    panel_name = Column(String(256), nullable=True)
    genome_build = Column(String(32), nullable=True)
    sequencing_depth = Column(Float, nullable=True)
    minimum_detectable_vaf = Column(Float, nullable=True)
    test_date = Column(Date, nullable=True)
    result_type = Column(SAEnum(AnalysisResultTypeEnum), nullable=False)
    limitations = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    specimen = relationship("SpecimenModel", back_populates="sequencing_tests")
    uploaded_files = relationship("UploadedFileModel", back_populates="sequencing_test", cascade="all, delete-orphan")
    variants = relationship("VariantModel", back_populates="sequencing_test", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SequencingTestModel(id={self.id}, assay={self.assay_name!r})>"


class SequencingTestCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    specimen_id: str
    laboratory: Optional[str] = Field(None, max_length=256)
    assay_name: str = Field(..., max_length=256)
    assay_version: Optional[str] = Field(None, max_length=64)
    panel_name: Optional[str] = Field(None, max_length=256)
    genome_build: Optional[str] = Field(None, max_length=32)
    sequencing_depth: Optional[float] = None
    minimum_detectable_vaf: Optional[float] = None
    test_date: Optional[date] = None
    result_type: AnalysisResultTypeEnum = AnalysisResultTypeEnum.SOMATIC
    limitations: Optional[str] = None


class SequencingTestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    specimen_id: str
    laboratory: Optional[str] = None
    assay_name: str
    assay_version: Optional[str] = None
    panel_name: Optional[str] = None
    genome_build: Optional[str] = None
    sequencing_depth: Optional[float] = None
    minimum_detectable_vaf: Optional[float] = None
    test_date: Optional[date] = None
    result_type: str
    limitations: Optional[str] = None
    created_at: datetime
    updated_at: datetime
