"""
Knowledge repository — persists knowledge entities and relations.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy import select

from src.backend.database.models import CompatUUID, Base as DBBase


class KnowledgeEntityModel(DBBase):
    """Persistent storage for a knowledge entity."""
    __tablename__ = "domain_knowledge_entities"

    id = Column(CompatUUID, primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(32), nullable=False, index=True)
    source = Column(String(64), nullable=False)
    source_id = Column(String(256), nullable=False, index=True)
    name = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    aliases = Column(JSON, default=list)
    identifiers = Column(JSON, default=dict)
    entity_metadata = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class KnowledgeRelationModel(DBBase):
    """Persistent storage for a knowledge relation."""
    __tablename__ = "domain_knowledge_relations"

    id = Column(CompatUUID, primary_key=True, default=uuid.uuid4)
    source_entity_id = Column(CompatUUID, ForeignKey("domain_knowledge_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    target_entity_id = Column(CompatUUID, ForeignKey("domain_knowledge_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    relation_type = Column(String(64), nullable=False, index=True)
    evidence = Column(Text, nullable=True)
    source = Column(String(64), nullable=True)
    confidence = Column(String(32), default="unknown")
    relation_metadata = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class KnowledgeRepository:
    """Repository for knowledge entities and relations."""

    def __init__(self, db):
        self.db = db

    async def upsert_entity(self, entity_type: str, source: str, source_id: str,
                             name: str, description: str = "", aliases: Optional[list] = None,
                             identifiers: Optional[dict] = None,
                             entity_metadata: Optional[dict] = None) -> KnowledgeEntityModel:
        """Upsert a knowledge entity by (source, source_id)."""
        stmt = select(KnowledgeEntityModel).where(
            (KnowledgeEntityModel.source == source) &
            (KnowledgeEntityModel.source_id == source_id)
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.name = name
            if description:
                existing.description = description
            if aliases:
                current = list(existing.aliases or [])
                existing.aliases = list(set(current + aliases))
            if identifiers:
                current = dict(existing.identifiers or {})
                current.update(identifiers)
                existing.identifiers = current
            if entity_metadata:
                current = dict(existing.entity_metadata or {})
                current.update(entity_metadata)
                existing.entity_metadata = current
            existing.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        entity = KnowledgeEntityModel(
            entity_type=entity_type, source=source, source_id=source_id,
            name=name, description=description,
            aliases=aliases or [], identifiers=identifiers or {},
            entity_metadata=entity_metadata or {},
        )
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity

    async def get_entity(self, entity_id: uuid.UUID) -> Optional[KnowledgeEntityModel]:
        stmt = select(KnowledgeEntityModel).where(KnowledgeEntityModel.id == entity_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_entities(self, entity_type: str = "", source: str = "",
                             name: str = "", limit: int = 20) -> list[KnowledgeEntityModel]:
        stmt = select(KnowledgeEntityModel)
        if entity_type:
            stmt = stmt.where(KnowledgeEntityModel.entity_type == entity_type)
        if source:
            stmt = stmt.where(KnowledgeEntityModel.source == source)
        if name:
            stmt = stmt.where(KnowledgeEntityModel.name.ilike(f"%{name}%"))
        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_relation(self, source_entity_id: uuid.UUID, target_entity_id: uuid.UUID,
                               relation_type: str, evidence: str = "",
                               source: str = "", confidence: str = "unknown") -> KnowledgeRelationModel:
        relation = KnowledgeRelationModel(
            source_entity_id=source_entity_id, target_entity_id=target_entity_id,
            relation_type=relation_type, evidence=evidence,
            source=source, confidence=confidence,
        )
        self.db.add(relation)
        await self.db.commit()
        await self.db.refresh(relation)
        return relation

    async def get_relations(self, entity_id: uuid.UUID) -> list[KnowledgeRelationModel]:
        stmt = select(KnowledgeRelationModel).where(
            (KnowledgeRelationModel.source_entity_id == entity_id) |
            (KnowledgeRelationModel.target_entity_id == entity_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_entities(self) -> int:
        from sqlalchemy import func
        stmt = select(func.count(KnowledgeEntityModel.id))
        result = await self.db.execute(stmt)
        return result.scalar() or 0
