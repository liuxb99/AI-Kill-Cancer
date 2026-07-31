"""
Research paper service — paper 寫入由 Service 管理 transaction。

Transaction 管理（成功 commit、失敗 rollback 後 re-raise）在此處理，
API 層與 CRUD（保持 flush-only）都不直接 commit/rollback。
"""
from __future__ import annotations

from typing import Any

from src.backend.database.crud import create_research_paper
from src.backend.database.models import ResearchPaper
from src.backend.services.base import BaseService


class ResearchPaperService(BaseService):
    """Service 層管理 research paper 寫入的 transaction（commit/rollback）。"""

    async def submit(self, **data: Any) -> ResearchPaper:
        """提交論文：CRUD flush-only 寫入，Service 負責 commit。

        失敗時 rollback 後 re-raise。
        """
        try:
            paper = await create_research_paper(db=self.db, **data)
            await self.db.commit()
            return paper
        except Exception:
            await self.db.rollback()
            raise


__all__ = ["ResearchPaperService"]
