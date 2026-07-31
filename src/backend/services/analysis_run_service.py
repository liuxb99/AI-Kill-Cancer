"""
Analysis run service — manages transaction boundaries for analysis runs.

REVIEW-PHASE3F0-R3-P0-01：Repository 保持 flush-only；transaction
（commit/rollback）統一由 Service 層負責（見 tasks/plan-Phase-3F0-R3.md）。
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.domain.analysis_run import AnalysisRunModel
from src.backend.domain.enums import AnalysisStatusEnum
from src.backend.repositories.analysis_run_repo import AnalysisRunRepository
from src.backend.services.base import BaseService

logger = logging.getLogger(__name__)


class AnalysisRunService(BaseService):
    """Wraps AnalysisRunRepository with transaction commit/rollback management."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self.repo = AnalysisRunRepository(db)

    async def create(self, **data: Any) -> AnalysisRunModel:
        """Create an analysis run in a single transaction.

        Preserves the endpoint-level default ``status=PENDING`` inside the
        service. Repo stays flush-only; commit/rollback is handled by
        ``run_in_transaction`` (failure rolls back and re-raises).
        """
        data["status"] = AnalysisStatusEnum.PENDING
        return await self._run(lambda: self.repo.create(**data))
