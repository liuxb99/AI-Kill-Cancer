"""
EvidenceItemRepository — persists evidence items with upsert, versioning, and history.

Payload hash deduplication ensures we don't create duplicate records for
identical evidence across refreshes. first_seen_at / last_seen_at track
evidence lifespan. withdrawn and superseded status support lifecycle.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime

from sqlalchemy import and_, or_, select

from src.backend.evidence.domain import EvidenceItemModel
from src.backend.repositories.base import BaseRepository


def _compute_payload_hash(item: dict) -> str:
    """Compute SHA256 of the unique evidence payload fields."""
    payload = {
        "source": item.get("source", ""),
        "source_record_id": str(item.get("source_record_id", "")),
        "gene_symbol": item.get("gene_symbol", ""),
        "drug_name": item.get("drug_name", ""),
        "disease": item.get("disease", ""),
        "evidence_type": item.get("evidence_type", ""),
        "evidence_direction": item.get("evidence_direction", ""),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class EvidenceItemRepository(BaseRepository[EvidenceItemModel]):
    """Repository for EvidenceItemModel with upsert and lifecycle tracking."""

    def __init__(self, db):
        super().__init__(EvidenceItemModel, db)

    async def upsert(self, source_id: uuid.UUID, item: dict, match_level: str = "gene_level_only",
                     conflict_status: str = "not_evaluable", now: datetime | None = None) -> EvidenceItemModel:
        """
        Upsert an evidence item. Uses payload hash + source_record_id for dedup.
        If the item exists, updates last_seen_at and metadata.
        If not, creates with first_seen_at = now.
        """
        if now is None:
            now = datetime.utcnow()

        payload_hash = _compute_payload_hash(item)
        source_record_id = str(item.get("source_record_id", "")) if item.get("source_record_id") else ""

        # Try to find existing by payload hash first
        stmt = select(EvidenceItemModel).where(
            EvidenceItemModel.payload_hash == payload_hash
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update metadata
            existing.last_seen_at = now
            existing.match_level = match_level
            existing.conflict_status = conflict_status
            existing.retrieved_at = now
            existing.disease = item.get("disease", existing.disease)
            existing.drug_name = item.get("drug_name", existing.drug_name)
            existing.clinical_significance = item.get("clinical_significance", existing.clinical_significance)
            existing.description = item.get("description", existing.description)
            existing.citation = item.get("citation", existing.citation)
            existing.evidence_direction = item.get("evidence_direction", existing.evidence_direction)
            existing.evidence_level = item.get("evidence_level", existing.evidence_level)
            existing.source_native_level = item.get("source_native_level", item.get("evidence_level", existing.source_native_level))
            existing.confidence = item.get("confidence", existing.confidence)
            existing.url = item.get("url", existing.url)
            if item.get("pmid"):
                existing.pmid = str(item.get("pmid", existing.pmid))
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        # Try by source + source_record_id (for idempotent re-imports)
        if source_record_id and source_id:
            stmt2 = select(EvidenceItemModel).where(
                and_(
                    EvidenceItemModel.source_id == source_id,
                    EvidenceItemModel.source_record_id == source_record_id,
                )
            )
            result2 = await self.db.execute(stmt2)
            existing2 = result2.scalar_one_or_none()
            if existing2:
                existing2.last_seen_at = now
                existing2.payload_hash = payload_hash
                existing2.match_level = match_level
                existing2.conflict_status = conflict_status
                existing2.retrieved_at = now
                await self.db.commit()
                await self.db.refresh(existing2)
                return existing2

        # Create new
        instance = EvidenceItemModel(
            source_id=source_id,
            source_record_id=source_record_id,
            gene_symbol=item.get("gene_symbol", ""),
            disease=item.get("disease", ""),
            drug_name=item.get("drug_name", ""),
            evidence_type=item.get("evidence_type", ""),
            evidence_direction=item.get("evidence_direction", ""),
            evidence_level=item.get("evidence_level", ""),
            source_native_level=item.get("source_native_level", item.get("evidence_level", "")),
            clinical_significance=item.get("clinical_significance", ""),
            description=item.get("description", ""),
            citation=item.get("citation", ""),
            pmid=str(item.get("pmid", "")) if item.get("pmid") else None,
            url=item.get("url", ""),
            interaction_type=item.get("interaction_type", ""),
            interaction_score=item.get("interaction_score"),
            confidence=item.get("confidence", ""),
            match_level=match_level,
            conflict_status=conflict_status,
            payload_hash=payload_hash,
            first_seen_at=now,
            last_seen_at=now,
            retrieved_at=now,
            source_version=item.get("source_version", ""),
            api_request_hash=item.get("_request_hash", ""),
            api_response_hash=item.get("_response_hash", ""),
        )
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def find_by_variant_id(self, variant_id: uuid.UUID) -> list[EvidenceItemModel]:
        stmt = select(EvidenceItemModel).where(
            and_(
                EvidenceItemModel.variant_id == variant_id,
                EvidenceItemModel.withdrawn_at.is_(None),
                or_(
                    EvidenceItemModel.is_superseded.is_(None),
                    not EvidenceItemModel.is_superseded,
                ),
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def find_by_gene_symbol(self, gene_symbol: str) -> list[EvidenceItemModel]:
        stmt = select(EvidenceItemModel).where(
            and_(
                EvidenceItemModel.gene_symbol == gene_symbol,
                EvidenceItemModel.withdrawn_at.is_(None),
                or_(
                    EvidenceItemModel.is_superseded.is_(None),
                    not EvidenceItemModel.is_superseded,
                ),
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_active(self) -> int:
        stmt = select(EvidenceItemModel).where(
            and_(
                EvidenceItemModel.withdrawn_at.is_(None),
                or_(
                    EvidenceItemModel.is_superseded.is_(None),
                    not EvidenceItemModel.is_superseded,
                ),
            )
        )
        result = await self.db.execute(stmt)
        return len(list(result.scalars().all()))

    async def withdraw_by_source_record(self, source_id: uuid.UUID, source_record_ids: list[str],
                                         now: datetime | None = None) -> int:
        """Mark evidence items as withdrawn if their source_record_id is no longer present."""
        if now is None:
            now = datetime.utcnow()
        stmt = select(EvidenceItemModel).where(
            and_(
                EvidenceItemModel.source_id == source_id,
                EvidenceItemModel.source_record_id.notin_(source_record_ids),
                EvidenceItemModel.withdrawn_at.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        for item in items:
            item.withdrawn_at = now
        await self.db.commit()
        return len(items)
