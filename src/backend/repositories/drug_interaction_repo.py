"""
DrugInteractionRepository — persists drug-gene interactions with upsert and versioning.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime

from sqlalchemy import and_, select

from src.backend.evidence.domain import DrugInteractionModel
from src.backend.repositories.base import BaseRepository


def _compute_interaction_hash(item: dict) -> str:
    payload = {
        "gene_symbol": item.get("gene_symbol", ""),
        "drug_name": item.get("drug_name", ""),
        "interaction_type": item.get("interaction_type", ""),
        "source_db_name": item.get("source_db_name", ""),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class DrugInteractionRepository(BaseRepository[DrugInteractionModel]):
    """Repository for DrugInteractionModel with upsert."""

    def __init__(self, db):
        super().__init__(DrugInteractionModel, db)

    async def upsert(self, source_id: uuid.UUID, item: dict, now: datetime | None = None) -> DrugInteractionModel:
        if now is None:
            now = datetime.utcnow()

        payload_hash = _compute_interaction_hash(item)

        # Try to find existing by payload hash
        stmt = select(DrugInteractionModel).where(
            DrugInteractionModel.payload_hash == payload_hash
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.last_seen_at = now
            existing.interaction_score = item.get("interaction_score", existing.interaction_score)
            existing.pmids = item.get("pmids", existing.pmids)
            existing.source_version = item.get("source_version", existing.source_version)
            existing.retrieved_at = now
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        # Create new
        instance = DrugInteractionModel(
            source_id=source_id,
            gene_symbol=item.get("gene_symbol", ""),
            drug_name=item.get("drug_name", ""),
            interaction_type=item.get("interaction_type", ""),
            interaction_score=item.get("interaction_score"),
            source_db_name=item.get("source_db_name", ""),
            pmids=item.get("pmids", []),
            payload_hash=payload_hash,
            first_seen_at=now,
            last_seen_at=now,
            retrieved_at=now,
            source_version=item.get("source_version", ""),
        )
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def find_by_gene(self, gene_symbol: str) -> list[DrugInteractionModel]:
        stmt = select(DrugInteractionModel).where(
            and_(
                DrugInteractionModel.gene_symbol == gene_symbol,
                DrugInteractionModel.withdrawn_at.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_active(self) -> int:
        stmt = select(DrugInteractionModel).where(
            DrugInteractionModel.withdrawn_at.is_(None)
        )
        result = await self.db.execute(stmt)
        return len(list(result.scalars().all()))
