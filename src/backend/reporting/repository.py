"""
ReportRepository — persists clinical reports with versioning.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Text, DateTime, JSON, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.models import CompatUUID, Base as DBBase


class ClinicalReportModel(DBBase):
    """Persistent storage for a clinical report."""
    __tablename__ = "domain_clinical_reports"

    id = Column(CompatUUID, primary_key=True, default=uuid.uuid4)
    case_id = Column(String(36), nullable=True, index=True)
    version = Column(String(32), nullable=False, default="1.0.0")
    supersedes_report_id = Column(String(36), nullable=True)
    status = Column(String(32), nullable=False, default="draft")
    report_data = Column(JSON, nullable=False)
    html_content = Column(Text, nullable=True)
    fhir_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ReportRepository:
    """Repository for ClinicalReportModel with versioning."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, report_data: dict, html_content: str = "",
                      fhir_data: Optional[dict] = None) -> ClinicalReportModel:
        """Create a new report."""
        instance = ClinicalReportModel(
            case_id=report_data.get("metadata", {}).get("case_id"),
            version=report_data.get("metadata", {}).get("version", "1.0.0"),
            supersedes_report_id=report_data.get("metadata", {}).get("supersedes_report_id"),
            status=report_data.get("metadata", {}).get("status", "draft"),
            report_data=report_data,
            html_content=html_content,
            fhir_data=fhir_data,
        )
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def get(self, report_id: uuid.UUID) -> Optional[ClinicalReportModel]:
        stmt = select(ClinicalReportModel).where(ClinicalReportModel.id == report_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(self, report_id: uuid.UUID, status: str) -> Optional[ClinicalReportModel]:
        instance = await self.get(report_id)
        if not instance:
            return None
        instance.status = status
        instance.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def list_by_case(self, case_id: str, limit: int = 10) -> list[ClinicalReportModel]:
        stmt = (select(ClinicalReportModel)
                .where(ClinicalReportModel.case_id == case_id)
                .order_by(ClinicalReportModel.created_at.desc())
                .limit(limit))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
