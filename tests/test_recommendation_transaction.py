"""
Batch D: Transaction Tests (T1) — Recommendation/Trace/Steps All-or-Nothing.

Tests that a failure at ANY persistence step rolls back ALL changes.
Uses a real aiosqlite in-memory database with SQLAlchemy event listeners
to simulate failures at specific flush/commit points, then verifies
zero residue via fresh session queries.

Cases
-----
1. RecommendationModel add fails (before_flush rejects RecommendationModel)
2. RecommendationTraceModel add fails (before_flush rejects TraceModel)
3. RecommendationTraceStepModel add fails (before_flush rejects StepModel)
4. AsyncSession.commit fails (mock commit raises)
5. Success — full pipeline + GET retrievable
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base
from src.backend.domain.recommendation import (
    RecommendationModel,
    RecommendationTraceModel,
    RecommendationTraceStepModel,
)

# ─── Module-level constants ───────────────────────────────────────────────────

_PATIENT_UUID = "550e8400-e29b-41d4-a716-446655440000"
_USER_UUID = "550e8400-e29b-41d4-a716-446655440000"


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
async def db_engine():
    """In-memory SQLite database engine with all tables created."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Clean AsyncSession (no listener).  Rollback on teardown."""
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def patient_in_db(db_session):
    """Pre-create a Patient record so FK constraints are satisfied."""
    from src.backend.domain.patient import PatientModel

    pid = uuid.UUID(_PATIENT_UUID)
    p = PatientModel(id=pid, display_name="TX-TEST-PATIENT")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest.fixture
async def fresh_count(db_engine):
    """Return a callable that counts rows of a model in a fresh session."""

    async def _count(model_cls: type) -> int:
        factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            result = await s.execute(select(model_cls))
            return len(result.scalars().all())

    return _count


# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_pipeline_result(drug_names: list[str] | None = None) -> dict[str, Any]:
    """Build a synthetic pipeline result resembling RecommendationEngine.run()."""
    drugs = drug_names or ["Osimertinib", "Afatinib"]
    aggregated: dict[str, dict] = {}
    for i, name in enumerate(drugs):
        key = name.lower()
        aggregated[key] = {"total_weight": 1.0 - i * 0.1, "item_count": 3}
    return {
        "drugs_ranked": [],
        "aggregated": aggregated,
        "evidence_count": 12,
        "rules_evaluated": 5,
        "rules_fired": 3,
        "rule_results": [],
        "pipeline_status": "success",
    }


def _make_rank_result(name: str, rank: int):
    """Build a lightweight rank-result object."""
    return type(
        "RankResult",
        (),
        {
            "drug_name": name,
            "rank": rank + 1,
            "overall_score": type("Score", (), {"raw_score": 0.95 - rank * 0.1})(),
            "evidence_score": type("Score", (), {"confidence_score": 0.9 - rank * 0.1})(),
            "sensitivity": type("Score", (), {"score": 0.85 - rank * 0.1})(),
            "resistance": type("Score", (), {"score": 0.1 + rank * 0.05})(),
            "conflict_score": type("Score", (), {"score": 0.05 + rank * 0.02})(),
        },
    )


def _add_reject_listener(session: AsyncSession, model_class: type, msg: str):
    """Attach a before_flush listener that rejects inserts of *model_class*.

    Returns the listener function so it can be removed via ``event.remove``.
    """
    sync_session = session.sync_session

    def _reject(s, ctx, instances):
        for obj in s.new:
            if isinstance(obj, model_class):
                raise ValueError(msg)

    event.listen(sync_session, "before_flush", _reject)
    return _reject


