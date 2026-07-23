"""
Evidence and EvidenceAssertion domain models.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

from src.backend.database.models import Base as DBBase
from src.backend.database.models import CompatUUID
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
    source_record_id: str | None = Field(None, max_length=256)
    publication_id: str | None = None
    clinical_trial_id: str | None = None
    gene_symbol: str | None = Field(None, max_length=32)
    variant_id: str | None = None
    drug_id: str | None = None
    cancer_type: str | None = Field(None, max_length=64)
    study_type: str | None = Field(None, max_length=64)
    sample_size: int | None = None
    evidence_direction: EvidenceDirectionEnum
    evidence_level: EvidenceLevelEnum
    quality: str | None = Field(None, max_length=32)
    summary: str | None = None
    limitations: str | None = None
    publication_date: date | None = None
    source_version: str | None = Field(None, max_length=64)
    license: str | None = Field(None, max_length=128)


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    evidence_type: str
    source_name: str
    source_record_id: str | None = None
    publication_id: str | None = None
    clinical_trial_id: str | None = None
    gene_symbol: str | None = None
    variant_id: str | None = None
    drug_id: str | None = None
    cancer_type: str | None = None
    study_type: str | None = None
    sample_size: int | None = None
    evidence_direction: str
    evidence_level: str
    quality: str | None = None
    summary: str | None = None
    limitations: str | None = None
    publication_date: date | None = None
    retrieved_at: datetime
    source_version: str | None = None
    license: str | None = None
    created_at: datetime


class EvidenceSearchResult(BaseModel):
    status: str  # "found" | "not_found" | "not_searched" | "insufficient_data"
    items: list[EvidenceResponse]
    total: int
