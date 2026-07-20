"""
AnalysisRun domain model — ensures every analysis is reproducible.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Column, String, DateTime, BigInteger, Enum as SAEnum, ForeignKey, JSON
from sqlalchemy.orm import relationship

from src.backend.database.models import CompatUUID, Base as DBBase
from src.backend.domain.enums import AnalysisStatusEnum


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class AnalysisRunModel(DBBase):
    __tablename__ = "domain_analysis_runs"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    case_id = Column(CompatUUID, ForeignKey("domain_cancer_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    sequencing_test_id = Column(CompatUUID, ForeignKey("domain_sequencing_tests.id", ondelete="CASCADE"), nullable=True)
    status = Column(SAEnum(AnalysisStatusEnum), default=AnalysisStatusEnum.PENDING, nullable=False)
    pipeline_version = Column(String(64), nullable=True)
    dataset_version = Column(String(64), nullable=True)
    annotation_version = Column(String(64), nullable=True)
    evidence_version = Column(String(64), nullable=True)
    schema_version = Column(String(64), nullable=True)
    git_commit = Column(String(64), nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    duration_ms = Column(BigInteger, nullable=True)
    warnings = Column(JSON, default=list)
    errors = Column(JSON, default=list)
    input_manifest = Column(JSON, default=dict)
    output_manifest = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    cancer_case = relationship("CancerCaseModel", back_populates="analysis_runs")
    drug_candidates = relationship("DrugCandidateModel", back_populates="analysis_run", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AnalysisRunModel(id={self.id}, status={self.status})>"


class AnalysisRunCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    case_id: str
    sequencing_test_id: Optional[str] = None
    pipeline_version: Optional[str] = Field(None, max_length=64)
    dataset_version: Optional[str] = Field(None, max_length=64)
    annotation_version: Optional[str] = Field(None, max_length=64)
    evidence_version: Optional[str] = Field(None, max_length=64)
    schema_version: Optional[str] = Field(None, max_length=64)
    git_commit: Optional[str] = Field(None, max_length=64)


class AnalysisRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    case_id: str
    sequencing_test_id: Optional[str] = None
    status: str
    pipeline_version: Optional[str] = None
    dataset_version: Optional[str] = None
    annotation_version: Optional[str] = None
    evidence_version: Optional[str] = None
    schema_version: Optional[str] = None
    git_commit: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    warnings: list = []
    errors: list = []
    input_manifest: dict = {}
    output_manifest: dict = {}
    created_at: datetime
