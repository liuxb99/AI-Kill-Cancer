"""
Sequencing test service — sequencing test persistence with Service-owned transaction.

Transaction management (commit on success, rollback + re-raise on failure)
is handled here via :class:`BaseService` / ``run_in_transaction``, not by the
API layer or the repository (which remains flush-only).
"""
from __future__ import annotations

from src.backend.repositories.sequencing_test_repo import SequencingTestRepository
from src.backend.services.base import BaseService


class SequencingTestService(BaseService):
    """Service 層管理 sequencing test 寫入的 transaction（commit/rollback）。"""

    def __init__(self, db) -> None:
        super().__init__(db)
        self._repo = SequencingTestRepository(db)

    async def create(self, **data):
        """建立 sequencing test：repo flush-only 寫入，Service 負責 commit。

        失敗時 rollback 後 re-raise。
        """

        async def _operation():
            return await self._repo.create(**data)

        return await self._run(_operation)


__all__ = ["SequencingTestService"]
