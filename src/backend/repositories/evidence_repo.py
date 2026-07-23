"""Evidence repository."""
from sqlalchemy import select

from src.backend.domain.evidence import EvidenceModel
from src.backend.repositories.base import BaseRepository


class EvidenceRepository(BaseRepository[EvidenceModel]):
    def __init__(self, db):
        super().__init__(EvidenceModel, db)

    async def find_by_gene(self, gene_symbol: str):
        stmt = select(EvidenceModel).where(EvidenceModel.gene_symbol == gene_symbol)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def find_by_drug(self, drug_id):
        stmt = select(EvidenceModel).where(EvidenceModel.drug_id == drug_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def find_by_variant(self, variant_id):
        stmt = select(EvidenceModel).where(EvidenceModel.variant_id == variant_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
