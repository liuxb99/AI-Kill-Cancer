"""
Case access service — case ACL grant/revoke with Service-owned transaction.

Transaction management (commit on success, rollback + re-raise on failure)
is handled here via :class:`BaseService` / ``run_in_transaction``, not by the
API layer or the repository (which remains flush-only).
"""
from __future__ import annotations

import uuid

from src.backend.auth.case_acl_service import CaseACLService as _CaseACLAuthService
from src.backend.domain.case_acl import CaseACLModel, CaseRole
from src.backend.domain.user import UserModel
from src.backend.services.base import BaseService


class CaseAccessService(BaseService):
    """Service 層管理 case ACL 寫入的 transaction（grant/revoke）。

    底層 ``CaseACLService``（auth）只 flush、不 commit；本 Service 在成功後
    commit 一次，任何例外（含 PermissionDeniedError）rollback 後 re-raise，
    由 endpoint 決定回應碼（403 / 500）。
    """

    def __init__(self, db) -> None:
        super().__init__(db)
        self._acl_service = _CaseACLAuthService(db)

    async def grant(
        self,
        case_id: uuid.UUID,
        grantor: UserModel,
        target_user_id: uuid.UUID,
        role: CaseRole,
    ) -> CaseACLModel:
        """授予 case 權限；成功 commit，失敗 rollback 後 re-raise。"""

        async def _operation():
            return await self._acl_service.grant_access(
                case_id=case_id,
                grantor=grantor,
                target_user_id=target_user_id,
                role=role,
            )

        return await self._run(_operation)

    async def revoke(
        self,
        case_id: uuid.UUID,
        grantor: UserModel,
        target_user_id: uuid.UUID,
    ) -> bool:
        """撤銷 case 權限；成功 commit，失敗 rollback 後 re-raise。"""

        async def _operation():
            return await self._acl_service.revoke_access(
                case_id=case_id,
                grantor=grantor,
                target_user_id=target_user_id,
            )

        return await self._run(_operation)


__all__ = ["CaseAccessService"]
