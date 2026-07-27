"""Clinical Graph Event Service — 在同一事务中创建 Outbox 事件。"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.repositories.clinical_graph_outbox_repo import ClinicalGraphOutboxRepository
from src.backend.schemas.clinical_graph_event import (
    ClinicalGraphEvent,
    GraphAggregateType,
    GraphEventType,
)


class ClinicalGraphEventService:
    """Outbox 事件服务 — 不管理事务边界。"""

    def __init__(self, db: AsyncSession):
        self._db = db
        self._repo = ClinicalGraphOutboxRepository(db)

    async def create_event(
        self,
        aggregate_type: GraphAggregateType,
        aggregate_id: str,
        event_type: GraphEventType,
        payload: Dict[str, Any],
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
    ) -> None:
        """创建 outbox 事件。
        
        在同一 db session 中创建，由调用方的 Service 控制 commit/rollback。
        """
        now = datetime.utcnow()
        event = ClinicalGraphEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            schema_version=1,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            occurred_at=now,
            actor_id=actor_id,
            correlation_id=correlation_id,
            causation_id=causation_id,
            payload=payload,
        )
        await self._repo.create(
            event_id=event.event_id,
            aggregate_type=aggregate_type.value,
            aggregate_id=aggregate_id,
            event_type=event_type.value,
            schema_version=event.schema_version,
            payload=payload,
            actor_id=actor_id,
            occurred_at=now,
            correlation_id=correlation_id,
            causation_id=causation_id,
        )


__all__ = ["ClinicalGraphEventService"]
