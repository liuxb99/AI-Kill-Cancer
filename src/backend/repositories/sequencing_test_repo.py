"""Sequencing test repository."""
from src.backend.repositories.base import BaseRepository
from src.backend.domain.sequencing import SequencingTestModel


class SequencingTestRepository(BaseRepository[SequencingTestModel]):
    def __init__(self, db):
        super().__init__(SequencingTestModel, db)
