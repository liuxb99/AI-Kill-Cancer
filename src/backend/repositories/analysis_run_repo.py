"""Analysis run repository."""
from src.backend.repositories.base import BaseRepository
from src.backend.domain.analysis_run import AnalysisRunModel


class AnalysisRunRepository(BaseRepository[AnalysisRunModel]):
    def __init__(self, db):
        super().__init__(AnalysisRunModel, db)
