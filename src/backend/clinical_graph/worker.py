"""Clinical Graph Projection Worker — 将 Outbox 事件投影到 KnowGraphGo。"""

import json
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.repositories.clinical_graph_outbox_repo import ClinicalGraphOutboxRepository
from src.backend.schemas.clinical_graph_event import (
    ClinicalGraphEvent,
    GraphAggregateType,
    GraphEventType,
)
from src.backend.clinical_graph.client import ClinicalGraphClient
from src.backend.clinical_graph.retry_policy import DEFAULT_RETRY_POLICY, GraphProjectionRetryPolicy

logger = logging.getLogger(__name__)


class ClinicalGraphProjectionWorker:
    """将 Outbox 事件投影到 KnowGraphGo。
    
    单次执行流程：
    1. claim pending events
    2. 逐条调用 Adapter
    3. 成功 -> mark_completed
    4. 失败 -> attempt_count + 1，设置 next available_at
    5. 超过 max attempts -> dead_letter
    """

    def __init__(
        self,
        db: AsyncSession,
        client: Optional[ClinicalGraphClient] = None,
        retry_policy: Optional[GraphProjectionRetryPolicy] = None,
        max_batch: int = 10,
    ):
        self._db = db
        self._repo = ClinicalGraphOutboxRepository(db)
        self._client = client or ClinicalGraphClient()
        self._retry_policy = retry_policy or DEFAULT_RETRY_POLICY
        self._max_batch = max_batch

    async def run_once(self) -> int:
        """执行一次投影。返回处理的事件数。"""
        events = await self._repo.claim_pending(max_batch=self._max_batch)
        if not events:
            return 0

        processed = 0
        for event in events:
            try:
                # 构建 ClinicalGraphEvent
                graph_event = ClinicalGraphEvent(
                    event_id=event.event_id,
                    event_type=GraphEventType(event.event_type),
                    schema_version=event.schema_version,
                    aggregate_type=GraphAggregateType(event.aggregate_type),
                    aggregate_id=event.aggregate_id,
                    payload=event.payload,
                )

                # 调用 CLI
                result = await self._client.apply_event(graph_event)

                if result.get("success"):
                    await self._repo.mark_completed(event.event_id)
                    processed += 1
                    logger.info("Event %s completed", event.event_id)
                else:
                    error = result.get("error", "unknown error")
                    await self._repo.mark_failed(event.event_id, error)
                    logger.warning("Event %s failed: %s", event.event_id, error)

            except Exception as e:
                logger.exception("Event %s processing error", event.event_id)
                await self._repo.mark_failed(event.event_id, str(e))

        await self._db.commit()
        return processed


__all__ = ["ClinicalGraphProjectionWorker"]
