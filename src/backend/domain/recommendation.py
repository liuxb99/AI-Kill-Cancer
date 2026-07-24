"""
Recommendation domain model — captures clinical recommendation outputs.

Each recommendation is produced by an engine run and carries the full
decision trace (steps) for auditability and explainability.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.backend.database.models import Base as DBBase
from src.backend.database.models import CompatUUID


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class RecommendationModel(DBBase):
    __tablename__ = "domain_recommendations"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    recommendation_id = Column(String(64), unique=True, nullable=False, index=True)
    patient_id = Column(CompatUUID, ForeignKey("domain_patients.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(CompatUUID, ForeignKey("domain_cancer_cases.id", ondelete="SET NULL"), nullable=True, index=True)
    trace_id = Column(String(64), nullable=True, index=True)
    engine_version = Column(String(32), nullable=False, default="1.0.0")
    status = Column(String(32), nullable=False, default="pending")
    request_payload = Column(JSON, nullable=True)
    result_payload = Column(JSON, nullable=True)
    report_html = Column(Text, nullable=True)
    created_by = Column(CompatUUID, ForeignKey("domain_users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    traces = relationship("RecommendationTraceModel", back_populates="recommendation", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self):
        return f"<RecommendationModel(id={self.id}, recommendation_id={self.recommendation_id!r}, status={self.status!r})>"


class RecommendationTraceModel(DBBase):
    __tablename__ = "domain_recommendation_traces"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    trace_id = Column(String(64), unique=True, nullable=False, index=True)
    recommendation_id = Column(CompatUUID, ForeignKey("domain_recommendations.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    recommendation = relationship("RecommendationModel", back_populates="traces")
    steps = relationship("RecommendationTraceStepModel", back_populates="trace", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self):
        return f"<RecommendationTraceModel(id={self.id}, trace_id={self.trace_id!r})>"


class RecommendationTraceStepModel(DBBase):
    __tablename__ = "domain_recommendation_trace_steps"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    trace_id = Column(CompatUUID, ForeignKey("domain_recommendation_traces.id", ondelete="CASCADE"), nullable=False, index=True)
    step_order = Column(Integer, nullable=False)
    step_type = Column(String(64), nullable=False)
    input_summary = Column(JSON, nullable=True)
    output_summary = Column(JSON, nullable=True)
    evidence_references = Column(JSON, nullable=True)
    weight = Column(Float, nullable=True)
    score = Column(Float, nullable=True)
    rank = Column(Integer, nullable=True)
    status = Column(String(32), nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    trace = relationship("RecommendationTraceModel", back_populates="steps", lazy="selectin")

    def __repr__(self):
        return f"<RecommendationTraceStepModel(id={self.id}, step_order={self.step_order}, step_type={self.step_type!r})>"
