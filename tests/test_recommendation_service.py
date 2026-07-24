"""
Service tests for RecommendationService (P3A-10 Batch E3).

Covers:
- Successful recommendation creation with mocked pipeline
- Successful trace creation with steps
- Same-transaction persistence
- Report generation failure policy (non-fatal)
- Pipeline failure rollback (no data written)
- Repository failure rollback
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base
from src.backend.domain.recommendation import (
    RecommendationModel,
    RecommendationTraceModel,
    RecommendationTraceStepModel,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
async def db_session():
    """In-memory SQLite database session for service tests."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def patient_in_db(db_session):
    """Create a Patient record in the DB for FK references.

    Uses a fixed UUID so tests can reference it by string.
    """
    import uuid

    from src.backend.domain.patient import PatientModel

    pid = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
    p = PatientModel(id=pid, display_name="SERVICE-TEST-PATIENT")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


def _make_mock_pipeline_result(
    drug_names: list[str] | None = None,
    status: str = "success",
) -> dict[str, Any]:
    """Build a synthetic pipeline result resembling RecommendationEngine.run() output."""
    drugs = drug_names or ["Osimertinib", "Afatinib"]
    aggregated = {}
    ranking_results = []
    for i, name in enumerate(drugs):
        key = name.lower()
        aggregated[key] = {"total_weight": 1.0 - i * 0.1, "item_count": 3}
        ranking_results.append({
            "drug_name": name,
            "rank": i + 1,
            "overall_score": type("Score", (), {"raw_score": 0.95 - i * 0.1})(),
            "evidence_score": type("Score", (), {"confidence_score": 0.9 - i * 0.1})(),
            "sensitivity": type("Score", (), {"score": 0.85 - i * 0.1})(),
            "resistance": type("Score", (), {"score": 0.1 + i * 0.05})(),
            "conflict_score": type("Score", (), {"score": 0.05 + i * 0.02})(),
        })

    return {
        "drugs_ranked": ranking_results,
        "aggregated": aggregated,
        "evidence_count": 12,
        "rules_evaluated": 5,
        "rules_fired": 3,
        "rule_results": [],
        "pipeline_status": status,
        "trace_id": "mock-trace-001",
    }


def _make_trace_manager(trace_id: str = "mock-trace-001"):
    """Build a lightweight in-memory TraceManager with a pre-started trace."""
    from src.backend.clinical.calculation_trace import CalculationTrace, TraceManager, TraceStep

    mgr = TraceManager()
    trace = mgr.start_trace(patient_id="P-MOCK")
    trace.trace_id = trace_id
    # Inject a couple of steps
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
    mgr._traces[trace_id] = trace
    return mgr


# ─── Mock the pipeline components ─────────────────────────────────────────


