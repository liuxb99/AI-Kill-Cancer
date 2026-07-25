"""
Tests for Clinical Decision repositories.

Covers ``ClinicalDecisionRepository`` and ``ClinicalDecisionTraceRepository``.
"""
from __future__ import annotations

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

    p = PatientModel(display_name="CDR-TEST-PATIENT")
    db_session.add(p)
    await db_session.flush()
    return p


@pytest.fixture
async def recommendation(db_session, patient):
    """Create a minimal Recommendation for FK references."""
    from src.backend.domain.recommendation import RecommendationModel

    rec = RecommendationModel(
        recommendation_id="cdr-rec-001",
        patient_id=patient.id,
    )
    db_session.add(rec)
    await db_session.flush()
    return rec


class TestClinicalDecisionRepository:
    """Tests for ClinicalDecisionRepository — CRUD and queries."""

    async def test_create(self, db_session, patient):
        """Repository.create() adds a clinical decision to the session."""
        from src.backend.domain.clinical_decision import ClinicalDecisionModel
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
        )

        repo = ClinicalDecisionRepository(db_session)
        model = ClinicalDecisionModel(
            decision_id="repo-create-001",
            patient_id=patient.id,
            decision_type="treatment_selection",
            reason="EGFR L858R mutation",
            confidence="high",
        )
        result = await repo.create(model)
        await db_session.flush()

        assert result is model  # same instance returned
        assert result.id is not None
        assert result.decision_id == "repo-create-001"

        # Confirm it's actually in the DB
        await db_session.commit()
        await db_session.refresh(result)
        assert result.decision_type == "treatment_selection"
        assert result.reason == "EGFR L858R mutation"

    async def test_get_by_id_found(self, db_session, patient):
        """get_by_id returns the matching model by decision_id."""
        from src.backend.domain.clinical_decision import ClinicalDecisionModel
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
        )

        repo = ClinicalDecisionRepository(db_session)
        model = ClinicalDecisionModel(
            decision_id="get-by-id-found",
            patient_id=patient.id,
            decision_type="test",
            reason="Found test",
            confidence="high",
        )
        await repo.create(model)
        await db_session.commit()

        fetched = await repo.get_by_id("get-by-id-found")
        assert fetched is not None
        assert fetched.decision_id == "get-by-id-found"
        assert str(fetched.id) == str(model.id)

    async def test_get_by_id_not_found(self, db_session):
        """get_by_id returns None for non-existent decision_id."""
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
        )

        repo = ClinicalDecisionRepository(db_session)
        result = await repo.get_by_id("non-existent-id")
        assert result is None

    async def test_get_by_uuid_found(self, db_session, patient):
        """get_by_uuid returns the matching model by primary key UUID."""
        from src.backend.domain.clinical_decision import ClinicalDecisionModel
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
        )

        repo = ClinicalDecisionRepository(db_session)
        model = ClinicalDecisionModel(
            decision_id="get-by-uuid-found",
            patient_id=patient.id,
            decision_type="test",
            reason="UUID lookup",
            confidence="medium",
        )
        await repo.create(model)
        await db_session.commit()

        fetched = await repo.get_by_uuid(model.id)
        assert fetched is not None
        assert fetched.decision_id == "get-by-uuid-found"
        assert fetched.id == model.id

    async def test_get_by_uuid_not_found(self, db_session):
        """get_by_uuid returns None for non-existent UUID."""
        import uuid

        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
        )

        repo = ClinicalDecisionRepository(db_session)
        result = await repo.get_by_uuid(uuid.uuid4())
        assert result is None

    async def test_list_by_patient_id(self, db_session, patient):
        """list_by_patient_id returns decisions for a specific patient."""
        from src.backend.domain.clinical_decision import ClinicalDecisionModel
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
        )

        repo = ClinicalDecisionRepository(db_session)
        for i in range(3):
            model = ClinicalDecisionModel(
                decision_id=f"list-pat-{i:02d}",
                patient_id=patient.id,
                decision_type="test",
                reason=f"Decision {i}",
                confidence="high",
            )
            await repo.create(model)
        await db_session.commit()

        results = await repo.list_by_patient_id(patient.id)
        assert len(results) == 3
        # Should be ordered by created_at desc (newest first)
        assert all(r.patient_id == patient.id for r in results)

    async def test_list_by_patient_id_empty(self, db_session):
        """list_by_patient_id returns empty list for non-existent patient."""
        import uuid

        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
        )

        repo = ClinicalDecisionRepository(db_session)
        results = await repo.list_by_patient_id(uuid.uuid4())
        assert results == []

    async def test_list_by_patient_id_pagination(self, db_session, patient):
        """list_by_patient_id supports skip and limit pagination."""
        from src.backend.domain.clinical_decision import ClinicalDecisionModel
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
        )

        repo = ClinicalDecisionRepository(db_session)
        for i in range(5):
            model = ClinicalDecisionModel(
                decision_id=f"page-{i:02d}",
                patient_id=patient.id,
                decision_type="test",
                reason=f"Pagination {i}",
                confidence="low",
            )
            await repo.create(model)
        await db_session.commit()

        # With limit
        results = await repo.list_by_patient_id(patient.id, limit=3)
        assert len(results) == 3

        # With skip
        results_skip = await repo.list_by_patient_id(patient.id, skip=3)
        assert len(results_skip) == 2

        # Skip beyond total
        results_empty = await repo.list_by_patient_id(patient.id, skip=10)
        assert results_empty == []

    async def test_list_by_recommendation_id(self, db_session, patient, recommendation):
        """list_by_recommendation_id returns decisions linked to a recommendation."""
        from src.backend.domain.clinical_decision import ClinicalDecisionModel
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
        )

        repo = ClinicalDecisionRepository(db_session)
        for i in range(2):
            model = ClinicalDecisionModel(
                decision_id=f"list-rec-{i:02d}",
                patient_id=patient.id,
                recommendation_id=recommendation.id,
                decision_type="test",
                reason=f"Rec decision {i}",
                confidence="high",
            )
            await repo.create(model)
        await db_session.commit()

        results = await repo.list_by_recommendation_id(recommendation.id)
        assert len(results) == 2
        assert all(r.recommendation_id == recommendation.id for r in results)

    async def test_list_by_recommendation_id_empty(self, db_session):
        """list_by_recommendation_id returns empty list for non-existent rec."""
        import uuid

        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
        )

        repo = ClinicalDecisionRepository(db_session)
        results = await repo.list_by_recommendation_id(uuid.uuid4())
        assert results == []

    async def test_create_with_json_fields(self, db_session, patient):
        """Repository persists JSON fields correctly."""
        from src.backend.domain.clinical_decision import ClinicalDecisionModel
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
        )

        repo = ClinicalDecisionRepository(db_session)
        model = ClinicalDecisionModel(
            decision_id="repo-json-001",
            patient_id=patient.id,
            decision_type="treatment_selection",
            reason="JSON test",
            confidence="high",
            evidence_summary={"sources": ["CIViC"], "count": 5},
            alternatives=[{"drug": "Osimertinib", "rank": 1}],
            contraindications=[{"drug": "Pembrolizumab", "reason": "PD-L1 negative"}],
        )
        await repo.create(model)
        await db_session.commit()
        await db_session.refresh(model)

        assert model.evidence_summary == {"sources": ["CIViC"], "count": 5}
        assert model.alternatives[0]["drug"] == "Osimertinib"
        assert model.contraindications[0]["reason"] == "PD-L1 negative"

    async def test_transaction_rollback(self, db_session, patient):
        """If rolled back, no data should persist."""
        from src.backend.domain.clinical_decision import ClinicalDecisionModel
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
        )

        repo = ClinicalDecisionRepository(db_session)
        model = ClinicalDecisionModel(
            decision_id="rollback-test",
            patient_id=patient.id,
            decision_type="test",
            reason="Should not persist",
            confidence="low",
        )
        await repo.create(model)

        # Rollback explicitly
        await db_session.rollback()

        # Verify it's not in DB
        fetched = await repo.get_by_id("rollback-test")
        assert fetched is None


