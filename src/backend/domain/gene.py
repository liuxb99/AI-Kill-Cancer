"""
Gene, Protein, and Pathway domain models.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from src.backend.database.models import CompatUUID, Base as DBBase


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


# ─── Gene ─────────────────────────────────────────────────────────────────────

class GeneModel(DBBase):
    __tablename__ = "domain_genes"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    symbol = Column(String(32), unique=True, nullable=False, index=True)
    full_name = Column(String(512), nullable=True)
    aliases = Column(JSON, default=list)
    chromosome = Column(String(16), nullable=True)
    gene_type = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    ncbi_gene_id = Column(String(32), nullable=True, unique=True)
    ensembl_gene_id = Column(String(64), nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    variants = relationship("VariantModel", back_populates="gene")
    proteins = relationship("ProteinModel", back_populates="gene", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GeneModel(id={self.id}, symbol={self.symbol!r})>"


class GeneCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    symbol: str = Field(..., max_length=32)
    full_name: Optional[str] = Field(None, max_length=512)
    aliases: Optional[list[str]] = None
    chromosome: Optional[str] = Field(None, max_length=16)
    gene_type: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = None
    ncbi_gene_id: Optional[str] = Field(None, max_length=32)
    ensembl_gene_id: Optional[str] = Field(None, max_length=64)


class GeneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    symbol: str
    full_name: Optional[str] = None
    aliases: list = []
    chromosome: Optional[str] = None
    gene_type: Optional[str] = None
    description: Optional[str] = None
    ncbi_gene_id: Optional[str] = None
    ensembl_gene_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ─── Protein ───────────────────────────────────────────────────────────────────

class ProteinModel(DBBase):
    __tablename__ = "domain_proteins"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    gene_id = Column(CompatUUID, ForeignKey("domain_genes.id", ondelete="CASCADE"), nullable=False, index=True)
    uniprot_id = Column(String(64), nullable=True, unique=True)
    name = Column(String(512), nullable=True)
    function = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    gene = relationship("GeneModel", back_populates="proteins")

    def __repr__(self):
        return f"<ProteinModel(id={self.id}, uniprot_id={self.uniprot_id!r})>"


# ─── Pathway ───────────────────────────────────────────────────────────────────

class PathwayModel(DBBase):
    __tablename__ = "domain_pathways"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    name = Column(String(256), nullable=False, index=True)
    source = Column(String(64), nullable=True)
    source_id = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    genes = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<PathwayModel(id={self.id}, name={self.name!r})>"


