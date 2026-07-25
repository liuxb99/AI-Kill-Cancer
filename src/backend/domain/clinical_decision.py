"""
Clinical Decision domain model — captures clinical decision outputs.

Each decision is produced by a clinical reasoning engine and carries the
full decision trace (steps) for auditability and explainability.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.backend.database.models import Base as DBBase
from src.backend.database.models import CompatUUID


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class ClinicalDecisionModel(DBBase):
    __tablename__ = "domain_clinical_decisions"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    decision_id = Column(String(64), unique=True, nullable=False, index=True)
    patient_id = Column(CompatUUID, ForeignKey("domain_patients.id", ondelete="CASCADE"), nullable=False, index=True)
    recommendation_id = Column(CompatUUID, ForeignKey("domain_recommendations.id", ondelete="SET NULL"), nullable=True, index=True)
    decision_type = Column(String(64), nullable=False)
    reason = Column(Text, nullable=False)
    evidence_summary = Column(JSON, nullable=True)
    confidence = Column(String(32), nullable=False)
    alternatives = Column(JSON, nullable=True)
    contraindications = Column(JSON, nullable=True)
    status = Column(String(32), nullable=False, default="active")
    created_by = Column(CompatUUID, ForeignKey("domain_users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    traces = relationship("ClinicalDecisionTraceModel", back_populates="clinical_decision", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self):
        return f"<ClinicalDecisionModel(id={self.id}, decision_id={self.decision_id!r}, decision_type={self.decision_type!r})>"


class ClinicalDecisionTraceModel(DBBase):
    __tablename__ = "domain_clinical_decision_traces"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    trace_id = Column(String(64), unique=True, nullable=False, index=True)
    clinical_decision_id = Column(CompatUUID, ForeignKey("domain_clinical_decisions.id", ondelete="CASCADE"), nullable=True, index=True)
    recommendation_id = Column(CompatUUID, ForeignKey("domain_recommendations.id", ondelete="SET NULL"), nullable=True, index=True)
    step_order = Column(Integer, nullable=False)
    step_type = Column(String(64), nullable=False)
    input_summary = Column(JSON, nullable=True)
    output_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    clinical_decision = relationship("ClinicalDecisionModel", back_populates="traces", lazy="selectin")

    def __repr__(self):
        return f"<ClinicalDecisionTraceModel(id={self.id}, trace_id={self.trace_id!r}, step_order={self.step_order})>"
