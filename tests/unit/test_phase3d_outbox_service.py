"""Phase 3D — Service Transaction Tests."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base

# 确保 ClinicalGraphOutboxModel 的表被注册到 Base.metadata
from src.backend.domain.clinical_graph_outbox import ClinicalGraphOutboxModel  # noqa: F401
from src.backend.schemas.clinical_graph_event import (
    GraphAggregateType,
    GraphEventType,
)


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


class TestEventService:
    """ClinicalGraphEventService 测试。"""

    async def test_create_event(self, db_session):
        """创建事件并通过 outbox repo 验证。"""
        from src.backend.repositories.clinical_graph_outbox_repo import (
            ClinicalGraphOutboxRepository,
        )
        from src.backend.services.clinical_graph_event_service import (
            ClinicalGraphEventService,
        )

        service = ClinicalGraphEventService(db_session)
        await service.create_event(
            aggregate_type=GraphAggregateType.PATIENT,
            aggregate_id="p-1",
            event_type=GraphEventType.PATIENT_CREATED,
            payload={"patient_id": "p-1", "display_name": "Test"},
            actor_id="user-1",
        )

        # 验证事件已创建到 outbox 表中
        repo = ClinicalGraphOutboxRepository(db_session)
        events = await repo.claim_pending(max_batch=10)
        matching = [e for e in events if e.aggregate_type == "patient"]
        assert len(matching) >= 1
        assert matching[0].event_type == "patient.created"

    async def test_create_recommendation_event(self, db_session):
        """创建 recommendation 事件。"""
        from src.backend.repositories.clinical_graph_outbox_repo import (
            ClinicalGraphOutboxRepository,
        )
        from src.backend.services.clinical_graph_event_service import (
            ClinicalGraphEventService,
        )

        service = ClinicalGraphEventService(db_session)
        await service.create_event(
            aggregate_type=GraphAggregateType.RECOMMENDATION,
            aggregate_id="rec-1",
            event_type=GraphEventType.RECOMMENDATION_CREATED,
            payload={"recommendation_id": "rec-1", "patient_id": "p-1"},
        )

        # 验证 recommendation 事件
        repo = ClinicalGraphOutboxRepository(db_session)
        events = await repo.claim_pending(max_batch=100)
        matching = [e for e in events if e.aggregate_type == "recommendation"]
        assert len(matching) >= 1
        assert matching[0].event_type == "recommendation.created"

    async def test_create_multiple_events(self, db_session):
        """创建多个事件。"""
        from src.backend.repositories.clinical_graph_outbox_repo import (
            ClinicalGraphOutboxRepository,
        )
        from src.backend.services.clinical_graph_event_service import (
            ClinicalGraphEventService,
        )

        service = ClinicalGraphEventService(db_session)
        await service.create_event(
            aggregate_type=GraphAggregateType.PATIENT,
            aggregate_id="p-1",
            event_type=GraphEventType.PATIENT_CREATED,
            payload={"patient_id": "p-1"},
        )
        await service.create_event(
            aggregate_type=GraphAggregateType.RECOMMENDATION,
            aggregate_id="rec-1",
            event_type=GraphEventType.RECOMMENDATION_CREATED,
            payload={"recommendation_id": "rec-1"},
        )
        await service.create_event(
            aggregate_type=GraphAggregateType.CLINICAL_DECISION,
            aggregate_id="cd-1",
            event_type=GraphEventType.CLINICAL_DECISION_CREATED,
            payload={"decision_id": "cd-1"},
        )

        repo = ClinicalGraphOutboxRepository(db_session)
        events = await repo.claim_pending(max_batch=10)
        assert len(events) >= 3

    async def test_service_injection(self):
        """验证 ClinicalGraphEventService 可注入到 RecommendationService。"""
        from src.backend.services.clinical_graph_event_service import (
            ClinicalGraphEventService,
        )
        from src.backend.services.recommendation_service import (
            RecommendationService,
        )

        mock_db = AsyncMock(spec=AsyncSession)
        service = RecommendationService(db=mock_db)
        assert service is not None

        # 验证可选的 graph_event_service 参数
        event_service = ClinicalGraphEventService(mock_db)
        service_with_graph = RecommendationService(
            db=mock_db, graph_event_service=event_service,
        )
        assert service_with_graph is not None
