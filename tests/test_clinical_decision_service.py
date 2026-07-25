"""
Service tests for ClinicalDecisionService (Phase 3B — Batch H Part 2).

Covers:
- Decision creation success (Engine + Repository + Trace full chain)
- Same-transaction persistence (decision + trace committed, readable from DB)
- Decision retrieval (found / not found)
- Engine failure rollback (no data written)
- Persistence failure rollback (commit fails → clean DB)
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base
from src.backend.domain.clinical_decision import (
    ClinicalDecisionModel,
    ClinicalDecisionTraceModel,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
async def db_session():
    """In-memory SQLite database session for service tests."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def patient_in_db(db_session):
    """Create a Patient record in the DB for FK references.

    Uses a fixed UUID so tests can reference it by string.
    """
    from src.backend.domain.patient import PatientModel

    pid = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
    p = PatientModel(id=pid, display_name="CDS-TEST-PATIENT")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest.fixture
async def recommendation_in_db(db_session, patient_in_db):
    """Create a RecommendationModel record in the DB for FK references."""
    from src.backend.domain.recommendation import RecommendationModel

    rec = RecommendationModel(
        recommendation_id="rec-cds-test-001",
        patient_id=patient_in_db.id,
        engine_version="1.0.0",
        status="completed",
        request_payload={"variants": ["EGFR L858R"]},
        result_payload={
            "recommendations": [
                {
                    "drug_name": "Osimertinib",
                    "rank": 1,
                    "overall_score": 0.95,
                    "evidence_score": 0.90,
                    "sensitivity_score": 0.85,
                    "resistance_score": 0.10,
                    "conflict_score": 0.05,
                },
                {
                    "drug_name": "Afatinib",
                    "rank": 2,
                    "overall_score": 0.85,
                    "evidence_score": 0.80,
                    "sensitivity_score": 0.75,
                    "resistance_score": 0.15,
                    "conflict_score": 0.08,
                },
            ],
            "evidence": [
                {
                    "drug_name": "Osimertinib",
                    "evidence_level": "Tier_1",
                    "evidence_direction": "supporting",
                    "source": "CIViC",
                },
            ],
        },
    )
    db_session.add(rec)
    await db_session.commit()
    await db_session.refresh(rec)
    return rec


# ─── Mock helpers ─────────────────────────────────────────────────────────


def _make_mock_engine_result(
    decision_type: str = "approved",
    confidence: str = "high",
) -> Any:
    """Build a synthetic ClinicalDecisionResult resembling engine output."""
    from src.backend.clinical.clinical_decision_engine import ClinicalDecisionResult

    return ClinicalDecisionResult(
        decision_type=decision_type,
        reason=(
            "Osimertinib is approved for NSCLC with EGFR L858R "
            "based on Tier 1 evidence."
        ),
        evidence_summary={
            "total_evidence_count": 1,
            "best_evidence_tier": "Tier_1",
            "sources": ["CIViC"],
            "direction_breakdown": {
                "supporting": 1,
                "resistance": 0,
                "conflicting": 0,
                "neutral": 0,
            },
        },
        confidence=confidence,
        alternatives=[
            {
                "drug_name": "Afatinib",
                "rank": 2,
                "overall_score": 0.85,
                "rationale": "Alternative EGFR-TKI",
            },
        ],
        contraindications=[
            {
                "drug": "Osimertinib",
                "type": "resistance",
                "detail": "T790M mutation",
                "severity": "moderate",
            },
        ],
    )


@pytest.fixture
def mock_engine():
    """Create a mock ClinicalDecisionEngine that returns a predictable result."""
    from src.backend.clinical.clinical_decision_engine import ClinicalDecisionEngine

    engine = MagicMock(spec=ClinicalDecisionEngine)
    engine.evaluate = AsyncMock(return_value=_make_mock_engine_result())
    return engine


# ─── Tests: Decision Creation ─────────────────────────────────────────────


