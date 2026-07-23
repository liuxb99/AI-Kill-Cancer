"""
DrugCandidate domain model.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

from src.backend.database.models import Base as DBBase
from src.backend.database.models import CompatUUID
from src.backend.domain.enums import CandidateCategoryEnum, EvidenceLevelEnum


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class DrugCandidateModel(DBBase):
    __tablename__ = "domain_drug_candidates"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    analysis_run_id = Column(CompatUUID, ForeignKey("domain_analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    drug_id = Column(CompatUUID, ForeignKey("domain_drugs.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(CompatUUID, ForeignKey("domain_variants.id", ondelete="SET NULL"), nullable=True)
    cancer_type = Column(String(64), nullable=False, index=True)
    candidate_category = Column(SAEnum(CandidateCategoryEnum), nullable=False)
    approval_status = Column(String(64), nullable=True)
    off_label = Column(String(64), nullable=True)
    clinical_trial_available = Column(String(64), nullable=True)
    mechanism = Column(Text, nullable=True)
    molecular_rationale = Column(Text, nullable=True)
    evidence_level = Column(SAEnum(EvidenceLevelEnum), nullable=False)
    confidence = Column(String(32), nullable=True)
    score = Column(Float, nullable=True)
    supporting_evidence_ids = Column(JSON, default=list)
    conflicting_evidence_ids = Column(JSON, default=list)
    limitations = Column(Text, nullable=True)
    safety_notes = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    analysis_run = relationship("AnalysisRunModel", back_populates="drug_candidates")
    drug = relationship("DrugModel", back_populates="drug_candidates")
    variant = relationship("VariantModel", back_populates="drug_candidates")

    def __repr__(self):
        return f"<DrugCandidateModel(id={self.id}, category={self.candidate_category})>"


class DrugCandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    analysis_run_id: str
    drug_id: str
    variant_id: str | None = None
    cancer_type: str
    candidate_category: str
    approval_status: str | None = None
    off_label: str | None = None
    clinical_trial_available: str | None = None
    mechanism: str | None = None
    molecular_rationale: str | None = None
    evidence_level: str
    confidence: str | None = None
    score: float | None = None
    supporting_evidence_ids: list = []
    conflicting_evidence_ids: list = []
    limitations: str | None = None
    safety_notes: str | None = None
    explanation: str | None = None
    created_at: datetime


class DrugCandidateListResponse(BaseModel):
    items: list[DrugCandidateResponse]
    total: int
