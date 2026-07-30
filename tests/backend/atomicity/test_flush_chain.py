"""
T-23: Flush Chain 測試 — 驗證 flush 後 PK 可用、FK 子資料可建立

情境：使用 TreatmentPlan 領域的完整 flush chain：
1. Plan flush → 取得 plan.id（PK）
2. Phase 使用 plan.id（FK）→ flush → 取得 phase.id
3. Item 使用 phase.id（FK）→ flush → 取得 item.id
4. Outbox 使用 plan_id（business ID）→ flush
5. Service commit → 所有資料持久化

驗證：每個步驟 flush 後 PK 可用，FK 子資料可正確建立，
最終 commit 後所有資料存在。
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
    from src.backend.domain.treatment_plan import (  # noqa: F401
        TreatmentItemModel,
        TreatmentMonitoringModel,
        TreatmentPhaseModel,
        TreatmentPlanModel,
        TreatmentPlanTraceModel,
        TreatmentSafetyRuleModel,
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


class TestFlushChain:
    """驗證 flush chain：每個步驟 flush 後 PK 可用，FK 子資料可建立。"""

    async def test_plan_phase_item_outbox_flush_chain(
        self,
        db_session,
    ) -> None:
        """GREEN LIGHT: Plan → Phase → Item → Outbox flush chain。

        模擬 Service 層的真實交易流程：
        1. 建立 Patient（flush 取得 PK）
        2. 建立 Plan 使用 patient.id（flush 取得 plan.id）
        3. 建立 Phase 使用 plan.id（flush 取得 phase.id）
        4. 建立 Item 使用 plan.id + phase.id（flush 取得 item.id）
        5. 建立 Trace 使用 plan.id（flush）
        6. 建立 Outbox 使用 plan_id（flush）
        7. Commit 全部
        8. 驗證所有資料存在
        """
        from src.backend.domain.enums import ConsentStatusEnum, SexEnum
        from src.backend.domain.patient import PatientModel
        from src.backend.domain.treatment_plan import (
            TreatmentItemModel,
            TreatmentPhaseModel,
            TreatmentPlanModel,
            TreatmentPlanTraceModel,
        )
        from src.backend.repositories.clinical_graph_outbox_repo import (
            ClinicalGraphOutboxRepository,
        )

        plan_id_str = f"plan-{uuid.uuid4().hex[:12]}"

        # ═══════════════════════════════════════════════════════════════
        # Step 1: 建立 Patient（flush 取得 PK）
        # ═══════════════════════════════════════════════════════════════
        patient = PatientModel(
            display_name="Flush Chain Patient",
            sex=SexEnum.UNKNOWN,
            consent_status=ConsentStatusEnum.GRANTED,
        )
        db_session.add(patient)
        await db_session.flush()
        assert patient.id is not None, (
            "Step 1 FAILED: Patient PK should be available after flush"
        )
        print(f"  ✓ Patient PK = {patient.id}")

        # ═══════════════════════════════════════════════════════════════
        # Step 2: 建立 Plan 使用 patient.id（FK 參考）
        # ═══════════════════════════════════════════════════════════════
        plan = TreatmentPlanModel(
            plan_id=plan_id_str,
            version=1,
            patient_id=patient.id,
            plan_status="draft",
            plan_intent="curative",
            is_current=True,
        )
        db_session.add(plan)
        await db_session.flush()
        assert plan.id is not None, (
            "Step 2 FAILED: Plan PK should be available after flush"
        )
        print(f"  ✓ Plan PK = {plan.id}")

        # ═══════════════════════════════════════════════════════════════
        # Step 3: 建立 Phase 使用 plan.id（FK 參考）
        # ═══════════════════════════════════════════════════════════════
        phase = TreatmentPhaseModel(
            phase_id=f"phase-{uuid.uuid4().hex[:12]}",
            plan_id=plan.id,
            phase_order=1,
            phase_type="preparation",
            name="Preparation Phase",
            duration_days=14,
            status="planned",
        )
        db_session.add(phase)
        await db_session.flush()
        assert phase.id is not None, (
            "Step 3 FAILED: Phase PK should be available after flush"
        )
        assert phase.plan_id == plan.id, (
            "Step 3 FAILED: Phase.plan_id should reference Plan.id"
        )
        print(f"  ✓ Phase PK = {phase.id}")

        # ═══════════════════════════════════════════════════════════════
        # Step 4: 建立 Item 使用 plan.id + phase.id（FK 參考）
        # ═══════════════════════════════════════════════════════════════
        item = TreatmentItemModel(
            item_id=f"item-{uuid.uuid4().hex[:12]}",
            plan_id=plan.id,
            phase_id=phase.id,
            item_order=1,
            item_type="medication",
            name="Lenvatinib",
        )
        db_session.add(item)
        await db_session.flush()
        assert item.id is not None, (
            "Step 4 FAILED: Item PK should be available after flush"
        )
        assert item.plan_id == plan.id, (
            "Step 4 FAILED: Item.plan_id should reference Plan.id"
        )
        assert item.phase_id == phase.id, (
            "Step 4 FAILED: Item.phase_id should reference Phase.id"
        )
        print(f"  ✓ Item PK = {item.id}")

        # ═══════════════════════════════════════════════════════════════
        # Step 5: 建立 Trace 使用 plan.id（FK 參考）
        # ═══════════════════════════════════════════════════════════════
        trace = TreatmentPlanTraceModel(
            trace_id=f"trace-{uuid.uuid4().hex[:12]}",
            plan_id=plan.id,
            step_order=1,
            step_type="engine_generation",
        )
        db_session.add(trace)
        await db_session.flush()
        assert trace.id is not None, (
            "Step 5 FAILED: Trace PK should be available after flush"
        )
        assert trace.plan_id == plan.id, (
            "Step 5 FAILED: Trace.plan_id should reference Plan.id"
        )
        print(f"  ✓ Trace PK = {trace.id}")

        # ═══════════════════════════════════════════════════════════════
        # Step 6: 建立 Outbox 使用 plan_id（business ID）
        # ═══════════════════════════════════════════════════════════════
        outbox_repo = ClinicalGraphOutboxRepository(db_session)
        outbox = await outbox_repo.create(
            event_id=f"event-{uuid.uuid4().hex}",
            aggregate_type="treatment_plan",
            aggregate_id=plan_id_str,
            event_type="treatment_plan.created",
            schema_version=1,
            payload={"plan_id": plan_id_str},
            actor_id="test-user",
        )
        assert outbox.id is not None, (
            "Step 6 FAILED: Outbox PK should be available after flush"
        )
        assert outbox.aggregate_id == plan_id_str, (
            "Step 6 FAILED: Outbox.aggregate_id should reference plan_id_str"
        )
        print(f"  ✓ Outbox PK = {outbox.id}")

        # ═══════════════════════════════════════════════════════════════
        # Step 7: Commit 全部
        # ═══════════════════════════════════════════════════════════════
        await db_session.commit()

        # ═══════════════════════════════════════════════════════════════
        # Step 8: 驗證所有資料存在
        # ═══════════════════════════════════════════════════════════════
        from sqlalchemy import select

        # 驗證 Patient
        stmt = select(PatientModel).where(PatientModel.id == patient.id)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is not None, (
            "Step 8 FAILED: Patient should exist after commit"
        )

        # 驗證 Plan
        stmt = select(TreatmentPlanModel).where(TreatmentPlanModel.id == plan.id)
        result = await db_session.execute(stmt)
        found_plan = result.scalar_one_or_none()
        assert found_plan is not None, "Plan should exist after commit"
        assert str(found_plan.patient_id) == str(patient.id), (
            "Plan patient_id should match Patient id"
        )

        # 驗證 Phase
        stmt = select(TreatmentPhaseModel).where(TreatmentPhaseModel.id == phase.id)
        result = await db_session.execute(stmt)
        found_phase = result.scalar_one_or_none()
        assert found_phase is not None, "Phase should exist after commit"
        assert str(found_phase.plan_id) == str(plan.id), (
            "Phase plan_id should match Plan id"
        )

        # 驗證 Item
        stmt = select(TreatmentItemModel).where(TreatmentItemModel.id == item.id)
        result = await db_session.execute(stmt)
        found_item = result.scalar_one_or_none()
        assert found_item is not None, "Item should exist after commit"
        assert str(found_item.plan_id) == str(plan.id), (
            "Item plan_id should match Plan id"
        )
        assert str(found_item.phase_id) == str(phase.id), (
            "Item phase_id should match Phase id"
        )

        # 驗證 Trace
        stmt = select(TreatmentPlanTraceModel).where(
            TreatmentPlanTraceModel.id == trace.id,
        )
        result = await db_session.execute(stmt)
        found_trace = result.scalar_one_or_none()
        assert found_trace is not None, "Trace should exist after commit"
        assert str(found_trace.plan_id) == str(plan.id), (
            "Trace plan_id should match Plan id"
        )

        # 驗證 Outbox
        from src.backend.domain.clinical_graph_outbox import (
            ClinicalGraphOutboxModel,
        )
        stmt = select(ClinicalGraphOutboxModel).where(
            ClinicalGraphOutboxModel.id == outbox.id,
        )
        result = await db_session.execute(stmt)
        found_outbox = result.scalar_one_or_none()
        assert found_outbox is not None, "Outbox should exist after commit"
        assert found_outbox.aggregate_id == plan_id_str, (
            "Outbox aggregate_id should match plan_id_str"
        )

    async def test_flush_chain_rollback_removes_all(
        self,
        db_session,
    ) -> None:
        """驗證 flush chain rollback 後所有資料不存在。

        建立完整的 Plan → Phase → Item → Trace → Outbox chain，
        然後 rollback，確認所有資料都不存在。
        """
        from src.backend.domain.enums import ConsentStatusEnum, SexEnum
        from src.backend.domain.patient import PatientModel
        from src.backend.domain.treatment_plan import (
            TreatmentItemModel,
            TreatmentPhaseModel,
            TreatmentPlanModel,
            TreatmentPlanTraceModel,
        )
        from src.backend.repositories.clinical_graph_outbox_repo import (
            ClinicalGraphOutboxRepository,
        )

        plan_id_str = f"plan-{uuid.uuid4().hex[:12]}"

        # 建立 Patient
        patient = PatientModel(
            display_name="Rollback Test Patient",
            sex=SexEnum.UNKNOWN,
            consent_status=ConsentStatusEnum.GRANTED,
        )
        db_session.add(patient)
        await db_session.flush()

        # 建立 Plan
        plan = TreatmentPlanModel(
            plan_id=plan_id_str,
            version=1,
            patient_id=patient.id,
            plan_status="draft",
            plan_intent="curative",
            is_current=True,
        )
        db_session.add(plan)
        await db_session.flush()

        # 建立 Phase
        phase = TreatmentPhaseModel(
            phase_id=f"phase-{uuid.uuid4().hex[:12]}",
            plan_id=plan.id,
            phase_order=1,
            phase_type="preparation",
            name="Preparation Phase",
            duration_days=14,
            status="planned",
        )
        db_session.add(phase)
        await db_session.flush()

        # 建立 Item
        item = TreatmentItemModel(
            item_id=f"item-{uuid.uuid4().hex[:12]}",
            plan_id=plan.id,
            phase_id=phase.id,
            item_order=1,
            item_type="medication",
            name="Lenvatinib",
        )
        db_session.add(item)
        await db_session.flush()

        # 建立 Trace
        trace = TreatmentPlanTraceModel(
            trace_id=f"trace-{uuid.uuid4().hex[:12]}",
            plan_id=plan.id,
            step_order=1,
            step_type="engine_generation",
        )
        db_session.add(trace)
        await db_session.flush()

        # 建立 Outbox
        outbox_repo = ClinicalGraphOutboxRepository(db_session)
        outbox = await outbox_repo.create(
            event_id=f"event-{uuid.uuid4().hex}",
            aggregate_type="treatment_plan",
            aggregate_id=plan_id_str,
            event_type="treatment_plan.created",
            schema_version=1,
            payload={"plan_id": plan_id_str},
            actor_id="test-user",
        )

        # ---- Rollback ----
        await db_session.rollback()

        # ---- Assert: 全部不存在 ----
        from sqlalchemy import select

        from src.backend.domain.clinical_graph_outbox import (
            ClinicalGraphOutboxModel,
        )

        assert (await db_session.execute(
            select(PatientModel).where(PatientModel.id == patient.id),
        )).scalar_one_or_none() is None, "Patient should not exist after rollback"

        assert (await db_session.execute(
            select(TreatmentPlanModel).where(TreatmentPlanModel.id == plan.id),
        )).scalar_one_or_none() is None, "Plan should not exist after rollback"

        assert (await db_session.execute(
            select(TreatmentPhaseModel).where(TreatmentPhaseModel.id == phase.id),
        )).scalar_one_or_none() is None, "Phase should not exist after rollback"

        assert (await db_session.execute(
            select(TreatmentItemModel).where(TreatmentItemModel.id == item.id),
        )).scalar_one_or_none() is None, "Item should not exist after rollback"

        assert (await db_session.execute(
            select(TreatmentPlanTraceModel).where(TreatmentPlanTraceModel.id == trace.id),
        )).scalar_one_or_none() is None, "Trace should not exist after rollback"

        assert (await db_session.execute(
            select(ClinicalGraphOutboxModel).where(ClinicalGraphOutboxModel.id == outbox.id),
        )).scalar_one_or_none() is None, "Outbox should not exist after rollback"