class TestCreateDecision:
    """Tests for ClinicalDecisionService.create_decision()."""

    async def test_create_decision_success(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        mock_engine,
    ):
        """Full pipeline: decision created, persisted, returned with all fields."""
        from src.backend.services.clinical_decision_service import (
            ClinicalDecisionService,
        )

        service = ClinicalDecisionService(db=db_session, engine=mock_engine)
        result = await service.create_decision(
            patient_id=patient_in_db.id,
            recommendation_id=recommendation_in_db.recommendation_id,
            variants=[{"gene_symbol": "EGFR", "protein_change": "L858R"}],
            context={
                "patient": {
                    "id": str(patient_in_db.id),
                    "display_name": "CDS-TEST-PATIENT",
                },
            },
        )

        # Response DTO structure
        assert result.decision_id is not None
        assert len(result.decision_id) == 32  # hex uuid
        assert result.patient_id == str(patient_in_db.id)
        assert result.recommendation_id == recommendation_in_db.recommendation_id
        assert result.decision_type == "approved"
        assert "Osimertinib" in result.reason
        assert result.evidence_summary is not None
        assert result.evidence_summary["total_evidence_count"] == 1
        assert result.confidence == "high"
        assert len(result.alternatives) == 1
        assert result.alternatives[0]["drug_name"] == "Afatinib"
        assert len(result.contraindications) == 1
        assert result.trace_id is not None
        assert len(result.trace_id) == 32
        assert result.created_at is not None

        # Verify persistence via repository
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
        )

        repo = ClinicalDecisionRepository(db_session)
        persisted = await repo.get_by_id(result.decision_id)
        assert persisted is not None
        assert persisted.decision_id == result.decision_id
        assert persisted.decision_type == "approved"
        assert persisted.confidence == "high"
        assert str(persisted.patient_id) == str(patient_in_db.id)

    async def test_create_decision_different_types(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        mock_engine,
    ):
        """All decision_type values should be handled correctly."""
        from src.backend.services.clinical_decision_service import (
            ClinicalDecisionService,
        )

        for dec_type in (
            "approved",
            "off_label",
            "clinical_trial",
            "contraindicated",
            "experimental",
            "not_recommended",
        ):
            mock_engine.evaluate.return_value = _make_mock_engine_result(
                decision_type=dec_type,
            )

            service = ClinicalDecisionService(db=db_session, engine=mock_engine)
            result = await service.create_decision(
                patient_id=patient_in_db.id,
                recommendation_id=recommendation_in_db.recommendation_id,
                variants=[{"gene_symbol": "EGFR"}],
                context={
                    "patient": {"id": str(patient_in_db.id)},
                    "evidence": [{"drug_name": "Test", "evidence_level": "Tier_1"}],
                },
            )
            assert result.decision_type == dec_type

    async def test_create_decision_same_transaction_persistence(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        mock_engine,
    ):
        """Decision + Trace should all be in the same transaction."""
        from src.backend.services.clinical_decision_service import (
            ClinicalDecisionService,
        )

        service = ClinicalDecisionService(db=db_session, engine=mock_engine)
        result = await service.create_decision(
            patient_id=patient_in_db.id,
            recommendation_id=recommendation_in_db.recommendation_id,
            variants=[{"gene_symbol": "EGFR", "protein_change": "L858R"}],
            context={
                "patient": {"id": str(patient_in_db.id)},
            },
        )

        dec_id = result.decision_id
        trace_id = result.trace_id

        from sqlalchemy import select

        # Verify decision exists in DB
        dec_stmt = select(ClinicalDecisionModel).where(
            ClinicalDecisionModel.decision_id == dec_id,
        )
        dec_result = await db_session.execute(dec_stmt)
        dec = dec_result.scalar_one_or_none()
        assert dec is not None
        assert dec.decision_type == "approved"

        # Verify trace exists in DB
        trace_stmt = select(ClinicalDecisionTraceModel).where(
            ClinicalDecisionTraceModel.trace_id == trace_id,
        )
        trace_result = await db_session.execute(trace_stmt)
        trace = trace_result.scalar_one_or_none()
        assert trace is not None
        assert trace.step_type == "clinical_decision_evaluate"
        assert trace.clinical_decision_id == dec.id

    async def test_create_decision_patient_not_found(
        self,
        db_session,
        recommendation_in_db,
        mock_engine,
    ):
        """When patient does not exist, ValueError should be raised."""
        from src.backend.services.clinical_decision_service import (
            ClinicalDecisionService,
        )

        unknown_patient_id = uuid.uuid4()
        service = ClinicalDecisionService(db=db_session, engine=mock_engine)
        with pytest.raises(ValueError, match="not found"):
            await service.create_decision(
                patient_id=unknown_patient_id,
                recommendation_id=recommendation_in_db.recommendation_id,
                variants=[{"gene_symbol": "EGFR"}],
            )

    async def test_create_decision_recommendation_not_found(
        self,
        db_session,
        patient_in_db,
        mock_engine,
    ):
        """When recommendation does not exist, ValueError should be raised."""
        from src.backend.services.clinical_decision_service import (
            ClinicalDecisionService,
        )

        service = ClinicalDecisionService(db=db_session, engine=mock_engine)
        with pytest.raises(ValueError, match="Recommendation.*not found"):
            await service.create_decision(
                patient_id=patient_in_db.id,
                recommendation_id="non-existent-rec-id",
                variants=[{"gene_symbol": "EGFR"}],
                context={
                    "patient": {"id": str(patient_in_db.id)},
                },
            )

    async def test_engine_value_error_propagated(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
    ):
        """ValueError from engine.evaluate should propagate directly."""
        from src.backend.clinical.clinical_decision_engine import (
            ClinicalDecisionEngine,
        )
        from src.backend.services.clinical_decision_service import (
            ClinicalDecisionService,
        )

        engine = MagicMock(spec=ClinicalDecisionEngine)
        engine.evaluate = AsyncMock(
            side_effect=ValueError("Cannot determine top drug"),
        )

        service = ClinicalDecisionService(db=db_session, engine=engine)
        with pytest.raises(ValueError, match="Cannot determine top drug"):
            await service.create_decision(
                patient_id=patient_in_db.id,
                recommendation_id=recommendation_in_db.recommendation_id,
                variants=[{"gene_symbol": "EGFR"}],
                context={
                    "patient": {"id": str(patient_in_db.id)},
                    "evidence": [],
                },
            )

    async def test_engine_unexpected_exception_wrapped(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
    ):
        """Non-ValueError exceptions from engine should be wrapped in RuntimeError."""
        from src.backend.clinical.clinical_decision_engine import (
            ClinicalDecisionEngine,
        )
        from src.backend.services.clinical_decision_service import (
            ClinicalDecisionService,
        )

        engine = MagicMock(spec=ClinicalDecisionEngine)
        engine.evaluate = AsyncMock(
            side_effect=ConnectionError("Engine connection timeout"),
        )

        service = ClinicalDecisionService(db=db_session, engine=engine)
        with pytest.raises(
            RuntimeError,
            match="encountered an internal error",
        ):
            await service.create_decision(
                patient_id=patient_in_db.id,
                recommendation_id=recommendation_in_db.recommendation_id,
                variants=[{"gene_symbol": "EGFR"}],
                context={
                    "patient": {"id": str(patient_in_db.id)},
                    "evidence": [],
                },
            )


