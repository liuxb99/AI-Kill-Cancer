"""Evidence Ingestion Service — manages transaction boundaries for evidence merging."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.evidence.merger import EvidenceMerger

logger = logging.getLogger(__name__)


class EvidenceIngestionService:
    """Wraps EvidenceMerger with transaction commit/rollback management.

    Each method delegates to the corresponding EvidenceMerger method and
    then commits on success or rolls back on exception.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.merger = EvidenceMerger(db=db)

    async def refresh_all(
        self,
        gene_symbol: str,
        hgvs: str = "",
        chromosome: str = "",
        position: int = 0,
        reference: str = "",
        alternate: str = "",
        variant_name: str = "",
        request_id: str = "",
    ) -> dict[str, Any]:
        """Full refresh: query sources, merge, persist, then commit."""
        try:
            result = await self.merger.refresh_all(
                gene_symbol=gene_symbol,
                hgvs=hgvs,
                chromosome=chromosome,
                position=position,
                reference=reference,
                alternate=alternate,
                variant_name=variant_name,
                request_id=request_id,
            )
            await self.db.commit()
            return result
        except Exception:
            await self.db.rollback()
            raise

    async def merge_variant_evidence(
        self,
        gene_symbol: str,
        hgvs: str = "",
        chromosome: str = "",
        position: int = 0,
        reference: str = "",
        alternate: str = "",
        variant_name: str = "",
        request_id: str = "",
    ) -> dict[str, Any]:
        """Merge variant evidence with transaction management."""
        try:
            result = await self.merger.merge_variant_evidence(
                gene_symbol=gene_symbol,
                hgvs=hgvs,
                chromosome=chromosome,
                position=position,
                reference=reference,
                alternate=alternate,
                variant_name=variant_name,
                request_id=request_id,
            )
            await self.db.commit()
            return result
        except Exception:
            await self.db.rollback()
            raise

    async def merge_gene_evidence(
        self,
        gene_symbol: str,
        request_id: str = "",
    ) -> dict[str, Any]:
        """Merge gene evidence with transaction management."""
        try:
            result = await self.merger.merge_gene_evidence(
                gene_symbol=gene_symbol,
                request_id=request_id,
            )
            await self.db.commit()
            return result
        except Exception:
            await self.db.rollback()
            raise
