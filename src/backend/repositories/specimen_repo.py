"""Specimen repository."""
from src.backend.repositories.base import BaseRepository
from src.backend.domain.specimen import SpecimenModel


class SpecimenRepository(BaseRepository[SpecimenModel]):
    def __init__(self, db):
        super().__init__(SpecimenModel, db)
