"""Variant repository."""
from sqlalchemy import select

from src.backend.domain.variant import VariantModel
from src.backend.repositories.base import BaseRepository


class VariantRepository(BaseRepository[VariantModel]):
    def __init__(self, db):
        super().__init__(VariantModel, db)

    async def find_by_sequencing_test(self, sequencing_test_id):
        stmt = select(VariantModel).where(VariantModel.sequencing_test_id == sequencing_test_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def find_by_gene(self, gene_symbol: str):
        stmt = select(VariantModel).where(VariantModel.gene_symbol == gene_symbol)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create(self, items: list[dict]) -> list[VariantModel]:
        instances = [VariantModel(**item) for item in items]
        for inst in instances:
            self.db.add(inst)
        await self.db.commit()
        for inst in instances:
            await self.db.refresh(inst)
        return instances
