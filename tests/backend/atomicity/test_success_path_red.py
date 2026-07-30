"""
T-05: Service 成功路徑測試 — 驗證 TreatmentPlanService 交易邊界

情境：
1. 使用 TreatmentPlanService.create_plan() 建立一筆完整資料（含子資料 + Outbox）
2. 驗證 Service commit 後所有資料存在
3. Outbox 存在

預期：綠燈（PASS）
- TreatmentPlanService 正確管理交易邊界
- flush-only Repository 由 Service commit
- Transactional Outbox 模式正確運作
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base
from src.backend.repositories.clinical_graph_outbox_repo import (
    ClinicalGraphOutboxRepository,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
async def db_session():
    """Create a database session for testing. Supports Postgres via DATABASE_URL env var."""
    url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite://")

    from src.backend.domain.clinical_decision import ClinicalDecisionModel  # noqa: F401
    from src.backend.domain.clinical_graph_outbox import (  # noqa: F401
        ClinicalGraphOutboxModel,
    )
    from src.backend.domain.patient import PatientModel  # noqa: F401
    from src.backend.domain.recommendation import (  # noqa: F401
        RecommendationModel,
        RecommendationTraceModel,
        RecommendationTraceStepModel,
    )
    from src.backend.domain.treatment_plan import (  # noqa: F401
        TreatmentItemModel,
        TreatmentMonitoringModel,
        TreatmentPhaseModel,
        TreatmentPlanModel,
        TreatmentPlanTraceModel,
        TreatmentSafetyRuleModel,
    )
    from src.backend.domain.tumor_board import (  # noqa: F401
        TumorBoardConsensusModel,
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
async def upstream_data(db_session):
    """建立 Service 需要的上游資料（User, Patient, Recommendation, ClinicalDecision, Consensus）。

    直接在 db_session 中建立資料並 flush，確保與 Service 使用同一個 session。
    注意：不 commit，讓 Service 決定交易邊界。
    """
    from src.backend.domain.clinical_decision import ClinicalDecisionModel
    from src.backend.domain.enums import (
        ConfidenceLevelEnum,
        ConsentStatusEnum,
        DecisionStatusEnum,
        DecisionTypeEnum,
        RecommendationStatusEnum,
        SexEnum,
    )
    from src.backend.domain.patient import PatientModel
    from src.backend.domain.recommendation import RecommendationModel
    from src.backend.domain.tumor_board import TumorBoardConsensusModel
    from src.backend.domain.user import UserModel

    data = {}

    # ── User (must exist in domain_users for created_by FK) ──
    user = UserModel(
        username=f"t05-user-{uuid.uuid4().hex}",
        password_hash="test-hash",
    )
    db_session.add(user)
    await db_session.flush()
    data["user"] = user
    data["user_id"] = user.id

    # ── Patient ──
    patient = PatientModel(
        display_name="T05-PATIENT",
        sex=SexEnum.UNKNOWN,
        consent_status=ConsentStatusEnum.GRANTED,
    )
    db_session.add(patient)
    await db_session.flush()
    data["patient"] = patient
    data["patient_id"] = patient.id

    # ── Recommendation ──
    rec = RecommendationModel(
        patient_id=patient.id,
        recommendation_id=f"rec-{uuid.uuid4().hex}",
        status=RecommendationStatusEnum.COMPLETED,
        result_payload={
            "recommendations": [
                {"drug_name": "Lenvatinib", "rank": 1, "overall_score": 0.95},
            ],
        },
    )
    db_session.add(rec)
    await db_session.flush()
    data["recommendation"] = rec
    data["recommendation_id"] = rec.recommendation_id

    # ── Clinical Decision ──
    cd = ClinicalDecisionModel(
        patient_id=patient.id,
        recommendation_id=rec.id,
        decision_id=f"cd-{uuid.uuid4().hex}",
        decision_type=DecisionTypeEnum.APPROVED,
        reason="Test reason",
        confidence=ConfidenceLevelEnum.HIGH,
        status=DecisionStatusEnum.ACTIVE,
        evidence_summary={"drug": "Lenvatinib", "level": "Level_1"},
        alternatives=[],
        contraindications=[],
    )
    db_session.add(cd)
    await db_session.flush()
    data["clinical_decision"] = cd
    data["clinical_decision_id"] = cd.decision_id

    # ── Tumor Board Consensus ──
    cons = TumorBoardConsensusModel(
        patient_id=patient.id,
        recommendation_id=rec.id,
        clinical_decision_id=cd.id,
        consensus_id=f"cons-{uuid.uuid4().hex}",
        consensus_status="unanimous",
        consensus_score=1.0,
        supporting_rationale="All specialists agree",
        final_recommendation="Lenvatinib",
        dissenting_opinions=[],
        participating_specialties=["medical_oncology"],
    )
    db_session.add(cons)
    await db_session.flush()
    data["consensus"] = cons
    data["consensus_id"] = cons.consensus_id

    return data


@pytest.fixture
def sample_request(upstream_data):
    """Create a valid CreatePlanRequest."""
    from src.backend.services.treatment_plan_service import CreatePlanRequest

    return CreatePlanRequest(
        patient_id=str(upstream_data["patient_id"]),
        recommendation_id=upstream_data["recommendation_id"],
        clinical_decision_id=upstream_data["clinical_decision_id"],
        consensus_id=upstream_data["consensus_id"],
        plan_intent="curative",
        treatment_goals=["tumor_resection", "prevent_recurrence"],
        clinical_context={"cancer_type": "PTC"},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════════




class TestTreatmentPlanServiceSuccessPath:
    """TreatmentPlanService 成功路徑測試。

    此測試驗證 Service 正確管理交易邊界：
    - Repository 使用 flush-only
    - Service 在建立完整資料後 commit
    - Transactional Outbox 模式正確運作
    """

    async def test_service_create_plan_success_path(
        self,
        db_session,
        upstream_data,
        sample_request,
    ) -> None:
        """GREEN LIGHT: Service 成功建立完整治療計劃。

        情境：
        1. 使用 TreatmentPlanService.create_plan() 建立計劃
        2. 驗證 Service 回傳完整的 TreatmentPlanResponse
        3. 驗證資料庫中存在 TreatmentPlan + Phases + Items + Trace + Outbox
        """
        from sqlalchemy import select

        from src.backend.clinical.treatment_plan_engine import (
            TreatmentPlanEngine,
        )
        from src.backend.clinical.treatment_plan_rules import (
            TreatmentPlanRuleSet,
        )
        from src.backend.domain.user import UserModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentItemRepository,
            TreatmentMonitoringRepository,
            TreatmentPhaseRepository,
            TreatmentPlanRepository,
            TreatmentPlanTraceRepository,
            TreatmentSafetyRuleRepository,
        )
        from src.backend.services.treatment_plan_service import (
            TreatmentPlanResponse,
            TreatmentPlanService,
        )

        # ---- Arrange ----
        rule_set = TreatmentPlanRuleSet()
        engine = TreatmentPlanEngine(rule_set=rule_set)

        service = TreatmentPlanService(
            db=db_session,
            engine=engine,
            plan_repo=TreatmentPlanRepository(db_session),
            phase_repo=TreatmentPhaseRepository(db_session),
            item_repo=TreatmentItemRepository(db_session),
            monitoring_repo=TreatmentMonitoringRepository(db_session),
            safety_repo=TreatmentSafetyRuleRepository(db_session),
            trace_repo=TreatmentPlanTraceRepository(db_session),
            outbox_repo=ClinicalGraphOutboxRepository(db_session),
        )

        user_id = str(upstream_data["user_id"])

        # ---- Act ----
        response: TreatmentPlanResponse = await service.create_plan(
            request=sample_request,
            user_id=user_id,
        )

        # ---- Assert ----
        # 1. Response 結構驗證
        assert isinstance(response, TreatmentPlanResponse), (
            "Response should be a TreatmentPlanResponse instance"
        )
        assert response.plan_id is not None, "plan_id should be set"
        assert response.version == 1, "First version should be 1"
        assert response.plan_status == "draft", "Default status should be draft"
        assert response.patient_id == str(upstream_data["patient_id"])
        assert response.is_current is True
        assert response.created_by == user_id

        # 2. 子資料存在
        assert len(response.phases) > 0, "Should have phases from engine output"
        assert len(response.items) > 0, "Should have items from engine output"

        # 3. 資料庫驗證：TreatmentPlan 存在
        plan_repo = TreatmentPlanRepository(db_session)
        plan_model = await plan_repo.get_current_by_plan_id(response.plan_id)
        assert plan_model is not None, (
            "✅ GREEN LIGHT: TreatmentPlan exists in database after "
            "service.create_plan() commits."
        )
        assert str(plan_model.created_by) == user_id, (
            "created_by should match the user_id passed to service"
        )

        # 3b. 驗證對應 User row 存在（PostgreSQL FK 相容性）
        user_stmt = select(UserModel).where(UserModel.id == plan_model.created_by)
        user_result = await db_session.execute(user_stmt)
        user_row = user_result.scalar_one_or_none()
        assert user_row is not None, (
            "✅ GREEN LIGHT: Corresponding domain_users row exists for created_by FK."
        )

        # 4. 資料庫驗證：Phase 存在
        phase_repo = TreatmentPhaseRepository(db_session)
        phases = await phase_repo.list_by_plan_id(plan_model.id)
        assert len(phases) > 0, "Phases should be persisted"

        # 5. 資料庫驗證：Item 存在
        item_repo = TreatmentItemRepository(db_session)
        items = await item_repo.list_by_plan_id(plan_model.id)
        assert len(items) > 0, "Items should be persisted"

        # 6. 資料庫驗證：Trace 存在
        trace_repo = TreatmentPlanTraceRepository(db_session)
        traces = await trace_repo.list_by_plan_id(plan_model.id)
        assert len(traces) > 0, "Traces should be persisted"

        # 7. 資料庫驗證：Outbox 存在
        # 使用 aggregate_id 查詢（因為 event_id 由 repo 自動產生）
        from src.backend.domain.clinical_graph_outbox import (
            ClinicalGraphOutboxModel,
        )
        stmt = select(ClinicalGraphOutboxModel).where(
            ClinicalGraphOutboxModel.aggregate_id == response.plan_id,
        )
        result = await db_session.execute(stmt)
        outboxes = list(result.scalars().all())
        assert len(outboxes) > 0, (
            "✅ GREEN LIGHT: Outbox record exists after "
            "service.create_plan(). The transactional outbox pattern works."
        )
        outbox = outboxes[0]

        assert outbox.status == "pending", "Outbox should start as pending"
        assert outbox.aggregate_id == response.plan_id
        assert outbox.event_type == "treatment_plan.created"

        # 8. 驗證 datetime 為 UTC-naive（PostgreSQL TIMESTAMP WITHOUT TIME ZONE 相容）
        assert plan_model.created_at.tzinfo is None, (
            "created_at must be UTC-naive for PostgreSQL compatibility"
        )
        assert plan_model.updated_at.tzinfo is None, (
            "updated_at must be UTC-naive for PostgreSQL compatibility"
        )
        for phase in phases:
            assert phase.created_at.tzinfo is None
            assert phase.updated_at.tzinfo is None
        for item in items:
            assert item.created_at.tzinfo is None
            assert item.updated_at.tzinfo is None
