"""Clinical Graph Projection Worker — 将 Outbox 事件投影到 KnowGraphGo。"""

import json
import logging
from datetime import datetime
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
        """执行一次投影。返回处理的事件数。
        
        采用三段式事务：
        Phase 1: Claim Transaction — 声明事件后立即提交，释放 DB lock
        Phase 2: External Work — 调用 CLI，不持有 DB lock
        Phase 3: Result Transaction — 更新事件状态后提交
        """
        # === Phase 1: Claim Transaction ===
        events = await self._repo.claim_pending(max_batch=self._max_batch)
        if not events:
            return 0
        await self._db.commit()  # 释放 DB lock
        # 此时事件状态已改为 processing，token 已设定

        # === Phase 2: External Work (不持有 DB lock) ===
        processed = 0
        results = []  # list of (event_id, success, error_or_none)
        for event in events:
            try:
                graph_event = ClinicalGraphEvent(
                    event_id=event.event_id,
                    event_type=GraphEventType(event.event_type),
                    schema_version=event.schema_version,
                    aggregate_type=GraphAggregateType(event.aggregate_type),
                    aggregate_id=event.aggregate_id,
                    occurred_at=event.occurred_at or datetime.utcnow(),
                    correlation_id=event.correlation_id,
                    causation_id=event.causation_id,
                    actor_id=event.actor_id,
                    payload=event.payload,
                )
                result = await self._client.apply_event(graph_event)
                if result.get("success"):
                    results.append((event.event_id, True, None))
                    processed += 1
                else:
                    results.append((event.event_id, False, result.get("error", "unknown error")))
            except Exception as e:
                results.append((event.event_id, False, str(e)))

        # === Phase 3: Result Transaction ===
        for event_id, success, error in results:
            if success:
                await self._repo.mark_completed(event_id)
                logger.info("Event %s completed", event_id)
            else:
                await self._repo.mark_failed(event_id, error)
                logger.warning("Event %s failed: %s", event_id, error)
        await self._db.commit()
        return processed


__all__ = ["ClinicalGraphProjectionWorker"]
