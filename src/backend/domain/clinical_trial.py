"""
ClinicalTrial domain model.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from src.backend.database.models import Base as DBBase
from src.backend.database.models import CompatUUID


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class ClinicalTrialModel(DBBase):
    __tablename__ = "domain_clinical_trials"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    nct_id = Column(String(32), unique=True, nullable=True, index=True)
    title = Column(String(1024), nullable=False)
    phase = Column(String(32), nullable=True)
    status = Column(String(64), nullable=True)
    conditions = Column(JSON, default=list)
    interventions = Column(JSON, default=list)
    biomarkers = Column(JSON, default=list)
    sponsor = Column(String(256), nullable=True)
    locations = Column(JSON, default=list)
    enrollment = Column(Integer, nullable=True)
    start_date = Column(Date, nullable=True)
    completion_date = Column(Date, nullable=True)
    url = Column(String(1024), nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    evidences = relationship("EvidenceModel", back_populates="clinical_trial")

    def __repr__(self):
        return f"<ClinicalTrialModel(id={self.id}, nct_id={self.nct_id!r})>"