class TestClinicalDecisionTraceRepository:
    """Tests for ClinicalDecisionTraceRepository — CRUD for trace records."""

    async def _setup_decision(self, db_session, patient):
        """Helper: create a clinical decision and return it."""
        from src.backend.domain.clinical_decision import ClinicalDecisionModel

        decision = ClinicalDecisionModel(
            decision_id="trace-repo-dec",
            patient_id=patient.id,
            decision_type="test",
            reason="Trace repo helper",
            confidence="high",
        )
        db_session.add(decision)
        await db_session.flush()
        return decision

    async def test_create(self, db_session, patient):
        """TraceRepository.create() adds a trace to the session."""
        from src.backend.domain.clinical_decision import ClinicalDecisionTraceModel
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionTraceRepository,
        )

        decision = await self._setup_decision(db_session, patient)
        repo = ClinicalDecisionTraceRepository(db_session)

        trace = ClinicalDecisionTraceModel(
            trace_id="trace-create-001",
            clinical_decision_id=decision.id,
            step_order=1,
            step_type="evidence_collection",
            input_summary={"variants": ["EGFR"]},
            output_summary={"count": 3},
        )
        result = await repo.create(trace)
        await db_session.flush()
        assert result is trace
        assert result.id is not None
        await db_session.commit()

    async def test_get_by_decision_id(self, db_session, patient):
        """get_by_decision_id returns all traces for a decision, ordered."""
        from src.backend.domain.clinical_decision import ClinicalDecisionTraceModel
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionTraceRepository,
        )

        decision = await self._setup_decision(db_session, patient)
        repo = ClinicalDecisionTraceRepository(db_session)

        for i in range(1, 4):
            trace = ClinicalDecisionTraceModel(
                trace_id=f"trace-by-dec-{i:02d}",
                clinical_decision_id=decision.id,
                step_order=i,
                step_type=f"step_{i}",
            )
            await repo.create(trace)
        await db_session.commit()

        results = await repo.get_by_decision_id(decision.id)
        assert len(results) == 3
        assert results[0].step_order == 1
        assert results[1].step_order == 2
        assert results[2].step_order == 3

    async def test_get_by_decision_id_empty(self, db_session):
        """get_by_decision_id returns empty list for no traces."""
        import uuid

        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionTraceRepository,
        )

        repo = ClinicalDecisionTraceRepository(db_session)
        results = await repo.get_by_decision_id(uuid.uuid4())
        assert results == []

    async def test_get_by_recommendation_id(self, db_session, patient, recommendation):
        """get_by_recommendation_id returns traces linked to a recommendation."""
        from src.backend.domain.clinical_decision import (
            ClinicalDecisionModel,
            ClinicalDecisionTraceModel,
        )
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionTraceRepository,
        )

        decision = ClinicalDecisionModel(
            decision_id="trace-rec-link",
            patient_id=patient.id,
            recommendation_id=recommendation.id,
            decision_type="test",
            reason="Link to recommendation",
            confidence="high",
        )
        db_session.add(decision)
        await db_session.flush()

        repo = ClinicalDecisionTraceRepository(db_session)
        trace = ClinicalDecisionTraceModel(
            trace_id="trace-rec-001",
            clinical_decision_id=decision.id,
            recommendation_id=recommendation.id,
            step_order=1,
            step_type="test",
        )
        await repo.create(trace)
        await db_session.commit()

        results = await repo.get_by_recommendation_id(recommendation.id)
        assert len(results) == 1
        assert results[0].trace_id == "trace-rec-001"

    async def test_get_by_recommendation_id_empty(self, db_session):
        """get_by_recommendation_id returns empty list for no matches."""
        import uuid

        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionTraceRepository,
        )

        repo = ClinicalDecisionTraceRepository(db_session)
        results = await repo.get_by_recommendation_id(uuid.uuid4())
        assert results == []

    async def test_get_by_trace_id_found(self, db_session, patient):
        """get_by_trace_id returns the matching trace by trace_id string."""
        from src.backend.domain.clinical_decision import ClinicalDecisionTraceModel
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionTraceRepository,
        )

        decision = await self._setup_decision(db_session, patient)
        repo = ClinicalDecisionTraceRepository(db_session)

        trace = ClinicalDecisionTraceModel(
            trace_id="trace-lookup-001",
            clinical_decision_id=decision.id,
            step_order=1,
            step_type="test",
        )
        await repo.create(trace)
        await db_session.commit()

        fetched = await repo.get_by_trace_id("trace-lookup-001")
        assert fetched is not None
        assert fetched.trace_id == "trace-lookup-001"

    async def test_get_by_trace_id_not_found(self, db_session):
        """get_by_trace_id returns None for non-existent trace_id."""
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionTraceRepository,
        )

        repo = ClinicalDecisionTraceRepository(db_session)
        result = await repo.get_by_trace_id("non-existent-trace")
        assert result is None

    async def test_transaction_rollback(self, db_session, patient):
        """If rolled back, no trace data should persist."""
        from src.backend.domain.clinical_decision import ClinicalDecisionTraceModel
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionTraceRepository,
        )

        decision = await self._setup_decision(db_session, patient)
        repo = ClinicalDecisionTraceRepository(db_session)

        trace = ClinicalDecisionTraceModel(
            trace_id="trace-rollback",
            clinical_decision_id=decision.id,
            step_order=1,
            step_type="test",
        )
        await repo.create(trace)

        await db_session.rollback()

        fetched = await repo.get_by_trace_id("trace-rollback")
        assert fetched is None
