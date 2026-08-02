"""Integrated PTC research, scientific herbal medicine and recommendation snapshots."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, String, Text, UniqueConstraint

from src.backend.database.models import Base, CompatUUID


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class PTCHerbModel(Base):
    __tablename__ = "domain_ptc_herbs"
    __table_args__ = (UniqueConstraint("herb_key", name="uq_ptc_herb_key"),)

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    herb_key = Column(String(160), nullable=False, index=True)
    chinese_name = Column(String(128), nullable=False)
    english_name = Column(String(256), nullable=True)
    latin_name = Column(String(256), nullable=True)
    medicinal_part = Column(String(128), nullable=True)
    traditional_functions = Column(JSON, nullable=False, default=list)
    investigated_genes = Column(JSON, nullable=False, default=list)
    investigated_pathways = Column(JSON, nullable=False, default=list)
    evidence_level = Column(String(64), nullable=False, default="preclinical")
    evidence_summary = Column(Text, nullable=True)
    source_name = Column(String(128), nullable=False)
    source_record_id = Column(String(256), nullable=True)
    license = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class PTCHerbCompoundModel(Base):
    __tablename__ = "domain_ptc_herb_compounds"
    __table_args__ = (UniqueConstraint("compound_key", name="uq_ptc_herb_compound_key"),)

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    compound_key = Column(String(192), nullable=False, index=True)
    herb_key = Column(String(160), nullable=False, index=True)
    compound_name = Column(String(256), nullable=False)
    pubchem_cid = Column(String(64), nullable=True)
    inchikey = Column(String(64), nullable=True)
    target_genes = Column(JSON, nullable=False, default=list)
    pathways = Column(JSON, nullable=False, default=list)
    source_name = Column(String(128), nullable=False)
    source_record_id = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PTCHerbDrugInteractionModel(Base):
    __tablename__ = "domain_ptc_herb_drug_interactions"
    __table_args__ = (
        UniqueConstraint("herb_key", "therapy_key", "interaction_type", name="uq_ptc_herb_drug_interaction"),
    )

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    herb_key = Column(String(160), nullable=False, index=True)
    therapy_key = Column(String(160), nullable=False, index=True)
    interaction_type = Column(String(64), nullable=False)
    severity = Column(String(32), nullable=False, default="unknown")
    mechanism = Column(Text, nullable=True)
    clinical_effect = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    evidence_level = Column(String(64), nullable=False, default="unknown")
    source_name = Column(String(128), nullable=False)
    source_record_id = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PTCCaseSimilarityModel(Base):
    __tablename__ = "domain_ptc_case_similarities"
    __table_args__ = (UniqueConstraint("case_id", "similar_case_id", name="uq_ptc_case_similarity"),)

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    case_id = Column(String(128), nullable=False, index=True)
    similar_case_id = Column(String(128), nullable=False, index=True)
    score = Column(Float, nullable=False)
    shared_genes = Column(JSON, nullable=False, default=list)
    shared_stage = Column(String(64), nullable=True)
    rationale = Column(Text, nullable=True)
    algorithm_version = Column(String(32), nullable=False, default="ptc-jaccard-v1")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PTCRecommendationSnapshotModel(Base):
    __tablename__ = "domain_ptc_recommendation_snapshots"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    recommendation_id = Column(String(128), nullable=False, unique=True, index=True)
    case_id = Column(String(128), nullable=False, index=True)
    recommendation_type = Column(String(64), nullable=False, default="research_support")
    ranked_therapies = Column(JSON, nullable=False, default=list)
    matching_trials = Column(JSON, nullable=False, default=list)
    supporting_evidence = Column(JSON, nullable=False, default=list)
    herb_research = Column(JSON, nullable=False, default=list)
    interaction_warnings = Column(JSON, nullable=False, default=list)
    similar_cases = Column(JSON, nullable=False, default=list)
    explanation = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    engine_version = Column(String(32), nullable=False, default="ptc-research-v1")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


__all__ = [
    "PTCHerbModel",
    "PTCHerbCompoundModel",
    "PTCHerbDrugInteractionModel",
    "PTCCaseSimilarityModel",
    "PTCRecommendationSnapshotModel",
]
