"""
KnowledgeSourceRepository — manages registered evidence sources.

Provides upsert, version tracking, health check recording.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select

from src.backend.repositories.base import BaseRepository
from src.backend.evidence.domain import KnowledgeSourceModel


class KnowledgeSourceRepository(BaseRepository[KnowledgeSourceModel]):
    """Repository for KnowledgeSourceModel with upsert and health tracking."""

    def __init__(self, db):
        super().__init__(KnowledgeSourceModel, db)

    async def upsert(self, name: str, **kwargs) -> KnowledgeSourceModel:
        """Upsert a knowledge source by name. Returns the record."""
        stmt = select(KnowledgeSourceModel).where(KnowledgeSourceModel.name == name)
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            for field, value in kwargs.items():
                if value is not None and hasattr(existing, field):
                    setattr(existing, field, value)
            existing.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        else:
            instance = KnowledgeSourceModel(name=name, **kwargs)
            self.db.add(instance)
            await self.db.commit()
            await self.db.refresh(instance)
            return instance

    async def get_by_name(self, name: str) -> Optional[KnowledgeSourceModel]:
        stmt = select(KnowledgeSourceModel).where(KnowledgeSourceModel.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_configured(self) -> list[KnowledgeSourceModel]:
        stmt = select(KnowledgeSourceModel).where(
            KnowledgeSourceModel.is_configured == "configured"
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def record_health_check(self, name: str, status: str, version: Optional[str] = None) -> Optional[KnowledgeSourceModel]:
        """Record a health check result for a source."""
        source = await self.get_by_name(name)
        if not source:
            return None
        source.last_health_check = datetime.utcnow()
        source.is_configured = status
        if version:
            source.version = version
        source.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(source)
        return source