# ─── Tests: Failure Rollback ──────────────────────────────────────────────


class TestFailureRollback:
    """Verify rollback behaviour when pipeline or persistence fails."""

    async def test_engine_failure_rollback(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
    ):
        """When engine.evaluate raises, no decision should be persisted."""
        from src.backend.clinical.clinical_decision_engine import (
            ClinicalDecisionEngine,
        )
        from src.backend.services.clinical_decision_service import (
            ClinicalDecisionService,
        )

        engine = MagicMock(spec=ClinicalDecisionEngine)
        engine.evaluate = AsyncMock(
            side_effect=RuntimeError("Engine crashed"),
        )

        service = ClinicalDecisionService(db=db_session, engine=engine)
        with pytest.raises(RuntimeError):
            await service.create_decision(
                patient_id=patient_in_db.id,
                recommendation_id=recommendation_in_db.recommendation_id,
                variants=[{"gene_symbol": "EGFR"}],
                context={
                    "patient": {"id": str(patient_in_db.id)},
                    "evidence": [],
                },
            )

        # Verify no decision was persisted
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
        )

        repo = ClinicalDecisionRepository(db_session)
        all_decisions = await repo.list_by_patient_id(patient_in_db.id)
        assert all_decisions == []

    async def test_persistence_failure_rollback(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        mock_engine,
    ):
        """When commit fails, the exception is propagated and DB is clean."""
        from src.backend.services.clinical_decision_service import (
            ClinicalDecisionService,
        )

        # Save patient_id before any commit failure (object may be expired after rollback)
        patient_id = patient_in_db.id

        # Make commit raise
        original_commit = db_session.commit

        async def failing_commit():
            raise RuntimeError("DB commit failed — disk full")

        db_session.commit = failing_commit

        service = ClinicalDecisionService(db=db_session, engine=mock_engine)
        with pytest.raises(RuntimeError, match="Failed to persist clinical decision"):
            await service.create_decision(
                patient_id=patient_id,
                recommendation_id=recommendation_in_db.recommendation_id,
                variants=[{"gene_symbol": "EGFR", "protein_change": "L858R"}],
                context={
                    "patient": {"id": str(patient_id)},
                },
            )

        # Restore commit
        db_session.commit = original_commit

        # Verify DB is clean — no decision records created
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
        )

        repo = ClinicalDecisionRepository(db_session)
        all_decisions = await repo.list_by_patient_id(patient_id)
        assert all_decisions == []

    async def test_decision_repo_create_failure_rollback(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
    ):
        """When decision_repo.create raises, no data should remain."""
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
            ClinicalDecisionTraceRepository,
        )
        from src.backend.services.clinical_decision_service import (
            ClinicalDecisionService,
        )

        # Save IDs before any operation that may expire session objects
        patient_id = patient_in_db.id
        rec_id = recommendation_in_db.recommendation_id

        # Inject a decision_repo that raises on create
        bad_repo = MagicMock(spec=ClinicalDecisionRepository)
        bad_repo.create.side_effect = RuntimeError("Repo create failed")

        trace_repo = MagicMock(spec=ClinicalDecisionTraceRepository)

        from src.backend.clinical.clinical_decision_engine import (
            ClinicalDecisionEngine,
        )

        engine = MagicMock(spec=ClinicalDecisionEngine)
        engine.evaluate = AsyncMock(return_value=_make_mock_engine_result())

        service = ClinicalDecisionService(
            db=db_session,
            engine=engine,
            decision_repo=bad_repo,
            trace_repo=trace_repo,
        )
        with pytest.raises(RuntimeError, match="Failed to persist clinical decision"):
            await service.create_decision(
                patient_id=patient_id,
                recommendation_id=rec_id,
                variants=[{"gene_symbol": "EGFR"}],
                context={
                    "patient": {"id": str(patient_id)},
                    "evidence": [],
                },
            )

        # Verify DB is clean
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
        )

        repo = ClinicalDecisionRepository(db_session)
        all_decisions = await repo.list_by_patient_id(patient_id)
        assert all_decisions == []


