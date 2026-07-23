"""Uploaded file repository."""
from sqlalchemy import select

from src.backend.domain.uploaded_file import UploadedFileModel
from src.backend.repositories.base import BaseRepository


class UploadedFileRepository(BaseRepository[UploadedFileModel]):
    def __init__(self, db):
        super().__init__(UploadedFileModel, db)

    async def find_by_sha256(self, sha256: str) -> list[UploadedFileModel]:
        stmt = select(UploadedFileModel).where(UploadedFileModel.sha256 == sha256)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
