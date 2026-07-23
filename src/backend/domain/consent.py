"""
Consent domain model.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

from src.backend.database.models import Base as DBBase
from src.backend.database.models import CompatUUID
from src.backend.domain.enums import ConsentTypeEnum


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class ConsentModel(DBBase):
    __tablename__ = "domain_consents"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    patient_id = Column(CompatUUID, ForeignKey("domain_patients.id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type = Column(SAEnum(ConsentTypeEnum), nullable=False)
    granted_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    consent_document = Column(String(1024), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient = relationship("PatientModel", back_populates="consents")

    def __repr__(self):
        return f"<ConsentModel(id={self.id}, type={self.consent_type})>"


class ConsentCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    patient_id: str
    consent_type: ConsentTypeEnum
    granted_at: datetime | None = None
    expires_at: datetime | None = None
    consent_document: str | None = Field(None, max_length=1024)
    notes: str | None = None


class ConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    patient_id: str
    consent_type: str
    granted_at: datetime | None = None
    revoked_at: datetime | None = None
    expires_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
