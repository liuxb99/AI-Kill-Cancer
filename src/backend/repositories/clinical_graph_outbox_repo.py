"""Clinical Graph Outbox Repository."""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Sequence

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from src.backend.clinical_graph.retry_policy import DEFAULT_RETRY_POLICY
from src.backend.domain.clinical_graph_outbox import ClinicalGraphOutboxModel


def _next_available_at(attempt_count: int) -> datetime:
    """根据尝试次数计算下次可用时间。"""
    return DEFAULT_RETRY_POLICY.next_available_at(attempt_count)


def _coerce_event_id(value: object | None) -> str:
    """Return a valid event ID or generate one when omitted.

    The repository acts as the final persistence safety net. Callers may still
    provide deterministic or externally assigned IDs, but blank and non-string
    values are rejected before reaching the database.
    """
    if value is None:
        return str(uuid.uuid4())
    if not isinstance(value, str):
        raise TypeError("event_id must be a string")
    event_id = value.strip()
    if not event_id:
        raise ValueError("event_id must not be blank")
    if len(event_id) > 64:
        raise ValueError("event_id must not exceed 64 characters")
    return event_id


class ClinicalGraphOutboxRepository:
    """Transactional Outbox 仓储 — 不管理事务边界。"""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(self, **kwargs) -> ClinicalGraphOutboxModel:
        """创建新 outbox 记录并保证 event_id 契约。"""
        kwargs["event_id"] = _coerce_event_id(kwargs.get("event_id"))
        if "id" not in kwargs:
            kwargs["id"] = uuid.uuid4()
        model = ClinicalGraphOutboxModel(**kwargs)
        self._db.add(model)
        await self._db.flush()
        return model

    async def get_by_event_id(self, event_id: str) -> Optional[ClinicalGraphOutboxModel]:
        """按 event_id 查询。"""
        stmt = select(ClinicalGraphOutboxModel).where(
            ClinicalGraphOutboxModel.event_id == event_id
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def claim_pending(self, max_batch: int = 10) -> Sequence[ClinicalGraphOutboxModel]:
        """Claim 待处理事件（含 pending/failed，使用 FOR UPDATE SKIP LOCKED）。"""
        now = datetime.utcnow()
        stmt: Select = (
            select(ClinicalGraphOutboxModel)
            .where(
                and_(
                    ClinicalGraphOutboxModel.status.in_(["pending", "failed"]),
                    ClinicalGraphOutboxModel.available_at <= now,
                )
            )
            .order_by(ClinicalGraphOutboxModel.available_at.asc())
            .limit(max_batch)
            .with_for_update(skip_locked=True)
        )
        result = await self._db.execute(stmt)
        rows = result.scalars().all()
        for row in rows:
            row.status = "processing"
            row.claim_token = str(uuid.uuid4())
            row.processing_started_at = now
        return rows

    async def mark_completed(self, event_id: str) -> None:
        """标记事件为已完成。"""
        now = datetime.utcnow()
        stmt = (
            update(ClinicalGraphOutboxModel)
            .where(ClinicalGraphOutboxModel.event_id == event_id)
            .values(status="completed", processed_at=now, updated_at=now)
        )
        await self._db.execute(stmt)

    async def mark_failed(self, event_id: str, error: str) -> None:
        """标记事件为失败，更新尝试次数和下次可用时间。"""
        now = datetime.utcnow()
        model = await self.get_by_event_id(event_id)
        if model is None:
            return
        new_attempt = model.attempt_count + 1
        if DEFAULT_RETRY_POLICY.is_dead_letter(new_attempt):
            new_status = "dead_letter"
        else:
            new_status = "failed"
        stmt = (
            update(ClinicalGraphOutboxModel)
            .where(ClinicalGraphOutboxModel.event_id == event_id)
            .values(
                status=new_status,
                attempt_count=new_attempt,
                last_error=error[:1024],
                available_at=_next_available_at(new_attempt),
                last_failed_at=now,
                updated_at=now,
            )
        )
        await self._db.execute(stmt)

    async def mark_dead_letter(self, event_id: str, error: str) -> None:
        """直接标记为死信。"""
        now = datetime.utcnow()
        stmt = (
            update(ClinicalGraphOutboxModel)
            .where(ClinicalGraphOutboxModel.event_id == event_id)
            .values(
                status="dead_letter",
                last_error=error[:1024],
                updated_at=now,
            )
        )
        await self._db.execute(stmt)

    async def release_stale(self, timeout_minutes: int = 30) -> int:
        """释放卡在 processing 超过指定分钟的陈旧事件，重设为 pending。"""
        now = datetime.utcnow()
        deadline = now - timedelta(minutes=timeout_minutes)
        stmt = (
            select(ClinicalGraphOutboxModel)
            .where(
                and_(
                    ClinicalGraphOutboxModel.status == "processing",
                    ClinicalGraphOutboxModel.processing_started_at < deadline,
                )
            )
            .with_for_update(skip_locked=True)
        )
        result = await self._db.execute(stmt)
        rows = result.scalars().all()
        for row in rows:
            row.status = "pending"
            row.claim_token = None
            row.processing_started_at = None
        return len(rows)

    async def get_failed_events(self, limit: int = 50) -> Sequence[ClinicalGraphOutboxModel]:
        """查询 failed / dead_letter 事件。"""
        stmt = (
            select(ClinicalGraphOutboxModel)
            .where(
                ClinicalGraphOutboxModel.status.in_(["failed", "dead_letter"])
            )
            .order_by(ClinicalGraphOutboxModel.updated_at.desc())
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def get_status_counts(self) -> dict:
        """返回各状态的事件计数。"""
        from sqlalchemy import func

        stmt = (
            select(
                ClinicalGraphOutboxModel.status,
                func.count().label("count"),
            )
            .group_by(ClinicalGraphOutboxModel.status)
        )
        result = await self._db.execute(stmt)
        counts: dict[str, int] = {}
        for row in result.all():
            counts[row.status] = row.count
        return counts

    async def list_failed(self, limit: int = 50) -> Sequence[ClinicalGraphOutboxModel]:
        """列出失败/死信事件。"""
        stmt = (
            select(ClinicalGraphOutboxModel)
            .where(
                ClinicalGraphOutboxModel.status.in_(["failed", "dead_letter"])
            )
            .order_by(ClinicalGraphOutboxModel.updated_at.desc())
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return result.scalars().all()


__all__ = ["ClinicalGraphOutboxRepository"]
