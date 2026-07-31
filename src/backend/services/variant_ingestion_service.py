"""Variant Ingestion Service — manages transaction boundaries for variant operations."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.domain.variant import VariantModel
from src.backend.repositories.variant_repo import VariantRepository

logger = logging.getLogger(__name__)


class VariantIngestionService:
    """Wraps VariantRepository with transaction commit/rollback management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = VariantRepository(db)

    async def bulk_create_variants(
        self,
        variants_data: list[dict[str, Any]],
    ) -> list[VariantModel]:
        """Bulk create variants with transaction management.

        Returns the list of created VariantModel instances.
        """
        try:
            variants = await self.repo.bulk_create(variants_data)
            # REVIEW-PHASE3F0-R4-P0-01 / REVIEW-OPEN
            # R3 尚未完整關閉原驗證條件：此處在 Service 返回前即 commit，之後若 endpoint
            # 的 response model validation、序列化或其他後段處理失敗，已提交的 variants
            # 無法由 get_db() rollback，仍會形成「請求失敗但資料已落庫」的部分成功。
            # 現有測試只證明 get_db 不會再提交 Service 之後新增的資料 B，卻刻意允許
            # Service 已提交的資料 A 保留，與原 REVIEW 要求「Service 返回後 endpoint 失敗
            # 不留下部分提交資料」不一致。
            # 修改：明確選定並實作唯一請求交易邊界。建議 Service 僅 flush，由 endpoint/use-case
            # orchestration 在所有 response 建構前最後 commit；或將完整 response DTO 建構納入
            # Service transaction 成功條件。不得只修改測試文字放寬原需求。
            # 驗證：真實呼叫 import endpoint，讓 Service 寫入後的 response validation/序列化失敗，
            # fresh session 必須查不到本次新增 variants；成功路徑仍只能 commit 一次。
            await self.db.commit()
            return variants
        except Exception:
            await self.db.rollback()
            raise
