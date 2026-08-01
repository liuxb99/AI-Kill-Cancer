import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backend.api.v1.ptc_trial_matching import (
    ELIGIBILITY_FIELDS,
    MATCHING_VERSION,
    RELEVANCE_WEIGHTS,
    _match_trial,
    match_trials,
)
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


def make_case(case_id: str, *, age_range: str | None = "40-50", sex: str | None = "Female"):
    case = PTCResearchCaseModel(
        case_id=case_id,
        source_dataset="TCGA-THCA",
        source_project="TCGA-THCA",
        pathologic_stage="Stage I",
        age_range=age_range,
        sex=sex,
    )
    case.variants = [PTCVariantModel(
        variant_id=f"{case_id}-braf-v600e",
        case_id=case_id,
        source_dataset="TCGA-THCA",
        gene="BRAF",
        protein_change="p.V600E",
        classification="Missense_Mutation",
    )]
    return case


def make_trial(nct_id: str, eligibility: str):
    return PTCClinicalTrialModel(
        nct_id=nct_id,
        brief_title="Recruiting BRAF V600E PTC trial",
        overall_status="RECRUITING",
        phases=["PHASE2"],
        conditions=["Papillary Thyroid Carcinoma"],
        interventions=[{"name": "Dabrafenib"}],
        target_genes=["BRAF"],
        eligibility=eligibility,
        locations=[{"facility": "Research Center", "country": "United States"}],
        source_url=f"https://clinicaltrials.gov/study/{nct_id}",
    )


@pytest.mark.asyncio
async def test_trial_matching_returns_research_candidate_without_eligibility_claim(session):
    case = make_case("TCGA-TRIAL-001")
    session.add(case)
    await session.flush()
    for variant in case.variants:
        variant.research_case_id = case.id
        session.add(variant)
    session.add(make_trial(
        "NCT-MATCH-001",
        "Minimum Age: 18 Years\nMaximum Age: 75 Years\nStage I\nBRAF P.V600E\nECOG 0-1",
    ))
    await session.commit()

    result = await match_trials("TCGA-TRIAL-001", gene="BRAF", active_only=True, limit=50, db=session)
    item = result["matches"][0]

    assert item["classification"] == "research_candidate"
    assert item["eligibility_determination"] is False
    assert item["score_type"] == "research_relevance"
    assert item["score_version"] == MATCHING_VERSION
    assert sum(RELEVANCE_WEIGHTS.values()) == 100.0
    assert result["methodology"]["eligibility_separate_from_score"] is True
    assert result["methodology"]["eligibility_determination"] is False
    assert result["trace"][-1]["name"] == "rank_without_eligibility_claim"
    assert "not trial eligibility" in result["disclaimer"]

    relevance_names = {criterion["name"] for criterion in item["relevance_criteria"]}
    eligibility_names = {criterion["name"] for criterion in item["eligibility_criteria"]}
    assert relevance_names == set(RELEVANCE_WEIGHTS)
    assert eligibility_names == set(ELIGIBILITY_FIELDS)
    assert all(criterion["track"] == "relevance" for criterion in item["relevance_criteria"])
    assert all(criterion["track"] == "eligibility" for criterion in item["eligibility_criteria"])
    assert all(criterion["awarded"] == 0 for criterion in item["eligibility_criteria"])
    assert "ecog_performance_status" in item["missing_or_unverified_eligibility"]


def test_eligibility_text_never_changes_research_relevance_score():
    case = make_case("TCGA-TRIAL-SCORE")
    aligned = make_trial(
        "NCT-ALIGNED",
        "Minimum Age: 18 Years\nMaximum Age: 75 Years\nStage I\nBRAF P.V600E\nFemale",
    )
    conflicting = make_trial(
        "NCT-CONFLICT",
        "Minimum Age: 65 Years\nStage IV\nBRAF P.V600E\nMale only",
    )

    aligned_result = _match_trial(case, aligned)
    conflict_result = _match_trial(case, conflicting)

    assert aligned_result["score"] == conflict_result["score"]
    assert aligned_result["relevance_criteria"] == conflict_result["relevance_criteria"]
    assert aligned_result["eligibility_status"] != conflict_result["eligibility_status"]
    assert conflict_result["eligibility_status"] == "conflict_detected"
    assert {"age", "pathologic_stage", "sex"}.issubset(set(conflict_result["eligibility_conflicts"]))


def test_missing_clinical_fields_cannot_become_eligible():
    case = make_case("TCGA-TRIAL-MISSING", age_range=None, sex=None)
    case.pathologic_stage = None
    trial = make_trial("NCT-MISSING", "BRAF P.V600E")

    result = _match_trial(case, trial)

    assert result["classification"] == "research_candidate"
    assert result["eligibility_status"] == "incomplete_review_required"
    assert result["eligibility_determination"] is False
    assert set(ELIGIBILITY_FIELDS).issubset(set(result["missing_or_unverified_eligibility"]))
