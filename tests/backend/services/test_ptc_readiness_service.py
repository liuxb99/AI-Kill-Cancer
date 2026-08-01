import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backend.database.models import Base
from src.backend.domain.ptc_knowledge import (
    PTCClinicalTrialModel,
    PTCEvidenceRecordModel,
    PTCTherapyModel,
    PTCTherapyTargetModel,
)
from src.backend.domain.ptc_research import PTCResearchCaseModel, PTCVariantModel
from src.backend.services.ptc_readiness_service import PTCReadinessService


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
async def test_empty_database_is_not_ready(session):
    result = await PTCReadinessService(session).evaluate()
    assert result["status"] == "not_ready"
    assert result["demo_ready"] is False
    assert "cases_gte_1" in result["blockers"]
    assert "graph_has_relations" in result["blockers"]


@pytest.mark.asyncio
async def test_minimum_complete_dataset_is_demo_ready(session):
    case = PTCResearchCaseModel(
        case_id="TCGA-READY-0001",
        source_dataset="TCGA-THCA",
        pathologic_stage="Stage I",
        vital_status="Alive",
    )
    session.add(case)
    await session.flush()
    session.add(
        PTCVariantModel(
            variant_id="TCGA-READY-0001:BRAF:V600E",
            research_case_id=case.id,
            case_id=case.case_id,
            source_dataset="TCGA-THCA",
            gene="BRAF",
            protein_change="p.V600E",
            classification="Missense_Mutation",
        )
    )
    therapy = PTCTherapyModel(
        therapy_key="openfda:dabrafenib-ready",
        name="Dabrafenib",
        generic_name="dabrafenib",
        source_name="openFDA",
        source_record_id="dabrafenib-ready",
        approval_status="FDA label available",
    )
    session.add(therapy)
    await session.flush()
    session.add(
        PTCTherapyTargetModel(
            therapy_id=therapy.id,
            gene_symbol="BRAF",
            variant="V600E",
            evidence_level="label_or_curated_mapping",
        )
    )
    session.add(
        PTCEvidenceRecordModel(
            evidence_key="pubmed:ready:braf",
            source_name="PubMed",
            source_record_id="PMID-READY",
            evidence_type="publication",
            evidence_level="published_literature",
            gene_symbol="BRAF",
            therapy_id=therapy.id,
            title="BRAF evidence in PTC",
        )
    )
    session.add(
        PTCClinicalTrialModel(
            nct_id="NCTREADY0001",
            brief_title="BRAF targeted PTC study",
            target_genes=["BRAF"],
            phases=["PHASE2"],
            overall_status="RECRUITING",
        )
    )
    await session.commit()

    result = await PTCReadinessService(session).evaluate()
    assert result["status"] == "ready"
    assert result["demo_ready"] is True
    assert result["research_ready"] is False
    assert result["blockers"] == []
    assert result["graph"]["dangling_edge_count"] == 0
    assert result["checks"]["structural"]["knowgraph_export_endpoints_valid"] is True
