"""
T-04: Treatment Plan 完整流程原子性測試 — 綠燈

情境：
1. 建立 Treatment Plan → flush 取得 plan.id
2. 建立 Phase（使用 plan.id）
3. 建立 Item（使用 phase.id）
4. 建立 Trace + Outbox
5. 中間任一步失敗（NOT NULL 約束違反、UNIQUE 約束違反）
6. Rollback
7. 驗證所有資料都不存在（flush-only + rollback）

預期：全部綠燈（PASS）
- 所有 Repository 使用 flush-only，不 commit
- Service 層控制交易邊界
- 失敗後 rollback 清除所有未 commit 的資料
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

    from src.backend.domain.patient import PatientModel  # noqa: F401
    from src.backend.domain.treatment_plan import (  # noqa: F401
        TreatmentItemModel,
        TreatmentMonitoringModel,
        TreatmentPhaseModel,
        TreatmentPlanModel,
        TreatmentPlanTraceModel,
        TreatmentSafetyRuleModel,
    )
    from src.backend.domain.clinical_graph_outbox import (  # noqa: F401
        ClinicalGraphOutboxModel,
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
async def patient(db_session):
    """Create a minimal Patient for FK references.

    注意：使用 PatientRepository.create()（繼承 BaseRepository），
    現在為 flush-only 模式。Patient 與測試主體共用同一 session，
    因此 FK 約束檢查可正常通過（同一交易中可見）。
    """
    from src.backend.repositories.patient_repo import PatientRepository

    repo = PatientRepository(db_session)
    p = await repo.create(display_name="T04-TEST-PATIENT")
    return p


class TestTreatmentPlanFlowAtomicity:
    """測試 Treatment Plan 完整流程的原子性。"""

    async def _create_plan(
        self,
        db_session: AsyncSession,
        patient,
        plan_id: str = "t04-plan-001",
        version: int = 1,
        **kwargs,
    ):
        """Helper to create a TreatmentPlan via repository."""
        from src.backend.domain.treatment_plan import TreatmentPlanModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        repo = TreatmentPlanRepository(db_session)
        model = TreatmentPlanModel(
            plan_id=plan_id,
            version=version,
            patient_id=patient.id,
            plan_status=kwargs.get("plan_status", "draft"),
            plan_intent=kwargs.get("plan_intent", "curative"),
            is_current=kwargs.get("is_current", True),
        )
        return await repo.create(model)

    async def _create_phase(
        self,
        db_session: AsyncSession,
        plan_model,
        phase_id: str = "t04-phase-001",
        phase_order: int = 1,
        **kwargs,
    ):
        """Helper to create a TreatmentPhase via repository."""
        from src.backend.domain.treatment_plan import TreatmentPhaseModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPhaseRepository,
        )

        repo = TreatmentPhaseRepository(db_session)
        model = TreatmentPhaseModel(
            phase_id=phase_id,
            plan_id=plan_model.id,
            phase_order=phase_order,
            phase_type=kwargs.get("phase_type", "preparation"),
            name=kwargs.get("name", "Preparation Phase"),
            duration_days=kwargs.get("duration_days", 14),
            status="planned",
        )
        return await repo.create(model)

    async def _create_item(
        self,
        db_session: AsyncSession,
        plan_model,
        phase_model,
        item_id: str = "t04-item-001",
        item_order: int = 1,
        **kwargs,
    ):
        """Helper to create a TreatmentItem via repository."""
        from src.backend.domain.treatment_plan import TreatmentItemModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentItemRepository,
        )

        repo = TreatmentItemRepository(db_session)
        model = TreatmentItemModel(
            item_id=item_id,
            plan_id=plan_model.id,
            phase_id=phase_model.id,
            item_order=item_order,
            item_type=kwargs.get("item_type", "medication"),
            name=kwargs.get("name", "Test Medication"),
        )
        return await repo.create(model)

    async def _create_trace(
        self,
        db_session: AsyncSession,
        plan_model,
        trace_id: str = "t04-trace-001",
        step_order: int = 1,
        **kwargs,
    ):
        """Helper to create a TreatmentPlanTrace via repository."""
        from src.backend.domain.treatment_plan import TreatmentPlanTraceModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanTraceRepository,
        )

        repo = TreatmentPlanTraceRepository(db_session)
        model = TreatmentPlanTraceModel(
            trace_id=trace_id,
            plan_id=plan_model.id,
            step_order=step_order,
            step_type=kwargs.get("step_type", "test_step"),
        )
        return await repo.create(model)

    async def _create_outbox(
        self,
        db_session: AsyncSession,
        plan_model,
        **kwargs,
    ):
        """Helper to create an outbox record."""
        from src.backend.repositories.clinical_graph_outbox_repo import (
            ClinicalGraphOutboxRepository,
        )

        repo = ClinicalGraphOutboxRepository(db_session)
        return await repo.create(
            event_id=kwargs.get("event_id", f"event-{uuid.uuid4().hex}"),
            aggregate_type="treatment_plan",
            aggregate_id=plan_model.plan_id,
            event_type="treatment_plan.created",
            schema_version=1,
            payload={"plan_id": plan_model.plan_id},
            actor_id=kwargs.get("actor_id", "t04-test-user"),
        )

    # ── Tests ──────────────────────────────────────────────────────────

    async def test_full_flow_rollback_on_item_failure(self, db_session, patient) -> None:
        """GREEN LIGHT: 當 Item 建立失敗（NOT NULL 違反）時，所有資料應被 rollback。

        情境：
        1. 建立 Treatment Plan（flush）
        2. 建立 Phase（flush）
        3. 建立 Item 時故意遺漏必要欄位 name（NOT NULL）→ 失敗
        4. Rollback
        5. 驗證 Plan 和 Phase 不存在

        注意：SQLite 的 NOT NULL 約束永遠被檢查（無需 PRAGMA）。
        """
        # ---- Arrange ----
        # Step 1: 建立 Treatment Plan
        plan = await self._create_plan(db_session, patient)
        plan_id = plan.id

        # Step 2: 建立 Phase
        phase = await self._create_phase(db_session, plan)
        phase_id = phase.id

        # ---- Act ----
        # Step 3: 建立 Item 時故意遺漏必要欄位 name（NOT NULL 違反）
        from src.backend.domain.treatment_plan import TreatmentItemModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentItemRepository,
        )

        item_repo = TreatmentItemRepository(db_session)
        with pytest.raises(Exception) as exc_info:
            bad_item = TreatmentItemModel(
                item_id="t04-item-bad",
                plan_id=plan_id,
                phase_id=phase_id,  # 使用正確的 phase_id
                item_order=1,
                item_type="medication",
                # name 未設定 → 預設為 None → NOT NULL 違反！
            )
            await item_repo.create(bad_item)

        # Step 4: Rollback 清除 PendingRollbackError 狀態
        await db_session.rollback()

        # ---- Assert ----
        # 驗證 Plan 不存在（flush-only，rollback 生效）
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
            TreatmentPhaseRepository,
        )
        plan_repo = TreatmentPlanRepository(db_session)
        found_plan = await plan_repo.get(plan_id)
        assert found_plan is None, (
            "✅ GREEN LIGHT: TreatmentPlan was rollbacked after Item NOT NULL failure."
        )

        # 驗證 Phase 不存在
        phase_repo = TreatmentPhaseRepository(db_session)
        found_phase = await phase_repo.get(phase_id)
        assert found_phase is None, (
            "✅ GREEN LIGHT: TreatmentPhase was rollbacked after Item NOT NULL failure."
        )

    async def test_full_flow_rollback_on_trace_failure(self, db_session, patient) -> None:
        """GREEN LIGHT: 當 Trace 建立失敗（UNIQUE 違反）時，所有資料應被 rollback。

        情境：
        1. 建立 Treatment Plan（flush）
        2. 建立 Phase（flush）
        3. 建立 Item（flush）
        4. 建立 Trace 時故意違反 UNIQUE 約束 → 失敗
        5. Rollback
        6. 驗證所有資料不存在
        """
        # ---- Arrange ----
        # Steps 1-3: 建立 Plan + Phase + Item
        plan = await self._create_plan(db_session, patient, plan_id="t04-plan-002")
        phase = await self._create_phase(
            db_session, plan, phase_id="t04-phase-002",
        )
        item = await self._create_item(
            db_session, plan, phase, item_id="t04-item-002",
        )

        # Step 4a: 建立第一個 Trace（成功）
        trace = await self._create_trace(
            db_session, plan, trace_id="t04-trace-002",
        )

        # ---- Act ----
        # Step 4b: 建立第二個 Trace 使用相同的 trace_id + step_order
        # （違反 UniqueConstraint("trace_id", "step_order")）
        from src.backend.domain.treatment_plan import TreatmentPlanTraceModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanTraceRepository,
        )

        trace_repo = TreatmentPlanTraceRepository(db_session)
        with pytest.raises(Exception):
            duplicate_trace = TreatmentPlanTraceModel(
                trace_id="t04-trace-002",  # 與上一個相同
                plan_id=plan.id,
                step_order=1,  # 與上一個相同 → 違反 UQ
                step_type="duplicate_step",
            )
            await trace_repo.create(duplicate_trace)

        # Step 5: Rollback
        await db_session.rollback()

        # ---- Assert ----
        # 驗證所有資料都不存在
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
            TreatmentPhaseRepository,
            TreatmentItemRepository,
        )

        plan_repo = TreatmentPlanRepository(db_session)
        phase_repo = TreatmentPhaseRepository(db_session)
        item_repo = TreatmentItemRepository(db_session)

        assert await plan_repo.get(plan.id) is None, "Plan should be rollbacked"
        assert await phase_repo.get(phase.id) is None, "Phase should be rollbacked"
        assert await item_repo.get(item.id) is None, "Item should be rollbacked"

    async def test_full_flow_rollback_on_outbox_failure(self, db_session, patient) -> None:
        """GREEN LIGHT: 當 Outbox 建立失敗（NOT NULL 違反）時，所有資料應被 rollback。

        情境：
        1. 建立 Treatment Plan（flush）
        2. 建立 Phase（flush）
        3. 建立 Item（flush）
        4. 建立 Trace（flush）
        5. 建立 Outbox 時故意傳入無效資料（遺漏必要欄位） → 失敗
        6. Rollback
        7. 驗證所有資料不存在
        """
        # ---- Arrange ----
        plan = await self._create_plan(db_session, patient, plan_id="t04-plan-003")
        phase = await self._create_phase(
            db_session, plan, phase_id="t04-phase-003",
        )
        item = await self._create_item(
            db_session, plan, phase, item_id="t04-item-003",
        )
        trace = await self._create_trace(
            db_session, plan, trace_id="t04-trace-003",
        )

        # ---- Act ----
        # 建立 Outbox 時故意遺漏必要欄位
        from src.backend.domain.clinical_graph_outbox import (
            ClinicalGraphOutboxModel,
        )

        with pytest.raises(Exception):
            # 直接使用 model 並遺漏必要欄位
            bad_outbox = ClinicalGraphOutboxModel(
                # 缺少 aggregate_type（NOT NULL）
                # 缺少 aggregate_id（NOT NULL）
                # 缺少 event_type（NOT NULL）
                payload={"test": True},
            )
            db_session.add(bad_outbox)
            await db_session.flush()

        # Rollback
        await db_session.rollback()

        # ---- Assert ----
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
            TreatmentPhaseRepository,
            TreatmentItemRepository,
            TreatmentPlanTraceRepository,
        )

        plan_repo = TreatmentPlanRepository(db_session)
        phase_repo = TreatmentPhaseRepository(db_session)
        item_repo = TreatmentItemRepository(db_session)
        trace_repo = TreatmentPlanTraceRepository(db_session)

        assert await plan_repo.get(plan.id) is None, "Plan should be rollbacked"
        assert await phase_repo.get(phase.id) is None, "Phase should be rollbacked"
        assert await item_repo.get(item.id) is None, "Item should be rollbacked"
        # 注意：trace 也可能需要清理
        traces = await trace_repo.list_by_plan_id(plan.id)
        assert len(traces) == 0, "Traces should be rollbacked"
