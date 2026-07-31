"""PTC therapy, evidence, and clinical-trial knowledge models."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from src.backend.database.models import Base, CompatUUID


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class PTCTherapyModel(Base):
    __tablename__ = "domain_ptc_therapies"
    __table_args__ = (UniqueConstraint("source_name", "source_record_id", name="uq_ptc_therapy_source"),)

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    therapy_key = Column(String(160), nullable=False, unique=True, index=True)
    name = Column(String(256), nullable=False, index=True)
    generic_name = Column(String(256), nullable=True)
    therapy_type = Column(String(64), nullable=False, default="drug")
    approval_status = Column(String(128), nullable=True)
    indications = Column(JSON, nullable=False, default=list)
    mechanism = Column(Text, nullable=True)
    dosage_and_administration = Column(Text, nullable=True)
    warnings = Column(JSON, nullable=False, default=list)
    source_name = Column(String(64), nullable=False)
    source_record_id = Column(String(256), nullable=False)
    source_url = Column(String(1024), nullable=True)
    source_version = Column(String(64), nullable=True)
    retrieved_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    targets = relationship("PTCTherapyTargetModel", back_populates="therapy", cascade="all, delete-orphan")
    evidences = relationship("PTCEvidenceRecordModel", back_populates="therapy")


class PTCTherapyTargetModel(Base):
    __tablename__ = "domain_ptc_therapy_targets"
    __table_args__ = (UniqueConstraint("therapy_id", "gene_symbol", "variant", name="uq_ptc_therapy_target"),)

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    therapy_id = Column(CompatUUID, ForeignKey("domain_ptc_therapies.id", ondelete="CASCADE"), nullable=False, index=True)
    gene_symbol = Column(String(32), nullable=False, index=True)
    variant = Column(String(128), nullable=True, index=True)
    target_type = Column(String(64), nullable=True)
    interaction_type = Column(String(128), nullable=True)
    evidence_level = Column(String(64), nullable=True)
    source_record_id = Column(String(256), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    therapy = relationship("PTCTherapyModel", back_populates="targets")


class PTCClinicalTrialModel(Base):
    __tablename__ = "domain_ptc_clinical_trials"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    nct_id = Column(String(32), nullable=False, unique=True, index=True)
    brief_title = Column(String(1024), nullable=False)
    official_title = Column(Text, nullable=True)
    overall_status = Column(String(64), nullable=True, index=True)
    phases = Column(JSON, nullable=False, default=list)
    study_type = Column(String(64), nullable=True)
    conditions = Column(JSON, nullable=False, default=list)
    interventions = Column(JSON, nullable=False, default=list)
    target_genes = Column(JSON, nullable=False, default=list)
    eligibility = Column(Text, nullable=True)
    enrollment = Column(Integer, nullable=True)
    locations = Column(JSON, nullable=False, default=list)
    start_date = Column(String(32), nullable=True)
    completion_date = Column(String(32), nullable=True)
    source_url = Column(String(1024), nullable=True)
    source_version = Column(String(64), nullable=True)
    last_update_posted = Column(String(32), nullable=True)
    retrieved_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    evidences = relationship("PTCEvidenceRecordModel", back_populates="clinical_trial")


class PTCEvidenceRecordModel(Base):
    __tablename__ = "domain_ptc_evidence_records"
    __table_args__ = (UniqueConstraint("source_name", "source_record_id", name="uq_ptc_evidence_source"),)

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    evidence_key = Column(String(256), nullable=False, unique=True, index=True)
    source_name = Column(String(64), nullable=False, index=True)
    source_record_id = Column(String(256), nullable=False)
    title = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    evidence_type = Column(String(64), nullable=False)
    evidence_level = Column(String(64), nullable=True, index=True)
    direction = Column(String(32), nullable=True)
    gene_symbol = Column(String(32), nullable=True, index=True)
    variant = Column(String(128), nullable=True, index=True)
    disease = Column(String(128), nullable=False, default="papillary_thyroid_carcinoma")
    therapy_id = Column(CompatUUID, ForeignKey("domain_ptc_therapies.id", ondelete="SET NULL"), nullable=True, index=True)
    clinical_trial_id = Column(CompatUUID, ForeignKey("domain_ptc_clinical_trials.id", ondelete="SET NULL"), nullable=True)
    publication_id = Column(String(64), nullable=True)
    citation = Column(Text, nullable=True)
    source_url = Column(String(1024), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    retrieved_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    therapy = relationship("PTCTherapyModel", back_populates="evidences")
    clinical_trial = relationship("PTCClinicalTrialModel", back_populates="evidences")

    @property
    def genes(self) -> list[str]:
        """Compatibility view used by the integrated research engine."""
        return [self.gene_symbol] if self.gene_symbol else []


class PTCTherapyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    therapy_key: str
    name: str
    generic_name: str | None = None
    therapy_type: str
    approval_status: str | None = None
    indications: list
    mechanism: str | None = None
    warnings: list
    source_name: str
    source_record_id: str
    source_url: str | None = None


class PTCTrialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nct_id: str
    brief_title: str
    overall_status: str | None = None
    phases: list
    conditions: list
    interventions: list
    target_genes: list
    enrollment: int | None = None
    locations: list
    source_url: str | None = None


class PTCEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_key: str
    source_name: str
    title: str | None = None
    summary: str | None = None
    evidence_type: str
    evidence_level: str | None = None
    direction: str | None = None
    gene_symbol: str | None = None
    variant: str | None = None
    citation: str | None = None
    source_url: str | None = None


__all__ = [
    "PTCTherapyModel",
    "PTCTherapyTargetModel",
    "PTCClinicalTrialModel",
    "PTCEvidenceRecordModel",
    "PTCTherapyResponse",
    "PTCTrialResponse",
    "PTCEvidenceResponse",
]
