"""Specimen repository."""
from src.backend.domain.specimen import SpecimenModel
from src.backend.repositories.base import BaseRepository


class SpecimenRepository(BaseRepository[SpecimenModel]):
    def __init__(self, db):
        super().__init__(SpecimenModel, db)
