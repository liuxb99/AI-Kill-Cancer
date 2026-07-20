"""Patient repository."""
from src.backend.repositories.base import BaseRepository
from src.backend.domain.patient import PatientModel


class PatientRepository(BaseRepository[PatientModel]):
    def __init__(self, db):
        super().__init__(PatientModel, db)

    async def find_by_external_id(self, external_id: str):
        from sqlalchemy import select
        stmt = select(PatientModel).where(PatientModel.external_id == external_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
