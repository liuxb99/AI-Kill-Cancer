"""
AuditLog domain model.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, Column, DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum

from src.backend.database.models import Base as DBBase
from src.backend.database.models import CompatUUID
from src.backend.domain.enums import AuditActionEnum


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class AuditLogModel(DBBase):
    __tablename__ = "domain_audit_logs"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    patient_id = Column(CompatUUID, ForeignKey("domain_patients.id", ondelete="SET NULL"), nullable=True, index=True)
    actor = Column(String(256), nullable=True)
    action = Column(SAEnum(AuditActionEnum), nullable=False)
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(String(128), nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<AuditLogModel(id={self.id}, action={self.action}, resource={self.resource_type})>"


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    patient_id: str | None = None
    actor: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    details: dict = {}
    ip_address: str | None = None
    created_at: datetime
