"""
T-07 Restart Recovery — Treatment Plan 完整重启恢复集成测试。

验证：
1. App 1 (session 1) 建立完整 Treatment Plan（含 Phases/Items/Monitoring/Safety/Trace）
2. 模拟 Shutdown（session.close()）
3. App 2 (session 2) GET Plan / Phases / Items / Trace
4. 确认所有資料完整讀回，資料一致

使用文件型 SQLite 使得數據在 session 關閉後仍然存在。
遵循既有 test_restart_recovery.py 模式，但以 Service 層直接操作（而非 API）。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base as DBBase
from src.backend.domain.treatment_plan import (
    TreatmentItemModel,
    TreatmentMonitoringModel,
    TreatmentPhaseModel,
    TreatmentPlanModel,
    TreatmentPlanTraceModel,
    TreatmentSafetyRuleModel,
)
from src.backend.services.treatment_plan_service import (
    CreatePlanRequest,
    TreatmentPlanService,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _make_uuid(seed: str = "00000001") -> uuid.UUID:
    """Deterministic UUID from an 8-char hex seed (first group)."""
    return uuid.UUID(f"{seed}-0000-0000-0000-000000000000")


PATIENT_UUID = _make_uuid("10000001")
USER_UUID = _make_uuid("90000001")

VALID_REQUEST = CreatePlanRequest(
    patient_id=str(PATIENT_UUID),
    recommendation_id="rec-001",
    clinical_decision_id="cd-001",
    consensus_id="cons-001",
    plan_intent="curative",
    treatment_goals=["tumor_resection", "prevent_recurrence"],
    clinical_context={"cancer_type": "PTC"},
)

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
async def db_engine():
    """文件型 SQLite 引擎，數據跨 session 存在。"""
    file_path = f"test_restart_tp_{uuid.uuid4().hex}.db"
    url = f"sqlite+aiosqlite:///{file_path}"
    engine = create_async_engine(url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(DBBase.metadata.create_all)

    yield engine

    await engine.dispose()
    # 清理臨時 DB 文件及 WAL/SHM 文件
    import os
    for suffix in ("", "-wal", "-shm"):
        path = file_path + suffix
        if os.path.exists(path):
            try:
                os.unlink(path)
            except PermissionError:
                pass


@pytest.fixture
async def session1(db_engine) -> AsyncSession:
    """第一個 session — 用於建立 Plan。"""
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest.fixture
async def session2(db_engine) -> AsyncSession:
    """第二個 session — 用於重啟後讀回。"""
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


# ═══════════════════════════════════════════════════════════════════════════════
# T-07: Restart Recovery
# ═══════════════════════════════════════════════════════════════════════════════


class TestTreatmentPlanRestartRecovery:
    """完整 Plan 重啟恢復測試。"""

    async def _create_full_plan(self, db: AsyncSession) -> TreatmentPlanModel:
        """使用 TreatmentPlanService 建立一個完整的 Plan。

        注意：由於此處沒有真正的上游數據（recommendation/decision/consensus），
        我們直接操作 Repository 層來建立完整 Plan，模擬 create_plan 的輸出。
        """
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentItemRepository,
            TreatmentMonitoringRepository,
            TreatmentPhaseRepository,
            TreatmentPlanRepository,
            TreatmentPlanTraceRepository,
            TreatmentSafetyRuleRepository,
        )

        now = datetime.now(timezone.utc)
        plan_id_hex = uuid.uuid4().hex

        # ── Plan ────────────────────────────────────────────────────────────
        plan_model = TreatmentPlanModel(
            plan_id=plan_id_hex,
            version=1,
            patient_id=PATIENT_UUID,
            plan_status="draft",
            plan_intent="curative",
            treatment_goals=["tumor_resection", "prevent_recurrence"],
            summary="Test treatment plan for restart recovery",
            clinical_rationale="Test rationale",
            is_current=True,
            created_by=USER_UUID,
            created_at=now,
            updated_at=now,
        )
        plan_repo = TreatmentPlanRepository(db)
        plan_model = await plan_repo.create(plan_model)

        # ── Phases ──────────────────────────────────────────────────────────
        phase_repo = TreatmentPhaseRepository(db)
        phases = [
            TreatmentPhaseModel(
                phase_id=f"phase-{uuid.uuid4().hex}",
                plan_id=plan_model.id,
                phase_order=1,
                phase_type="preparation",
                name="Preparation",
                description="Pre-treatment preparation",
                duration_days=14,
                status="planned",
                created_at=now,
                updated_at=now,
            ),
            TreatmentPhaseModel(
                phase_id=f"phase-{uuid.uuid4().hex}",
                plan_id=plan_model.id,
                phase_order=2,
                phase_type="primary_treatment",
                name="Primary Treatment",
                description="Main treatment phase",
                duration_days=90,
                status="planned",
                created_at=now,
                updated_at=now,
            ),
        ]
        await phase_repo.create_many(phases)

        # ── Items ───────────────────────────────────────────────────────────
        item_repo = TreatmentItemRepository(db)
        items = [
            TreatmentItemModel(
                item_id=f"item-{uuid.uuid4().hex}",
                plan_id=plan_model.id,
                phase_id=phases[0].id,
                item_order=1,
                item_type="medication",
                name="Lenvatinib",
                description="Primary medication",
                drug_id="DB09021",
                procedure_code=None,
                frequency="once_daily",
                duration="24 weeks",
                route="oral",
                planned_dose_text="24 mg once daily with dose adjustments",
                priority=1,
                status="planned",
                rationale="Top-ranked drug",
                source_recommendation="recommendation_engine",
                created_at=now,
                updated_at=now,
            ),
            TreatmentItemModel(
                item_id=f"item-{uuid.uuid4().hex}",
                plan_id=plan_model.id,
                phase_id=phases[1].id,
                item_order=2,
                item_type="procedure",
                name="Tumor Resection",
                description="Surgical procedure",
                drug_id=None,
                procedure_code="CPT-47120",
                frequency=None,
                duration=None,
                route=None,
                planned_dose_text=None,
                priority=2,
                status="planned",
                rationale="Standard of care",
                created_at=now,
                updated_at=now,
            ),
        ]
        await item_repo.create_many(items)

        # ── Monitoring ─────────────────────────────────────────────────────
        monitoring_repo = TreatmentMonitoringRepository(db)
        monitoring = [
            TreatmentMonitoringModel(
                monitoring_id=f"mon-{uuid.uuid4().hex}",
                plan_id=plan_model.id,
                monitoring_type="laboratory",
                name="Complete Blood Count",
                schedule="weekly",
                target_range={"WBC": "4.0-10.0", "Hb": "12.0-16.0"},
                warning_threshold={"WBC": "3.0-11.0"},
                critical_threshold={"WBC": "<2.0 or >15.0"},
                action_if_abnormal="Notify attending physician and adjust dose",
                baseline_required=True,
                repeat_interval="7d",
                responsible_specialty="hematology",
                created_at=now,
                updated_at=now,
            ),
        ]
        await monitoring_repo.create_many(monitoring)

        # ── Safety Rules ───────────────────────────────────────────────────
        safety_repo = TreatmentSafetyRuleRepository(db)
        safety_rules = [
            TreatmentSafetyRuleModel(
                rule_id=f"rule-{uuid.uuid4().hex}",
                plan_id=plan_model.id,
                rule_type="review",
                condition={"type": "contraindication", "detail": "test"},
                severity="medium",
                recommended_action="Review",
                requires_review=True,
                created_at=now,
            ),
        ]
        await safety_repo.create_many(safety_rules)

        # ── Trace ──────────────────────────────────────────────────────────
        trace_repo = TreatmentPlanTraceRepository(db)
        trace_id = f"trace-{uuid.uuid4().hex}"
        traces = [
            TreatmentPlanTraceModel(
                trace_id=trace_id,
                plan_id=plan_model.id,
                step_order=0,
                step_type="load_context",
                input_summary={},
                output_summary={"status": "loaded"},
                created_at=now,
            ),
            TreatmentPlanTraceModel(
                trace_id=trace_id,
                plan_id=plan_model.id,
                step_order=1,
                step_type="validate_links",
                input_summary={},
                output_summary={"status": "validated"},
                created_at=now,
            ),
        ]
        await trace_repo.create_many(traces)

        # ── Commit ─────────────────────────────────────────────────────────
        await db.commit()

        # 回傳 plan 與各子模型的 metadata，避免 lazy loading（async 不支援）
        return (
            plan_model,
            [p.phase_id for p in phases],
            [i.item_id for i in items],
            [m.monitoring_id for m in monitoring],
            [s.rule_id for s in safety_rules],
            [t.trace_id for t in traces],
        )

    async def test_restart_recovery_full_plan(self, db_engine, session1, session2):
        """App 建立完整 Plan → Shutdown → 新 Session 讀回 → 驗證完整。

        步驟：
        1. Session 1: 建立包含 Phases/Items/Monitoring/SafetyRules/Trace 的 Plan
        2. Session 關閉（模擬 restart）
        3. Session 2: 讀回所有數據並驗證一致性
        """
        # ═════════════════════════════════════════════════════════════════
        # Phase 1: Session 1 — 建立完整 Plan
        # ═════════════════════════════════════════════════════════════════
        plan, phase_ids, item_ids, mon_ids, rule_ids, trace_ids = (
            await self._create_full_plan(session1)
        )
        plan_id = plan.plan_id
        plan_pk = plan.id

        # 記錄各子項目的數量（使用回傳的 ID list，避免 lazy loading）
        n_phases = len(phase_ids)
        n_items = len(item_ids)
        n_monitoring = len(mon_ids)
        n_safety = len(rule_ids)
        n_traces = len(trace_ids)

        assert n_phases > 0, "必須有至少一個 Phase"
        assert n_items > 0, "必須有至少一個 Item"
        assert n_monitoring > 0, "必須有至少一個 Monitoring"
        assert n_safety > 0, "必須有至少一個 Safety Rule"
        assert n_traces > 0, "必須有至少一個 Trace"

        # ═════════════════════════════════════════════════════════════════
        # Phase 2: Shutdown — session1 close 模擬重啟
        # ═════════════════════════════════════════════════════════════════
        await session1.close()

        # ═════════════════════════════════════════════════════════════════
        # Phase 3: Session 2 — 新 session 讀回並驗證
        # ═════════════════════════════════════════════════════════════════
        # 使用 session2 直接查詢資料庫

        # 3a: 讀回 Plan
        from sqlalchemy.orm import selectinload

        stmt = (
            select(TreatmentPlanModel)
            .options(
                selectinload(TreatmentPlanModel.phases),
                selectinload(TreatmentPlanModel.items),
                selectinload(TreatmentPlanModel.monitoring),
                selectinload(TreatmentPlanModel.safety_rules),
                selectinload(TreatmentPlanModel.traces),
            )
            .where(TreatmentPlanModel.id == plan_pk)
        )
        result = await session2.execute(stmt)
        restored = result.scalar_one_or_none()

        assert restored is not None, "Plan 必須能在新 session 中讀回"
        assert restored.plan_id == plan_id, "plan_id 必須一致"
        assert restored.version == 1, "version 必須為 1"
        assert restored.plan_status == "draft", "plan_status 必須為 draft"
        assert restored.plan_intent == "curative", "plan_intent 必須一致"
        assert restored.is_current is True, "is_current 必須為 True"
        assert restored.patient_id == PATIENT_UUID, "patient_id 必須一致"

        # 3b: 驗證 Phases
        assert len(restored.phases) == n_phases, (
            f"Phase 數量必須一致: 預期 {n_phases}, 得到 {len(restored.phases)}"
        )
        restored_phase_ids = {p.phase_id for p in restored.phases}
        assert restored_phase_ids == set(phase_ids), "phase_ids 必須一致"
        for phase in restored.phases:
            assert phase.plan_id == plan_pk, "Phase 的 plan_id 必須指向正確的 Plan"
            assert phase.phase_order in (1, 2), "phase_order 必須有效"
            assert phase.name in ("Preparation", "Primary Treatment")

        # 3c: 驗證 Items
        assert len(restored.items) == n_items, (
            f"Item 數量必須一致: 預期 {n_items}, 得到 {len(restored.items)}"
        )
        restored_item_ids = {i.item_id for i in restored.items}
        assert restored_item_ids == set(item_ids), "item_ids 必須一致"
        for item in restored.items:
            assert item.plan_id == plan_pk, "Item 的 plan_id 必須指向正確的 Plan"

        # 3c-2: 逐欄驗證 Item Engine Output 欄位在 restart 後不遺失
        for item in restored.items:
            if item.item_type == "medication":
                assert item.drug_id == "DB09021", \
                    f"drug_id mismatch: {item.drug_id}"
                assert item.procedure_code is None, \
                    f"procedure_code should be None: {item.procedure_code}"
                assert item.frequency == "once_daily", \
                    f"frequency mismatch: {item.frequency}"
                assert item.duration == "24 weeks", \
                    f"duration mismatch: {item.duration}"
                assert item.route == "oral", \
                    f"route mismatch: {item.route}"
                assert item.planned_dose_text == "24 mg once daily with dose adjustments", \
                    f"planned_dose_text mismatch: {item.planned_dose_text}"
            elif item.item_type == "procedure":
                assert item.drug_id is None, \
                    f"drug_id should be None for procedure: {item.drug_id}"
                assert item.procedure_code == "CPT-47120", \
                    f"procedure_code mismatch: {item.procedure_code}"
                assert item.frequency is None, \
                    f"frequency should be None for procedure: {item.frequency}"
                assert item.duration is None, \
                    f"duration should be None for procedure: {item.duration}"
                assert item.route is None, \
                    f"route should be None for procedure: {item.route}"
                assert item.planned_dose_text is None, \
                    f"planned_dose_text should be None for procedure: {item.planned_dose_text}"

        # 3d: 驗證 Monitoring
        assert len(restored.monitoring) == n_monitoring, (
            f"Monitoring 數量必須一致: 預期 {n_monitoring}, 得到 {len(restored.monitoring)}"
        )
        for mon in restored.monitoring:
            assert mon.plan_id == plan_pk, "Monitoring 的 plan_id 必須指向正確的 Plan"
            assert mon.monitoring_type == "laboratory"
            assert mon.schedule == "weekly"

        # 3d-2: 逐欄驗證 Monitoring 欄位在 restart 後不遺失
        for mon in restored.monitoring:
            assert mon.target_range == {"WBC": "4.0-10.0", "Hb": "12.0-16.0"}, \
                f"target_range mismatch: {mon.target_range}"
            assert mon.warning_threshold == {"WBC": "3.0-11.0"}, \
                f"warning_threshold mismatch: {mon.warning_threshold}"
            assert mon.critical_threshold == {"WBC": "<2.0 or >15.0"}, \
                f"critical_threshold mismatch: {mon.critical_threshold}"
            assert mon.action_if_abnormal == "Notify attending physician and adjust dose", \
                f"action_if_abnormal mismatch: {mon.action_if_abnormal}"
            assert mon.responsible_specialty == "hematology", \
                f"responsible_specialty mismatch: {mon.responsible_specialty}"

        # 3e: 驗證 Safety Rules
        assert len(restored.safety_rules) == n_safety, (
            f"Safety Rule 數量必須一致: 預期 {n_safety}, 得到 {len(restored.safety_rules)}"
        )
        for rule in restored.safety_rules:
            assert rule.plan_id == plan_pk, "Safety Rule 的 plan_id 必須指向正確的 Plan"
            assert rule.rule_type == "review"

        # 3f: 驗證 Trace
        assert len(restored.traces) == n_traces, (
            f"Trace 數量必須一致: 預期 {n_traces}, 得到 {len(restored.traces)}"
        )
        # 所有 trace steps 應共用同一個 trace_id
        trace_ids_set = {t.trace_id for t in restored.traces}
        assert len(trace_ids_set) == 1, \
            f"所有 trace steps 應共用同一個 trace_id: {trace_ids_set}"
        # step_order 應連續不重複
        step_orders = sorted(t.step_order for t in restored.traces)
        assert step_orders == list(range(n_traces)), \
            f"step_order 應連續不重複: {step_orders}"
        restored_trace_ids = {t.trace_id for t in restored.traces}
        assert restored_trace_ids == set(trace_ids), "trace_ids 必須一致"
        for trace in restored.traces:
            assert trace.plan_id == plan_pk, "Trace 的 plan_id 必須指向正確的 Plan"
            assert trace.step_type in ("load_context", "validate_links")

        # 3g: 驗證 Service 層也能讀取
        service = TreatmentPlanService(session2)
        response = await service.get_plan(plan_id)
        assert response is not None, "Service 必須能讀回 Plan"
        assert response.plan_id == plan_id
        assert len(response.phases) == n_phases
        assert len(response.items) == n_items
        assert len(response.trace) == n_traces

    async def test_restart_recovery_nonexistent_returns_none(
        self, db_engine, session2,
    ):
        """重啟後查詢不存在的 Plan 應返回 None。"""
        service = TreatmentPlanService(session2)
        result = await service.get_plan("nonexistent-plan-id")
        assert result is None, "不存在的 Plan 應返回 None"

    async def test_monitoring_persistence_columns(
        self, db_engine, session1, session2,
    ):
        """建立 Plan 後直接查 DB 逐欄驗證 Monitoring 欄位已寫入。

        驗證 target_range, warning_threshold, critical_threshold,
        action_if_abnormal, responsible_specialty 與 Engine Output 一致。
        """
        from sqlalchemy import select

        from src.backend.domain.treatment_plan import TreatmentMonitoringModel

        # 使用 _create_full_plan 建立完整資料（含 monitoring 欄位）
        plan_model, *_ = await self._create_full_plan(session1)
        await session1.close()

        # 在新 session 中直接查 DB
        stmt = select(TreatmentMonitoringModel).where(
            TreatmentMonitoringModel.plan_id == plan_model.id,
        )
        result = await session2.execute(stmt)
        rows = result.scalars().all()

        assert len(rows) >= 1, "必須有至少一個 Monitoring 記錄"

        for row in rows:
            assert row.target_range == {"WBC": "4.0-10.0", "Hb": "12.0-16.0"}, \
                f"target_range mismatch: {row.target_range}"
            assert row.warning_threshold == {"WBC": "3.0-11.0"}, \
                f"warning_threshold mismatch: {row.warning_threshold}"
            assert row.critical_threshold == {"WBC": "<2.0 or >15.0"}, \
                f"critical_threshold mismatch: {row.critical_threshold}"
            assert row.action_if_abnormal == "Notify attending physician and adjust dose", \
                f"action_if_abnormal mismatch: {row.action_if_abnormal}"
            assert row.responsible_specialty == "hematology", \
                f"responsible_specialty mismatch: {row.responsible_specialty}"

    async def test_trace_correctness(
        self, db_engine, session1, session2,
    ):
        """驗證 Trace 的正確性。

        測試：
        1. 建立 plan 後所有 trace steps 共用同一個 trace_id
        2. step_order 連續不重複（0-based）
        3. UNIQUE(trace_id, step_order) 約束有效（重複 step_order 應報錯）
        4. Restart 後 trace 資料完整讀回
        """
        from sqlalchemy import select
        from sqlalchemy.exc import IntegrityError

        from src.backend.domain.treatment_plan import TreatmentPlanTraceModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanTraceRepository,
        )

        # ── 1. 建立 plan 並取得 trace 資料 ──────────────────────────────
        (plan_model, *_, trace_ids) = await self._create_full_plan(session1)
        plan_pk = plan_model.id  # 在 session close 前保存主鍵值

        # 直接查 DB 驗證
        stmt = (
            select(TreatmentPlanTraceModel)
            .where(TreatmentPlanTraceModel.plan_id == plan_model.id)
            .order_by(TreatmentPlanTraceModel.step_order)
        )
        result = await session1.execute(stmt)
        traces = result.scalars().all()

        assert len(traces) == 2, f"預期 2 個 traces, 得到 {len(traces)}"

        # 所有 trace steps 共用同一個 trace_id
        trace_ids_found = {t.trace_id for t in traces}
        assert len(trace_ids_found) == 1, \
            f"所有 trace steps 應共用同一個 trace_id: {trace_ids_found}"

        # step_order 連續不重複
        step_orders = [t.step_order for t in traces]
        assert step_orders == [0, 1], \
            f"step_order 應連續不重複: {step_orders}"

        # ── 2. UNIQUE(trace_id, step_order) 約束有效 ──────────────────
        shared_trace_id = traces[0].trace_id
        duplicate = TreatmentPlanTraceModel(
            trace_id=shared_trace_id,
            plan_id=plan_model.id,
            step_order=0,  # 與第一個 trace 重複
            step_type="duplicate_test",
        )
        repo = TreatmentPlanTraceRepository(session1)
        with pytest.raises(IntegrityError):
            await repo.create(duplicate)
        await session1.rollback()  # 清理壞掉的 session

        # ── 3. Restart 後 trace 資料完整讀回 ──────────────────────────
        await session1.close()
        stmt2 = (
            select(TreatmentPlanTraceModel)
            .where(TreatmentPlanTraceModel.plan_id == plan_pk)
            .order_by(TreatmentPlanTraceModel.step_order)
        )
        result2 = await session2.execute(stmt2)
        restored_traces = result2.scalars().all()

        assert len(restored_traces) == 2, \
            f"Restart 後 trace 數量應一致: 預期 2, 得到 {len(restored_traces)}"
        assert restored_traces[0].trace_id == shared_trace_id, \
            "Restart 後 trace_id 應一致"
        assert restored_traces[1].trace_id == shared_trace_id, \
            "Restart 後 trace_id 應一致"
        assert [t.step_order for t in restored_traces] == [0, 1], \
            f"Restart 後 step_order 應連續: {[t.step_order for t in restored_traces]}"

    async def test_restart_recovery_multiple_plans(
        self, db_engine, session1, session2,
    ):
        """重啟後應能正確讀回多個 Plan。"""
        # 建立兩個 Plan
        plan1, p1_phase_ids, p1_item_ids, p1_mon_ids, p1_rule_ids, p1_trace_ids = (
            await self._create_full_plan(session1)
        )
        plan2, p2_phase_ids, *_ = await self._create_full_plan(session1)
        await session1.close()

        # 在新 session 中讀回
        service = TreatmentPlanService(session2)
        result1 = await service.get_plan(plan1.plan_id)
        result2 = await service.get_plan(plan2.plan_id)

        assert result1 is not None
        assert result2 is not None
        assert result1.plan_id == plan1.plan_id
        assert result2.plan_id == plan2.plan_id
        assert result1.plan_id != result2.plan_id

        # 驗證各自的子項目數量正確（使用回傳的 ID list）
        n_phases1 = len(p1_phase_ids)
        n_phases2 = len(p2_phase_ids)
        assert len(result1.phases) == n_phases1
        assert len(result2.phases) == n_phases2
