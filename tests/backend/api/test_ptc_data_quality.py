from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backend.api.v1.ptc_data_quality import get_data_quality_overview, get_gene_quality
from src.backend.database.models import Base
from src.backend.domain.ptc_knowledge import (
    PTCClinicalTrialModel,
    PTCEvidenceRecordModel,
    PTCTherapyModel,
    PTCTherapyTargetModel,
)
from src.backend.domain.ptc_research import (
    PTCImportBatchModel,
    PTCResearchCaseModel,
    PTCVariantModel,
)


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        yield db
    await engine.dispose()


@pytest.mark.asyncio
async def test_quality_audit_reports_freshness_inventory_and_gene_coverage(session):
    now = datetime.utcnow()
    case = PTCResearchCaseModel(
        case_id="TCGA-QUALITY-001",
        source_dataset="TCGA-THCA",
        source_project="TCGA-THCA",
    )
    session.add(case)
    await session.flush()
    session.add(
        PTCVariantModel(
            variant_id="quality-braf-v600e",
            research_case_id=case.id,
            case_id=case.case_id,
            source_dataset="TCGA-THCA",
            gene="BRAF",
            protein_change="p.V600E",
        )
    )
    therapy = PTCTherapyModel(
        therapy_key="openfda:dabrafenib",
        name="Dabrafenib",
        generic_name="dabrafenib",
        therapy_type="drug",
        source_name="openFDA",
        source_record_id="label-1",
        source_url="https://open.fda.gov/",
        source_version="v1",
        retrieved_at=now,
    )
    session.add(therapy)
    await session.flush()
    session.add(
        PTCTherapyTargetModel(
            therapy_id=therapy.id,
            gene_symbol="BRAF",
            variant="V600E",
        )
    )
    session.add_all([
        PTCEvidenceRecordModel(
            evidence_key="pubmed:quality:braf",
            source_name="PubMed",
            source_record_id="123",
            evidence_type="publication",
            gene_symbol="BRAF",
            source_url="https://pubmed.ncbi.nlm.nih.gov/123/",
            retrieved_at=now - timedelta(days=45),
        ),
        PTCClinicalTrialModel(
            nct_id="NCT-QUALITY-001",
            brief_title="BRAF PTC trial",
            target_genes=["BRAF"],
            source_url="https://clinicaltrials.gov/study/NCT-QUALITY-001",
            source_version="2026-08",
            retrieved_at=now,
        ),
        PTCImportBatchModel(
            batch_id="quality-batch",
            source_dataset="TCGA-THCA",
            source_version="GDC-2026",
            status="completed",
            record_count=1,
            started_at=now,
            completed_at=now,
        ),
    ])
    await session.commit()

    result = await get_data_quality_overview(stale_only=False, db=session)

    assert result["inventory"]["cases"] == 1
    assert result["inventory"]["variants"] == 1
    sources = {item["source_name"]: item for item in result["sources"]}
    assert sources["openFDA"]["freshness"] == "fresh"
    assert sources["PubMed"]["freshness"] == "stale"
    assert sources["TCGA-THCA"]["failed_or_incomplete_batches"] == 0
    braf = next(item for item in result["gene_coverage"] if item["gene"] == "BRAF")
    assert braf["coverage_score"] == 4
    assert braf["gaps"] == []
    assert result["trace"][-1]["name"] == "emit_objective_quality_gaps"


@pytest.mark.asyncio
async def test_gene_quality_returns_explicit_gaps_for_unknown_gene(session):
    result = await get_gene_quality("RET", db=session)
    assert result["found"] is False
    assert result["coverage"]["coverage_score"] == 0
    assert "no_evidence" in result["coverage"]["gaps"]
