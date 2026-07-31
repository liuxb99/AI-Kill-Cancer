"""Drug Ranking Service — 統一管理 ranking run 的 transaction 邊界。

REVIEW-PHASE3F0-R3-P0-01：Repository 層只做 flush，commit/rollback 一律由
Service 層透過 BaseService._run / run_in_transaction 處理。
"""

from __future__ import annotations

import logging
from typing import Any

from src.backend.ranking.repository import RankingRunRepository
from src.backend.services.base import BaseService

logger = logging.getLogger(__name__)


class DrugRankingService(BaseService):
    """提供 drug ranking run 的持久化與 transaction 管理。"""

    async def persist_run(self, **data: Any):
        """在單一 transaction 中寫入 ranking run。

        成功時 commit 一次；失敗時 rollback 後 re-raise，
        由 API 層轉成固定訊息 + error_id。
        """
        return await self._run(
            lambda: RankingRunRepository(self.db).create(**data)
        )