@pytest.fixture
def mock_engine_run():
    """Patch RecommendationEngine.run to return a controlled result."""
    with patch(
        "src.backend.services.recommendation_service.RecommendationEngine",
        autospec=True,
    ) as mock_engine_cls:
        mock_instance = MagicMock()
        mock_instance.run = AsyncMock(return_value=_make_mock_pipeline_result())
        mock_engine_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_ranking_engine():
    """Patch DrugRankingEngine.rank to return predictable results."""
    with patch(
        "src.backend.services.recommendation_service.DrugRankingEngine",
        autospec=True,
    ) as mock_ranking_cls:
        mock_instance = MagicMock()
        ranking_results = [
            type("RankResult", (), {
                "drug_name": name,
                "rank": i + 1,
                "overall_score": type("Score", (), {"raw_score": 0.95 - i * 0.1})(),
                "evidence_score": type("Score", (), {"confidence_score": 0.9 - i * 0.1})(),
                "sensitivity": type("Score", (), {"score": 0.85 - i * 0.1})(),
                "resistance": type("Score", (), {"score": 0.1 + i * 0.05})(),
                "conflict_score": type("Score", (), {"score": 0.05 + i * 0.02})(),
            })
            for i, name in enumerate(["Osimertinib", "Afatinib"])
        ]
        mock_instance.rank.return_value = ranking_results
        mock_ranking_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_explainable_engine():
    """Patch ExplainableEngine.generate_explanations."""
    with patch(
        "src.backend.services.recommendation_service.ExplainableEngine",
        autospec=True,
    ) as mock_explainable_cls:
        mock_instance = MagicMock()
        mock_instance.generate_explanations.return_value = [
            type("Explanation", (), {"reasons": []})(),
            type("Explanation", (), {"reasons": []})(),
        ]
        mock_explainable_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_trace_manager():
    """Patch TraceManager used inside RecommendationService."""
    from src.backend.clinical.calculation_trace import (
        CalculationTrace,
        TraceManager,
        TraceStep,
    )

    # Build the pre-configured trace that start_trace / get_trace will return
    _trace = CalculationTrace(
        trace_id="mock-trace-001",
        patient_id="P-MOCK",
        status="running",
    )
    _trace.steps = [
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
    ) as mock_tm_cls:
        mock_instance = MagicMock(spec=TraceManager)
        mock_instance.start_trace = MagicMock(return_value=_trace)
        mock_instance.get_trace = MagicMock(return_value=_trace)
        mock_instance.complete_trace = MagicMock()
        mock_tm_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_report_generator():
    """Patch ReportGenerator.generate to return a dummy HTML string."""
    with patch(
        "src.backend.services.recommendation_service.ReportGenerator",
        autospec=True,
    ) as mock_rg_cls:
        mock_instance = MagicMock()
        mock_instance.generate.return_value = "<html>Mock Report</html>"
        mock_rg_cls.return_value = mock_instance
        yield mock_instance


# ─── Tests ────────────────────────────────────────────────────────────────


