"""Variant Ingestion Service — manages transaction boundaries for variant operations."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.domain.variant import VariantModel
from src.backend.repositories.variant_repo import VariantRepository

logger = logging.getLogger(__name__)


class VariantIngestionService:
    """Wraps VariantRepository with transaction commit/rollback management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = VariantRepository(db)

    async def bulk_create_variants(
        self,
        variants_data: list[dict[str, Any]],
    ) -> list[VariantModel]:
        """Bulk create variants with transaction management.

        Returns the list of created VariantModel instances.
        """
        try:
            variants = await self.repo.bulk_create(variants_data)
            await self.db.commit()
            return variants
        except Exception:
            await self.db.rollback()
            raise
