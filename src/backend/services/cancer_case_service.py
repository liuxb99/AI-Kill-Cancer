"""
Cancer case service — case 寫入（create/update/delete）由 Service 管理 transaction。

Transaction 管理（成功 commit、失敗 rollback 後 re-raise）在此處理，
API 層與 Repository（保持 flush-only）都不直接 commit/rollback。
create 會在同一個 transaction 中完成 case 建立與 creator 的 owner ACL 授予，
任一步驟失敗即整體 rollback。
"""
from __future__ import annotations

import uuid
from typing import Any

from src.backend.auth.case_acl_service import CaseACLService
from src.backend.domain.cancer_case import CancerCaseModel
from src.backend.repositories.cancer_case_repo import CancerCaseRepository
from src.backend.services.base import BaseService


class CancerCaseService(BaseService):
    """Service 層管理 cancer case 寫入的 transaction（commit/rollback）。"""

    def __init__(self, db) -> None:
        super().__init__(db)
        self._repo = CancerCaseRepository(db)

    async def create(self, user_id: uuid.UUID, **data: Any) -> CancerCaseModel:
        """建立 case 並自動授予 creator owner 權限，同一交易提交。

        - repo.create 為 flush-only（取得 case.id 但未 commit）
        - CaseACLService.grant_owner 在同一 transaction 寫入 ACL
        - 兩步皆成功才 commit；任一步失敗 rollback 後 re-raise
        """
        try:
            case = await self._repo.create(**data)
            await CaseACLService(self.db).grant_owner(
                case_id=case.id,
                user_id=user_id,
            )
            await self.db.commit()
            return case
        except Exception:
            await self.db.rollback()
            raise

    async def update(
        self,
        case_id: uuid.UUID,
        **data: Any,
    ) -> CancerCaseModel | None:
        """更新 case：repo flush-only 寫入，Service 負責 commit。

        失敗時 rollback 後 re-raise。
        """
        try:
            case = await self._repo.update(case_id, **data)
            await self.db.commit()
            return case
        except Exception:
            await self.db.rollback()
            raise

    async def delete(self, case_id: uuid.UUID) -> bool:
        """刪除 case：repo flush-only 寫入，Service 負責 commit。

        失敗時 rollback 後 re-raise。
        """
        try:
            deleted = await self._repo.delete(case_id)
            await self.db.commit()
            return deleted
        except Exception:
            await self.db.rollback()
            raise


__all__ = ["CancerCaseService"]