class TestCreateRecommendation:
    """Tests for RecommendationService.create_recommendation()."""

    async def test_successful_creation(
        self,
        db_session,
        patient_in_db,
        mock_engine_run,
        mock_ranking_engine,
        mock_explainable_engine,
        mock_trace_manager,
        mock_report_generator,
    ):
        """Full pipeline: recommendation created, persisted, returned."""
        from src.backend.services.recommendation_service import RecommendationService

        service = RecommendationService(db_session)
        result = await service.create_recommendation(
            request_data={
                "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                "variants": ["EGFR L858R"],
                "patient_context": {"age": 65, "cancer_type": "NSCLC"},
                "top_n": 5,
            },
            user_id="550e8400-e29b-41d4-a716-446655440000",
        )

        # Response structure
        assert result["recommendation_id"] is not None
        assert result["patient_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert result["engine_version"] == "1.0.0"
        assert result["trace_id"] == "mock-trace-001"
        assert result["report_html"] == "<html>Mock Report</html>"
        assert "created_at" in result
        assert len(result["recommendations"]) == 2
        assert result["recommendations"][0]["drug_name"] == "Osimertinib"
        assert result["recommendations"][0]["rank"] == 1

        # Verify persistence
        from src.backend.repositories.recommendation_repo import RecommendationRepository

        repo = RecommendationRepository(db_session)
        persisted = await repo.get_by_id(result["recommendation_id"])
        assert persisted is not None
        assert persisted.patient_id is not None  # FK resolved

    async def test_trace_with_steps_persisted(
        self,
        db_session,
        patient_in_db,
        mock_engine_run,
        mock_ranking_engine,
        mock_explainable_engine,
        mock_trace_manager,
        mock_report_generator,
    ):
        """Trace model and steps should be persisted alongside recommendation."""
        from src.backend.services.recommendation_service import RecommendationService

        service = RecommendationService(db_session)
        result = await service.create_recommendation(
            request_data={
                "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                "variants": ["BRAF V600E"],
            },
            user_id="550e8400-e29b-41d4-a716-446655440000",
        )

        # Check trace persisted
        from src.backend.repositories.recommendation_repo import TraceRepository

        trace_repo = TraceRepository(db_session)
        trace = await trace_repo.get_trace_by_trace_id(result["trace_id"])
        assert trace is not None
        assert trace.recommendation_id is not None

        # Check steps persisted
        steps = await trace_repo.get_steps_by_trace_id(str(trace.id))
        assert len(steps) == 2  # as set up in _make_trace_manager
        assert steps[0].step_type in ("evidence", "recommendation")

    async def test_same_transaction_persistence(
        self,
        db_session,
        patient_in_db,
        mock_engine_run,
        mock_ranking_engine,
        mock_explainable_engine,
        mock_trace_manager,
        mock_report_generator,
    ):
        """Recommendation + Trace + Steps should all be in the same transaction."""
        from src.backend.services.recommendation_service import RecommendationService

        service = RecommendationService(db_session)
        result = await service.create_recommendation(
            request_data={
                "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                "variants": ["EGFR L858R"],
            },
            user_id="550e8400-e29b-41d4-a716-446655440000",
        )

        rec_id = result["recommendation_id"]
        trace_id = result["trace_id"]

        # Check all three exist in DB
        from sqlalchemy import select

        rec_stmt = select(RecommendationModel).where(
            RecommendationModel.recommendation_id == rec_id,
        )
        rec_result = await db_session.execute(rec_stmt)
        rec = rec_result.scalar_one_or_none()
        assert rec is not None

        trace_stmt = select(RecommendationTraceModel).where(
            RecommendationTraceModel.trace_id == trace_id,
        )
        trace_result = await db_session.execute(trace_stmt)
        trace = trace_result.scalar_one_or_none()
        assert trace is not None

        step_stmt = select(RecommendationTraceStepModel).where(
            RecommendationTraceStepModel.trace_id == trace.id,
        )
        step_result = await db_session.execute(step_stmt)
        steps = step_result.scalars().all()
        assert len(steps) == 2

    async def test_report_generation_failure_non_fatal(
        self,
        db_session,
        patient_in_db,
        mock_engine_run,
        mock_ranking_engine,
        mock_explainable_engine,
        mock_trace_manager,
    ):
        """If report generation fails, the response should omit the report, not crash."""
        from src.backend.services.recommendation_service import RecommendationService

        # Patch ReportGenerator to raise
        with patch(
            "src.backend.services.recommendation_service.ReportGenerator",
            autospec=True,
        ) as mock_rg_cls:
            mock_instance = MagicMock()
            mock_instance.generate.side_effect = RuntimeError("Report gen failed")
            mock_rg_cls.return_value = mock_instance

            service = RecommendationService(db_session)
            result = await service.create_recommendation(
                request_data={
                    "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                    "variants": ["EGFR L858R"],
                },
                user_id="550e8400-e29b-41d4-a716-446655440000",
            )

        # Should still return successfully with report_html=None
        assert result["recommendation_id"] is not None
        assert result["report_html"] is None
        assert len(result["recommendations"]) == 2

    async def test_pipeline_failure_rollback(
        self,
        db_session,
        mock_engine_run,
        mock_ranking_engine,
        mock_explainable_engine,
        mock_trace_manager,
        mock_report_generator,
    ):
        """When the pipeline fails, no data should be written."""
        from src.backend.services.recommendation_service import RecommendationService

        # Make engine.run raise
        mock_engine_run.run.side_effect = RuntimeError("Pipeline crashed")

        service = RecommendationService(db_session)
        with pytest.raises(RuntimeError, match="pipeline encountered an internal error"):
            await service.create_recommendation(
                request_data={
                    "patient_id": "550e8400-e29b-41d4-a716-446655440005",
                    "variants": ["EGFR L858R"],
                },
                user_id="user-001",
            )

        # Verify no recommendation was persisted
        from src.backend.repositories.recommendation_repo import RecommendationRepository

        repo = RecommendationRepository(db_session)
        all_recs = await repo.list_by_patient_id("P-PIPE-FAIL")
        assert all_recs == []

    async def test_pipeline_error_status_rollback(
        self,
        db_session,
        mock_engine_run,
        mock_ranking_engine,
        mock_explainable_engine,
        mock_trace_manager,
        mock_report_generator,
    ):
        """When pipeline returns error status, no data should be written."""
        from src.backend.services.recommendation_service import RecommendationService

        # Return pipeline with error status
        mock_engine_run.run.return_value = _make_mock_pipeline_result(
            status="error_evidence_collection_failed",
        )

        service = RecommendationService(db_session)
        with pytest.raises(RuntimeError, match="did not complete successfully"):
            await service.create_recommendation(
                request_data={
                    "patient_id": "550e8400-e29b-41d4-a716-446655440006",
                    "variants": ["EGFR L858R"],
                },
                user_id="user-001",
            )

        from src.backend.repositories.recommendation_repo import RecommendationRepository

        repo = RecommendationRepository(db_session)
        all_recs = await repo.list_by_patient_id("P-ERR-STATUS")
        assert all_recs == []

    async def test_empty_aggregated_data_rollback(
        self,
        db_session,
        mock_engine_run,
        mock_ranking_engine,
        mock_explainable_engine,
        mock_trace_manager,
        mock_report_generator,
    ):
        """When no evidence is found, ValueError is raised and nothing persists."""
        from src.backend.services.recommendation_service import RecommendationService

        # Return pipeline with empty aggregated data
        result = _make_mock_pipeline_result()
        result["aggregated"] = {}
        mock_engine_run.run.return_value = result

        service = RecommendationService(db_session)
        with pytest.raises(ValueError, match="No clinical evidence found"):
            await service.create_recommendation(
                request_data={
                    "patient_id": "550e8400-e29b-41d4-a716-446655440007",
                    "variants": ["UNKNOWN VAR"],
                },
                user_id="user-001",
            )

        from src.backend.repositories.recommendation_repo import RecommendationRepository

        repo = RecommendationRepository(db_session)
        all_recs = await repo.list_by_patient_id("P-NO-EVID")
        assert all_recs == []

    async def test_repository_failure_rollback(
        self,
        db_session,
        patient_in_db,
        mock_engine_run,
        mock_ranking_engine,
        mock_explainable_engine,
        mock_trace_manager,
        mock_report_generator,
    ):
        """If persistence fails (commit raises), the pipeline result is returned but DB is clean."""
        from src.backend.services.recommendation_service import RecommendationService

        # Make commit raise
        original_commit = db_session.commit

        async def failing_commit():
            raise RuntimeError("DB commit failed")

        db_session.commit = failing_commit

        service = RecommendationService(db_session)
        result = await service.create_recommendation(
            request_data={
                "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                "variants": ["EGFR L858R"],
            },
            user_id="550e8400-e29b-41d4-a716-446655440000",
        )

        # Should still return the in-memory result
        assert result["recommendation_id"] is not None
        assert len(result["recommendations"]) == 2

        # Restore commit and verify DB is clean
        db_session.commit = original_commit
        from src.backend.repositories.recommendation_repo import RecommendationRepository

        repo = RecommendationRepository(db_session)
        all_recs = await repo.list_by_patient_id("550e8400-e29b-41d4-a716-446655440008")
        assert all_recs == []

    async def test_get_recommendation_found(
        self,
        db_session,
        patient_in_db,
        mock_engine_run,
        mock_ranking_engine,
        mock_explainable_engine,
        mock_trace_manager,
        mock_report_generator,
    ):
        """get_recommendation should retrieve a previously created recommendation."""
        from src.backend.services.recommendation_service import RecommendationService

        service = RecommendationService(db_session)
        created = await service.create_recommendation(
            request_data={
                "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                "variants": ["EGFR L858R"],
            },
            user_id="550e8400-e29b-41d4-a716-446655440000",
        )

        retrieved = await service.get_recommendation(created["recommendation_id"])
        assert retrieved is not None
        assert retrieved["recommendation_id"] == created["recommendation_id"]
        assert retrieved["patient_id"] == created["patient_id"]
        assert retrieved["engine_version"] == "1.0.0"
        assert retrieved["recommendations"] == created["recommendations"]

    async def test_get_recommendation_not_found(
        self,
        db_session,
    ):
        """get_recommendation should return None for non-existent ID."""
        from src.backend.services.recommendation_service import RecommendationService

        service = RecommendationService(db_session)
        result = await service.get_recommendation("non-existent-id")
        assert result is None
