"""Cancer case repository."""
from sqlalchemy import select

from src.backend.domain.cancer_case import CancerCaseModel
from src.backend.repositories.base import BaseRepository


class CancerCaseRepository(BaseRepository[CancerCaseModel]):
    def __init__(self, db):
        super().__init__(CancerCaseModel, db)

    async def find_by_patient(self, patient_id):
        stmt = select(CancerCaseModel).where(CancerCaseModel.patient_id == patient_id).order_by(CancerCaseModel.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