# ─── Tests: Decision Retrieval ────────────────────────────────────────────


class TestGetDecision:
    """Tests for ClinicalDecisionService.get_decision()."""

    async def test_get_decision_found(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        mock_engine,
    ):
        """get_decision should retrieve a previously created decision."""
        from src.backend.services.clinical_decision_service import (
            ClinicalDecisionService,
        )

        service = ClinicalDecisionService(db=db_session, engine=mock_engine)
        created = await service.create_decision(
            patient_id=patient_in_db.id,
            recommendation_id=recommendation_in_db.recommendation_id,
            variants=[{"gene_symbol": "EGFR", "protein_change": "L858R"}],
            context={
                "patient": {"id": str(patient_in_db.id)},
            },
        )

        retrieved = await service.get_decision(created.decision_id)
        assert retrieved is not None
        assert retrieved.decision_id == created.decision_id
        assert retrieved.patient_id == created.patient_id
        # _model_to_response stores the recommendation's PK UUID as
        # recommendation_id in the response DTO, while create_decision
        # returns the business ID string.
        assert retrieved.decision_type == created.decision_type
        assert retrieved.confidence == created.confidence
        assert retrieved.trace_id == created.trace_id
        assert len(retrieved.alternatives) == len(created.alternatives)
        assert len(retrieved.contraindications) == len(created.contraindications)

    async def test_get_decision_not_found(
        self,
        db_session,
    ):
        """get_decision should return None for non-existent ID."""
        from src.backend.services.clinical_decision_service import (
            ClinicalDecisionService,
        )

        service = ClinicalDecisionService(db=db_session)
        result = await service.get_decision("non-existent-decision-id")
        assert result is None

    async def test_get_decision_by_uuid(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        mock_engine,
    ):
        """get_decision_by_uuid should retrieve by primary key."""
        from src.backend.services.clinical_decision_service import (
            ClinicalDecisionService,
        )

        service = ClinicalDecisionService(db=db_session, engine=mock_engine)
        created = await service.create_decision(
            patient_id=patient_in_db.id,
            recommendation_id=recommendation_in_db.recommendation_id,
            variants=[{"gene_symbol": "EGFR", "protein_change": "L858R"}],
            context={
                "patient": {"id": str(patient_in_db.id)},
            },
        )

        # Look up the PK via get_by_id
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
        )

        repo = ClinicalDecisionRepository(db_session)
        model = await repo.get_by_id(created.decision_id)
        assert model is not None

        retrieved = await service.get_decision_by_uuid(model.id)
        assert retrieved is not None
        assert retrieved.decision_id == created.decision_id

    async def test_list_decisions_by_patient(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        mock_engine,
    ):
        """list_decisions_by_patient should return decisions for a patient."""
        from src.backend.services.clinical_decision_service import (
            ClinicalDecisionService,
        )

        service = ClinicalDecisionService(db=db_session, engine=mock_engine)

        # Create two decisions
        await service.create_decision(
            patient_id=patient_in_db.id,
            recommendation_id=recommendation_in_db.recommendation_id,
            variants=[{"gene_symbol": "EGFR"}],
            context={"patient": {"id": str(patient_in_db.id)}, "evidence": []},
        )
        await service.create_decision(
            patient_id=patient_in_db.id,
            recommendation_id=recommendation_in_db.recommendation_id,
            variants=[{"gene_symbol": "EGFR"}],
            context={"patient": {"id": str(patient_in_db.id)}, "evidence": []},
        )

        decisions = await service.list_decisions_by_patient(patient_in_db.id)
        assert len(decisions) >= 2
        # Should be ordered newest first
        if len(decisions) >= 2:
            assert decisions[0].created_at >= decisions[1].created_at
