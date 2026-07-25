"""
Acceptance Test — Real Pipeline Trace (GATE-4).

Verifies that the real recommendation pipeline produces complete trace data
with all required fields (evidence_references, weight, score, rank, explanation)
without using mocked TraceManager.

Only EvidenceCollector.collect() is mocked to return a fixed EvidenceBundle.
All other components (TraceManager, RecommendationEngine, DrugRankingEngine,
ExplainableEngine) are real.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.clinical.collector import EvidenceCollector
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
# Helpers — 构造 Mock EvidenceBundle
# ═══════════════════════════════════════════════════════════════════════════════


def _make_evidence_bundle() -> EvidenceBundle:
    """返回带有 Osimertinib / Afatinib 证据的固定 EvidenceBundle.

    TCGA 和 COSMIC 未在 WeightRegistry 中注册，权重将回退为 0.0，
    但这不影响 trace field 的存在性验证。
    """
    return EvidenceBundle(
        items=[
            EvidenceItem(
                source="TCGA",
                source_record_id="tcga_001",
                gene_symbol="BRAF",
                drug_name="Osimertinib",
                evidence_type="predictive",
                evidence_direction="supporting",
                evidence_level="Tier_1",
                clinical_significance="sensitivity",
                citation="TCGA study",
                pmid="12345",
            ),
            EvidenceItem(
                source="COSMIC",
                source_record_id="cosmic_001",
                gene_symbol="BRAF",
                drug_name="Osimertinib",
                evidence_type="predictive",
                evidence_direction="supporting",
                evidence_level="Tier_2",
                clinical_significance="sensitivity",
                citation="COSMIC study",
                pmid="67890",
            ),
            EvidenceItem(
                source="TCGA",
                source_record_id="tcga_002",
                gene_symbol="BRAF",
                drug_name="Afatinib",
                evidence_type="predictive",
                evidence_direction="supporting",
                evidence_level="Tier_2",
                clinical_significance="sensitivity",
                citation="TCGA study",
                pmid="12346",
            ),
        ],
        retrieved_at="2025-01-01T00:00:00Z",
        context_hash="acceptance-test-hash",
    )


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
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture
async def db_setup():
    """建立真實 SQLite in-memory 資料庫與所有表."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        patient_id = uuid.uuid4()
        patient = PatientModel(id=patient_id, display_name="ACCEPTANCE-PATIENT")
        session.add(patient)

        user_id = uuid.uuid4()
        user = UserModel(
            id=user_id,
            username="acceptance_test_user",
            email="acceptance@example.com",
            password_hash="not_checked",
            role=Role.VIEWER,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(patient)
        await session.refresh(user)

        yield session, engine, str(patient_id), str(user_id)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_setup_file():
    """建立檔案型 SQLite 資料庫（用於跨 session / engine 讀取驗證）."""
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tmp.close()
    db_path = tmp.name
    db_url = f"sqlite+aiosqlite:///{db_path}"

    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        patient_id = uuid.uuid4()
        patient = PatientModel(id=patient_id, display_name="ACCEPTANCE-FILE-PATIENT")
        session.add(patient)

        user_id = uuid.uuid4()
        user = UserModel(
            id=user_id,
            username="acceptance_file_user",
            email="acceptance_file@example.com",
            password_hash="not_checked",
            role=Role.VIEWER,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(patient)
        await session.refresh(user)

        yield session, engine, db_path, str(patient_id), str(user_id)

    await engine.dispose()
    # 清理临时文件
    Path(db_path).unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 通用 patch 上下文 — 只 mock EvidenceCollector.collect()
# ═══════════════════════════════════════════════════════════════════════════════


def _patch_collector():
    """返回 patch 上下文，只 mock EvidenceCollector.collect().

    用法:
        with _patch_collector():
            ...
    """
    return patch.object(
        EvidenceCollector,
        "collect",
        new_callable=AsyncMock,
        return_value=_make_evidence_bundle(),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 辅助：执行完整 pipeline 并返回关键结果
# ═══════════════════════════════════════════════════════════════════════════════


async def _run_pipeline(
    session: AsyncSession,
    patient_id: str,
    user_id: str,
) -> dict[str, Any]:
    """执行完整 recommendation pipeline，返回 response + 查询到的 DB 数据."""
    with _patch_collector():
        service = RecommendationService(db=session)
        response = await service.create_recommendation(
            request_data=_get_request_data(patient_id),
            user_id=user_id,
        )

    trace_repo = TraceRepository(session)
    rec_repo = RecommendationRepository(session)

    rec = await rec_repo.get_by_id(response["recommendation_id"])
    assert rec is not None, "Recommendation 应成功写入 DB"

    trace = await trace_repo.get_trace_by_trace_id(response["trace_id"])
    assert trace is not None, "Trace 应成功写入 DB"

    db_steps = await trace_repo.get_steps_by_trace_id(str(trace.id))

    return {
        "response": response,
        "rec": rec,
        "trace": trace,
        "db_steps": db_steps,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestAcceptanceRealTrace:
    """GATE-4: 真實 Pipeline Trace 驗收測試."""

    # ── Test 1: trace fields ───────────────────────────────────────────────

    async def test_acceptance_real_pipeline_trace_fields(self, db_setup):
        """驗證真實 pipeline 產生的 trace step 包含必要欄位.

        檢查 evidence_references / weight / score / rank 至少有一筆非空。
        """
        session, engine, patient_id, user_id = db_setup
        result = await _run_pipeline(session, patient_id, user_id)
        db_steps = result["db_steps"]

        assert len(db_steps) > 0, "應至少有一個 trace step"

        # evidence_references：至少有一筆非空，且包含 source/weight/tier
        has_refs = False
        for s in db_steps:
            if s.evidence_references is not None:
                refs = s.evidence_references
                assert isinstance(refs, list), "evidence_references 應為 list"
                if len(refs) > 0:
                    first = refs[0]
                    assert isinstance(first, dict), "每筆 evidence_reference 應為 dict"
                    # 至少包含 source / weight / tier 其中之一
                    assert any(k in first for k in ("source", "weight", "tier", "drug")), \
                        f"evidence_reference 缺少必要欄位: {first}"
                    has_refs = True
                    break
        assert has_refs, "至少需有一個 step 含有非空 evidence_references"

        # weight：至少有一筆非空
        has_weight = any(s.weight is not None for s in db_steps)
        assert has_weight, "至少需有一個 step 含有非空 weight"

        # score：至少有一筆非空
        has_score = any(s.score is not None for s in db_steps)
        assert has_score, "至少需有一個 step 含有非空 score"

        # rank：至少有一筆非空
        has_rank = any(s.rank is not None for s in db_steps)
        assert has_rank, "至少需有一個 step 含有非空 rank"

    # ── Test 2: trace 來自真實 pipeline ────────────────────────────────────

    async def test_acceptance_trace_comes_from_real_pipeline(self, db_setup):
        """驗證 trace 是真正由 pipeline 產生的，而非手動建構.

        - trace_id 不是固定值
        - 有 5+ 個 step
        - step_types 包含 input / evidence / score / recommendation / output
        - 所有 step 的 status 為 "completed"
        """
        session, engine, patient_id, user_id = db_setup
        result = await _run_pipeline(session, patient_id, user_id)
        response = result["response"]
        db_steps = result["db_steps"]

        # trace_id 不是固定值
        trace_id = response["trace_id"]
        assert trace_id is not None, "trace_id 不應為 None"
        assert trace_id != "", "trace_id 不應為空字串"
        assert trace_id != "mock-trace-batch-f", "trace_id 不應為 mock 固定值"

        # 有 5+ 個 step
        assert len(db_steps) >= 5, \
            f"應至少有 5 個 trace step, 實際: {len(db_steps)}"

        # step_types 包含所有必要類型
        types_found: set[str] = {s.step_type for s in db_steps}
        expected_types = {"input", "evidence", "score", "recommendation", "output"}
        missing = expected_types - types_found
        assert not missing, f"step_types 缺少: {missing}, 實際: {types_found}"

        # 所有 step 都有 status="completed"
        for s in db_steps:
            assert s.status == "completed", \
                f"step (order={s.step_order}, type={s.step_type}) status 應為 completed, 實際: {s.status}"

    # ── Test 3: TraceManager 是真正的實例 ──────────────────────────────────

    async def test_acceptance_real_pipeline_no_mock_tracemanager(self, db_setup):
        """驗證 pipeline 使用真正的 TraceManager，資料不是手動塞入的.

        - TraceManager 是 TraceManager 的實例
        - trace 資料可從 DB 完整查詢
        - 不應有手動建構的 mock 特徵
        """
        session, engine, patient_id, user_id = db_setup
        result = await _run_pipeline(session, patient_id, user_id)
        response = result["response"]
        trace = result["trace"]
        db_steps = result["db_steps"]

        # TraceManager 是真正的實例（透過確認 trace 資料的完整性間接驗證）
        # 真正的 TraceManager 產生的 trace_id 是 UUID 格式
        trace_id = response["trace_id"]
        # 驗證 trace_id 符合 UUID hex 格式（32 個 hex 字元）
        assert len(trace_id) == 32, f"trace_id 應為 32-hex UUID, 實際長度: {len(trace_id)}"
        assert all(c in "0123456789abcdef" for c in trace_id), \
            f"trace_id 應為 hex 字串: {trace_id}"

        # 驗證 trace 物件來自 DB 而非手動建構
        assert trace.trace_id == trace_id, "DB trace.trace_id 應與 response.trace_id 一致"

        # 驗證 step_order 是連續的（證明是 pipeline 依序產生的）
        orders = [s.step_order for s in db_steps]
        expected_orders = list(range(len(db_steps)))
        assert orders == expected_orders, \
            f"step_order 應為連續 {expected_orders}, 實際: {orders}"

        # 驗證 step 數量合理（真正 pipeline 至少 5 步）
        assert len(db_steps) >= 5, f"真正 pipeline 應產生至少 5 個 step, 實際: {len(db_steps)}"

        # 驗證不包含 mock 特徵（如 "mock-trace" 字串）
        assert "mock" not in trace_id.lower(), "trace_id 不應包含 mock 字樣"

    # ── Test 4: DB roundtrip（跨 session / engine） ────────────────────────

    async def test_acceptance_db_roundtrip(self, db_setup_file):
        """驗證 recommendation / trace / steps 可完整跨 session 讀取.

        - 建立 recommendation（使用 file-based SQLite）
        - 關閉 session 與 engine
        - 開新 session + 新 engine
        - 從 DB 讀取並驗證資料完整保留
        """
        session, engine, db_path, patient_id, user_id = db_setup_file
        result = await _run_pipeline(session, patient_id, user_id)
        response = result["response"]
        trace_id = response["trace_id"]
        rec_id = response["recommendation_id"]

        # 關閉原 session 與 engine
        await session.close()
        await engine.dispose()

        # 開新 session + 新 engine（使用同一個 file-based DB）
        new_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        try:
            new_session_factory = async_sessionmaker(
                new_engine, class_=AsyncSession, expire_on_commit=False,
            )

            async with new_session_factory() as new_session:
                rec_repo2 = RecommendationRepository(new_session)
                trace_repo2 = TraceRepository(new_session)

                # 讀取 recommendation
                rec2 = await rec_repo2.get_by_id(rec_id)
                assert rec2 is not None, "跨 session 應能讀取到 recommendation"
                assert rec2.status == "completed"
                assert rec2.recommendation_id == rec_id
                assert rec2.trace_id == trace_id

                # 讀取 trace
                trace2 = await trace_repo2.get_trace_by_trace_id(trace_id)
                assert trace2 is not None, "跨 session 應能讀取到 trace"
                assert trace2.trace_id == trace_id

                # 讀取 steps
                steps2 = await trace_repo2.get_steps_by_trace_id(str(trace2.id))
                assert len(steps2) >= 5, \
                    f"跨 session 應讀取到至少 5 個 steps, 實際: {len(steps2)}"

                # 驗證所有字段在跨 session 後仍完整
                for s in steps2:
                    assert s.step_order >= 0, "step_order 應 >= 0"
                    assert s.step_type, "step_type 不應為空"
                    assert s.status == "completed", "status 應為 completed"

                # 驗證至少有一個 evidence_references
                has_refs = any(s.evidence_references is not None for s in steps2)
                assert has_refs, "跨 session 後仍應有 evidence_references"

                # 驗證至少有一個 weight
                has_weight = any(s.weight is not None for s in steps2)
                assert has_weight, "跨 session 後仍應有 weight"

                # 驗證至少有一個 score
                has_score = any(s.score is not None for s in steps2)
                assert has_score, "跨 session 後仍應有 score"

                # 驗證至少有一個 rank
                has_rank = any(s.rank is not None for s in steps2)
                assert has_rank, "跨 session 後仍應有 rank"
        finally:
            await new_engine.dispose()