# ═══════════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestRecommendationTransaction:
    """All-or-nothing transaction guarantees for recommendation persistence."""

    # ── Service factory helper ─────────────────────────────────────────────

    async def _call_service(
        self,
        db_session,
        *,
        fail_on: str | None = None,
        patient_id: str = _PATIENT_UUID,
    ) -> dict:
        """Run ``create_recommendation`` with mocked pipeline components.

        Parameters
        ----------
        fail_on : str | None
            ``"recommendation"`` | ``"trace"`` | ``"step"`` | ``"commit"`` | ``None``
        """
        from src.backend.services.recommendation_service import RecommendationService

        # Build mocks in scope so they apply
        with patch(
            "src.backend.services.recommendation_service.RecommendationEngine",
            autospec=True,
        ) as eng_cls:
            eng_inst = MagicMock()
            eng_inst.run = AsyncMock(return_value=_make_pipeline_result())
            eng_cls.return_value = eng_inst

            with patch(
                "src.backend.services.recommendation_service.DrugRankingEngine",
                autospec=True,
            ) as rank_cls:
                rank_inst = MagicMock()
                rank_inst.rank.return_value = [
                    _make_rank_result(n, i)
                    for i, n in enumerate(["Osimertinib", "Afatinib"])
                ]
                rank_cls.return_value = rank_inst

                with patch(
                    "src.backend.services.recommendation_service.ExplainableEngine",
                    autospec=True,
                ) as expl_cls:
                    expl_inst = MagicMock()
                    expl_inst.generate_explanations.return_value = [
                        type("Explanation", (), {"reasons": []})(),
                        type("Explanation", (), {"reasons": []})(),
                    ]
                    expl_cls.return_value = expl_inst

                    # Build a pre-configured trace
                    from src.backend.clinical.calculation_trace import (
                        CalculationTrace,
                        TraceManager,
                        TraceStep,
                    )

                    trace = CalculationTrace(
                        trace_id="tx-mock-trace-001",
                        patient_id="P-TX",
                        status="running",
                    )
                    trace.steps = [
                        TraceStep(
                            step_name="collect_evidence",
                            step_type="evidence",
                            input_data={"variants": ["EGFR L858R"]},
                        ),
                        TraceStep(
                            step_name="rank_drugs",
                            step_type="recommendation",
                            input_data={"top_n": 5},
                        ),
                    ]

                    with patch(
                        "src.backend.services.recommendation_service.TraceManager",
                        autospec=True,
                    ) as tm_cls:
                        tm_inst = MagicMock(spec=TraceManager)
                        tm_inst.start_trace.return_value = trace
                        tm_inst.get_trace.return_value = trace
                        tm_inst.complete_trace = MagicMock()
                        tm_cls.return_value = tm_inst

                        with patch(
                            "src.backend.services.recommendation_service.ReportGenerator",
                            autospec=True,
                        ) as rg_cls:
                            rg_inst = MagicMock()
                            rg_inst.generate.return_value = "<html>Tx Report</html>"
                            rg_cls.return_value = rg_inst

                            # ── Attach failure listener if requested ──
                            listeners = []
                            if fail_on == "recommendation":
                                fn = _add_reject_listener(
                                    db_session,
                                    RecommendationModel,
                                    "Simulated: RecommendationModel insert failed",
                                )
                                listeners.append(fn)
                            elif fail_on == "trace":
                                fn = _add_reject_listener(
                                    db_session,
                                    RecommendationTraceModel,
                                    "Simulated: TraceModel insert failed",
                                )
                                listeners.append(fn)
                            elif fail_on == "step":
                                fn = _add_reject_listener(
                                    db_session,
                                    RecommendationTraceStepModel,
                                    "Simulated: StepModel insert failed",
                                )
                                listeners.append(fn)
                            elif fail_on == "commit":

                                async def failing_commit():
                                    raise RuntimeError("Simulated: commit failed")

                                db_session.commit = failing_commit

                            # ── Call service ──
                            service = RecommendationService(db_session)
                            try:
                                result = await service.create_recommendation(
                                    request_data={
                                        "patient_id": patient_id,
                                        "variants": ["EGFR L858R"],
                                        "patient_context": {
                                            "age": 65,
                                            "cancer_type": "NSCLC",
                                        },
                                        "top_n": 5,
                                    },
                                    user_id=_USER_UUID,
                                )
                                return result
                            finally:
                                # Cleanup listeners
                                for fn in listeners:
                                    try:
                                        event.remove(
                                            db_session.sync_session,
                                            "before_flush",
                                            fn,
                                        )
                                    except (ValueError, AttributeError):
                                        pass


    # ── Case 1: RecommendationModel insert fails ───────────────────────────

    async def test_recommendation_insert_failure(
        self,
        db_engine,
        db_session,
        patient_in_db,
        fresh_count,
    ):
        """When RecommendationModel insert fails → no residue of any kind."""
        with pytest.raises(RuntimeError, match="Failed to persist recommendation"):
            await self._call_service(
                db_session,
                fail_on="recommendation",
            )

        # Verify no residue in a fresh session
        assert await fresh_count(RecommendationModel) == 0
        assert await fresh_count(RecommendationTraceModel) == 0
        assert await fresh_count(RecommendationTraceStepModel) == 0

    # ── Case 2: TraceModel insert fails ────────────────────────────────────

    async def test_trace_insert_failure(
        self,
        db_engine,
        db_session,
        patient_in_db,
        fresh_count,
    ):
        """When TraceModel insert fails → no residue of any kind."""
        with pytest.raises(RuntimeError, match="Failed to persist recommendation"):
            await self._call_service(
                db_session,
                fail_on="trace",
            )

        assert await fresh_count(RecommendationModel) == 0
        assert await fresh_count(RecommendationTraceModel) == 0
        assert await fresh_count(RecommendationTraceStepModel) == 0

    # ── Case 3: StepModel insert fails ─────────────────────────────────────

    async def test_step_insert_failure(
        self,
        db_engine,
        db_session,
        patient_in_db,
        fresh_count,
    ):
        """When StepModel insert fails → no residue of any kind."""
        with pytest.raises(RuntimeError, match="Failed to persist recommendation"):
            await self._call_service(
                db_session,
                fail_on="step",
            )

        assert await fresh_count(RecommendationModel) == 0
        assert await fresh_count(RecommendationTraceModel) == 0
        assert await fresh_count(RecommendationTraceStepModel) == 0

    # ── Case 4: commit fails ───────────────────────────────────────────────

    async def test_commit_failure(
        self,
        db_engine,
        db_session,
        patient_in_db,
        fresh_count,
    ):
        """When commit raises → rollback, no residue, no recommendation_id returned."""
        with pytest.raises(RuntimeError, match="Failed to persist recommendation"):
            await self._call_service(
                db_session,
                fail_on="commit",
            )

        assert await fresh_count(RecommendationModel) == 0
        assert await fresh_count(RecommendationTraceModel) == 0
        assert await fresh_count(RecommendationTraceStepModel) == 0

    # ── Case 5: Success ────────────────────────────────────────────────────

    async def test_success_pipeline(
        self,
        db_engine,
        db_session,
        patient_in_db,
        fresh_count,
    ):
        """Full success: all records written, retrievable via GET."""
        result = await self._call_service(db_session)

        # Response must contain a recommendation_id
        rec_id = result.get("recommendation_id")
        assert rec_id is not None, "Expected recommendation_id in response"

        # Verify all records were persisted
        assert await fresh_count(RecommendationModel) == 1
        assert await fresh_count(RecommendationTraceModel) == 1
        assert await fresh_count(RecommendationTraceStepModel) == 2

        # Verify the data is retrievable via service.get_recommendation
        from src.backend.services.recommendation_service import RecommendationService

        service = RecommendationService(db_session)
        retrieved = await service.get_recommendation(rec_id)
        assert retrieved is not None
        assert retrieved["recommendation_id"] == rec_id
        assert retrieved["patient_id"] == _PATIENT_UUID
        assert retrieved["engine_version"] == "1.0.0"
        assert len(retrieved["recommendations"]) == 2
        assert retrieved["recommendations"][0]["drug_name"] == "Osimertinib"

    # ── Edge: empty pipeline result (no aggregated data) ───────────────────

    async def test_empty_aggregated_data_rollback(
        self,
        db_engine,
        db_session,
        fresh_count,
    ):
        """When pipeline returns no evidence → ValueError, nothing persisted."""
        from src.backend.services.recommendation_service import RecommendationService

        # Patch engine to return empty aggregated data
        with patch(
            "src.backend.services.recommendation_service.RecommendationEngine",
            autospec=True,
        ) as eng_cls:
            eng_inst = MagicMock()
            result = _make_pipeline_result()
            result["aggregated"] = {}
            eng_inst.run = AsyncMock(return_value=result)
            eng_cls.return_value = eng_inst

            with patch(
                "src.backend.services.recommendation_service.DrugRankingEngine",
                autospec=True,
            ) as rank_cls:
                rank_inst = MagicMock()
                rank_inst.rank.return_value = []
                rank_cls.return_value = rank_inst

                with patch(
                    "src.backend.services.recommendation_service.ExplainableEngine",
                    autospec=True,
                ) as expl_cls:
                    expl_inst = MagicMock()
                    expl_inst.generate_explanations.return_value = []
                    expl_cls.return_value = expl_inst

                    from src.backend.clinical.calculation_trace import (
                        CalculationTrace,
                        TraceManager,
                    )

                    trace = CalculationTrace(trace_id="empty-trace", patient_id="P-EMPTY")
                    with patch(
                        "src.backend.services.recommendation_service.TraceManager",
                        autospec=True,
                    ) as tm_cls:
                        tm_inst = MagicMock(spec=TraceManager)
                        tm_inst.start_trace.return_value = trace
                        tm_inst.get_trace.return_value = trace
                        tm_inst.complete_trace = MagicMock()
                        tm_cls.return_value = tm_inst

                        service = RecommendationService(db_session)
                        with pytest.raises(ValueError, match="No clinical evidence found"):
                            await service.create_recommendation(
                                request_data={
                                    "patient_id": _PATIENT_UUID,
                                    "variants": ["UNKNOWN VAR"],
                                },
                                user_id=_USER_UUID,
                            )

        assert await fresh_count(RecommendationModel) == 0
        assert await fresh_count(RecommendationTraceModel) == 0
        assert await fresh_count(RecommendationTraceStepModel) == 0
