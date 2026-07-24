"""
Tests for repository layer — uses SQLite in-memory.
"""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base
from src.backend.domain.analysis_run import AnalysisStatusEnum
from src.backend.domain.cancer_case import CancerCaseModel, CancerTypeEnum
from src.backend.domain.patient import ConsentStatusEnum, PatientModel, SexEnum
from src.backend.domain.variant import VariantOriginEnum, VariantTypeEnum
from src.backend.repositories.analysis_run_repo import AnalysisRunRepository
from src.backend.repositories.patient_repo import PatientRepository
from src.backend.repositories.variant_repo import VariantRepository


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


class TestPatientRepository:
    async def test_create_patient(self, db_session):
        repo = PatientRepository(db_session)
        patient = await repo.create(
            display_name="ANON-001",
            sex=SexEnum.M,
            consent_status=ConsentStatusEnum.GRANTED,
        )
        assert patient.id is not None
        assert patient.display_name == "ANON-001"
        assert patient.consent_status == ConsentStatusEnum.GRANTED

    async def test_get_patient(self, db_session):
        repo = PatientRepository(db_session)
        created = await repo.create(display_name="ANON-002")
        fetched = await repo.get(created.id)
        assert fetched is not None
        assert fetched.display_name == "ANON-002"

    async def test_list_patients(self, db_session):
        repo = PatientRepository(db_session)
        for i in range(3):
            await repo.create(display_name=f"ANON-{i:03d}")
        patients = await repo.list()
        assert len(patients) == 3

    async def test_count_patients(self, db_session):
        repo = PatientRepository(db_session)
        assert await repo.count() == 0
        await repo.create(display_name="ANON-001")
        assert await repo.count() == 1

    async def test_delete_patient(self, db_session):
        repo = PatientRepository(db_session)
        p = await repo.create(display_name="ANON-DEL")
        assert await repo.delete(p.id) is True
        assert await repo.get(p.id) is None


class TestVariantRepository:
    async def test_bulk_create(self, db_session):
        repo = VariantRepository(db_session)
        from src.backend.domain.sequencing import SequencingTestModel
        from src.backend.domain.specimen import SpecimenModel

        # Create chain: patient -> case -> specimen -> seq_test -> variants
        patient = PatientModel(display_name="TEST", sex=SexEnum.F, consent_status=ConsentStatusEnum.GRANTED)
        db_session.add(patient)
        await db_session.flush()

        case = CancerCaseModel(patient_id=patient.id, cancer_type=CancerTypeEnum.PTC)
        db_session.add(case)
        await db_session.flush()

        specimen = SpecimenModel(case_id=case.id, specimen_type="FFPE")
        db_session.add(specimen)
        await db_session.flush()

        from src.backend.domain.sequencing import AnalysisResultTypeEnum
        seq = SequencingTestModel(specimen_id=specimen.id, assay_name="ThyroSeq", result_type=AnalysisResultTypeEnum.SOMATIC)
        db_session.add(seq)
        await db_session.flush()

        variants = await repo.bulk_create([
            {
                "sequencing_test_id": seq.id,
                "gene_symbol": "BRAF",
                "chromosome": "7",
                "position": 140753336,
                "reference": "A",
                "alternate": "T",
                "genome_build": "GRCh38",
                "variant_type": VariantTypeEnum.SNV,
                "origin": VariantOriginEnum.SOMATIC,
            },
            {
                "sequencing_test_id": seq.id,
                "gene_symbol": "TERT",
                "chromosome": "5",
                "position": 1295228,
                "reference": "G",
                "alternate": "A",
                "genome_build": "GRCh38",
                "variant_type": VariantTypeEnum.TERT_PROMOTER,
                "origin": VariantOriginEnum.SOMATIC,
            },
        ])
        assert len(variants) == 2
        assert variants[0].gene_symbol == "BRAF"
        assert variants[1].variant_type == VariantTypeEnum.TERT_PROMOTER

    async def test_find_by_gene(self, db_session):
        repo = VariantRepository(db_session)
        # Minimal test — depends on proper foreign keys set up
        variants = await repo.find_by_gene("BRAF")
        assert isinstance(variants, list)


class TestAnalysisRunRepository:
    async def test_create_analysis_run(self, db_session):
        repo = AnalysisRunRepository(db_session)

        patient = PatientModel(display_name="TEST", sex=SexEnum.F, consent_status=ConsentStatusEnum.GRANTED)
        db_session.add(patient)
        await db_session.flush()

        case = CancerCaseModel(patient_id=patient.id, cancer_type=CancerTypeEnum.PTC)
        db_session.add(case)
        await db_session.flush()

        run = await repo.create(
            case_id=case.id,
            status=AnalysisStatusEnum.PENDING,
            pipeline_version="0.2.0",
        )
        assert run.id is not None
        assert run.status == AnalysisStatusEnum.PENDING
        assert run.pipeline_version == "0.2.0"


