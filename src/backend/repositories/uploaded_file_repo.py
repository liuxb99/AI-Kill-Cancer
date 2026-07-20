"""Uploaded file repository."""
from src.backend.repositories.base import BaseRepository
from src.backend.domain.uploaded_file import UploadedFileModel


class UploadedFileRepository(BaseRepository[UploadedFileModel]):
    def __init__(self, db):
        super().__init__(UploadedFileModel, db)
