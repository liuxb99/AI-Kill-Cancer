"""Phase 3D — Clinical Graph Outbox Repository Tests."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base

# 确保 ClinicalGraphOutboxModel 的表被注册到 Base.metadata
from src.backend.domain.clinical_graph_outbox import ClinicalGraphOutboxModel  # noqa: F401


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


class TestOutboxRepository:
    """Outbox Repository 操作测试。"""

    async def test_create(self, db_session):
        """创建 outbox 记录。"""
        from src.backend.repositories.clinical_graph_outbox_repo import (
            ClinicalGraphOutboxRepository,
        )

        repo = ClinicalGraphOutboxRepository(db_session)
        event_id = str(uuid.uuid4())
        model = await repo.create(
            event_id=event_id,
            aggregate_type="patient",
            aggregate_id="patient-1",
            event_type="patient.created",
            schema_version=1,
            payload={"patient_id": "patient-1"},
        )
        assert model.event_id == event_id
        assert model.status == "pending"
        assert model.attempt_count == 0

    async def test_unique_event_id(self, db_session):
        """唯一 event_id 约束。"""
        from src.backend.repositories.clinical_graph_outbox_repo import (
            ClinicalGraphOutboxRepository,
        )

        repo = ClinicalGraphOutboxRepository(db_session)
        event_id = str(uuid.uuid4())
        await repo.create(
            event_id=event_id,
            aggregate_type="patient",
            aggregate_id="p-1",
            event_type="patient.created",
            schema_version=1,
            payload={},
        )
        await db_session.commit()
        # 相同 event_id 应该报错
        with pytest.raises(Exception):
            await repo.create(
                event_id=event_id,
                aggregate_type="patient",
                aggregate_id="p-2",
                event_type="patient.created",
                schema_version=1,
                payload={},
            )
            await db_session.commit()

    async def test_claim_pending(self, db_session):
        """claim pending 事件。"""
        from src.backend.repositories.clinical_graph_outbox_repo import (
            ClinicalGraphOutboxRepository,
        )

        repo = ClinicalGraphOutboxRepository(db_session)
        await repo.create(
            event_id=str(uuid.uuid4()),
            aggregate_type="patient",
            aggregate_id="p-1",
            event_type="patient.created",
            schema_version=1,
            payload={},
        )
        await repo.create(
            event_id=str(uuid.uuid4()),
            aggregate_type="recommendation",
            aggregate_id="r-1",
            event_type="recommendation.created",
            schema_version=1,
            payload={},
        )
        await db_session.commit()

        events = await repo.claim_pending(max_batch=10)
        assert len(events) >= 2
        for evt in events:
            assert evt.status == "processing"

    async def test_mark_completed(self, db_session):
        """标记完成。"""
        from src.backend.repositories.clinical_graph_outbox_repo import (
            ClinicalGraphOutboxRepository,
        )

        repo = ClinicalGraphOutboxRepository(db_session)
        event_id = str(uuid.uuid4())
        await repo.create(
            event_id=event_id,
            aggregate_type="patient",
            aggregate_id="p-1",
            event_type="patient.created",
            schema_version=1,
            payload={},
        )
        await db_session.commit()
        await repo.mark_completed(event_id)
        await db_session.commit()
        evt = await repo.get_by_event_id(event_id)
        assert evt is not None
        assert evt.status == "completed"
        assert evt.processed_at is not None

    async def test_mark_failed(self, db_session):
        """标记失败。"""
        from src.backend.repositories.clinical_graph_outbox_repo import (
            ClinicalGraphOutboxRepository,
        )

        repo = ClinicalGraphOutboxRepository(db_session)
        event_id = str(uuid.uuid4())
        await repo.create(
            event_id=event_id,
            aggregate_type="patient",
            aggregate_id="p-1",
            event_type="patient.created",
            schema_version=1,
            payload={},
        )
        await db_session.commit()
        await repo.mark_failed(event_id, "test error")
        await db_session.commit()
        evt = await repo.get_by_event_id(event_id)
        assert evt is not None
        assert evt.status in ("failed", "dead_letter")
        assert evt.attempt_count >= 1
        assert "test error" in (evt.last_error or "")

    async def test_dead_letter(self, db_session):
        """超过最大重试次数后标记为死信。"""
        from src.backend.repositories.clinical_graph_outbox_repo import (
            ClinicalGraphOutboxRepository,
        )

        repo = ClinicalGraphOutboxRepository(db_session)
        event_id = str(uuid.uuid4())
        await repo.create(
            event_id=event_id,
            aggregate_type="patient",
            aggregate_id="p-1",
            event_type="patient.created",
            schema_version=1,
            payload={},
        )
        await db_session.commit()
        # 模拟多次失败（超过 5 次重试）
        for i in range(6):
            await repo.mark_failed(event_id, f"attempt {i}")
            await db_session.commit()
        evt = await repo.get_by_event_id(event_id)
        assert evt is not None
        assert evt.attempt_count >= 5
        assert evt.status == "dead_letter"

    async def test_list_failed(self, db_session):
        """列出失败事件。"""
        from src.backend.repositories.clinical_graph_outbox_repo import (
            ClinicalGraphOutboxRepository,
        )

        repo = ClinicalGraphOutboxRepository(db_session)
        event_id = str(uuid.uuid4())
        await repo.create(
            event_id=event_id,
            aggregate_type="patient",
            aggregate_id="p-1",
            event_type="patient.created",
            schema_version=1,
            payload={},
        )
        await db_session.commit()
        # 使用 mark_dead_letter 直接标记为死信，确保 list_failed 能查到
        await repo.mark_dead_letter(event_id, "fatal error")
        await db_session.commit()
        failed = await repo.list_failed()
        assert len(failed) >= 1
        event_ids = [e.event_id for e in failed]
        assert event_id in event_ids
