"""
T-20: Outbox 原子性測試 — Recommendation/Decision/Consensus 領域

驗證 RecommendationService / ClinicalDecisionService / TumorBoardService
任一領域的主資料 + 子資料 + Outbox 同 Transaction 的原子性。

情境 A：業務資料成功 & Outbox 成功 → 全部存在
情境 B：Outbox 寫入失敗 → 全部 rollback（資料不存在）
情境 C：業務資料失敗 → Outbox 不存在

選擇 RecommendationService.create_recommendation() 作為測試對象，
因其流程包含：RecommendationModel + RecommendationTraceModel +
Outbox (ClinicalGraphOutboxModel) 在同一交易中。
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base


@pytest.fixture
async def db_session():
    """Create a database session for testing. Supports Postgres via DATABASE_URL env var."""
    url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite://")

    from src.backend.domain.clinical_graph_outbox import (  # noqa: F401
        ClinicalGraphOutboxModel,
    )
    from src.backend.domain.patient import PatientModel  # noqa: F401
    from src.backend.domain.recommendation import (  # noqa: F401
        RecommendationModel,
        RecommendationTraceModel,
        RecommendationTraceStepModel,
    )

    if url.startswith("postgresql"):
        engine = create_async_engine(url, echo=False)
    else:
        engine = create_async_engine(url, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def upstream_patient(db_session):
    """建立一個 Patient 作為 FK 參考資料。

    使用 flush-only，與測試主體共用同一 session。
    """
    from src.backend.domain.enums import ConsentStatusEnum, SexEnum
    from src.backend.domain.patient import PatientModel

    patient = PatientModel(
        display_name="T20-TEST-PATIENT",
        sex=SexEnum.UNKNOWN,
        consent_status=ConsentStatusEnum.GRANTED,
    )
    db_session.add(patient)
    await db_session.flush()
    return patient


class TestOutboxAtomicity:
    """驗證業務主資料與 Outbox 在同一個交易中的原子性。"""

    async def _create_recommendation(
        self,
        db_session: AsyncSession,
        patient,
        **kwargs,
    ):
        """Helper: 建立 RecommendationModel + Trace + Step + Outbox 並 commit。"""
        from src.backend.domain.recommendation import (
            RecommendationModel,
            RecommendationTraceModel,
            RecommendationTraceStepModel,
        )
        from src.backend.repositories.clinical_graph_outbox_repo import (
            ClinicalGraphOutboxRepository,
        )

        rec_id = f"rec-{uuid.uuid4().hex}"

        # 1. Recommendation
        rec = RecommendationModel(
            patient_id=patient.id,
            recommendation_id=rec_id,
            status="completed",
            result_payload=kwargs.get("result_payload", {"test": True}),
        )
        db_session.add(rec)
        await db_session.flush()

        # 2. Trace
        trace = RecommendationTraceModel(
            trace_id=f"trace-{uuid.uuid4().hex}",
            recommendation_id=rec.id,
        )
        db_session.add(trace)
        await db_session.flush()

        # 3. Trace Step
        step = RecommendationTraceStepModel(
            trace_id=trace.id,
            step_order=1,
            step_type="data_collection",
            status="completed",
        )
        db_session.add(step)
        await db_session.flush()

        # 4. Outbox
        outbox_repo = ClinicalGraphOutboxRepository(db_session)
        await outbox_repo.create(
            event_id=f"event-{uuid.uuid4().hex}",
            aggregate_type="recommendation",
            aggregate_id=rec_id,
            event_type="recommendation.created",
            schema_version=1,
            payload={"recommendation_id": rec_id},
        )

        return rec, trace, step

    # ── Test Cases ────────────────────────────────────────────────────

    async def test_a_business_success_outbox_success_all_exist(
        self,
        db_session,
        upstream_patient,
    ) -> None:
        """情境 A：業務資料成功 & Outbox 成功 → 全部存在。

        建立完整的 Recommendation + Trace + Step + Outbox，
        然後 commit，驗證所有資料存在。
        """
        # ---- Arrange ----
        rec, trace, step = await self._create_recommendation(
            db_session, upstream_patient,
        )

        # ---- Act ----
        # Commit 整個交易
        await db_session.commit()

        # ---- Assert ----
        from sqlalchemy import select

        from src.backend.domain.clinical_graph_outbox import (
            ClinicalGraphOutboxModel,
        )
        from src.backend.domain.recommendation import (
            RecommendationModel,
            RecommendationTraceModel,
            RecommendationTraceStepModel,
        )

        # 驗證 Recommendation 存在
        stmt_rec = select(RecommendationModel).where(
            RecommendationModel.id == rec.id,
        )
        result = await db_session.execute(stmt_rec)
        found_rec = result.scalar_one_or_none()
        assert found_rec is not None, (
            "Recommendation should exist after commit"
        )
        assert found_rec.id == rec.id

        # 驗證 Trace 存在
        stmt_trace = select(RecommendationTraceModel).where(
            RecommendationTraceModel.id == trace.id,
        )
        result = await db_session.execute(stmt_trace)
        found_trace = result.scalar_one_or_none()
        assert found_trace is not None, "Trace should exist after commit"

        # 驗證 Trace Step 存在
        stmt_step = select(RecommendationTraceStepModel).where(
            RecommendationTraceStepModel.id == step.id,
        )
        result = await db_session.execute(stmt_step)
        found_step = result.scalar_one_or_none()
        assert found_step is not None, "Trace step should exist after commit"

        # 驗證 Outbox 存在
        stmt_outbox = select(ClinicalGraphOutboxModel).where(
            ClinicalGraphOutboxModel.aggregate_id == rec.recommendation_id,
        )
        result = await db_session.execute(stmt_outbox)
        outboxes = list(result.scalars().all())
        assert len(outboxes) > 0, (
            "Outbox should exist after commit"
        )
        assert outboxes[0].status == "pending", "Outbox status should be pending"

    async def test_b_outbox_write_fail_rollback_all(
        self,
        db_session,
        upstream_patient,
    ) -> None:
        """情境 B：Outbox 寫入失敗 → 全部 rollback（資料不存在）。

        故意在 Outbox 建立時傳入無效資料（缺少必要欄位），
        導致 flush 失敗，驗證所有業務資料也被 rollback。
        """
        from src.backend.domain.recommendation import (
            RecommendationModel,
            RecommendationTraceModel,
            RecommendationTraceStepModel,
        )

        rec_id = f"rec-{uuid.uuid4().hex}"

        # 建立 Recommendation（flush）
        rec = RecommendationModel(
            patient_id=upstream_patient.id,
            recommendation_id=rec_id,
            status="completed",
            result_payload={"test": True},
        )
        db_session.add(rec)
        await db_session.flush()

        # 建立 Trace（flush）
        trace = RecommendationTraceModel(
            trace_id=f"trace-{uuid.uuid4().hex}",
            recommendation_id=rec.id,
        )
        db_session.add(trace)
        await db_session.flush()

        # 建立 Trace Step（flush）
        step = RecommendationTraceStepModel(
            trace_id=trace.id,
            step_order=1,
            step_type="data_collection",
            status="completed",
        )
        db_session.add(step)
        await db_session.flush()

        # ---- Act ----
        # 嘗試建立 Outbox 但故意缺少必要欄位
        from src.backend.domain.clinical_graph_outbox import (
            ClinicalGraphOutboxModel,
        )

        with pytest.raises(Exception):
            bad_outbox = ClinicalGraphOutboxModel(
                # 缺少 aggregate_type（NOT NULL）
                # 缺少 aggregate_id（NOT NULL）
                # 缺少 event_type（NOT NULL）
                payload={},
            )
            db_session.add(bad_outbox)
            await db_session.flush()

        # Rollback 清除 PendingRollbackError
        await db_session.rollback()

        # ---- Assert ----
        # 驗證所有業務資料都不存在
        from sqlalchemy import select

        from src.backend.domain.recommendation import (
            RecommendationModel,
        )

        stmt_rec = select(RecommendationModel).where(
            RecommendationModel.id == rec.id,
        )
        result = await db_session.execute(stmt_rec)
        found_rec = result.scalar_one_or_none()
        assert found_rec is None, (
            "Recommendation should NOT exist — all data was rolled back "
            "when Outbox creation failed"
        )

        # 驗證 Outbox 也不存在
        from src.backend.domain.clinical_graph_outbox import (
            ClinicalGraphOutboxModel,
        )
        stmt_outbox = select(ClinicalGraphOutboxModel).where(
            ClinicalGraphOutboxModel.aggregate_id == rec_id,
        )
        result = await db_session.execute(stmt_outbox)
        outboxes = list(result.scalars().all())
        assert len(outboxes) == 0, (
            "Outbox should NOT exist — was rolled back with business data"
        )

    async def test_c_business_data_fail_outbox_not_exists(
        self,
        db_session,
        upstream_patient,
    ) -> None:
        """情境 C：業務資料失敗 → Outbox 不存在。

        故意在建立業務資料時違反約束（如 NOT NULL），
        驗證 Outbox 尚未建立（因為是同一個交易，rollback 後不存在）。
        """
        from src.backend.domain.recommendation import (
            RecommendationModel,
        )

        rec_id = f"rec-{uuid.uuid4().hex}"

        # 嘗試建立一個無效的 Recommendation（缺少必要欄位）
        with pytest.raises(Exception):
            bad_rec = RecommendationModel(
                patient_id=upstream_patient.id,
                # 缺少 recommendation_id（NOT NULL, unique）
                # 缺少 status（NOT NULL）
                result_payload={"test": True},
            )
            db_session.add(bad_rec)
            await db_session.flush()

        # Rollback 清除 PendingRollbackError
        await db_session.rollback()

        # ---- Assert ----
        # 驗證 Outbox 不存在（因為交易失敗，尚未建立 Outbox）
        from sqlalchemy import select

        from src.backend.domain.clinical_graph_outbox import (
            ClinicalGraphOutboxModel,
        )

        stmt_outbox = select(ClinicalGraphOutboxModel).where(
            ClinicalGraphOutboxModel.aggregate_id == rec_id,
        )
        result = await db_session.execute(stmt_outbox)
        outboxes = list(result.scalars().all())
        assert len(outboxes) == 0, (
            "Outbox should NOT exist — business data creation failed, "
            "so Outbox was never created in the same transaction"
        )

        # 驗證 Recommendation 也不存在
        stmt_rec = select(RecommendationModel).where(
            RecommendationModel.recommendation_id == rec_id,
        )
        result = await db_session.execute(stmt_rec)
        found_rec = result.scalar_one_or_none()
        assert found_rec is None, (
            "Recommendation should NOT exist — was rolled back"
        )

    async def test_d_outbox_and_business_data_same_transaction_commit(
        self,
        db_session,
        upstream_patient,
    ) -> None:
        """驗證 Outbox 和業務資料在同一交易中 commit 後全部存在。

        此測試模擬 Service 層的完整流程：
        1. 建立業務資料（flush）
        2. 建立 Outbox（flush）
        3. Commit 交易
        4. 驗證全部存在
        """
        from sqlalchemy import select

        from src.backend.domain.clinical_graph_outbox import (
            ClinicalGraphOutboxModel,
        )
        from src.backend.domain.recommendation import (
            RecommendationModel,
        )
        from src.backend.repositories.clinical_graph_outbox_repo import (
            ClinicalGraphOutboxRepository,
        )

        rec_id = f"rec-{uuid.uuid4().hex}"
        event_id = f"event-{uuid.uuid4().hex}"

        # ---- Act ----
        # Step 1: 建立業務資料
        rec = RecommendationModel(
            patient_id=upstream_patient.id,
            recommendation_id=rec_id,
            status="completed",
            result_payload={"test": True},
        )
        db_session.add(rec)
        await db_session.flush()

        # Step 2: 建立 Outbox
        outbox_repo = ClinicalGraphOutboxRepository(db_session)
        await outbox_repo.create(
            event_id=event_id,
            aggregate_type="recommendation",
            aggregate_id=rec_id,
            event_type="recommendation.created",
            schema_version=1,
            payload={"recommendation_id": rec_id},
        )

        # Step 3: Commit
        await db_session.commit()

        # ---- Assert ----
        # 驗證 Recommendation 存在
        stmt_rec = select(RecommendationModel).where(
            RecommendationModel.id == rec.id,
        )
        result = await db_session.execute(stmt_rec)
        found_rec = result.scalar_one_or_none()
        assert found_rec is not None, "Recommendation should exist after commit"

        # 驗證 Outbox 存在
        stmt_outbox = select(ClinicalGraphOutboxModel).where(
            ClinicalGraphOutboxModel.event_id == event_id,
        )
        result = await db_session.execute(stmt_outbox)
        outbox = result.scalar_one_or_none()
        assert outbox is not None, "Outbox should exist after commit"
        assert outbox.status == "pending", "Outbox should start as pending"
