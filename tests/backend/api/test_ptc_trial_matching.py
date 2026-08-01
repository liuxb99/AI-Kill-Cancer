import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backend.api.v1.ptc_trial_matching import match_trials
from src.backend.database.models import Base
from src.backend.domain.ptc_knowledge import PTCClinicalTrialModel
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
async def test_trial_matching_ranks_explainable_potential_match_first(session):
    case = PTCResearchCaseModel(
        case_id="TCGA-TRIAL-001",
        source_dataset="TCGA-THCA",
        source_project="TCGA-THCA",
        pathologic_stage="Stage I",
        age_range="40-50",
        sex="Female",
    )
    session.add(case)
    await session.flush()
    session.add(
        PTCVariantModel(
            variant_id="trial-braf-v600e",
            research_case_id=case.id,
            case_id=case.case_id,
            source_dataset="TCGA-THCA",
            gene="BRAF",
            protein_change="p.V600E",
            classification="Missense_Mutation",
        )
    )
    session.add_all([
        PTCClinicalTrialModel(
            nct_id="NCT-MATCH-001",
            brief_title="Recruiting BRAF V600E PTC trial",
            overall_status="RECRUITING",
            phases=["PHASE2"],
            conditions=["Papillary Thyroid Carcinoma"],
            interventions=[{"name": "Dabrafenib"}],
            target_genes=["BRAF"],
            eligibility="Minimum Age: 18 Years\nMaximum Age: 75 Years\nStage I\nBRAF P.V600E\nFemale and Male",
            source_url="https://clinicaltrials.gov/study/NCT-MATCH-001",
        ),
        PTCClinicalTrialModel(
            nct_id="NCT-MISMATCH-001",
            brief_title="Male-only older population trial",
            overall_status="RECRUITING",
            phases=["PHASE1"],
            conditions=["Papillary Thyroid Carcinoma"],
            interventions=[{"name": "Investigational agent"}],
            target_genes=["RET"],
            eligibility="Minimum Age: 65 Years\nMale only\nStage IV",
            source_url="https://clinicaltrials.gov/study/NCT-MISMATCH-001",
        ),
    ])
    await session.commit()

    result = await match_trials("TCGA-TRIAL-001", gene="BRAF", active_only=True, limit=50, db=session)

    assert result["case_id"] == "TCGA-TRIAL-001"
    assert result["selected_gene"] == "BRAF"
    assert result["matches"][0]["nct_id"] == "NCT-MATCH-001"
    assert result["matches"][0]["classification"] == "potential_match"
    assert result["matches"][0]["score"] >= 80
    criteria = {item["name"]: item for item in result["matches"][0]["criteria"]}
    assert criteria["gene"]["status"] == "match"
    assert criteria["protein_variant"]["status"] == "match"
    assert criteria["age"]["status"] == "match"
    assert result["summary"]["potential_match"] == 1
    assert result["trace"][-1]["name"] == "rank_without_clinical_recommendation"


@pytest.mark.asyncio
async def test_trial_matching_marks_explicit_mismatches(session):
    case = PTCResearchCaseModel(
        case_id="TCGA-TRIAL-002",
        source_dataset="TCGA-THCA",
        source_project="TCGA-THCA",
        age_range="40-50",
        sex="Female",
    )
    session.add(case)
    await session.flush()
    session.add(
        PTCVariantModel(
            variant_id="trial-ret",
            research_case_id=case.id,
            case_id=case.case_id,
            source_dataset="TCGA-THCA",
            gene="RET",
            protein_change="p.M918T",
        )
    )
    session.add(
        PTCClinicalTrialModel(
            nct_id="NCT-MISMATCH-002",
            brief_title="Male age 65+ RET trial",
            overall_status="RECRUITING",
            phases=["PHASE1"],
            conditions=["Papillary Thyroid Carcinoma"],
            interventions=[],
            target_genes=["RET"],
            eligibility="Minimum Age: 65 Years\nMale only",
        )
    )
    await session.commit()

    result = await match_trials("TCGA-TRIAL-002", gene="RET", active_only=True, limit=50, db=session)
    item = result["matches"][0]
    assert item["classification"] == "unlikely_match"
    assert "age" in item["blocking_mismatches"]
    assert "sex" in item["blocking_mismatches"]
