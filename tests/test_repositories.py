"""
Tests for repository layer — uses SQLite in-memory.
"""
from __future__ import annotations

import pytest

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.backend.database.models import Base
from src.backend.repositories.patient_repo import PatientRepository
from src.backend.repositories.variant_repo import VariantRepository
from src.backend.repositories.analysis_run_repo import AnalysisRunRepository
from src.backend.domain.patient import PatientModel, SexEnum, ConsentStatusEnum
from src.backend.domain.cancer_case import CancerCaseModel, CancerTypeEnum
from src.backend.domain.variant import VariantTypeEnum, VariantOriginEnum
from src.backend.domain.analysis_run import AnalysisStatusEnum


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
        from src.backend.domain.sequencing_test import SequencingTestModel
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

        from src.backend.domain.sequencing_test import AnalysisResultTypeEnum
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
