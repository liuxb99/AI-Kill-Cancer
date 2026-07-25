"""
Batch F — Trace Persistence Tests (P0-3 验证).

验证正式 Recommendation Service 产生的 Trace Step 含有以下字段且非空：
- evidence_references
- weight
- score
- rank
- explanation（可从 output_summary 还原）

使用真实 SQLite in-memory 数据库 + 完整 Service 链路。
不手动创建 Model 对象，所有数据通过 Service 产生。
只 mock EvidenceCollector.collect() 以返回固定 EvidenceBundle。
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.clinical.evidence_models import EvidenceBundle, EvidenceItem
from src.backend.database.models import Base
from src.backend.domain.enums import Role
from src.backend.domain.patient import PatientModel
from src.backend.domain.user import UserModel
from src.backend.repositories.recommendation_repo import (
    RecommendationRepository,
    TraceRepository,
)
from src.backend.services.recommendation_service import RecommendationService

# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture
async def db_setup():
    """建立真实 SQLite 内存数据库与所有表."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # 创建必要的 Patient 和 User 记录（外键约束）
        patient_id = uuid.uuid4()
        patient = PatientModel(id=patient_id, display_name="BATCH-F-PATIENT")
        session.add(patient)

        user_id = uuid.uuid4()
        user = UserModel(
            id=user_id,
            username="batch_f_test_user",
            email="test@example.com",
            password_hash="not_checked",
            role=Role.VIEWER,
        )
        session.add(user)
        await session.commit()
        await session.refresh(patient)
        await session.refresh(user)

        yield session, engine, str(patient_id), str(user_id)

    await engine.dispose()


