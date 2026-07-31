"""
Patient service — patient persistence with Service-owned transaction.

Transaction management (commit on success, rollback + re-raise on failure)
is handled here via try/except (or :class:`BaseService` / ``run_in_transaction``),
not by the API layer or the repository (which remains flush-only).
"""
from __future__ import annotations

import uuid
from typing import Any

from src.backend.domain.patient import PatientModel
from src.backend.repositories.patient_repo import PatientRepository
from src.backend.services.base import BaseService


class PatientService(BaseService):
    """Service 層管理 patient 寫入的 transaction（commit/rollback）。"""

    def __init__(self, db) -> None:
        super().__init__(db)
        self._repo = PatientRepository(db)

    async def create(self, **data: Any) -> PatientModel:
        """建立 patient：repo flush-only 寫入，Service 負責 commit。

        失敗時 rollback 後 re-raise。
        """
        try:
            patient = await self._repo.create(**data)
            await self.db.commit()
            return patient
        except Exception:
            await self.db.rollback()
            raise

    async def update(
        self,
        patient_id: uuid.UUID,
        **data: Any,
    ) -> PatientModel | None:
        """更新 patient：repo flush-only 寫入，Service 負責 commit。

        失敗時 rollback 後 re-raise。
        """
        try:
            patient = await self._repo.update(patient_id, **data)
            await self.db.commit()
            return patient
        except Exception:
            await self.db.rollback()
            raise

    async def delete(self, patient_id: uuid.UUID) -> bool:
        """刪除 patient：repo flush-only 寫入，Service 負責 commit。

        失敗時 rollback 後 re-raise。
        """
        try:
            deleted = await self._repo.delete(patient_id)
            await self.db.commit()
            return deleted
        except Exception:
            await self.db.rollback()
            raise


__all__ = ["PatientService"]
