"""
Tests for analysis job persistence and transactions.
"""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.backend.database.models import Base
from src.backend.domain.enums import AnalysisStatusEnum
from src.backend.pipeline.analysis_job import create_and_run_job, load_job_from_db


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


class TestAnalysisPersistence:
    async def test_create_and_run_job(self, db_session):
        """Job should create DB record and run pipeline."""
        from src.backend.domain.cancer_case import CancerCaseModel
        from src.backend.domain.patient import PatientModel
        from src.backend.domain.enums import SexEnum, ConsentStatusEnum, CancerTypeEnum

        # Create required FK records
        patient = PatientModel(display_name="TEST", sex=SexEnum.M, consent_status=ConsentStatusEnum.GRANTED)
        db_session.add(patient)
        await db_session.flush()

        case = CancerCaseModel(patient_id=patient.id, cancer_type=CancerTypeEnum.PTC)
        db_session.add(case)
        await db_session.flush()

        job = await create_and_run_job(
            case_id=str(case.id),
            sequencing_test_id="",
            raw_variants=[
                {"chromosome": "7", "position": 140753336, "reference": "A", "alternate": "T"},
            ],
            db_session=db_session,
            pipeline_version="0.3.1",
            git_commit="test-commit",
        )
        assert job.status in (AnalysisStatusEnum.COMPLETED, AnalysisStatusEnum.PARTIAL, AnalysisStatusEnum.FAILED)
        assert job.duration_ms is not None
        assert job.started_at is not None
        assert job.finished_at is not None

    async def test_load_job_from_db(self, db_session):
        """Job should be loadable from DB after creation."""
        from src.backend.domain.cancer_case import CancerCaseModel
        from src.backend.domain.patient import PatientModel
        from src.backend.domain.enums import SexEnum, ConsentStatusEnum, CancerTypeEnum

        patient = PatientModel(display_name="TEST", sex=SexEnum.M, consent_status=ConsentStatusEnum.GRANTED)
        db_session.add(patient)
        await db_session.flush()
        case = CancerCaseModel(patient_id=patient.id, cancer_type=CancerTypeEnum.PTC)
        db_session.add(case)
        await db_session.flush()

        job = await create_and_run_job(
            case_id=str(case.id),
            sequencing_test_id="",
            raw_variants=[{"chromosome": "7", "position": 140753336, "reference": "A", "alternate": "T"}],
            db_session=db_session,
        )
        job_id = job.job_id

        # Clear cache and load from DB
        from src.backend.pipeline.analysis_job import _job_cache
        _job_cache.clear()

        loaded = await load_job_from_db(job_id, db_session)
        assert loaded is not None
        assert loaded.status == AnalysisStatusEnum.COMPLETED or loaded.status == AnalysisStatusEnum.PARTIAL

    async def test_job_provenance(self, db_session):
        """Job should produce complete provenance."""
        from src.backend.domain.cancer_case import CancerCaseModel
        from src.backend.domain.patient import PatientModel
        from src.backend.domain.enums import SexEnum, ConsentStatusEnum, CancerTypeEnum

        patient = PatientModel(display_name="TEST", sex=SexEnum.M, consent_status=ConsentStatusEnum.GRANTED)
        db_session.add(patient)
        await db_session.flush()
        case = CancerCaseModel(patient_id=patient.id, cancer_type=CancerTypeEnum.PTC)
        db_session.add(case)
        await db_session.flush()

        job = await create_and_run_job(
            case_id=str(case.id),
            sequencing_test_id="",
            raw_variants=[{"chromosome": "7", "position": 140753336, "reference": "A", "alternate": "T"}],
            db_session=db_session,
        )
        prov = job.get_provenance()
        assert "pipeline_version" in prov
        assert "normalization" in prov
        assert "vep" in prov
        assert "record_count" in prov
        assert prov["record_count"]["input"] == 1
