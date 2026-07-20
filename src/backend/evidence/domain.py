"""
Unified evidence domain models for clinical evidence integration (Phase 2B).

Provides a single set of models for CIViC, DGIdb, and any future evidence
sources. Every piece of evidence has a source, version, license, and
provenance for full auditability.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Column, String, Float, Text, DateTime, JSON, Integer, Enum as SAEnum, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from src.backend.database.models import CompatUUID, Base as DBBase


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


# ─── Match Level Enum ─────────────────────────────────────────────────────────


MATCH_LEVEL_PRECEDENCE = [
    "exact_variant",
    "equivalent_hgvs",
    "coordinate_match",
    "molecular_profile_match",
    "gene_level_only",
    "unmatched",
]

MATCH_LEVEL_ORDER = {v: i for i, v in enumerate(MATCH_LEVEL_PRECEDENCE)}


# ─── SQLAlchemy Models ─────────────────────────────────────────────────────────


class KnowledgeSourceModel(DBBase):
    """A registered knowledge source (CIViC, DGIdb, etc.)."""
    __tablename__ = "domain_knowledge_sources"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    name = Column(String(128), unique=True, nullable=False, index=True)
    version = Column(String(64), nullable=True)
    license = Column(String(256), nullable=True)
    base_url = Column(String(512), nullable=True)
    is_configured = Column(String(16), default="not_configured", nullable=False)
    last_health_check = Column(DateTime, nullable=True)
    retrieval_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class EvidenceItemModel(DBBase):
    """A single evidence item from any knowledge source."""
    __tablename__ = "domain_evidence_items"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    source_id = Column(CompatUUID, ForeignKey("domain_knowledge_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    source_record_id = Column(String(256), nullable=True, index=True, comment="Original ID in source system")
    variant_id = Column(CompatUUID, ForeignKey("domain_variants.id", ondelete="SET NULL"), nullable=True, index=True)
    gene_symbol = Column(String(32), nullable=True, index=True)
    disease = Column(String(256), nullable=True)
    drug_name = Column(String(256), nullable=True)
    drug_id = Column(CompatUUID, ForeignKey("domain_drugs.id", ondelete="SET NULL"), nullable=True)
    evidence_type = Column(String(64), nullable=True, comment="Predictive, prognostic, diagnostic, etc.")
    evidence_direction = Column(String(32), nullable=True, comment="Supporting, conflicting, neutral")
    evidence_level = Column(String(32), nullable=True, comment="Normalized: A, B, C, D, E or Level_1-5")
    source_native_level = Column(String(64), nullable=True, comment="Original evidence level from source (e.g. CIViC A, OncoKB 3B)")
    clinical_significance = Column(String(64), nullable=True, comment="Sensitivity, resistance, etc.")
    description = Column(Text, nullable=True)
    citation = Column(String(512), nullable=True)
    pmid = Column(String(32), nullable=True)
    url = Column(String(512), nullable=True)
    interaction_type = Column(String(128), nullable=True, comment="DGIdb interaction type")
    interaction_score = Column(Float, nullable=True, comment="DGIdb interaction score")
    confidence = Column(String(32), nullable=True)

    # --- Phase 2B new fields ---
    match_level = Column(String(32), nullable=True, comment="exact_variant, equivalent_hgvs, coordinate_match, molecular_profile_match, gene_level_only, unmatched")
    conflict_status = Column(String(32), nullable=True, comment="supporting, conflicting, uncertain, not_evaluable")
    payload_hash = Column(String(64), nullable=True, comment="SHA256 of unique evidence payload for dedup")
    first_seen_at = Column(DateTime, nullable=True, comment="When this evidence was first retrieved")
    last_seen_at = Column(DateTime, nullable=True, comment="When this evidence was last seen in refresh")
    withdrawn_at = Column(DateTime, nullable=True, comment="When the source withdrew this evidence")
    superseded_by = Column(String(36), nullable=True, comment="ID of superseding evidence item")
    is_superseded = Column(Boolean, default=False, nullable=True)

    source_version = Column(String(64), nullable=True)
    retrieved_at = Column(DateTime, nullable=False)
    api_request_hash = Column(String(64), nullable=True, comment="SHA256 of API request params")
    api_response_hash = Column(String(64), nullable=True, comment="SHA256 of raw API response")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    source = relationship("KnowledgeSourceModel")


class DrugInteractionModel(DBBase):
    """A drug-gene interaction from DGIdb or similar."""
    __tablename__ = "domain_drug_interactions"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    source_id = Column(CompatUUID, ForeignKey("domain_knowledge_sources.id", ondelete="CASCADE"), nullable=False)
    gene_symbol = Column(String(32), nullable=False, index=True)
    drug_name = Column(String(256), nullable=False)
    interaction_type = Column(String(128), nullable=True)
    interaction_score = Column(Float, nullable=True)
    source_db_name = Column(String(64), nullable=True)
    pmids = Column(JSON, default=list)
    source_version = Column(String(64), nullable=True)

    # --- Phase 2B new fields ---
    payload_hash = Column(String(64), nullable=True, comment="SHA256 for dedup")
    first_seen_at = Column(DateTime, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)
    withdrawn_at = Column(DateTime, nullable=True)
    superseded_by = Column(String(36), nullable=True)
    is_superseded = Column(Boolean, default=False, nullable=True)

    retrieved_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    source = relationship("KnowledgeSourceModel")


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────


class KnowledgeSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    id: str
    name: str
    version: Optional[str] = None
    license: Optional[str] = None
    is_configured: str
    last_health_check: Optional[datetime] = None


class EvidenceItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    id: str
    source_name: Optional[str] = None
    source_record_id: Optional[str] = None
    gene_symbol: Optional[str] = None
    disease: Optional[str] = None
    drug_name: Optional[str] = None
    evidence_type: Optional[str] = None
    evidence_direction: Optional[str] = None
    evidence_level: Optional[str] = None
    source_native_level: Optional[str] = None
    match_level: Optional[str] = None
    conflict_status: Optional[str] = None
    clinical_significance: Optional[str] = None
    description: Optional[str] = None
    citation: Optional[str] = None
    pmid: Optional[str] = None
    url: Optional[str] = None
    interaction_type: Optional[str] = None
    interaction_score: Optional[float] = None
    confidence: Optional[str] = None
    source_version: Optional[str] = None
    retrieved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class DrugInteractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    id: str
    gene_symbol: str
    drug_name: str
    interaction_type: Optional[str] = None
    interaction_score: Optional[float] = None
    source_db_name: Optional[str] = None
    pmids: list = []
    source_version: Optional[str] = None
    retrieved_at: Optional[datetime] = None


class EvidenceVariantResponse(BaseModel):
    """Response with variant, evidence items, and drug interactions."""
    variant_id: str
    gene_symbol: str
    evidence_items: list[EvidenceItemResponse] = []
    drug_interactions: list[DrugInteractionResponse] = []
    evidence_count: int = 0
    drug_count: int = 0
    highest_evidence_level: Optional[str] = None
    match_level: Optional[str] = None
    retrieved_at: str = ""


class EvidenceGeneResponse(BaseModel):
    """Response with gene-level evidence summary."""
    gene_symbol: str
    evidence_items: list[EvidenceItemResponse] = []
    drug_interactions: list[DrugInteractionResponse] = []
    evidence_count: int = 0
    drug_count: int = 0
    retrieved_at: str = ""


class EvidenceRefreshResponse(BaseModel):
    status: str
    sources_updated: list[str] = []
    total_evidence: int = 0
    total_interactions: int = 0
    errors: list[str] = []
    started_at: str = ""
    finished_at: str = ""


class EvidenceCacheInvalidateResponse(BaseModel):
    status: str
    cache_type: str = ""
    cleared_at: str = ""