@pytest.fixture
def mock_evidence_collector():
    """
    只 mock EvidenceCollector.collect()，使其回傳固定 EvidenceBundle。
    其餘 Pipeline 元件（TraceManager、RecommendationEngine、DrugRankingEngine、
    ExplainableEngine、ReportGenerator）皆為真實實例。
    """
    items = [
        EvidenceItem(
            drug_name="Osimertinib",
            source="TCGA",
            evidence_level="Tier_1",
            evidence_direction="supporting",
            clinical_significance="sensitive",
            source_record_id="tcga-001",
        ),
        EvidenceItem(
            drug_name="Osimertinib",
            source="COSMIC",
            evidence_level="Tier_2",
            evidence_direction="supporting",
            clinical_significance="sensitive",
            source_record_id="cosmic-001",
        ),
        EvidenceItem(
            drug_name="Afatinib",
            source="TCGA",
            evidence_level="Tier_2",
            evidence_direction="supporting",
            clinical_significance="sensitive",
            source_record_id="tcga-002",
        ),
    ]
    bundle = EvidenceBundle(items=items)

    with patch(
        "src.backend.services.recommendation_service.EvidenceCollector.collect",
        new_callable=AsyncMock,
        return_value=bundle,
    ):
        yield


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _get_request_data(patient_id: str) -> dict[str, Any]:
    """构造传给 create_recommendation 的 request_data."""
    return {
        "patient_id": patient_id,
        "variants": ["BRAF V600E"],
        "patient_context": {
            "age": 58,
            "cancer_type": "Melanoma",
            "gender": "M",
            "diagnosis": "Melanoma",
            "stage": "IV",
            "histology": "NOS",
        },
        "top_n": 3,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestRealPipelineTracePersistence:
    """
    使用真实 Pipeline（仅 mock EvidenceCollector）驗證 Trace Step 的 persistence。
    """

    # ── Test 1: evidence_references ───────────────────────────────────────────

    async def test_real_pipeline_trace_evidence_references(
        self,
        db_setup: tuple[AsyncSession, Any, str, str],
        mock_evidence_collector: None,
    ) -> None:
        """驗證真實 Pipeline 產生的 trace step 含有 evidence_references 且非空."""
        session, engine, patient_id, user_id = db_setup

        service = RecommendationService(db=session)
        response = await service.create_recommendation(
            request_data=_get_request_data(patient_id),
            user_id=user_id,
        )

        trace_repo = TraceRepository(session)
        trace = await trace_repo.get_trace_by_trace_id(response["trace_id"])
        assert trace is not None, "Trace 應已持久化"

        db_steps = await trace_repo.get_steps_by_trace_id(str(trace.id))

        # 验证至少有一个 step 的 evidence_references 非空
        steps_with_refs = [s for s in db_steps if s.evidence_references is not None]
        assert len(steps_with_refs) > 0, "至少需有一个 step 的 evidence_references 非空"

        # 验证 reference 包含 source/weight/tier 等資訊
        refs = steps_with_refs[0].evidence_references
        assert isinstance(refs, list), "evidence_references 须为 list"
        first_ref = refs[0]
        assert isinstance(first_ref, dict), "每个 reference 须为 dict"
        # 检查关键字段
        assert "source" in first_ref, f"reference 应包含 source: {first_ref}"
        assert "weight" in first_ref or "tier" in first_ref, \
            f"reference 应包含 weight 或 tier: {first_ref}"

    # ── Test 2: weight / score / rank ─────────────────────────────────────────

    async def test_real_pipeline_trace_weight_score_rank(
        self,
        db_setup: tuple[AsyncSession, Any, str, str],
        mock_evidence_collector: None,
    ) -> None:
        """驗證至少有一個 step 包含 weight / score / rank 欄位且非空."""
        session, engine, patient_id, user_id = db_setup

        service = RecommendationService(db=session)
        response = await service.create_recommendation(
            request_data=_get_request_data(patient_id),
            user_id=user_id,
        )

        trace_repo = TraceRepository(session)
        trace = await trace_repo.get_trace_by_trace_id(response["trace_id"])
        db_steps = await trace_repo.get_steps_by_trace_id(str(trace.id))

        has_weight = any(s.weight is not None for s in db_steps)
        has_score = any(s.score is not None for s in db_steps)
        has_rank = any(s.rank is not None for s in db_steps)

        assert has_weight, "至少需有一个 step 的 weight 非空"
        assert has_score, "至少需有一个 step 的 score 非空"
        assert has_rank, "至少需有一个 step 的 rank 非空"

    # ── Test 3: explanation ──────────────────────────────────────────────────

    async def test_real_pipeline_trace_explanation(
        self,
        db_setup: tuple[AsyncSession, Any, str, str],
        mock_evidence_collector: None,
    ) -> None:
        """
        驗證 Pipeline 產生的 response 包含 explanation 資訊，
        且 trace steps 中有對應的 evidence 數據可還原解釋。
        """
        session, engine, patient_id, user_id = db_setup

        service = RecommendationService(db=session)
        response = await service.create_recommendation(
            request_data=_get_request_data(patient_id),
            user_id=user_id,
        )

        # 1) response 中的 recommendations 應包含 explanations
        recommendations = response.get("recommendations", [])
        assert len(recommendations) > 0, "response 應包含至少一個 recommendation"

        all_explanations = []
        for rec in recommendations:
            expl = rec.get("explanations", [])
            all_explanations.extend(expl)

        assert len(all_explanations) > 0, \
            "recommendations 應包含 explanations"

        # 驗證 explanation 結構
        first_expl = all_explanations[0]
        assert isinstance(first_expl, dict), "每個 explanation 須為 dict"
        assert "category" in first_expl or "detail" in first_expl, \
            f"explanation 應包含 category/detail: {first_expl}"

        # 2) trace steps 中應有 evidence_references 或 ranking 等可還原解釋的數據
        trace_repo = TraceRepository(session)
        trace = await trace_repo.get_trace_by_trace_id(response["trace_id"])
        db_steps = await trace_repo.get_steps_by_trace_id(str(trace.id))

        has_explanation_data = any(
            s.output_summary is not None
            and (
                "evidence_references" in s.output_summary
                or "ranking" in s.output_summary
            )
            for s in db_steps
        )
        assert has_explanation_data, \
            "trace steps 中應包含 evidence_references 或 ranking 等可還原解釋的數據"

    # ── Test 4: step types ───────────────────────────────────────────────────

    async def test_real_pipeline_trace_step_types(
        self,
        db_setup: tuple[AsyncSession, Any, str, str],
        mock_evidence_collector: None,
    ) -> None:
        """驗證 step types 包含 input / evidence / score / recommendation / output."""
        session, engine, patient_id, user_id = db_setup

        service = RecommendationService(db=session)
        response = await service.create_recommendation(
            request_data=_get_request_data(patient_id),
            user_id=user_id,
        )

        trace_repo = TraceRepository(session)
        trace = await trace_repo.get_trace_by_trace_id(response["trace_id"])
        db_steps = await trace_repo.get_steps_by_trace_id(str(trace.id))

        # 驗證至少存在 input、evidence、score、recommendation、output 等 step types
        types_found: set[str] = {s.step_type for s in db_steps}
        expected_types = {"input", "evidence", "score", "recommendation", "output"}
        assert types_found.issuperset(expected_types), \
            f"step types 應包含 {expected_types}, 實際: {types_found}"

        # 驗證 step_order 是連續且從 0 開始
        orders = [s.step_order for s in db_steps]
        expected_orders = list(range(len(db_steps)))
        assert orders == expected_orders, \
            f"step_order 應為 {expected_orders}, 實際: {orders}"

        # 每個 step 應有非空的 status
        for s in db_steps:
            assert s.status == "completed", \
                f"status 應為 completed (order={s.step_order})"

    # ── Test 5: 完整 chain DB roundtrip ──────────────────────────────────────

    async def test_real_pipeline_full_chain_db_roundtrip(
        self,
        db_setup: tuple[AsyncSession, Any, str, str],
        mock_evidence_collector: None,
    ) -> None:
        """
        完整 chain: Service → Pipeline → DB → 關閉 session → 開新 session → 讀取驗證。
        驗證跨 session 讀取時資料一致。
        """
        session, engine, patient_id, user_id = db_setup

        service = RecommendationService(db=session)
        response = await service.create_recommendation(
            request_data=_get_request_data(patient_id),
            user_id=user_id,
        )

        rec_id = response["recommendation_id"]
        trace_id_val = response["trace_id"]

        # 關閉當前 session
        await session.close()

        # 使用同一個 engine 的新 session 讀取
        async with async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )() as session2:
            rec_repo2 = RecommendationRepository(session2)
            trace_repo2 = TraceRepository(session2)

            # 驗證 recommendation
            rec2 = await rec_repo2.get_by_id(rec_id)
            assert rec2 is not None, "跨 session 應能讀取到 recommendation"
            assert rec2.status == "completed"
            assert rec2.recommendation_id == rec_id

            # 驗證 trace
            trace2 = await trace_repo2.get_trace_by_trace_id(trace_id_val)
            assert trace2 is not None, "跨 session 應能讀取到 trace"
            assert trace2.trace_id == trace_id_val

            # 驗證 steps
            steps2 = await trace_repo2.get_steps_by_trace_id(str(trace2.id))
            assert len(steps2) > 0, "trace 應包含至少一個 step"

            # 驗證 step 欄位在跨 session 後仍完整
            for s in steps2:
                assert s.step_order >= 0
                assert s.step_type
                assert s.status == "completed"

            # 驗證關鍵欄位
            has_refs = any(s.evidence_references is not None for s in steps2)
            has_weight = any(s.weight is not None for s in steps2)
            has_score = any(s.score is not None for s in steps2)
            has_rank = any(s.rank is not None for s in steps2)

            assert has_refs, "跨 session 後仍應有 evidence_references"
            assert has_weight, "跨 session 後仍應有 weight"
            assert has_score, "跨 session 後仍應有 score"
            assert has_rank, "跨 session 後仍應有 rank"

            # 驗證 step types 跨 session 一致
            types_found: set[str] = {s.step_type for s in steps2}
            expected_types = {"input", "evidence", "score", "recommendation", "output"}
            assert types_found.issuperset(expected_types), \
                f"跨 session 後 step types 應包含 {expected_types}, 實際: {types_found}"

            # 驗證 step_order 連續
            orders = [s.step_order for s in steps2]
            expected_orders = list(range(len(steps2)))
            assert orders == expected_orders, \
                f"跨 session 後 step_order 應為 {expected_orders}, 實際: {orders}"
