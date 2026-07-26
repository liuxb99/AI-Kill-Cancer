"""
Tests for Tumor Board repositories (Phase 3C).

Covers ``TumorBoardConsensusRepository``, ``TumorBoardOpinionRepository``,
and ``TumorBoardConsensusTraceRepository`` — CRUD and domain-specific queries.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base


@pytest.fixture
async def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def patient(db_session):
    """Create a minimal Patient for FK references."""
    from src.backend.domain.patient import PatientModel

    p = PatientModel(display_name="TBR-TEST-PATIENT")
    db_session.add(p)
    await db_session.flush()
    return p


@pytest.fixture
async def recommendation(db_session, patient):
    """Create a minimal Recommendation for FK references."""
    from src.backend.domain.recommendation import RecommendationModel

    rec = RecommendationModel(
        recommendation_id="tbr-rec-001",
        patient_id=patient.id,
    )
    db_session.add(rec)
    await db_session.flush()
    return rec


@pytest.fixture
async def clinical_decision(db_session, patient, recommendation):
    """Create a minimal ClinicalDecision for FK references."""
    from src.backend.domain.clinical_decision import ClinicalDecisionModel

    cd = ClinicalDecisionModel(
        decision_id="tbr-cd-001",
        patient_id=patient.id,
        recommendation_id=recommendation.id,
        decision_type="treatment_selection",
        reason="Test",
        confidence="high",
    )
    db_session.add(cd)
    await db_session.flush()
    return cd


# ═══════════════════════════════════════════════════════════════════════════════
# TumorBoardConsensusRepository Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTumorBoardConsensusRepository:
    """Tests for TumorBoardConsensusRepository — CRUD and queries."""

    async def _create_consensus(
        self,
        db_session,
        patient,
        recommendation=None,
        clinical_decision=None,
        consensus_id="tbr-consensus-001",
    ):
        """Helper to create a consensus model via repository."""
        from src.backend.domain.tumor_board import TumorBoardConsensusModel
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        repo = TumorBoardConsensusRepository(db_session)
        model = TumorBoardConsensusModel(
            consensus_id=consensus_id,
            patient_id=patient.id,
            recommendation_id=recommendation.id if recommendation else None,
            clinical_decision_id=clinical_decision.id if clinical_decision else None,
            consensus_status="unanimous",
            consensus_score=1.0,
            participating_specialties=["medical_oncology"],
        )
        await repo.create(model)
        return model

    async def test_create(
        self,
        db_session,
        patient,
        recommendation,
        clinical_decision,
    ) -> None:
        """Repository.create() adds a consensus to the session."""
        from src.backend.domain.tumor_board import TumorBoardConsensusModel
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        repo = TumorBoardConsensusRepository(db_session)
        model = TumorBoardConsensusModel(
            consensus_id="repo-create-tb",
            patient_id=patient.id,
            recommendation_id=recommendation.id,
            clinical_decision_id=clinical_decision.id,
            consensus_status="strong_consensus",
            consensus_score=0.85,
        )
        result = await repo.create(model)
        await db_session.flush()

        assert result is model
        assert result.id is not None
        assert result.consensus_id == "repo-create-tb"

        await db_session.commit()
        await db_session.refresh(result)
        assert result.consensus_status == "strong_consensus"
        assert result.consensus_score == 0.85

    async def test_get_by_uuid_found(
        self,
        db_session,
        patient,
    ) -> None:
        """get_by_uuid returns the matching model by consensus_id."""
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        model = await self._create_consensus(db_session, patient)
        await db_session.commit()

        repo = TumorBoardConsensusRepository(db_session)
        fetched = await repo.get_by_uuid("tbr-consensus-001")
        assert fetched is not None
        assert fetched.consensus_id == "tbr-consensus-001"
        assert str(fetched.id) == str(model.id)

    async def test_get_by_uuid_not_found(self, db_session) -> None:
        """get_by_uuid returns None for non-existent consensus_id."""
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        repo = TumorBoardConsensusRepository(db_session)
        result = await repo.get_by_uuid("non-existent-id")
        assert result is None

    async def test_get_by_id_found(
        self,
        db_session,
        patient,
    ) -> None:
        """get_by_id returns the matching model by primary key UUID string."""
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        model = await self._create_consensus(db_session, patient)
        await db_session.commit()

        repo = TumorBoardConsensusRepository(db_session)
        fetched = await repo.get_by_id(str(model.id))
        assert fetched is not None
        assert fetched.consensus_id == "tbr-consensus-001"

    async def test_get_by_id_not_found(self, db_session) -> None:
        """get_by_id returns None for non-existent UUID string."""
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        repo = TumorBoardConsensusRepository(db_session)
        result = await repo.get_by_id(str(uuid.uuid4()))
        assert result is None

    async def test_list_by_patient_id(
        self,
        db_session,
        patient,
    ) -> None:
        """list_by_patient_id returns consensuses for a specific patient."""
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        for i in range(3):
            await self._create_consensus(
                db_session, patient, consensus_id=f"tbr-list-pat-{i:02d}",
            )
        await db_session.commit()

        repo = TumorBoardConsensusRepository(db_session)
        results = await repo.list_by_patient_id(patient.id)
        assert len(results) == 3
        assert all(r.patient_id == patient.id for r in results)

    async def test_list_by_patient_id_empty(self, db_session) -> None:
        """list_by_patient_id returns empty list for non-existent patient."""
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        repo = TumorBoardConsensusRepository(db_session)
        results = await repo.list_by_patient_id(uuid.uuid4())
        assert results == []

    async def test_list_by_patient_id_pagination(
        self,
        db_session,
        patient,
    ) -> None:
        """list_by_patient_id supports skip and limit pagination."""
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        for i in range(5):
            await self._create_consensus(
                db_session, patient, consensus_id=f"tbr-page-{i:02d}",
            )
        await db_session.commit()

        repo = TumorBoardConsensusRepository(db_session)

        # With limit
        results = await repo.list_by_patient_id(patient.id, limit=3)
        assert len(results) == 3

        # With skip
        results_skip = await repo.list_by_patient_id(patient.id, skip=3)
        assert len(results_skip) == 2

        # Skip beyond total
        results_empty = await repo.list_by_patient_id(patient.id, skip=10)
        assert results_empty == []

    async def test_list_by_clinical_decision_id(
        self,
        db_session,
        patient,
        recommendation,
        clinical_decision,
    ) -> None:
        """list_by_clinical_decision_id returns consensuses linked to a CD."""
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        for i in range(2):
            await self._create_consensus(
                db_session,
                patient,
                recommendation=recommendation,
                clinical_decision=clinical_decision,
                consensus_id=f"tbr-cdlist-{i:02d}",
            )
        await db_session.commit()

        repo = TumorBoardConsensusRepository(db_session)
        results = await repo.list_by_clinical_decision_id(clinical_decision.id)
        assert len(results) == 2
        assert all(r.clinical_decision_id == clinical_decision.id for r in results)

    async def test_list_by_clinical_decision_id_empty(self, db_session) -> None:
        """list_by_clinical_decision_id returns empty list for no matches."""
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        repo = TumorBoardConsensusRepository(db_session)
        results = await repo.list_by_clinical_decision_id(uuid.uuid4())
        assert results == []

    async def test_count_by_patient_id_empty(self, db_session) -> None:
        """count_by_patient_id returns 0 when no consensuses exist."""
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        repo = TumorBoardConsensusRepository(db_session)
        count = await repo.count_by_patient_id(uuid.uuid4())
        assert count == 0

    async def test_count_by_patient_id_with_records(
        self,
        db_session,
        patient,
    ) -> None:
        """count_by_patient_id returns the correct count."""
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        for i in range(5):
            await self._create_consensus(
                db_session, patient, consensus_id=f"tbr-count-{i:02d}",
            )
        await db_session.commit()

        repo = TumorBoardConsensusRepository(db_session)
        count = await repo.count_by_patient_id(patient.id)
        assert count == 5

    async def test_count_by_patient_id_wrong_patient(
        self,
        db_session,
        patient,
    ) -> None:
        """count_by_patient_id returns 0 for unrelated patient."""
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        await self._create_consensus(db_session, patient)
        await db_session.commit()

        repo = TumorBoardConsensusRepository(db_session)
        count = await repo.count_by_patient_id(uuid.uuid4())
        assert count == 0

    async def test_create_with_json_fields(
        self,
        db_session,
        patient,
        recommendation,
        clinical_decision,
    ) -> None:
        """Repository persists JSON fields correctly."""
        from src.backend.domain.tumor_board import TumorBoardConsensusModel
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        repo = TumorBoardConsensusRepository(db_session)
        model = TumorBoardConsensusModel(
            consensus_id="tbr-json-001",
            patient_id=patient.id,
            recommendation_id=recommendation.id,
            clinical_decision_id=clinical_decision.id,
            consensus_status="split_decision",
            dissenting_opinions=[{"specialty": "pathology", "reason": "Disagree"}],
            participating_specialties=["med_onc", "surg_onc", "pathology"],
            unresolved_questions=["Need more data"],
            required_follow_up=["Schedule review"],
        )
        await repo.create(model)
        await db_session.commit()
        await db_session.refresh(model)

        assert model.dissenting_opinions == [{"specialty": "pathology", "reason": "Disagree"}]
        assert model.participating_specialties == ["med_onc", "surg_onc", "pathology"]
        assert model.unresolved_questions == ["Need more data"]
        assert model.required_follow_up == ["Schedule review"]

    async def test_transaction_rollback(self, db_session, patient) -> None:
        """If rolled back, no data should persist."""
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        repo = TumorBoardConsensusRepository(db_session)
        from src.backend.domain.tumor_board import TumorBoardConsensusModel

        model = TumorBoardConsensusModel(
            consensus_id="tbr-rollback",
            patient_id=patient.id,
        )
        await repo.create(model)

        await db_session.rollback()

        fetched = await repo.get_by_uuid("tbr-rollback")
        assert fetched is None


# ═══════════════════════════════════════════════════════════════════════════════
# TumorBoardOpinionRepository Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTumorBoardOpinionRepository:
    """Tests for TumorBoardOpinionRepository — CRUD for opinions."""

    async def _setup_consensus(self, db_session, patient):
        """Helper: create a consensus and return it."""
        from src.backend.domain.tumor_board import TumorBoardConsensusModel

        consensus = TumorBoardConsensusModel(
            consensus_id="tbr-opinion-repo",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.flush()
        return consensus

    async def test_create(self, db_session, patient) -> None:
        """OpinionRepository.create() adds an opinion to the session."""
        from src.backend.domain.tumor_board import TumorBoardOpinionModel
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardOpinionRepository,
        )

        consensus = await self._setup_consensus(db_session, patient)
        repo = TumorBoardOpinionRepository(db_session)

        opinion = TumorBoardOpinionModel(
            consensus_id=consensus.id,
            specialty="medical_oncology",
            position="support",
            confidence=0.95,
        )
        result = await repo.create(opinion)
        await db_session.flush()
        assert result is opinion
        assert result.id is not None
        await db_session.commit()

    async def test_create_many(self, db_session, patient) -> None:
        """OpinionRepository.create_many persists multiple opinions."""
        from src.backend.domain.tumor_board import (
            TumorBoardConsensusModel,
            TumorBoardOpinionModel,
        )
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardOpinionRepository,
        )

        consensus = TumorBoardConsensusModel(
            consensus_id="tbr-opinion-many",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.flush()

        repo = TumorBoardOpinionRepository(db_session)
        opinions = [
            TumorBoardOpinionModel(
                consensus_id=consensus.id,
                specialty=f"specialty_{i}",
                position="support" if i % 2 == 0 else "oppose",
                confidence=0.8,
            )
            for i in range(3)
        ]
        results = await repo.create_many(opinions)
        await db_session.commit()

        assert len(results) == 3
        assert all(o.id is not None for o in results)

    async def test_list_by_consensus_id(self, db_session, patient) -> None:
        """list_by_consensus_id returns all opinions for a consensus."""
        from src.backend.domain.tumor_board import (
            TumorBoardConsensusModel,
            TumorBoardOpinionModel,
        )
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardOpinionRepository,
        )

        consensus = TumorBoardConsensusModel(
            consensus_id="tbr-list-opinions",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.flush()

        repo = TumorBoardOpinionRepository(db_session)
        opinions = [
            TumorBoardOpinionModel(
                consensus_id=consensus.id,
                specialty=f"spec_{i}",
                position="support",
                confidence=0.8,
            )
            for i in range(3)
        ]
        await repo.create_many(opinions)
        await db_session.commit()

        results = await repo.list_by_consensus_id(consensus.id)
        assert len(results) == 3

    async def test_list_by_consensus_id_empty(self, db_session) -> None:
        """list_by_consensus_id returns empty list for no opinions."""
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardOpinionRepository,
        )

        repo = TumorBoardOpinionRepository(db_session)
        results = await repo.list_by_consensus_id(uuid.uuid4())
        assert results == []

    async def test_list_by_consensus_id_ordered(
        self,
        db_session,
        patient,
    ) -> None:
        """Opinions are ordered by created_at ascending."""
        from src.backend.domain.tumor_board import (
            TumorBoardConsensusModel,
            TumorBoardOpinionModel,
        )
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardOpinionRepository,
        )

        consensus = TumorBoardConsensusModel(
            consensus_id="tbr-order-opinions",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.flush()

        repo = TumorBoardOpinionRepository(db_session)
        opinions = [
            TumorBoardOpinionModel(
                consensus_id=consensus.id,
                specialty=f"spec_{i}",
                position="support",
                confidence=0.8,
            )
            for i in range(3)
        ]
        await repo.create_many(opinions)
        await db_session.commit()

        results = await repo.list_by_consensus_id(consensus.id)
        # Should be ordered by created_at ascending
        assert len(results) == 3

    async def test_transaction_rollback(self, db_session, patient) -> None:
        """If rolled back, no opinion data should persist."""
        from src.backend.domain.tumor_board import TumorBoardOpinionModel
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardOpinionRepository,
        )

        consensus = await self._setup_consensus(db_session, patient)
        repo = TumorBoardOpinionRepository(db_session)

        opinion = TumorBoardOpinionModel(
            consensus_id=consensus.id,
            specialty="radiology",
            position="abstain",
            confidence=0.5,
        )
        await repo.create(opinion)

        await db_session.rollback()

        results = await repo.list_by_consensus_id(consensus.id)
        assert results == []


# ═══════════════════════════════════════════════════════════════════════════════
# TumorBoardConsensusTraceRepository Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTumorBoardConsensusTraceRepository:
    """Tests for TumorBoardConsensusTraceRepository — CRUD for traces."""

    async def _setup_consensus(self, db_session, patient):
        """Helper: create a consensus and return it."""
        from src.backend.domain.tumor_board import TumorBoardConsensusModel

        consensus = TumorBoardConsensusModel(
            consensus_id="tbr-trace-repo",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.flush()
        return consensus

    async def test_create(self, db_session, patient) -> None:
        """TraceRepository.create() adds a trace to the session."""
        from src.backend.domain.tumor_board import TumorBoardConsensusTraceModel
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusTraceRepository,
        )

        consensus = await self._setup_consensus(db_session, patient)
        repo = TumorBoardConsensusTraceRepository(db_session)

        trace = TumorBoardConsensusTraceModel(
            trace_id="tbc-trace-create",
            consensus_id=consensus.id,
            step_order=1,
            step_type="load_context",
        )
        result = await repo.create(trace)
        await db_session.flush()
        assert result is trace
        assert result.id is not None
        await db_session.commit()

    async def test_create_many(self, db_session, patient) -> None:
        """TraceRepository.create_many persists multiple traces."""
        from src.backend.domain.tumor_board import (
            TumorBoardConsensusTraceModel,
        )
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusTraceRepository,
        )

        consensus = await self._setup_consensus(db_session, patient)
        repo = TumorBoardConsensusTraceRepository(db_session)

        traces = [
            TumorBoardConsensusTraceModel(
                trace_id="tbc-multi-001",
                consensus_id=consensus.id,
                step_order=i,
                step_type=f"step_{i}",
            )
            for i in range(3)
        ]
        results = await repo.create_many(traces)
        await db_session.commit()

        assert len(results) == 3
        assert all(t.id is not None for t in results)

    async def test_list_by_consensus_id(self, db_session, patient) -> None:
        """list_by_consensus_id returns all traces for a consensus, ordered."""
        from src.backend.domain.tumor_board import TumorBoardConsensusTraceModel
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusTraceRepository,
        )

        consensus = await self._setup_consensus(db_session, patient)
        repo = TumorBoardConsensusTraceRepository(db_session)

        for i in range(1, 4):
            trace = TumorBoardConsensusTraceModel(
                trace_id=f"tbc-list-{i:02d}",
                consensus_id=consensus.id,
                step_order=i,
                step_type=f"step_{i}",
            )
            await repo.create(trace)
        await db_session.commit()

        results = await repo.list_by_consensus_id(consensus.id)
        assert len(results) == 3
        assert results[0].step_order == 1
        assert results[1].step_order == 2
        assert results[2].step_order == 3

    async def test_list_by_consensus_id_empty(self, db_session) -> None:
        """list_by_consensus_id returns empty list for no traces."""
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusTraceRepository,
        )

        repo = TumorBoardConsensusTraceRepository(db_session)
        results = await repo.list_by_consensus_id(uuid.uuid4())
        assert results == []

    async def test_get_by_trace_id_found(self, db_session, patient) -> None:
        """get_by_trace_id returns all steps for a given trace_id."""
        from src.backend.domain.tumor_board import TumorBoardConsensusTraceModel
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusTraceRepository,
        )

        consensus = await self._setup_consensus(db_session, patient)
        repo = TumorBoardConsensusTraceRepository(db_session)

        for i in range(1, 4):
            trace = TumorBoardConsensusTraceModel(
                trace_id="tbc-get-by-trace",
                consensus_id=consensus.id,
                step_order=i,
                step_type=f"step_{i}",
            )
            await repo.create(trace)
        await db_session.commit()

        results = await repo.get_by_trace_id("tbc-get-by-trace")
        assert len(results) == 3
        assert results[0].step_order == 1

    async def test_get_by_trace_id_not_found(self, db_session) -> None:
        """get_by_trace_id returns empty list for non-existent trace_id."""
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusTraceRepository,
        )

        repo = TumorBoardConsensusTraceRepository(db_session)
        results = await repo.get_by_trace_id("non-existent-trace")
        assert results == []

    async def test_transaction_rollback(self, db_session, patient) -> None:
        """If rolled back, no trace data should persist."""
        from src.backend.domain.tumor_board import TumorBoardConsensusTraceModel
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusTraceRepository,
        )

        consensus = await self._setup_consensus(db_session, patient)
        repo = TumorBoardConsensusTraceRepository(db_session)

        trace = TumorBoardConsensusTraceModel(
            trace_id="tbc-rollback",
            consensus_id=consensus.id,
            step_order=1,
            step_type="test",
        )
        await repo.create(trace)

        await db_session.rollback()

        results = await repo.get_by_trace_id("tbc-rollback")
        assert results == []
