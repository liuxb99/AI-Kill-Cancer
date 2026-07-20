"""
Evidence and EvidenceAssertion domain models.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Column, String, Text, Integer, Date, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship

from src.backend.database.models import CompatUUID, Base as DBBase
from src.backend.domain.enums import EvidenceDirectionEnum, EvidenceLevelEnum, EvidenceTypeEnum


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class EvidenceModel(DBBase):
    __tablename__ = "domain_evidences"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    evidence_type = Column(SAEnum(EvidenceTypeEnum), nullable=False)
    source_name = Column(String(128), nullable=False)
    source_record_id = Column(String(256), nullable=True, index=True)
    publication_id = Column(CompatUUID, ForeignKey("domain_publications.id", ondelete="SET NULL"), nullable=True)
    clinical_trial_id = Column(CompatUUID, ForeignKey("domain_clinical_trials.id", ondelete="SET NULL"), nullable=True)
    gene_symbol = Column(String(32), nullable=True, index=True)
    variant_id = Column(CompatUUID, ForeignKey("domain_variants.id", ondelete="SET NULL"), nullable=True)
    drug_id = Column(CompatUUID, ForeignKey("domain_drugs.id", ondelete="SET NULL"), nullable=True)
    cancer_type = Column(String(64), nullable=True, index=True)
    study_type = Column(String(64), nullable=True)
    sample_size = Column(Integer, nullable=True)
    evidence_direction = Column(SAEnum(EvidenceDirectionEnum), nullable=False)
    evidence_level = Column(SAEnum(EvidenceLevelEnum), nullable=False)
    quality = Column(String(32), nullable=True)
    summary = Column(Text, nullable=True)
    limitations = Column(Text, nullable=True)
    publication_date = Column(Date, nullable=True)
    retrieved_at = Column(DateTime, nullable=False)
    source_version = Column(String(64), nullable=True)
    license = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    publication = relationship("PublicationModel", back_populates="evidences")
    clinical_trial = relationship("ClinicalTrialModel", back_populates="evidences")

    def __repr__(self):
        return f"<EvidenceModel(id={self.id}, source={self.source_name}, direction={self.evidence_direction})>"


class EvidenceCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    evidence_type: EvidenceTypeEnum
    source_name: str = Field(..., max_length=128)
    source_record_id: Optional[str] = Field(None, max_length=256)
    publication_id: Optional[str] = None
    clinical_trial_id: Optional[str] = None
    gene_symbol: Optional[str] = Field(None, max_length=32)
    variant_id: Optional[str] = None
    drug_id: Optional[str] = None
    cancer_type: Optional[str] = Field(None, max_length=64)
    study_type: Optional[str] = Field(None, max_length=64)
    sample_size: Optional[int] = None
    evidence_direction: EvidenceDirectionEnum
    evidence_level: EvidenceLevelEnum
    quality: Optional[str] = Field(None, max_length=32)
    summary: Optional[str] = None
    limitations: Optional[str] = None
    publication_date: Optional[date] = None
    source_version: Optional[str] = Field(None, max_length=64)
    license: Optional[str] = Field(None, max_length=128)


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    evidence_type: str
    source_name: str
    source_record_id: Optional[str] = None
    publication_id: Optional[str] = None
    clinical_trial_id: Optional[str] = None
    gene_symbol: Optional[str] = None
    variant_id: Optional[str] = None
    drug_id: Optional[str] = None
    cancer_type: Optional[str] = None
    study_type: Optional[str] = None
    sample_size: Optional[int] = None
    evidence_direction: str
    evidence_level: str
    quality: Optional[str] = None
    summary: Optional[str] = None
    limitations: Optional[str] = None
    publication_date: Optional[date] = None
    retrieved_at: datetime
    source_version: Optional[str] = None
    license: Optional[str] = None
    created_at: datetime


class EvidenceSearchResult(BaseModel):
    status: str  # "found" | "not_found" | "not_searched" | "insufficient_data"
    items: list[EvidenceResponse]
    total: int
