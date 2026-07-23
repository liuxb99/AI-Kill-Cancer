"""
Drug and DrugTarget domain models.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from src.backend.database.models import Base as DBBase
from src.backend.database.models import CompatUUID


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class DrugModel(DBBase):
    __tablename__ = "domain_drugs"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    name = Column(String(256), nullable=False, index=True)
    generic_name = Column(String(256), nullable=True)
    drugbank_id = Column(String(64), nullable=True, unique=True)
    atc_codes = Column(JSON, default=list)
    mechanism_of_action = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    approval_status = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    drug_targets = relationship("DrugTargetModel", back_populates="drug", cascade="all, delete-orphan")
    drug_candidates = relationship("DrugCandidateModel", back_populates="drug", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DrugModel(id={self.id}, name={self.name!r})>"


class DrugCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    name: str = Field(..., max_length=256)
    generic_name: str | None = Field(None, max_length=256)
    drugbank_id: str | None = Field(None, max_length=64)
    atc_codes: list[str] | None = None
    mechanism_of_action: str | None = None
    description: str | None = None
    approval_status: str | None = Field(None, max_length=64)


class DrugResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    name: str
    generic_name: str | None = None
    drugbank_id: str | None = None
    atc_codes: list = []
    mechanism_of_action: str | None = None
    description: str | None = None
    approval_status: str | None = None
    created_at: datetime
    updated_at: datetime


class DrugTargetModel(DBBase):
    __tablename__ = "domain_drug_targets"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    drug_id = Column(CompatUUID, ForeignKey("domain_drugs.id", ondelete="CASCADE"), nullable=False, index=True)
    gene_symbol = Column(String(32), nullable=False, index=True)
    target_type = Column(String(64), nullable=True)
    interaction_type = Column(String(128), nullable=True)
    source = Column(String(64), nullable=True)
    source_id = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    drug = relationship("DrugModel", back_populates="drug_targets")

    def __repr__(self):
        return f"<DrugTargetModel(id={self.id}, drug_id={self.drug_id}, gene={self.gene_symbol})>"
