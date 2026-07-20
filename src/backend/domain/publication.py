"""
Publication domain model.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, String, Text, Integer, DateTime, JSON
from sqlalchemy.orm import relationship

from src.backend.database.models import CompatUUID, Base as DBBase


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class PublicationModel(DBBase):
    __tablename__ = "domain_publications"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    title = Column(String(1024), nullable=False, index=True)
    authors = Column(JSON, default=list)
    journal = Column(String(256), nullable=True)
    year = Column(Integer, nullable=True)
    doi = Column(String(128), nullable=True, unique=True)
    pmid = Column(String(32), nullable=True, unique=True)
    abstract = Column(Text, nullable=True)
    keywords = Column(JSON, default=list)
    url = Column(String(1024), nullable=True)
    citation_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    evidences = relationship("EvidenceModel", back_populates="publication")

    def __repr__(self):
        return f"<PublicationModel(id={self.id}, pmid={self.pmid!r})>"
