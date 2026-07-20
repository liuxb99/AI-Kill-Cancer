"""Report repository."""
from src.backend.repositories.base import BaseRepository
from src.backend.domain.report import ReportModel


class ReportRepository(BaseRepository[ReportModel]):
    def __init__(self, db):
        super().__init__(ReportModel, db)
