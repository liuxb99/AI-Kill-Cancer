import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backend.database.models import Base
from src.backend.domain.clinical_graph_outbox import ClinicalGraphOutboxModel
from src.backend.domain.ptc_research import (
    PTCImportBatchModel,
    PTCOutcomeModel,
    PTCResearchCaseModel,
    PTCVariantModel,
)
from src.backend.importers.ptc_tcga.service import PTCTCGAImportService


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        yield db
    await engine.dispose()


def sample_record():
    return {
        "case_id": "TCGA-ET-0001",
        "gender": "female",
        "ajcc_pathologic_stage": "Stage I",
        "vital_status": "Alive",
        "variants": [
            {
                "hugo_symbol": "BRAF",
                "chromosome": "7",
                "start_position": 140453136,
                "reference_allele": "A",
                "tumor_seq_allele2": "T",
                "hgvsp_short": "p.V600E",
            }
        ],
    }


@pytest.mark.asyncio
async def test_import_persists_case_variant_outcome_and_outbox_atomically(session):
    service = PTCTCGAImportService(session)

    result = await service.import_records([sample_record()], batch_id="batch-one")

    assert result.imported_cases == 1
    assert result.imported_variants == 1
    assert result.imported_outcomes == 1
    assert result.outbox_events == 3
    assert await session.scalar(select(func.count()).select_from(PTCResearchCaseModel)) == 1
    assert await session.scalar(select(func.count()).select_from(PTCVariantModel)) == 1
    assert await session.scalar(select(func.count()).select_from(PTCOutcomeModel)) == 1
    assert await session.scalar(select(func.count()).select_from(ClinicalGraphOutboxModel)) == 3
    batch = await session.scalar(select(PTCImportBatchModel))
    assert batch.status == "completed"


@pytest.mark.asyncio
async def test_replay_is_idempotent_for_entities_and_outbox(session):
    service = PTCTCGAImportService(session)
    await service.import_records([sample_record()], batch_id="batch-one")
    replay = await service.import_records([sample_record()], batch_id="batch-two")

    assert replay.imported_cases == 1
    assert replay.outbox_events == 0
    assert await session.scalar(select(func.count()).select_from(PTCResearchCaseModel)) == 1
    assert await session.scalar(select(func.count()).select_from(PTCVariantModel)) == 1
    assert await session.scalar(select(func.count()).select_from(PTCOutcomeModel)) == 1
    assert await session.scalar(select(func.count()).select_from(ClinicalGraphOutboxModel)) == 3


@pytest.mark.asyncio
async def test_invalid_record_rolls_back_entire_batch(session):
    service = PTCTCGAImportService(session)
    invalid = sample_record()
    invalid["variants"].append({"hugo_symbol": None})
    invalid["case_id"] = None

    with pytest.raises(ValueError):
        await service.import_records([sample_record(), invalid], batch_id="batch-fail")

    assert await session.scalar(select(func.count()).select_from(PTCResearchCaseModel)) == 0
    assert await session.scalar(select(func.count()).select_from(ClinicalGraphOutboxModel)) == 0
