"""
Tumor Board domain models — consensus tracking for multi-disciplinary review.

Each TumorBoardConsensus captures the outcome of a multi-disciplinary review
of a clinical recommendation, including participant opinions, dissenting views,
and the reasoning trace that led to the final consensus.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from src.backend.database.models import Base as DBBase
from src.backend.database.models import CompatUUID


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class TumorBoardConsensusModel(DBBase):
    __tablename__ = "domain_tumor_board_consensus"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    consensus_id = Column(String(64), unique=True, nullable=False, index=True)
    patient_id = Column(CompatUUID, ForeignKey("domain_patients.id", ondelete="CASCADE"), nullable=False, index=True)
    recommendation_id = Column(CompatUUID, ForeignKey("domain_recommendations.id", ondelete="SET NULL"), nullable=True, index=True)
    clinical_decision_id = Column(CompatUUID, ForeignKey("domain_clinical_decisions.id", ondelete="SET NULL"), nullable=True, index=True)
    consensus_status = Column(String(32), nullable=False, default="unanimous")
    consensus_score = Column(Float, nullable=True)
    final_recommendation = Column(Text, nullable=True)
    supporting_rationale = Column(Text, nullable=True)
    dissenting_opinions = Column(JSON, nullable=True)
    unresolved_questions = Column(JSON, nullable=True)
    required_follow_up = Column(JSON, nullable=True)
    participating_specialties = Column(JSON, nullable=True)
    created_by = Column(CompatUUID, ForeignKey("domain_users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    opinions = relationship(
        "TumorBoardOpinionModel",
        back_populates="consensus",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    traces = relationship(
        "TumorBoardConsensusTraceModel",
        back_populates="consensus",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="TumorBoardConsensusTraceModel.step_order",
    )

    def __repr__(self):
        return (
            f"<TumorBoardConsensusModel(id={self.id}, "
            f"consensus_id={self.consensus_id!r}, "
            f"consensus_status={self.consensus_status!r})>"
        )


class TumorBoardOpinionModel(DBBase):
    __tablename__ = "domain_tumor_board_opinions"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    consensus_id = Column(
        CompatUUID,
        ForeignKey("domain_tumor_board_consensus.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    specialty = Column(String(64), nullable=False)
    participant_id = Column(String(128), nullable=True)
    position = Column(String(32), nullable=False)  # support / oppose / abstain
    confidence = Column(Float, nullable=False, default=0.5)
    rationale = Column(Text, nullable=True)
    supporting_evidence = Column(JSON, nullable=True)
    contraindications = Column(JSON, nullable=True)
    preferred_option = Column(Text, nullable=True)
    alternative_option = Column(Text, nullable=True)
    requires_more_information = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    consensus = relationship("TumorBoardConsensusModel", back_populates="opinions", lazy="selectin")

    def __repr__(self):
        return (
            f"<TumorBoardOpinionModel(id={self.id}, "
            f"specialty={self.specialty!r}, "
            f"position={self.position!r})>"
        )


class TumorBoardConsensusTraceModel(DBBase):
    __tablename__ = "domain_tumor_board_consensus_traces"
    __table_args__ = (
        UniqueConstraint("trace_id", "step_order", name="uq_tbc_trace_step"),
    )

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    trace_id = Column(String(64), nullable=False, index=True)
    consensus_id = Column(
        CompatUUID,
        ForeignKey("domain_tumor_board_consensus.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_order = Column(Integer, nullable=False)
    step_type = Column(String(64), nullable=False)
    input_summary = Column(JSON, nullable=True)
    output_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    consensus = relationship("TumorBoardConsensusModel", back_populates="traces", lazy="selectin")

    def __repr__(self):
        return (
            f"<TumorBoardConsensusTraceModel(id={self.id}, "
            f"trace_id={self.trace_id!r}, "
            f"step_order={self.step_order})>"
        )
