"""
KnowledgeService — orchestrates knowledge queries across multiple sources.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from src.backend.knowledge.repository import KnowledgeRepository
from src.backend.knowledge.models import KnowledgeEntityResponse, KnowledgeEntity
from src.backend.knowledge.identifiers import IdentifierMapper

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Orchestrates knowledge queries across sources."""

    def __init__(self, db):
        self.repo = KnowledgeRepository(db)
        self.id_mapper = IdentifierMapper()

    async def get_variant_knowledge(self, variant_id: str) -> KnowledgeEntityResponse:
        """Get all knowledge about a variant."""
        try:
            vid = uuid.UUID(variant_id)
        except ValueError:
            return KnowledgeEntityResponse()

        entity = await self.repo.get_entity(vid)
        if not entity:
            return KnowledgeEntityResponse()

        relations = await self.repo.get_relations(vid)
        return KnowledgeEntityResponse(
            entity=KnowledgeEntity(
                id=str(entity.id),
                entity_type=entity.entity_type,
                source=entity.source,
                source_id=entity.source_id,
                name=entity.name,
                identifiers=entity.identifiers or {},
            ),
            relations=[],
        )

    async def get_gene_knowledge(self, symbol: str) -> KnowledgeEntityResponse:
        """Get all knowledge about a gene."""
        entities = await self.repo.find_entities(entity_type="gene", name=symbol)
        if not entities:
            return KnowledgeEntityResponse()

        entity = entities[0]
        relations = await self.repo.get_relations(entity.id)
        return KnowledgeEntityResponse(
            entity=KnowledgeEntity(
                id=str(entity.id),
                entity_type="gene",
                source=entity.source,
                source_id=entity.source_id,
                name=entity.name,
                identifiers=entity.identifiers or {},
            ),
            relations=[],
        )

    async def count_knowledge(self) -> int:
        return await self.repo.count_entities()
