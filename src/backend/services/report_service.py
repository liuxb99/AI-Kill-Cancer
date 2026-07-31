"""
Report service — clinical report persistence with Service-owned transaction.

Transaction management (commit on success, rollback + re-raise on failure)
is handled here via try/except, not by the API layer or the repository
(which remains flush-only).
"""
from __future__ import annotations

from typing import Any

from src.backend.reporting.repository import ClinicalReportModel, ReportRepository
from src.backend.services.base import BaseService


class ReportService(BaseService):
    """Service 層管理 report 寫入的 transaction（commit/rollback）。"""

    def __init__(self, db) -> None:
        super().__init__(db)
        self._repo = ReportRepository(db)

    async def create(self, **data: Any) -> ClinicalReportModel:
        """建立 report：repo flush-only 寫入，Service 負責 commit。

        失敗時 rollback 後 re-raise。
        """
        try:
            report = await self._repo.create(**data)
            await self.db.commit()
            return report
        except Exception:
            await self.db.rollback()
            raise


__all__ = ["ReportService"]
