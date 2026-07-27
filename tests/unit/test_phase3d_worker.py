"""Phase 3D — Graph Projection Worker Tests."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base


@pytest.fixture
async def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


class TestWorkerBasic:
    """Worker 基本功能测试。"""

    async def test_worker_imports(self):
        """Worker 导入正常。"""
        from src.backend.clinical_graph.worker import ClinicalGraphProjectionWorker

        assert ClinicalGraphProjectionWorker is not None

    async def test_worker_no_pending_events(self, db_session):
        """没有待处理事件时 worker 不做任何事。"""
        from src.backend.clinical_graph.worker import ClinicalGraphProjectionWorker

        worker = ClinicalGraphProjectionWorker(db_session)
        count = await worker.run_once()
        assert count == 0

    async def test_worker_with_mock_client(self, db_session):
        """Worker 使用 mock client 处理事件。"""
        from src.backend.clinical_graph.worker import ClinicalGraphProjectionWorker
        from src.backend.clinical_graph.client import ClinicalGraphClient
        from src.backend.repositories.clinical_graph_outbox_repo import ClinicalGraphOutboxRepository

        # 创建待处理事件
        repo = ClinicalGraphOutboxRepository(db_session)
        event_id = str(uuid.uuid4())
        await repo.create(
            event_id=event_id,
            aggregate_type="patient",
            aggregate_id="p-1",
            event_type="patient.created",
            schema_version=1,
            payload={"patient_id": "p-1", "display_name": "Test"},
            occurred_at=datetime.now(timezone.utc),
        )
        await db_session.commit()

        # mock client
        mock_client = AsyncMock(spec=ClinicalGraphClient)
        mock_client.apply_event.return_value = {"success": True}

        worker = ClinicalGraphProjectionWorker(
            db_session,
            client=mock_client,
            max_batch=10,
        )
        count = await worker.run_once()
        assert count == 1

        # 验证事件已标记完成
        evt = await repo.get_by_event_id(event_id)
        assert evt.status == "completed"

    async def test_worker_retry_on_failure(self, db_session):
        """Worker 在失败时增加重试计数。"""
        from src.backend.clinical_graph.worker import ClinicalGraphProjectionWorker
        from src.backend.clinical_graph.client import ClinicalGraphClient
        from src.backend.repositories.clinical_graph_outbox_repo import ClinicalGraphOutboxRepository

        repo = ClinicalGraphOutboxRepository(db_session)
        event_id = str(uuid.uuid4())
        await repo.create(
            event_id=event_id,
            aggregate_type="recommendation",
            aggregate_id="r-1",
            event_type="recommendation.created",
            schema_version=1,
            payload={},
            occurred_at=datetime.now(timezone.utc),
        )
        await db_session.commit()

        mock_client = AsyncMock(spec=ClinicalGraphClient)
        mock_client.apply_event.return_value = {"success": False, "error": "test error"}

        worker = ClinicalGraphProjectionWorker(
            db_session,
            client=mock_client,
            max_batch=10,
        )
        count = await worker.run_once()
        assert count == 0  # 失败不计入已处理

        evt = await repo.get_by_event_id(event_id)
        assert evt.attempt_count >= 1
        assert "test error" in (evt.last_error or "")

    async def test_retry_policy(self):
        """重试策略计算。"""
        from src.backend.clinical_graph.retry_policy import GraphProjectionRetryPolicy

        policy = GraphProjectionRetryPolicy()
        assert policy.max_attempts == 5
        assert len(policy.retry_delays_minutes) == 5
        assert policy.retry_delays_minutes[0] == 1
        assert policy.retry_delays_minutes[-1] == 360
        assert policy.is_dead_letter(5) is True
        assert policy.is_dead_letter(3) is False

    async def test_client_import(self):
        """Client 导入正常。"""
        from src.backend.clinical_graph.client import ClinicalGraphClient

        client = ClinicalGraphClient(cli_path="echo")
        assert client is not None
