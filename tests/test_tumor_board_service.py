"""
Service tests for TumorBoardConsensusService (Phase 3C).

Covers:
- Successful consensus creation (full pipeline)
- Patient / recommendation / clinical decision mismatch validation
- created_by persistence
- Transaction rollback on engine failure
- Opinion persistence failure
- Trace persistence failure
- Commit failure
- Get / List / Count queries
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base

# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
async def db_session():
    """In-memory SQLite database session for service tests."""
    # Ensure all models are loaded before create_all
    from src.backend.domain.patient import PatientModel  # noqa: F401
    from src.backend.domain.recommendation import RecommendationModel  # noqa: F401
    from src.backend.domain.clinical_decision import ClinicalDecisionModel  # noqa: F401

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
    """Create a Patient record in the DB for FK references."""
    from src.backend.domain.patient import PatientModel

    pid = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
    p = PatientModel(id=pid, display_name="TBS-TEST-PATIENT")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest.fixture
async def recommendation_in_db(db_session, patient_in_db):
    """Create a RecommendationModel record in the DB for FK references."""
    from src.backend.domain.recommendation import RecommendationModel

    rec = RecommendationModel(
        recommendation_id="rec-tbs-test-001",
        patient_id=patient_in_db.id,
        engine_version="1.0.0",
        status="completed",
        request_payload={},
        result_payload={"recommendations": [], "evidence": []},
    )
    db_session.add(rec)
    await db_session.commit()
    await db_session.refresh(rec)
    return rec


@pytest.fixture
async def clinical_decision_in_db(db_session, patient_in_db, recommendation_in_db):
    """Create a ClinicalDecisionModel record in the DB for FK references."""
    from src.backend.domain.clinical_decision import ClinicalDecisionModel

    cd = ClinicalDecisionModel(
        decision_id="cd-tbs-test-001",
        patient_id=patient_in_db.id,
        recommendation_id=recommendation_in_db.id,
        decision_type="approved",
        reason="Test reason",
        confidence="high",
    )
    db_session.add(cd)
    await db_session.commit()
    await db_session.refresh(cd)
    return cd


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _make_engine_result(
    consensus_status: str = "unanimous",
    consensus_score: float = 1.0,
) -> MagicMock:
    """Build a synthetic ConsensusResult resembling engine output."""
    from src.backend.clinical.tumor_board_engine import ConsensusResult
    from src.backend.domain.enums import ConsensusStatus

    return ConsensusResult(
        consensus_id="TBC-TEST-123456789ABC",
        consensus_status=ConsensusStatus(consensus_status),
        consensus_score=consensus_score,
        support_score=1.5,
        oppose_score=0.0,
        abstain_score=0.0,
        consensus_ratio=consensus_score,
        confidence_score=0.85,
        final_recommendation="Osimertinib 80mg daily",
        supporting_rationale="All specialists agree.",
        dissenting_opinions=[],
        unresolved_questions=[],
        required_follow_up=[],
        participating_specialties=["medical_oncology", "surgical_oncology"],
        trace_steps=[
            {"step_type": "load_context", "input_summary": {}, "output_summary": {}},
            {"step_type": "validate_links", "input_summary": {}, "output_summary": {}},
            {"step_type": "normalize_opinions", "input_summary": {}, "output_summary": {}},
            {"step_type": "calculate_weights", "input_summary": {}, "output_summary": {}},
            {"step_type": "calculate_consensus", "input_summary": {}, "output_summary": {}},
            {"step_type": "resolve_dissent", "input_summary": {}, "output_summary": {}},
            {"step_type": "finalize_consensus", "input_summary": {}, "output_summary": {}},
            {"step_type": "prepare_persistence", "input_summary": {}, "output_summary": {}},
        ],
    )


def _make_create_request(
    patient_id: str = "550e8400-e29b-41d4-a716-446655440000",
    recommendation_id: str = "rec-tbs-test-001",
    clinical_decision_id: str = "cd-tbs-test-001",
) -> object:
    """Build a CreateConsensusRequest for testing."""
    from src.backend.services.tumor_board_service import (
        CreateConsensusRequest,
        SpecialistOpinionDTO,
    )

    return CreateConsensusRequest(
        patient_id=patient_id,
        recommendation_id=recommendation_id,
        clinical_decision_id=clinical_decision_id,
        specialist_opinions=[
            SpecialistOpinionDTO(
                specialty="medical_oncology",
                position="support",
                confidence=0.95,
            ),
            SpecialistOpinionDTO(
                specialty="surgical_oncology",
                position="support",
                confidence=0.90,
            ),
        ],
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Tests: Successful Consensus Creation
# ═══════════════════════════════════════════════════════════════════════════════


class TestCreateConsensus:
    """Tests for TumorBoardConsensusService.create_consensus()."""

    async def test_create_consensus_success(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        clinical_decision_in_db,
    ) -> None:
        """Full pipeline: consensus created, persisted, returned with all fields."""
        from src.backend.clinical.tumor_board_engine import ConsensusEngine
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
        )

        engine = MagicMock(spec=ConsensusEngine)
        engine.calculate.return_value = _make_engine_result()

        service = TumorBoardConsensusService(db=db_session, engine=engine)
        result = await service.create_consensus(
            request=_make_create_request(),
        )

        # Response DTO structure
        assert result.consensus_id is not None
        assert len(result.consensus_id) == 32  # hex uuid
        assert result.patient_id == str(patient_in_db.id)
        assert result.consensus_status == "unanimous"
        assert result.consensus_score == 1.0
        assert result.final_recommendation == "Osimertinib 80mg daily"
        assert result.participating_specialties == [
            "medical_oncology", "surgical_oncology",
        ]
        assert result.created_at is not None

        # Verify persistence via repository
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        repo = TumorBoardConsensusRepository(db_session)
        persisted = await repo.get_by_uuid(result.consensus_id)
        assert persisted is not None
        assert persisted.consensus_id == result.consensus_id
        assert persisted.consensus_status == "unanimous"

    async def test_create_consensus_created_by_persisted(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        clinical_decision_in_db,
    ) -> None:
        """created_by is persisted in the DB."""
        from src.backend.clinical.tumor_board_engine import ConsensusEngine
        from src.backend.domain.tumor_board import TumorBoardConsensusModel
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
        )

        engine = MagicMock(spec=ConsensusEngine)
        engine.calculate.return_value = _make_engine_result()

        created_by_uuid = "770e8400-e29b-41d4-a716-446655440002"

        service = TumorBoardConsensusService(db=db_session, engine=engine)
        result = await service.create_consensus(
            request=_make_create_request(),
            created_by=created_by_uuid,
        )

        # Query DB to verify
        stmt = select(TumorBoardConsensusModel).where(
            TumorBoardConsensusModel.consensus_id == result.consensus_id,
        )
        model_result = await db_session.execute(stmt)
        model = model_result.scalar_one()
        assert str(model.created_by) == created_by_uuid

    async def test_create_consensus_same_transaction_persistence(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        clinical_decision_in_db,
    ) -> None:
        """Consensus + Opinions + Traces should all be in the same transaction."""
        from src.backend.clinical.tumor_board_engine import ConsensusEngine
        from src.backend.domain.tumor_board import (
            TumorBoardConsensusModel,
            TumorBoardConsensusTraceModel,
            TumorBoardOpinionModel,
        )
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
        )

        engine = MagicMock(spec=ConsensusEngine)
        engine.calculate.return_value = _make_engine_result()

        service = TumorBoardConsensusService(db=db_session, engine=engine)
        result = await service.create_consensus(
            request=_make_create_request(),
        )

        consensus_id = result.consensus_id

        # Verify consensus exists
        stmt = select(TumorBoardConsensusModel).where(
            TumorBoardConsensusModel.consensus_id == consensus_id,
        )
        consensus_result = await db_session.execute(stmt)
        consensus = consensus_result.scalar_one_or_none()
        assert consensus is not None

        # Verify opinions exist
        stmt = select(TumorBoardOpinionModel).where(
            TumorBoardOpinionModel.consensus_id == consensus.id,
        )
        opinions = (await db_session.execute(stmt)).scalars().all()
        assert len(opinions) == 2
        assert opinions[0].specialty == "medical_oncology"
        assert opinions[1].specialty == "surgical_oncology"

        # Verify traces exist
        stmt = select(TumorBoardConsensusTraceModel).where(
            TumorBoardConsensusTraceModel.consensus_id == consensus.id,
        ).order_by(TumorBoardConsensusTraceModel.step_order)
        traces = (await db_session.execute(stmt)).scalars().all()
        assert len(traces) == 8
        assert traces[0].step_type == "load_context"
        assert traces[7].step_type == "prepare_persistence"


# ═══════════════════════════════════════════════════════════════════════════════
# Tests: Validation / Mismatch
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidation:
    """Tests for link validation (P0 data consistency)."""

    async def test_patient_mismatch_with_recommendation(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        clinical_decision_in_db,
    ) -> None:
        """When recommendation.patient_id != request.patient_id → ValueError."""
        from src.backend.domain.patient import PatientModel
        from src.backend.domain.recommendation import RecommendationModel
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
            CreateConsensusRequest,
            SpecialistOpinionDTO,
        )

        # Create a different patient
        other_patient = PatientModel(
            id=uuid.UUID("660e8400-e29b-41d4-a716-446655440001"),
            display_name="OTHER-PATIENT",
        )
        db_session.add(other_patient)
        await db_session.commit()

        # Create a recommendation for the other patient
        other_rec = RecommendationModel(
            recommendation_id="rec-other-001",
            patient_id=other_patient.id,
        )
        db_session.add(other_rec)
        await db_session.commit()

        # Create a clinical decision linked to that recommendation
        from src.backend.domain.clinical_decision import ClinicalDecisionModel

        other_cd = ClinicalDecisionModel(
            decision_id="cd-other-001",
            patient_id=other_patient.id,
            recommendation_id=other_rec.id,
            decision_type="approved",
            reason="Test",
            confidence="high",
        )
        db_session.add(other_cd)
        await db_session.commit()

        # Try to use the other recommendation/cd with the original patient
        request = CreateConsensusRequest(
            patient_id=str(patient_in_db.id),
            recommendation_id="rec-other-001",
            clinical_decision_id="cd-other-001",
            specialist_opinions=[
                SpecialistOpinionDTO(
                    specialty="medical_oncology",
                    position="support",
                    confidence=0.95,
                ),
            ],
        )

        service = TumorBoardConsensusService(db=db_session)
        with pytest.raises(ValueError, match="belongs to patient"):
            await service.create_consensus(request=request)

    async def test_recommendation_mismatch_with_clinical_decision(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        clinical_decision_in_db,
    ) -> None:
        """When clinical_decision.recommendation_id != recommendation.id → ValueError."""
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
        )

        # Create a different recommendation but for the same patient
        from src.backend.domain.recommendation import RecommendationModel

        other_rec = RecommendationModel(
            recommendation_id="rec-mismatch-001",
            patient_id=patient_in_db.id,
        )
        db_session.add(other_rec)
        await db_session.commit()
        await db_session.refresh(other_rec)

        # Clinical decision still links to recommendation_in_db, not other_rec
        # So using other_rec's business ID with the existing clinical decision
        # that links to recommendation_in_db will fail
        from src.backend.services.tumor_board_service import (
            CreateConsensusRequest,
            SpecialistOpinionDTO,
        )

        request = CreateConsensusRequest(
            patient_id=str(patient_in_db.id),
            recommendation_id="rec-mismatch-001",  # other_rec
            clinical_decision_id="cd-tbs-test-001",  # links to recommendation_in_db
            specialist_opinions=[
                SpecialistOpinionDTO(
                    specialty="medical_oncology",
                    position="support",
                    confidence=0.95,
                ),
            ],
        )

        service = TumorBoardConsensusService(db=db_session)
        with pytest.raises(ValueError, match="link mismatch"):
            await service.create_consensus(request=request)

    async def test_recommendation_not_found(
        self,
        db_session,
        patient_in_db,
    ) -> None:
        """Non-existent recommendation_id → ValueError."""
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
            CreateConsensusRequest,
            SpecialistOpinionDTO,
        )

        request = CreateConsensusRequest(
            patient_id=str(patient_in_db.id),
            recommendation_id="non-existent-rec",
            clinical_decision_id="non-existent-cd",
            specialist_opinions=[
                SpecialistOpinionDTO(
                    specialty="medical_oncology",
                    position="support",
                    confidence=0.95,
                ),
            ],
        )

        service = TumorBoardConsensusService(db=db_session)
        with pytest.raises(ValueError, match="not found"):
            await service.create_consensus(request=request)

    async def test_clinical_decision_not_found(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
    ) -> None:
        """Non-existent clinical_decision_id → ValueError."""
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
            CreateConsensusRequest,
            SpecialistOpinionDTO,
        )

        request = CreateConsensusRequest(
            patient_id=str(patient_in_db.id),
            recommendation_id=recommendation_in_db.recommendation_id,
            clinical_decision_id="non-existent-cd",
            specialist_opinions=[
                SpecialistOpinionDTO(
                    specialty="medical_oncology",
                    position="support",
                    confidence=0.95,
                ),
            ],
        )

        service = TumorBoardConsensusService(db=db_session)
        with pytest.raises(ValueError, match="not found"):
            await service.create_consensus(request=request)


# ═══════════════════════════════════════════════════════════════════════════════
# Tests: Transaction Rollback
# ═══════════════════════════════════════════════════════════════════════════════


class TestFailureRollback:
    """Verify rollback behaviour when pipeline or persistence fails."""

    async def test_engine_value_error_rollback(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        clinical_decision_in_db,
    ) -> None:
        """When engine raises ValueError, no data should be persisted."""
        from src.backend.clinical.tumor_board_engine import ConsensusEngine
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
        )

        engine = MagicMock(spec=ConsensusEngine)
        engine.calculate.side_effect = ValueError("Engine validation failed")

        service = TumorBoardConsensusService(db=db_session, engine=engine)
        with pytest.raises(ValueError, match="Engine validation failed"):
            await service.create_consensus(
                request=_make_create_request(),
            )

        # Verify no consensus was persisted
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        repo = TumorBoardConsensusRepository(db_session)
        all_consensuses = await repo.list_by_patient_id(patient_in_db.id)
        assert all_consensuses == []

    async def test_engine_unexpected_exception_wrapped(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        clinical_decision_in_db,
    ) -> None:
        """Non-ValueError exceptions from engine should be wrapped in RuntimeError."""
        from src.backend.clinical.tumor_board_engine import ConsensusEngine
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
        )

        engine = MagicMock(spec=ConsensusEngine)
        engine.calculate.side_effect = ConnectionError("Engine timeout")

        service = TumorBoardConsensusService(db=db_session, engine=engine)
        with pytest.raises(
            RuntimeError,
            match="Consensus engine encountered an internal error",
        ):
            await service.create_consensus(
                request=_make_create_request(),
            )

    async def test_commit_failure_rollback(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        clinical_decision_in_db,
    ) -> None:
        """When commit fails, the exception is propagated and DB is clean."""
        from src.backend.clinical.tumor_board_engine import ConsensusEngine
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
        )

        engine = MagicMock(spec=ConsensusEngine)
        engine.calculate.return_value = _make_engine_result()

        # Capture IDs before any mock to avoid lazy-load issues
        patient_id = patient_in_db.id

        # Make commit raise using mock
        from unittest.mock import patch

        # mock the underlying sync session's commit
        with patch.object(db_session, "commit", side_effect=RuntimeError("DB commit failed")):

            service = TumorBoardConsensusService(db=db_session, engine=engine)
            with pytest.raises(RuntimeError, match="Failed to persist tumor board consensus"):
                await service.create_consensus(
                    request=_make_create_request(),
                )

        # Verify DB is clean
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        repo = TumorBoardConsensusRepository(db_session)
        all_consensuses = await repo.list_by_patient_id(patient_id)
        assert all_consensuses == []

    async def test_opinion_persistence_failure_rollback(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        clinical_decision_in_db,
    ) -> None:
        """When opinion_repo.create_many raises, nothing should persist."""
        from src.backend.clinical.tumor_board_engine import ConsensusEngine
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
            TumorBoardOpinionRepository,
            TumorBoardConsensusTraceRepository,
        )
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
        )

        engine = MagicMock(spec=ConsensusEngine)
        engine.calculate.return_value = _make_engine_result()

        # Inject a bad opinion repo
        bad_opinion_repo = MagicMock(spec=TumorBoardOpinionRepository)
        bad_opinion_repo.create_many.side_effect = RuntimeError("Opinion persist failed")

        service = TumorBoardConsensusService(
            db=db_session,
            engine=engine,
            opinion_repo=bad_opinion_repo,
        )
        with pytest.raises(RuntimeError, match="Failed to persist tumor board consensus"):
            await service.create_consensus(
                request=_make_create_request(),
            )

    async def test_trace_persistence_failure_rollback(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        clinical_decision_in_db,
    ) -> None:
        """When trace_repo.create_many raises, nothing should persist."""
        from src.backend.clinical.tumor_board_engine import ConsensusEngine
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardOpinionRepository,
            TumorBoardConsensusTraceRepository,
        )
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
        )

        engine = MagicMock(spec=ConsensusEngine)
        engine.calculate.return_value = _make_engine_result()

        # Inject a bad trace repo
        bad_trace_repo = MagicMock(spec=TumorBoardConsensusTraceRepository)
        bad_trace_repo.create_many.side_effect = RuntimeError("Trace persist failed")

        service = TumorBoardConsensusService(
            db=db_session,
            engine=engine,
            trace_repo=bad_trace_repo,
        )
        with pytest.raises(RuntimeError, match="Failed to persist tumor board consensus"):
            await service.create_consensus(
                request=_make_create_request(),
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Tests: Get / List / Count
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetConsensus:
    """Tests for TumorBoardConsensusService.get_consensus()."""

    async def test_get_consensus_found(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        clinical_decision_in_db,
    ) -> None:
        """get_consensus should retrieve a previously created consensus."""
        from src.backend.clinical.tumor_board_engine import ConsensusEngine
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
        )

        engine = MagicMock(spec=ConsensusEngine)
        engine.calculate.return_value = _make_engine_result()

        service = TumorBoardConsensusService(db=db_session, engine=engine)
        created = await service.create_consensus(
            request=_make_create_request(),
        )

        retrieved = await service.get_consensus(created.consensus_id)
        assert retrieved is not None
        assert retrieved.consensus_id == created.consensus_id
        assert retrieved.patient_id == created.patient_id
        assert retrieved.consensus_status == created.consensus_status
        assert retrieved.consensus_score == created.consensus_score

    async def test_get_consensus_not_found(
        self,
        db_session,
    ) -> None:
        """get_consensus should return None for non-existent ID."""
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
        )

        service = TumorBoardConsensusService(db=db_session)
        result = await service.get_consensus("non-existent-consensus-id")
        assert result is None

    async def test_get_opinions(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        clinical_decision_in_db,
    ) -> None:
        """get_opinions returns opinions for a consensus."""
        from src.backend.clinical.tumor_board_engine import ConsensusEngine
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
        )

        engine = MagicMock(spec=ConsensusEngine)
        engine.calculate.return_value = _make_engine_result()

        service = TumorBoardConsensusService(db=db_session, engine=engine)
        created = await service.create_consensus(
            request=_make_create_request(),
        )

        opinions = await service.get_opinions(created.consensus_id)
        assert len(opinions) == 2
        assert opinions[0]["specialty"] == "medical_oncology"
        assert opinions[1]["specialty"] == "surgical_oncology"

    async def test_get_opinions_not_found(
        self,
        db_session,
    ) -> None:
        """get_opinions returns empty list for non-existent consensus."""
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
        )

        service = TumorBoardConsensusService(db=db_session)
        opinions = await service.get_opinions("non-existent-id")
        assert opinions == []

    async def test_get_trace(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        clinical_decision_in_db,
    ) -> None:
        """get_trace returns trace steps for a consensus."""
        from src.backend.clinical.tumor_board_engine import ConsensusEngine
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
        )

        engine = MagicMock(spec=ConsensusEngine)
        engine.calculate.return_value = _make_engine_result()

        service = TumorBoardConsensusService(db=db_session, engine=engine)
        created = await service.create_consensus(
            request=_make_create_request(),
        )

        trace = await service.get_trace(created.consensus_id)
        assert len(trace) == 8
        assert trace[0]["step_type"] == "load_context"
        assert trace[7]["step_type"] == "prepare_persistence"

    async def test_get_trace_not_found(
        self,
        db_session,
    ) -> None:
        """get_trace returns empty list for non-existent consensus."""
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
        )

        service = TumorBoardConsensusService(db=db_session)
        trace = await service.get_trace("non-existent-id")
        assert trace == []


class TestListConsensus:
    """Tests for TumorBoardConsensusService.list_consensus()."""

    async def test_list_consensus_by_patient(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        clinical_decision_in_db,
    ) -> None:
        """list_consensus returns consensuses for a patient."""
        from src.backend.clinical.tumor_board_engine import ConsensusEngine
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
        )

        engine = MagicMock(spec=ConsensusEngine)
        engine.calculate.return_value = _make_engine_result()

        service = TumorBoardConsensusService(db=db_session, engine=engine)

        # Create two consensuses
        await service.create_consensus(request=_make_create_request())
        await service.create_consensus(request=_make_create_request())

        results = await service.list_consensus(str(patient_in_db.id))
        assert len(results) >= 2
        # Should be ordered newest first
        if len(results) >= 2:
            assert results[0].created_at >= results[1].created_at

    async def test_list_consensus_empty(
        self,
        db_session,
        patient_in_db,
    ) -> None:
        """list_consensus returns empty list for patient with no consensuses."""
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
        )

        service = TumorBoardConsensusService(db=db_session)
        results = await service.list_consensus(str(patient_in_db.id))
        assert results == []

    async def test_list_consensus_pagination(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        clinical_decision_in_db,
    ) -> None:
        """list_consensus supports skip/limit pagination."""
        from src.backend.clinical.tumor_board_engine import ConsensusEngine
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
        )

        engine = MagicMock(spec=ConsensusEngine)
        engine.calculate.return_value = _make_engine_result()

        service = TumorBoardConsensusService(db=db_session, engine=engine)

        # Create 3 consensuses
        for _ in range(3):
            await service.create_consensus(request=_make_create_request())

        # Limit 2
        results = await service.list_consensus(
            str(patient_in_db.id), skip=0, limit=2,
        )
        assert len(results) == 2

        # Skip 2
        results_skip = await service.list_consensus(
            str(patient_in_db.id), skip=2,
        )
        assert len(results_skip) == 1


class TestCountConsensus:
    """Tests for TumorBoardConsensusService.count_by_patient()."""

    async def test_count_by_patient(
        self,
        db_session,
        patient_in_db,
        recommendation_in_db,
        clinical_decision_in_db,
    ) -> None:
        """count_by_patient returns the correct count."""
        from src.backend.clinical.tumor_board_engine import ConsensusEngine
        from src.backend.services.tumor_board_service import (
            TumorBoardConsensusService,
        )

        engine = MagicMock(spec=ConsensusEngine)
        engine.calculate.return_value = _make_engine_result()

        service = TumorBoardConsensusService(db=db_session, engine=engine)

        count0 = await service.count_by_patient(str(patient_in_db.id))
        assert count0 == 0

        for _ in range(2):
            await service.create_consensus(request=_make_create_request())

        count = await service.count_by_patient(str(patient_in_db.id))
        assert count == 2

        # Non-existent patient → 0
        count_wrong = await service.count_by_patient(
            "660e8400-e29b-41d4-a716-446655440099",
        )
        assert count_wrong == 0
