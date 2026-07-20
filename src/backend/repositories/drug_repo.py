"""Drug repository."""
from sqlalchemy import select
from src.backend.repositories.base import BaseRepository
from src.backend.domain.drug import DrugModel


class DrugRepository(BaseRepository[DrugModel]):
    def __init__(self, db):
        super().__init__(DrugModel, db)

    async def find_by_name(self, name: str):
        stmt = select(DrugModel).where(DrugModel.name.ilike(f"%{name}%"))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
