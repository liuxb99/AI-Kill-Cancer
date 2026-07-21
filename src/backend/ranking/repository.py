"""
Repository for persisting and retrieving Drug Ranking runs.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, JSON

from src.backend.database.models import CompatUUID, Base as DBBase

# We need to define SQLAlchemy models for ranking results
# These will be created via migration 008


class RankingRunModel(DBBase):
    """Persistent storage for a drug ranking run."""
    __tablename__ = "domain_drug_rankings"

    id = Column(CompatUUID, primary_key=True, default=uuid.uuid4)
    variant_id = Column(String(36), nullable=True, index=True)
    case_id = Column(String(36), nullable=True, index=True)
    gene_symbol = Column(String(32), nullable=True, index=True)
    disease = Column(String(256), nullable=True)
    ranking_data = Column(JSON, nullable=False, comment="Full DrugRankingResult as JSON")
    ranking_algorithm_version = Column(String(32), nullable=False)
    evidence_snapshot_id = Column(String(36), nullable=True)
    source_versions = Column(JSON, default=dict)
    git_commit = Column(String(64), nullable=True)
    status = Column(String(32), default="completed")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class RankingRunRepository:
    """Repository for RankingRunModel."""

    def __init__(self, db):
        self.db = db

    async def create(self, ranking_data: dict) -> RankingRunModel:
        instance = RankingRunModel(
            variant_id=ranking_data.get("variant_id"),
            case_id=ranking_data.get("case_id"),
            gene_symbol=ranking_data.get("gene_symbol"),
            disease=ranking_data.get("disease"),
            ranking_data=ranking_data,
            ranking_algorithm_version=ranking_data.get("ranking_algorithm_version", "0.5.0"),
            evidence_snapshot_id=ranking_data.get("evidence_snapshot_id"),
            source_versions=ranking_data.get("source_versions", {}),
            git_commit=ranking_data.get("git_commit", ""),
            status=ranking_data.get("status", "completed"),
        )
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def get(self, run_id: uuid.UUID) -> Optional[RankingRunModel]:
        from sqlalchemy import select
        stmt = select(RankingRunModel).where(RankingRunModel.id == run_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_gene(self, gene_symbol: str, limit: int = 10) -> list[RankingRunModel]:
        from sqlalchemy import select
        stmt = (select(RankingRunModel)
                .where(RankingRunModel.gene_symbol == gene_symbol)
                .order_by(RankingRunModel.created_at.desc())
                .limit(limit))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
