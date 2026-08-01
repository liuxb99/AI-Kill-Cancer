import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backend.api.v1.ptc_evidence_matrix import (
    OUTCOME_FIELDS_EXCLUDED,
    SCORE_WEIGHTS,
    SCORING_VERSION,
    get_case_evidence_matrix,
)
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


async def seed_matrix(session):
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
        source_url="https://open.fda.gov/label-1",
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
    return comparison


@pytest.mark.asyncio
async def test_matrix_joins_sources_and_labels_completeness_score(session):
    await seed_matrix(session)

    result = await get_case_evidence_matrix("TCGA-MATRIX-001", None, session)

    assert result["case_id"] == "TCGA-MATRIX-001"
    assert result["methodology"]["scoring_version"] == SCORING_VERSION
    assert result["methodology"]["score_type"] == "data_linkage_completeness"
    assert result["methodology"]["outcome_blind"] is True
    assert result["methodology"]["outcome_fields_excluded"] == OUTCOME_FIELDS_EXCLUDED
    assert sum(SCORE_WEIGHTS.values()) == 100.0

    row = result["rows"][0]
    assert row["gene"] == "BRAF"
    assert row["variants"][0]["protein_change"] == "p.V600E"
    assert row["therapies"][0]["name"] == "Dabrafenib"
    assert row["evidence"][0]["figures"] == 1
    assert row["evidence"][0]["tables"] == 1
    assert row["trials"][0]["active"] is True
    assert row["cohort"]["same_gene_cases"] == 1
    assert row["cohort"]["excluded_from_score"] is True
    assert row["score_type"] == "data_linkage_completeness"
    assert "same_gene_cohort" not in row["score_components"]
    assert "vital_status" not in row["score_components"]
    assert row["score"] > 60
    assert row["gaps"] == []
    assert result["trace"][-1]["name"] == "rank_by_completeness"


@pytest.mark.asyncio
async def test_cohort_outcome_changes_do_not_change_matrix_score(session):
    comparison = await seed_matrix(session)
    first = await get_case_evidence_matrix("TCGA-MATRIX-001", None, session)
    first_score = first["rows"][0]["score"]

    comparison.vital_status = "Dead"
    comparison.days_to_death = 90
    await session.commit()

    second = await get_case_evidence_matrix("TCGA-MATRIX-001", None, session)
    second_row = second["rows"][0]

    assert second_row["score"] == first_score
    assert second_row["score_components"] == first["rows"][0]["score_components"]
    assert second_row["cohort"]["vital_status_distribution"] == {"Dead": 1}


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
