"""
Report domain model.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON

from src.backend.database.models import CompatUUID, Base as DBBase


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class ReportModel(DBBase):
    __tablename__ = "domain_reports"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    analysis_run_id = Column(CompatUUID, ForeignKey("domain_analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    report_type = Column(String(64), nullable=False)  # "patient" | "professional" | "molecular_tumor_board"
    title = Column(String(512), nullable=False)
    content = Column(JSON, default=dict)
    version = Column(String(32), nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ReportModel(id={self.id}, type={self.report_type})>"
