"""Clinical Graph Outbox Model — Transactional Outbox for Knowledge Graph."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, JSON, String, Text
from src.backend.database.models import Base, CompatUUID


class ClinicalGraphOutboxModel(Base):
    __tablename__ = "domain_clinical_graph_outbox"

    id = Column(CompatUUID, primary_key=True, default=uuid.uuid4)
    event_id = Column(String(64), unique=True, nullable=False, index=True)
    correlation_id = Column(String(64), nullable=True, index=True)
    causation_id = Column(String(64), nullable=True)
    aggregate_type = Column(String(64), nullable=False, index=True)
    aggregate_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)
    schema_version = Column(Integer, nullable=False, default=1)
    payload = Column(JSON, nullable=False)
    status = Column(String(32), nullable=False, default="pending", index=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    actor_id = Column(String(64), nullable=True, index=True)
    claim_token = Column(String(64), nullable=True)
    available_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    occurred_at = Column(DateTime, nullable=True)
    processing_started_at = Column(DateTime, nullable=True)
    last_failed_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


__all__ = ["ClinicalGraphOutboxModel"]