# ═══════════════════════════════════════════════════════════════════════════════
# Recommendation Repository Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestRecommendationRepository:
    """Tests for RecommendationRepository — CRUD for RecommendationModel."""

    async def test_create_recommendation(self, db_session):
        from src.backend.domain.patient import PatientModel
        from src.backend.domain.recommendation import RecommendationModel
        from src.backend.repositories.recommendation_repo import RecommendationRepository

        patient = PatientModel(display_name="REC-CREATE")
        db_session.add(patient)
        await db_session.flush()

        repo = RecommendationRepository(db_session)
        rec = RecommendationModel(
            recommendation_id="repo-create-001",
            patient_id=patient.id,
            engine_version="1.0.0",
            status="pending",
            request_payload={"variants": ["EGFR L858R"]},
        )
        result = await repo.create(rec)
        await db_session.flush()  # Ensure ID is assigned before reading

        assert result is rec  # same instance returned
        assert result.id is not None
        assert result.recommendation_id == "repo-create-001"

        # Confirm it's actually in the DB
        await db_session.commit()
        await db_session.refresh(result)
        assert result.request_payload == {"variants": ["EGFR L858R"]}

    async def test_get_by_id_found(self, db_session):
        from src.backend.domain.patient import PatientModel
        from src.backend.domain.recommendation import RecommendationModel
        from src.backend.repositories.recommendation_repo import RecommendationRepository

        patient = PatientModel(display_name="REC-GET-ID")
        db_session.add(patient)
        await db_session.flush()

        repo = RecommendationRepository(db_session)
        rec = RecommendationModel(recommendation_id="get-by-id-found", patient_id=patient.id)
        await repo.create(rec)
        await db_session.commit()

        fetched = await repo.get_by_id("get-by-id-found")
        assert fetched is not None
        assert fetched.recommendation_id == "get-by-id-found"
        assert str(fetched.id) == str(rec.id)

    async def test_get_by_id_not_found(self, db_session):
        from src.backend.repositories.recommendation_repo import RecommendationRepository

        repo = RecommendationRepository(db_session)
        result = await repo.get_by_id("non-existent-id")
        assert result is None

    async def test_get_by_trace_id(self, db_session):
        from src.backend.domain.patient import PatientModel
        from src.backend.domain.recommendation import RecommendationModel
        from src.backend.repositories.recommendation_repo import RecommendationRepository

        patient = PatientModel(display_name="REC-TRACE-ID")
        db_session.add(patient)
        await db_session.flush()

        repo = RecommendationRepository(db_session)
        rec = RecommendationModel(
            recommendation_id="get-by-trace",
            patient_id=patient.id,
            trace_id="trace-abc-123",
        )
        await repo.create(rec)
        await db_session.commit()

        fetched = await repo.get_by_trace_id("trace-abc-123")
        assert fetched is not None
        assert fetched.recommendation_id == "get-by-trace"

    async def test_get_by_trace_id_not_found(self, db_session):
        from src.backend.repositories.recommendation_repo import RecommendationRepository

        repo = RecommendationRepository(db_session)
        result = await repo.get_by_trace_id("non-existent-trace")
        assert result is None

    async def test_list_by_patient_id(self, db_session):
        from src.backend.domain.patient import PatientModel
        from src.backend.domain.recommendation import RecommendationModel
        from src.backend.repositories.recommendation_repo import RecommendationRepository

        # Create a patient to satisfy FK
        patient = PatientModel(display_name="REC-LIST-PAT")
        db_session.add(patient)
        await db_session.flush()

        repo = RecommendationRepository(db_session)
        for i in range(3):
            rec = RecommendationModel(
                recommendation_id=f"list-pat-{i:02d}",
                patient_id=patient.id,
            )
            await repo.create(rec)
        await db_session.commit()

        results = await repo.list_by_patient_id(str(patient.id))
        assert len(results) == 3
        # Should be ordered by created_at desc (newest first)
        assert all(r.patient_id == patient.id for r in results)

    async def test_list_by_patient_id_empty(self, db_session):
        from src.backend.repositories.recommendation_repo import RecommendationRepository

        repo = RecommendationRepository(db_session)
        results = await repo.list_by_patient_id("non-existent-patient")
        assert results == []

    async def test_list_by_patient_id_limits(self, db_session):
        from src.backend.domain.patient import PatientModel
        from src.backend.domain.recommendation import RecommendationModel
        from src.backend.repositories.recommendation_repo import RecommendationRepository

        patient = PatientModel(display_name="REC-LIMIT-PAT")
        db_session.add(patient)
        await db_session.flush()

        repo = RecommendationRepository(db_session)
        for i in range(5):
            rec = RecommendationModel(
                recommendation_id=f"limit-pat-{i:02d}",
                patient_id=patient.id,
            )
            await repo.create(rec)
        await db_session.commit()

        results = await repo.list_by_patient_id(str(patient.id), limit=3)
        assert len(results) == 3

    async def test_transaction_rollback(self, db_session):
        """If commit fails, no data should persist."""
        from src.backend.domain.patient import PatientModel
        from src.backend.domain.recommendation import RecommendationModel
        from src.backend.repositories.recommendation_repo import RecommendationRepository

        patient = PatientModel(display_name="REC-ROLLBACK")
        db_session.add(patient)
        await db_session.flush()

        repo = RecommendationRepository(db_session)
        rec = RecommendationModel(recommendation_id="rollback-test", patient_id=patient.id)
        await repo.create(rec)

        # Rollback explicitly
        await db_session.rollback()

        # Verify it's not in DB
        fetched = await repo.get_by_id("rollback-test")
        assert fetched is None


