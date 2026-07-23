"""Report repository."""
from src.backend.domain.report import ReportModel
from src.backend.repositories.base import BaseRepository


class ReportRepository(BaseRepository[ReportModel]):
    def __init__(self, db):
        super().__init__(ReportModel, db)
