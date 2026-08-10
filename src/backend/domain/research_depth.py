from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint

from src.backend.database.models import Base, CompatUUID


class ResearchHypothesisModel(Base):
    """Versioned research-only hypothesis; never a clinical recommendation."""

    __tablename__ = "domain_research_hypotheses"
    __table_args__ = (
        UniqueConstraint("hypothesis_key", "version", name="uq_research_hypothesis_version"),
    )

    id = Column(CompatUUID, primary_key=True, default=uuid.uuid4)
    hypothesis_key = Column(String(256), nullable=False, index=True)
    gene_symbol = Column(String(32), nullable=False, index=True)
    protein_change = Column(String(128), nullable=True)
    hypothesis_type = Column(String(64), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="open", index=True)
    claim = Column(Text, nullable=False)
    rationale = Column(JSON, nullable=False, default=dict)
    supporting_observations = Column(JSON, nullable=False, default=list)
    counter_evidence = Column(JSON, nullable=False, default=list)
    uncertainties = Column(JSON, nullable=False, default=list)
    falsification_criteria = Column(Text, nullable=False)
    next_data_needed = Column(JSON, nullable=False, default=list)
    input_fingerprint = Column(String(128), nullable=False, index=True)
    clinical_use = Column(String(8), nullable=False, default="false")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ResearchRunModel(Base):
    """One deterministic controlled research-loop execution."""

    __tablename__ = "domain_research_runs"

    id = Column(CompatUUID, primary_key=True, default=uuid.uuid4)
    run_key = Column(String(128), unique=True, nullable=False, index=True)
    gene_symbol = Column(String(32), nullable=False, index=True)
    protein_change = Column(String(128), nullable=True)
    input_fingerprint = Column(String(128), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="completed", index=True)
    trace = Column(JSON, nullable=False, default=list)
    result_summary = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ResearchEventModel(Base):
    """Longitudinal event in the research digital thread."""

    __tablename__ = "domain_research_events"

    id = Column(CompatUUID, primary_key=True, default=uuid.uuid4)
    event_key = Column(String(256), unique=True, nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    gene_symbol = Column(String(32), nullable=True, index=True)
    hypothesis_id = Column(
        CompatUUID,
        ForeignKey("domain_research_hypotheses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    run_id = Column(
        CompatUUID,
        ForeignKey("domain_research_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    observed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    date_semantics = Column(String(32), nullable=False, default="generated_at")
    source_type = Column(String(64), nullable=False)
    source_id = Column(String(256), nullable=True)
    provenance = Column(JSON, nullable=False, default=dict)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


__all__ = ["ResearchHypothesisModel", "ResearchRunModel", "ResearchEventModel"]
