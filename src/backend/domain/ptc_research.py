"""Canonical papillary thyroid carcinoma research data models.

This module stores normalized, de-identified public research records.  It is
separate from patient-care records so TCGA/GDC data cannot be confused with a
real clinical patient.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from src.backend.database.models import Base, CompatUUID


class PTCResearchCaseModel(Base):
    __tablename__ = "domain_ptc_research_cases"
    __table_args__ = (
        UniqueConstraint("source_dataset", "case_id", name="uq_ptc_case_source_id"),
    )

    id = Column(CompatUUID, primary_key=True, default=uuid.uuid4)
    case_id = Column(String(128), nullable=False, index=True)
    source_dataset = Column(String(64), nullable=False, default="TCGA-THCA", index=True)
    source_project = Column(String(64), nullable=False, default="TCGA-THCA")
    disease = Column(String(128), nullable=False, default="papillary_thyroid_carcinoma", index=True)
    sex = Column(String(32), nullable=True)
    age_range = Column(String(32), nullable=True)
    pathologic_stage = Column(String(64), nullable=True)
    t_status = Column(String(32), nullable=True)
    n_status = Column(String(32), nullable=True)
    m_status = Column(String(32), nullable=True)
    vital_status = Column(String(32), nullable=True)
    days_to_last_follow_up = Column(Integer, nullable=True)
    days_to_death = Column(Integer, nullable=True)
    source_record_id = Column(String(256), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    variants = relationship(
        "PTCVariantModel",
        back_populates="research_case",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    outcomes = relationship(
        "PTCOutcomeModel",
        back_populates="research_case",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PTCVariantModel(Base):
    __tablename__ = "domain_ptc_variants"
    __table_args__ = (
        UniqueConstraint("source_dataset", "variant_id", name="uq_ptc_variant_source_id"),
    )

    id = Column(CompatUUID, primary_key=True, default=uuid.uuid4)
    variant_id = Column(String(256), nullable=False, index=True)
    research_case_id = Column(
        CompatUUID,
        ForeignKey("domain_ptc_research_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    case_id = Column(String(128), nullable=False, index=True)
    source_dataset = Column(String(64), nullable=False, default="TCGA-THCA", index=True)
    gene = Column(String(64), nullable=False, index=True)
    chromosome = Column(String(32), nullable=True)
    position = Column(Integer, nullable=True)
    reference = Column(Text, nullable=True)
    alternate = Column(Text, nullable=True)
    variant_type = Column(String(64), nullable=True)
    classification = Column(String(128), nullable=True)
    protein_change = Column(String(128), nullable=True)
    source_record_id = Column(String(256), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    research_case = relationship("PTCResearchCaseModel", back_populates="variants")


class PTCOutcomeModel(Base):
    __tablename__ = "domain_ptc_outcomes"
    __table_args__ = (
        UniqueConstraint("source_dataset", "outcome_id", name="uq_ptc_outcome_source_id"),
    )

    id = Column(CompatUUID, primary_key=True, default=uuid.uuid4)
    outcome_id = Column(String(256), nullable=False, index=True)
    research_case_id = Column(
        CompatUUID,
        ForeignKey("domain_ptc_research_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    case_id = Column(String(128), nullable=False, index=True)
    source_dataset = Column(String(64), nullable=False, default="TCGA-THCA", index=True)
    outcome_type = Column(String(64), nullable=False)
    outcome_value = Column(String(256), nullable=True)
    observed_at = Column(DateTime, nullable=True)
    source_record_id = Column(String(256), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    research_case = relationship("PTCResearchCaseModel", back_populates="outcomes")


class PTCImportBatchModel(Base):
    __tablename__ = "domain_ptc_import_batches"

    id = Column(CompatUUID, primary_key=True, default=uuid.uuid4)
    batch_id = Column(String(64), unique=True, nullable=False, index=True)
    source_dataset = Column(String(64), nullable=False, default="TCGA-THCA")
    source_version = Column(String(128), nullable=True)
    status = Column(String(32), nullable=False, default="running", index=True)
    record_count = Column(Integer, nullable=False, default=0)
    error_count = Column(Integer, nullable=False, default=0)
    checksum = Column(String(128), nullable=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class PTCVariantInput(BaseModel):
    variant_id: Optional[str] = None
    gene: str = Field(min_length=1, max_length=64)
    chromosome: Optional[str] = None
    position: Optional[int] = None
    reference: Optional[str] = None
    alternate: Optional[str] = None
    variant_type: Optional[str] = None
    classification: Optional[str] = None
    protein_change: Optional[str] = None
    source_record_id: Optional[str] = None


class PTCOutcomeInput(BaseModel):
    outcome_id: Optional[str] = None
    outcome_type: str = Field(min_length=1, max_length=64)
    outcome_value: Optional[str] = None
    observed_at: Optional[datetime] = None
    source_record_id: Optional[str] = None


class PTCResearchCaseInput(BaseModel):
    case_id: str = Field(min_length=1, max_length=128)
    source_dataset: str = "TCGA-THCA"
    source_project: str = "TCGA-THCA"
    sex: Optional[str] = None
    age_range: Optional[str] = None
    pathologic_stage: Optional[str] = None
    t_status: Optional[str] = None
    n_status: Optional[str] = None
    m_status: Optional[str] = None
    vital_status: Optional[str] = None
    days_to_last_follow_up: Optional[int] = None
    days_to_death: Optional[int] = None
    source_record_id: Optional[str] = None
    variants: list[PTCVariantInput] = Field(default_factory=list)
    outcomes: list[PTCOutcomeInput] = Field(default_factory=list)


class PTCResearchCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: str
    source_dataset: str
    source_project: str
    disease: str
    sex: Optional[str]
    age_range: Optional[str]
    pathologic_stage: Optional[str]
    t_status: Optional[str]
    n_status: Optional[str]
    m_status: Optional[str]
    vital_status: Optional[str]
    days_to_last_follow_up: Optional[int]
    days_to_death: Optional[int]
    variants: list[PTCVariantInput] = Field(default_factory=list)
    outcomes: list[PTCOutcomeInput] = Field(default_factory=list)


__all__ = [
    "PTCResearchCaseModel",
    "PTCVariantModel",
    "PTCOutcomeModel",
    "PTCImportBatchModel",
    "PTCResearchCaseInput",
    "PTCResearchCaseResponse",
    "PTCVariantInput",
    "PTCOutcomeInput",
]
