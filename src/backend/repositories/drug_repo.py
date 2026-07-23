"""Drug repository."""
from sqlalchemy import select

from src.backend.domain.drug import DrugModel, DrugTargetModel
from src.backend.repositories.base import BaseRepository


class DrugRepository(BaseRepository[DrugModel]):
    def __init__(self, db):
        super().__init__(DrugModel, db)

    async def find_by_name(self, name: str):
        stmt = select(DrugModel).where(DrugModel.name.ilike(f"%{name}%"))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def find_by_gene(self, gene_symbol: str) -> list[DrugModel]:
        """Find drugs that target a specific gene symbol."""
        stmt = (
            select(DrugModel)
            .join(DrugTargetModel, DrugTargetModel.drug_id == DrugModel.id)
            .where(DrugTargetModel.gene_symbol.ilike(gene_symbol))
            .distinct()
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
