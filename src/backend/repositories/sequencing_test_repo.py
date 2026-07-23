"""Sequencing test repository."""
from src.backend.domain.sequencing import SequencingTestModel
from src.backend.repositories.base import BaseRepository


class SequencingTestRepository(BaseRepository[SequencingTestModel]):
    def __init__(self, db):
        super().__init__(SequencingTestModel, db)
