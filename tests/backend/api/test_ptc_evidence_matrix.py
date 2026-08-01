import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backend.api.v1.ptc_evidence_matrix import get_case_evidence_matrix
from src.backend.database.models import Base
from src.backend.domain.ptc_knowledge import (
    PTCClinicalTrialModel,
    PTCEvidenceRecordModel,
    PTCTherapyModel,
    PTCTherapyTargetModel,
)
from src.backend.domain.ptc_research import PTCResearchCaseModel, PTCVariantModel


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
async def test_matrix_joins_variant_therapy_evidence_trial_and_cohort(session):
    anchor = PTCResearchCaseModel(
        case_id="TCGA-MATRIX-001",
        source_dataset="TCGA-THCA",
        source_project="TCGA-THCA",
        pathologic_stage="Stage I",
        vital_status="Alive",
    )
    comparison = PTCResearchCaseModel(
        case_id="TCGA-MATRIX-002",
        source_dataset="TCGA-THCA",
        source_project="TCGA-THCA",
        pathologic_stage="Stage II",
        vital_status="Alive",
    )
    session.add_all([anchor, comparison])
    await session.flush()
    session.add_all([
        PTCVariantModel(
            variant_id="matrix-1",
            research_case_id=anchor.id,
            case_id=anchor.case_id,
            source_dataset="TCGA-THCA",
            gene="BRAF",
            protein_change="p.V600E",
            classification="Missense_Mutation",
        ),
        PTCVariantModel(
            variant_id="matrix-2",
            research_case_id=comparison.id,
            case_id=comparison.case_id,
            source_dataset="TCGA-THCA",
            gene="BRAF",
            protein_change="p.V600E",
            classification="Missense_Mutation",
        ),
    ])
    therapy = PTCTherapyModel(
        therapy_key="openfda:dabrafenib",
        name="Dabrafenib",
        generic_name="dabrafenib",
        therapy_type="drug",
        approval_status="FDA label available",
        indications=["BRAF V600E"],
        source_name="openFDA",
        source_record_id="label-1",
    )
    session.add(therapy)
    await session.flush()
    session.add(
        PTCTherapyTargetModel(
            therapy_id=therapy.id,
            gene_symbol="BRAF",
            variant="V600E",
            interaction_type="inhibits_or_targets",
        )
    )
    session.add(
        PTCEvidenceRecordModel(
            evidence_key="pubmed:matrix:braf",
            source_name="PubMed",
            source_record_id="matrix-pmid",
            title="BRAF evidence",
            summary="Evidence summary",
            evidence_type="publication",
            evidence_level="A",
            direction="supports",
            gene_symbol="BRAF",
            publication_id="123",
            source_url="https://pubmed.ncbi.nlm.nih.gov/123/",
            payload={"figures": [{"id": "fig1"}], "tables": [{"id": "tbl1"}]},
        )
    )
    session.add(
        PTCClinicalTrialModel(
            nct_id="NCT-MATRIX-001",
            brief_title="BRAF thyroid trial",
            official_title="BRAF papillary thyroid carcinoma",
            overall_status="RECRUITING",
            phases=["PHASE2"],
            conditions=["Papillary Thyroid Carcinoma"],
            interventions=[{"name": "Dabrafenib"}],
            target_genes=["BRAF"],
            source_url="https://clinicaltrials.gov/study/NCT-MATRIX-001",
        )
    )
    await session.commit()

    result = await get_case_evidence_matrix("TCGA-MATRIX-001", None, session)

    assert result["case_id"] == "TCGA-MATRIX-001"
    assert result["summary"]["genes"] == 1
    row = result["rows"][0]
    assert row["gene"] == "BRAF"
    assert row["variants"][0]["protein_change"] == "p.V600E"
    assert row["therapies"][0]["name"] == "Dabrafenib"
    assert row["evidence"][0]["figures"] == 1
    assert row["evidence"][0]["tables"] == 1
    assert row["trials"][0]["active"] is True
    assert row["cohort"]["same_gene_cases"] == 1
    assert row["score"] > 80
    assert row["gaps"] == []
    assert result["trace"][-1]["name"] == "score_and_rank_matrix"


@pytest.mark.asyncio
async def test_matrix_rejects_gene_not_present_in_case(session):
    case = PTCResearchCaseModel(
        case_id="TCGA-MATRIX-EMPTY",
        source_dataset="TCGA-THCA",
        source_project="TCGA-THCA",
    )
    session.add(case)
    await session.commit()

    with pytest.raises(Exception) as exc:
        await get_case_evidence_matrix("TCGA-MATRIX-EMPTY", "BRAF", session)
    assert getattr(exc.value, "status_code", None) == 404
