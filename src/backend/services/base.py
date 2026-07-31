"""Service 層共用工具 — 統一 transaction 管理。"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def run_in_transaction(
    db: AsyncSession,
    operation: Callable[[], Awaitable[Any]],
) -> Any:
    """在單一 transaction 中執行操作：成功 commit 一次；異常 rollback 後 re-raise。"""
    try:
        result = await operation()
        await db.commit()
        return result
    except Exception:
        await db.rollback()
        raise


class BaseService:
    """薄 Service 基底：持有 session，提供 _run() 交易包裝。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _run(self, operation: Callable[[], Awaitable[Any]]) -> Any:
        return await run_in_transaction(self.db, operation)