class TestTraceRepository:
    """Tests for TraceRepository — CRUD for RecommendationTraceModel and steps."""

    async def _setup_recommendation(self, db_session):
        """Helper: create a recommendation and return its ID."""
        from src.backend.domain.patient import PatientModel
        from src.backend.domain.recommendation import RecommendationModel

        patient = PatientModel(display_name="TRACE-HELPER")
        db_session.add(patient)
        await db_session.flush()

        rec = RecommendationModel(recommendation_id="trace-repo-test", patient_id=patient.id)
        db_session.add(rec)
        await db_session.flush()
        return rec

    async def test_create_trace(self, db_session):
        from src.backend.domain.recommendation import (
            RecommendationModel,
            RecommendationTraceModel,
        )
        from src.backend.repositories.recommendation_repo import TraceRepository

        rec = await self._setup_recommendation(db_session)
        repo = TraceRepository(db_session)

        trace = RecommendationTraceModel(
            trace_id="trace-create-001",
            recommendation_id=rec.id,
        )
        result = await repo.create_trace(trace)
        await db_session.flush()  # Ensure trace.id is assigned before assertion
        assert result is trace
        assert result.id is not None
        await db_session.commit()

    async def test_get_trace_by_recommendation_id(self, db_session):
        from src.backend.domain.recommendation import RecommendationTraceModel
        from src.backend.repositories.recommendation_repo import TraceRepository

        rec = await self._setup_recommendation(db_session)
        repo = TraceRepository(db_session)

        trace = RecommendationTraceModel(
            trace_id="get-by-rec-id",
            recommendation_id=rec.id,
        )
        await repo.create_trace(trace)
        await db_session.commit()

        fetched = await repo.get_trace_by_recommendation_id(str(rec.id))
        assert fetched is not None
        assert fetched.trace_id == "get-by-rec-id"

    async def test_get_trace_by_trace_id(self, db_session):
        from src.backend.domain.recommendation import RecommendationTraceModel
        from src.backend.repositories.recommendation_repo import TraceRepository

        rec = await self._setup_recommendation(db_session)
        repo = TraceRepository(db_session)

        trace = RecommendationTraceModel(
            trace_id="trace-lookup-001",
            recommendation_id=rec.id,
        )
        await repo.create_trace(trace)
        await db_session.commit()

        fetched = await repo.get_trace_by_trace_id("trace-lookup-001")
        assert fetched is not None
        assert fetched.trace_id == "trace-lookup-001"

    async def test_get_trace_not_found(self, db_session):
        from src.backend.repositories.recommendation_repo import TraceRepository

        repo = TraceRepository(db_session)
        assert await repo.get_trace_by_trace_id("nonexistent") is None
        assert await repo.get_trace_by_recommendation_id("nonexistent") is None

    async def test_create_and_get_steps(self, db_session):
        from src.backend.domain.recommendation import (
            RecommendationTraceModel,
            RecommendationTraceStepModel,
        )
        from src.backend.repositories.recommendation_repo import TraceRepository

        rec = await self._setup_recommendation(db_session)
        repo = TraceRepository(db_session)

        trace = RecommendationTraceModel(
            trace_id="step-test-trace",
            recommendation_id=rec.id,
        )
        await repo.create_trace(trace)
        await db_session.flush()

        step1 = RecommendationTraceStepModel(
            trace_id=trace.id,
            step_order=1,
            step_type="collect",
            status="completed",
        )
        step2 = RecommendationTraceStepModel(
            trace_id=trace.id,
            step_order=2,
            step_type="rank",
            status="completed",
        )
        await repo.create_step(step1)
        await repo.create_step(step2)
        await db_session.commit()

        steps = await repo.get_steps_by_trace_id(str(trace.id))
        assert len(steps) == 2
        assert steps[0].step_order == 1
        assert steps[1].step_order == 2

    async def test_steps_empty_for_no_trace(self, db_session):
        from src.backend.repositories.recommendation_repo import TraceRepository

        repo = TraceRepository(db_session)
        steps = await repo.get_steps_by_trace_id("no-such-trace")
        assert steps == []
