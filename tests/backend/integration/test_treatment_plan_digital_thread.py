"""
T-08 Digital Thread — 完整鏈路整合測試。

測試完整追溯鏈：
Patient → Recommendation → Clinical Decision → Tumor Board Consensus
→ Treatment Plan → Phase → Item

驗證每個階段的 FK 連結正確，且可以從任一端點追溯回 Patient。
遵循既有 test_tumor_board_digital_thread.py 模式。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from src.backend.database.models import Base as DBBase
from src.backend.domain.clinical_decision import ClinicalDecisionModel
from src.backend.domain.enums import ConsentStatusEnum, SexEnum
from src.backend.domain.patient import PatientModel
from src.backend.domain.recommendation import RecommendationModel
from src.backend.domain.treatment_plan import (
    TreatmentItemModel,
    TreatmentMonitoringModel,
    TreatmentPhaseModel,
    TreatmentPlanModel,
    TreatmentPlanTraceModel,
    TreatmentSafetyRuleModel,
)
from src.backend.domain.tumor_board import (
    TumorBoardConsensusModel,
    TumorBoardOpinionModel,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

PATIENT_ID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
async def db_session():
    """In-memory SQLite database session for digital thread tests."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(DBBase.metadata.create_all)
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def patient(db_session):
    """Create a Patient record."""
    p = PatientModel(
        id=PATIENT_ID,
        display_name="DT-TEST-PATIENT-TP",
        sex=SexEnum.F,
        consent_status=ConsentStatusEnum.GRANTED,
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest.fixture
async def recommendation(db_session, patient):
    """Create a Recommendation record."""
    rec = RecommendationModel(
        recommendation_id="rec-dt-tp-001",
        patient_id=patient.id,
        engine_version="1.0.0",
        status="completed",
        request_payload={"variants": ["BRAF V600E"]},
        result_payload={
            "recommendations": [
                {"drug_name": "Dabrafenib", "rank": 1, "overall_score": 0.92},
            ],
            "evidence": [],
        },
    )
    db_session.add(rec)
    await db_session.commit()
    await db_session.refresh(rec)
    return rec


@pytest.fixture
async def clinical_decision(db_session, patient, recommendation):
    """Create a ClinicalDecision record."""
    cd = ClinicalDecisionModel(
        decision_id="cd-dt-tp-001",
        patient_id=patient.id,
        recommendation_id=recommendation.id,
        decision_type="approved",
        reason="Dabrafenib approved for BRAF V600E melanoma.",
        confidence="high",
        evidence_summary={"sources": ["TCGA"], "evidence_count": 1},
        alternatives=[],
        contraindications=[],
        status="active",
    )
    db_session.add(cd)
    await db_session.commit()
    await db_session.refresh(cd)
    return cd


@pytest.fixture
async def consensus(db_session, patient, recommendation, clinical_decision):
    """Create a TumorBoardConsensus record."""
    cons = TumorBoardConsensusModel(
        consensus_id="cons-dt-tp-001",
        patient_id=patient.id,
        recommendation_id=recommendation.id,
        clinical_decision_id=clinical_decision.id,
        consensus_status="unanimous",
        consensus_score=1.0,
        final_recommendation="Dabrafenib 150mg BID",
        supporting_rationale="All specialists agree on BRAF V600E targeted therapy.",
        participating_specialties=["medical_oncology", "surgical_oncology", "pathology"],
    )
    db_session.add(cons)
    await db_session.flush()

    # Add opinions
    opinions = [
        TumorBoardOpinionModel(
            consensus_id=cons.id,
            specialty="medical_oncology",
            position="support",
            confidence=0.95,
        ),
        TumorBoardOpinionModel(
            consensus_id=cons.id,
            specialty="surgical_oncology",
            position="support",
            confidence=0.90,
        ),
        TumorBoardOpinionModel(
            consensus_id=cons.id,
            specialty="pathology",
            position="support",
            confidence=0.85,
        ),
    ]
    db_session.add_all(opinions)
    await db_session.commit()
    await db_session.refresh(cons)
    return cons


# ═══════════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTreatmentPlanDigitalThread:
    """完整 Digital Thread 測試: Patient → Rec → CD → Consensus → Plan → Phase → Item."""

    async def _create_treatment_plan(
        self,
        db_session: AsyncSession,
        patient: PatientModel,
        recommendation: RecommendationModel,
        clinical_decision: ClinicalDecisionModel,
        consensus: TumorBoardConsensusModel,
    ) -> TreatmentPlanModel:
        """建立一個完整的 Treatment Plan 並返回。"""
        now = datetime.now(timezone.utc)

        # ── Treatment Plan ─────────────────────────────────────────────────
        plan = TreatmentPlanModel(
            plan_id="plan-dt-tp-001",
            version=1,
            patient_id=patient.id,
            recommendation_id=recommendation.id,
            clinical_decision_id=clinical_decision.id,
            consensus_id=consensus.id,
            plan_status="draft",
            plan_intent="curative",
            treatment_goals=["tumor_resection", "prevent_recurrence"],
            summary="Digital thread treatment plan",
            clinical_rationale="BRAF V600E targeted therapy",
            is_current=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(plan)
        await db_session.flush()

        # ── Phases ─────────────────────────────────────────────────────────
        phases = [
            TreatmentPhaseModel(
                phase_id="phase-dt-tp-001",
                plan_id=plan.id,
                phase_order=1,
                phase_type="preparation",
                name="Preparation Phase",
                description="Pre-treatment preparation and evaluation",
                duration_days=14,
                status="planned",
                created_at=now,
                updated_at=now,
            ),
            TreatmentPhaseModel(
                phase_id="phase-dt-tp-002",
                plan_id=plan.id,
                phase_order=2,
                phase_type="primary_treatment",
                name="Primary Treatment Phase",
                description="Main targeted therapy phase",
                duration_days=90,
                status="planned",
                created_at=now,
                updated_at=now,
            ),
        ]
        db_session.add_all(phases)
        await db_session.flush()

        # ── Items ──────────────────────────────────────────────────────────
        items = [
            TreatmentItemModel(
                item_id="item-dt-tp-001",
                plan_id=plan.id,
                phase_id=phases[0].id,
                item_order=1,
                item_type="medication",
                name="Dabrafenib",
                description="BRAF inhibitor targeted therapy",
                priority=1,
                status="planned",
                rationale="Top-ranked drug for BRAF V600E",
                source_recommendation="recommendation_engine",
                created_at=now,
                updated_at=now,
            ),
            TreatmentItemModel(
                item_id="item-dt-tp-002",
                plan_id=plan.id,
                phase_id=phases[0].id,
                item_order=2,
                item_type="laboratory",
                name="Baseline Blood Work",
                description="Complete blood count and chemistry panel",
                priority=2,
                status="planned",
                rationale="Pre-treatment baseline assessment",
                created_at=now,
                updated_at=now,
            ),
            TreatmentItemModel(
                item_id="item-dt-tp-003",
                plan_id=plan.id,
                phase_id=phases[1].id,
                item_order=3,
                item_type="medication",
                name="Trametinib",
                description="MEK inhibitor combination therapy",
                priority=3,
                status="planned",
                rationale="Combination therapy for enhanced efficacy",
                source_recommendation="clinical_guideline",
                created_at=now,
                updated_at=now,
            ),
        ]
        db_session.add_all(items)
        await db_session.flush()

        # ── Monitoring ────────────────────────────────────────────────────
        monitoring = [
            TreatmentMonitoringModel(
                monitoring_id="mon-dt-tp-001",
                plan_id=plan.id,
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
            TreatmentMonitoringModel(
                monitoring_id="mon-dt-tp-002",
                plan_id=plan.id,
                monitoring_type="imaging",
                name="CT Scan",
                schedule="every_3_months",
                target_range=None,
                warning_threshold=None,
                critical_threshold=None,
                action_if_abnormal="Schedule follow-up with radiology",
                baseline_required=True,
                repeat_interval="90d",
                responsible_specialty="radiology",
                created_at=now,
                updated_at=now,
            ),
        ]
        db_session.add_all(monitoring)
        await db_session.flush()

        # ── Safety Rules ──────────────────────────────────────────────────
        safety_rules = [
            TreatmentSafetyRuleModel(
                rule_id="rule-dt-tp-001",
                plan_id=plan.id,
                rule_type="contraindication",
                condition={"type": "pregnancy", "detail": "Exclude if pregnant"},
                severity="high",
                recommended_action="Pregnancy test required before starting treatment",
                requires_review=True,
                created_at=now,
            ),
            TreatmentSafetyRuleModel(
                rule_id="rule-dt-tp-002",
                plan_id=plan.id,
                rule_type="drug_interaction",
                condition={"type": "interaction", "detail": "CYP3A4 inhibitors"},
                severity="medium",
                recommended_action="Monitor for drug interactions",
                requires_review=False,
                created_at=now,
            ),
        ]
        db_session.add_all(safety_rules)
        await db_session.flush()

        # ── Trace ─────────────────────────────────────────────────────────
        trace_id = "trace-dt-tp-001"
        traces = [
            TreatmentPlanTraceModel(
                trace_id=trace_id,
                plan_id=plan.id,
                step_order=0,
                step_type="load_context",
                input_summary={},
                output_summary={"status": "loaded"},
                created_at=now,
            ),
            TreatmentPlanTraceModel(
                trace_id=trace_id,
                plan_id=plan.id,
                step_order=1,
                step_type="validate_links",
                input_summary={"patient_id": str(patient.id)},
                output_summary={"status": "validated", "links": "all_consistent"},
                created_at=now,
            ),
            TreatmentPlanTraceModel(
                trace_id=trace_id,
                plan_id=plan.id,
                step_order=2,
                step_type="generate_phases",
                input_summary={"plan_intent": "curative"},
                output_summary={
                    "phases": ["preparation", "primary_treatment"],
                    "status": "generated",
                },
                created_at=now,
            ),
        ]
        db_session.add_all(traces)

        await db_session.commit()
        await db_session.refresh(plan)
        return plan

    # ── Tests ─────────────────────────────────────────────────────────────

    async def test_full_digital_thread_creation(
        self,
        db_session,
        patient,
        recommendation,
        clinical_decision,
        consensus,
    ):
        """建立完整 Digital Thread 並驗證所有 FK 連結。"""
        plan = await self._create_treatment_plan(
            db_session, patient, recommendation, clinical_decision, consensus,
        )

        # 驗證 Plan 層級 FK
        assert plan.patient_id == patient.id
        assert plan.recommendation_id == recommendation.id
        assert plan.clinical_decision_id == clinical_decision.id
        assert plan.consensus_id == consensus.id
        assert plan.plan_id == "plan-dt-tp-001"
        assert plan.version == 1

        # 驗證 Phase 數量
        result = await db_session.execute(
            select(func.count()).where(
                TreatmentPhaseModel.plan_id == plan.id,
            ),
        )
        phase_count = result.scalar()
        assert phase_count == 2, f"預期 2 個 Phase, 得到 {phase_count}"

        # 驗證 Item 數量
        result = await db_session.execute(
            select(func.count()).where(
                TreatmentItemModel.plan_id == plan.id,
            ),
        )
        item_count = result.scalar()
        assert item_count == 3, f"預期 3 個 Item, 得到 {item_count}"

        # 驗證 Monitoring 數量
        result = await db_session.execute(
            select(func.count()).where(
                TreatmentMonitoringModel.plan_id == plan.id,
            ),
        )
        mon_count = result.scalar()
        assert mon_count == 2, f"預期 2 個 Monitoring, 得到 {mon_count}"

        # 驗證 Safety Rules 數量
        result = await db_session.execute(
            select(func.count()).where(
                TreatmentSafetyRuleModel.plan_id == plan.id,
            ),
        )
        safety_count = result.scalar()
        assert safety_count == 2, f"預期 2 個 Safety Rules, 得到 {safety_count}"

        # 驗證 Trace 數量
        result = await db_session.execute(
            select(func.count()).where(
                TreatmentPlanTraceModel.plan_id == plan.id,
            ),
        )
        trace_count = result.scalar()
        assert trace_count == 3, f"預期 3 個 Trace, 得到 {trace_count}"

    async def test_trace_back_from_plan_to_patient(
        self,
        db_session,
        patient,
        recommendation,
        clinical_decision,
        consensus,
    ):
        """從 Treatment Plan 追溯回 Patient。"""
        plan = await self._create_treatment_plan(
            db_session, patient, recommendation, clinical_decision, consensus,
        )

        # Plan → Consensus
        cons_stmt = select(TumorBoardConsensusModel).where(
            TumorBoardConsensusModel.id == plan.consensus_id,
        )
        cons_result = await db_session.execute(cons_stmt)
        loaded_consensus = cons_result.scalar_one()
        assert loaded_consensus.consensus_id == "cons-dt-tp-001"
        assert loaded_consensus.patient_id == patient.id

        # Consensus → Clinical Decision
        cd_stmt = select(ClinicalDecisionModel).where(
            ClinicalDecisionModel.id == loaded_consensus.clinical_decision_id,
        )
        cd_result = await db_session.execute(cd_stmt)
        loaded_cd = cd_result.scalar_one()
        assert loaded_cd.decision_id == "cd-dt-tp-001"

        # Clinical Decision → Recommendation
        rec_stmt = select(RecommendationModel).where(
            RecommendationModel.id == loaded_cd.recommendation_id,
        )
        rec_result = await db_session.execute(rec_stmt)
        loaded_rec = rec_result.scalar_one()
        assert loaded_rec.recommendation_id == "rec-dt-tp-001"

        # Recommendation → Patient
        pat_stmt = select(PatientModel).where(
            PatientModel.id == loaded_rec.patient_id,
        )
        pat_result = await db_session.execute(pat_stmt)
        loaded_patient = pat_result.scalar_one()
        assert loaded_patient.display_name == "DT-TEST-PATIENT-TP"

        # End-to-end 驗證
        assert plan.patient_id == patient.id

    async def test_trace_forward_from_patient_to_plan(
        self,
        db_session,
        patient,
        recommendation,
        clinical_decision,
        consensus,
    ):
        """從 Patient 正向追溯至 Treatment Plan 的 Phases 和 Items。"""
        await self._create_treatment_plan(
            db_session, patient, recommendation, clinical_decision, consensus,
        )

        # Patient → Recommendations → Clinical Decisions → Consensuses → Plans
        rec_stmt = select(RecommendationModel).where(
            RecommendationModel.patient_id == patient.id,
        )
        rec_result = await db_session.execute(rec_stmt)
        loaded_recs = rec_result.scalars().all()
        assert len(loaded_recs) == 1
        assert loaded_recs[0].recommendation_id == "rec-dt-tp-001"

        # Plans via Consensus
        plan_stmt = (
            select(TreatmentPlanModel)
            .options(
                selectinload(TreatmentPlanModel.phases),
                selectinload(TreatmentPlanModel.items),
            )
            .where(TreatmentPlanModel.patient_id == patient.id)
        )
        plan_result = await db_session.execute(plan_stmt)
        loaded_plans = plan_result.scalars().all()
        assert len(loaded_plans) == 1
        loaded_plan = loaded_plans[0]

        assert loaded_plan.plan_id == "plan-dt-tp-001"
        assert len(loaded_plan.phases) == 2
        assert len(loaded_plan.items) == 3

        # 驗證 Phase 名稱
        phase_names = {p.name for p in loaded_plan.phases}
        assert "Preparation Phase" in phase_names
        assert "Primary Treatment Phase" in phase_names

        # 驗證 Item 名稱
        item_names = {i.name for i in loaded_plan.items}
        assert "Dabrafenib" in item_names
        assert "Trametinib" in item_names
        assert "Baseline Blood Work" in item_names

        # 驗證 Phase-Item 關聯
        prep_phase = loaded_plan.phases[0]
        prep_items = [i for i in loaded_plan.items if i.phase_id == prep_phase.id]
        assert len(prep_items) == 2  # Dabrafenib + Blood Work

    async def test_digital_thread_integrity_after_reload(
        self,
        db_session,
        patient,
        recommendation,
        clinical_decision,
        consensus,
    ):
        """所有關聯資料在重新查詢後仍保持一致。"""
        plan = await self._create_treatment_plan(
            db_session, patient, recommendation, clinical_decision, consensus,
        )

        # 使用 selectinload 一次載入所有關聯
        stmt = (
            select(TreatmentPlanModel)
            .options(
                selectinload(TreatmentPlanModel.phases).selectinload(
                    TreatmentPhaseModel.items,
                ),
                selectinload(TreatmentPlanModel.items),
                selectinload(TreatmentPlanModel.monitoring),
                selectinload(TreatmentPlanModel.safety_rules),
                selectinload(TreatmentPlanModel.traces),
            )
            .where(TreatmentPlanModel.id == plan.id)
        )
        result = await db_session.execute(stmt)
        loaded = result.scalar_one()

        assert loaded.plan_id == "plan-dt-tp-001"

        # Verify consensus link
        cons_stmt = select(TumorBoardConsensusModel).where(
            TumorBoardConsensusModel.id == loaded.consensus_id,
        )
        cons_result = await db_session.execute(cons_stmt)
        cons = cons_result.scalar_one()
        assert cons.consensus_status == "unanimous"

        # Verify opinions exist on consensus
        op_count = await db_session.execute(
            select(func.count()).where(
                TumorBoardOpinionModel.consensus_id == cons.id,
            ),
        )
        assert op_count.scalar() == 3

        # Verify plan sub-items counts
        assert len(loaded.phases) == 2
        assert len(loaded.items) == 3
        assert len(loaded.monitoring) == 2
        assert len(loaded.safety_rules) == 2
        assert len(loaded.traces) == 3

        # Verify all phases reference the plan
        for phase in loaded.phases:
            assert phase.plan_id == plan.id

        # Verify all items reference the plan or a phase
        for item in loaded.items:
            assert item.plan_id == plan.id
            assert item.phase_id is not None

    async def test_multiple_plans_same_consensus(
        self,
        db_session,
        patient,
        recommendation,
        clinical_decision,
        consensus,
    ):
        """同一個 Consensus 可以關聯多個 Plan（版本迭代）。"""
        now = datetime.now(timezone.utc)

        # Plan v1
        plan1 = TreatmentPlanModel(
            plan_id="plan-dt-tp-v1",
            version=1,
            patient_id=patient.id,
            recommendation_id=recommendation.id,
            clinical_decision_id=clinical_decision.id,
            consensus_id=consensus.id,
            plan_status="superseded",
            plan_intent="curative",
            is_current=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(plan1)
        await db_session.flush()

        # Plan v2 (current)
        plan2 = TreatmentPlanModel(
            plan_id="plan-dt-tp-v2",
            version=2,
            patient_id=patient.id,
            recommendation_id=recommendation.id,
            clinical_decision_id=clinical_decision.id,
            consensus_id=consensus.id,
            plan_status="active",
            plan_intent="curative",
            is_current=True,
            previous_plan_id=plan1.plan_id,
            created_at=now,
            updated_at=now,
        )
        db_session.add(plan2)
        await db_session.commit()

        # 驗證兩個 Plan 都指向同一個 Consensus
        plan_stmt = select(TreatmentPlanModel).where(
            TreatmentPlanModel.consensus_id == consensus.id,
        ).order_by(TreatmentPlanModel.version.asc())
        plan_result = await db_session.execute(plan_stmt)
        plans = plan_result.scalars().all()

        assert len(plans) == 2
        assert plans[0].version == 1
        assert plans[1].version == 2
        assert plans[1].previous_plan_id == plans[0].plan_id

    async def test_plan_links_to_consensus_recommendation_and_cd(
        self,
        db_session,
        patient,
        recommendation,
        clinical_decision,
        consensus,
    ):
        """Plan 的 consensus_id / recommendation_id / clinical_decision_id 必須一致。"""
        plan = await self._create_treatment_plan(
            db_session, patient, recommendation, clinical_decision, consensus,
        )

        # Load all related records
        cons = await db_session.get(TumorBoardConsensusModel, consensus.id)
        cd = await db_session.get(ClinicalDecisionModel, clinical_decision.id)
        rec = await db_session.get(RecommendationModel, recommendation.id)
        pat = await db_session.get(PatientModel, patient.id)

        # Verify the FK chain end-to-end
        # Plan → Consensus → Clinical Decision → Recommendation → Patient
        assert cons.patient_id == pat.id
        assert cons.recommendation_id == rec.id
        assert cons.clinical_decision_id == cd.id
        assert cd.recommendation_id == rec.id
        assert cd.patient_id == pat.id
        assert rec.patient_id == pat.id

        # Plan FK 必須與鏈路一致
        assert plan.patient_id == pat.id
        assert plan.recommendation_id == rec.id
        assert plan.clinical_decision_id == cd.id
        assert plan.consensus_id == cons.id

    async def test_monitoring_columns_persisted(
        self,
        db_session,
        patient,
        recommendation,
        clinical_decision,
        consensus,
    ):
        """Digital Thread 情境：驗證 Monitoring 欄位正確寫入。

        逐欄驗證 target_range, warning_threshold, critical_threshold,
        action_if_abnormal, responsible_specialty。
        """
        from sqlalchemy import select

        plan = await self._create_treatment_plan(
            db_session, patient, recommendation, clinical_decision, consensus,
        )

        # 直接查 DB 驗證 Monitoring 欄位
        stmt = select(TreatmentMonitoringModel).where(
            TreatmentMonitoringModel.plan_id == plan.id,
        ).order_by(TreatmentMonitoringModel.monitoring_type)
        result = await db_session.execute(stmt)
        rows = result.scalars().all()

        assert len(rows) == 2

        # Laboratory monitoring
        lab = rows[0] if rows[0].monitoring_type == "laboratory" else rows[1]
        assert lab.target_range == {"WBC": "4.0-10.0", "Hb": "12.0-16.0"}
        assert lab.warning_threshold == {"WBC": "3.0-11.0"}
        assert lab.critical_threshold == {"WBC": "<2.0 or >15.0"}
        assert lab.action_if_abnormal == "Notify attending physician and adjust dose"
        assert lab.responsible_specialty == "hematology"

        # Imaging monitoring
        img = rows[1] if rows[1].monitoring_type == "imaging" else rows[0]
        assert img.target_range is None
        assert img.warning_threshold is None
        assert img.critical_threshold is None
        assert img.action_if_abnormal == "Schedule follow-up with radiology"
        assert img.responsible_specialty == "radiology"

    async def test_trace_correctness(
        self,
        db_session,
        patient,
        recommendation,
        clinical_decision,
        consensus,
    ):
        """Digital Thread 情境：驗證 Trace 正確性。

        驗證：
        1. 所有 trace steps 共用同一個 trace_id
        2. step_order 連續不重複 (0, 1, 2)
        3. Restart（refresh）後 trace 資料完整讀回
        """
        from sqlalchemy import select

        plan = await self._create_treatment_plan(
            db_session, patient, recommendation, clinical_decision, consensus,
        )

        # 直接查 DB 驗證 Trace
        stmt = (
            select(TreatmentPlanTraceModel)
            .where(TreatmentPlanTraceModel.plan_id == plan.id)
            .order_by(TreatmentPlanTraceModel.step_order)
        )
        result = await db_session.execute(stmt)
        traces = result.scalars().all()

        assert len(traces) == 3, f"預期 3 個 traces, 得到 {len(traces)}"

        # 所有 trace steps 共用同一個 trace_id
        trace_ids_found = {t.trace_id for t in traces}
        assert len(trace_ids_found) == 1, \
            f"所有 trace steps 應共用同一個 trace_id: {trace_ids_found}"
        assert list(trace_ids_found)[0] == "trace-dt-tp-001"

        # step_order 連續不重複
        step_orders = [t.step_order for t in traces]
        assert step_orders == [0, 1, 2], \
            f"step_order 應連續不重複: {step_orders}"

        # step_type 正確
        assert traces[0].step_type == "load_context"
        assert traces[1].step_type == "validate_links"
        assert traces[2].step_type == "generate_phases"

        # 再次查詢（模擬 reload）後資料一致
        result2 = await db_session.execute(stmt)
        traces2 = result2.scalars().all()
        assert len(traces2) == 3
        assert [t.step_order for t in traces2] == [0, 1, 2]
        assert {t.trace_id for t in traces2} == {"trace-dt-tp-001"}
