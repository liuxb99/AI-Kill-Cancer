import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backend.api.v1.ptc_assistant import PTCAssistantRequest, ask_ptc_assistant
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
async def test_assistant_returns_case_therapy_evidence_trial_and_trace(session):
    case = PTCResearchCaseModel(
        case_id="TCGA-ASSIST-001",
        source_dataset="TCGA-THCA",
        source_project="TCGA-THCA",
        pathologic_stage="Stage I",
        vital_status="Alive",
    )
    session.add(case)
    await session.flush()
    session.add(
        PTCVariantModel(
            variant_id="TCGA-ASSIST-001:BRAF:V600E",
            research_case_id=case.id,
            case_id=case.case_id,
            source_dataset="TCGA-THCA",
            gene="BRAF",
            protein_change="p.V600E",
            classification="Missense_Mutation",
        )
    )
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
    evidence = PTCEvidenceRecordModel(
        evidence_key="pubmed:123:braf",
        source_name="PubMed",
        source_record_id="123",
        title="BRAF V600E PTC study",
        summary="Evidence summary",
        evidence_type="publication",
        evidence_level="published_literature",
        direction="informational",
        gene_symbol="BRAF",
        publication_id="123",
        source_url="https://pubmed.ncbi.nlm.nih.gov/123/",
        payload={
            "pmcid": "PMC123",
            "figures": [{"id": "fig1", "caption": "BRAF response"}],
            "tables": [{"id": "tbl1", "headers": ["Variant", "Response"], "rows": [["V600E", "Observed"]]}],
        },
    )
    trial = PTCClinicalTrialModel(
        nct_id="NCT00000001",
        brief_title="BRAF thyroid cancer trial",
        official_title="BRAF V600E papillary thyroid carcinoma",
        phases=["PHASE2"],
        conditions=["Papillary Thyroid Carcinoma"],
        interventions=[{"name": "Dabrafenib"}],
        target_genes=["BRAF"],
        source_url="https://clinicaltrials.gov/study/NCT00000001",
    )
    session.add_all([evidence, trial])
    await session.commit()

    result = await ask_ptc_assistant(
        PTCAssistantRequest(
            case_id="TCGA-ASSIST-001",
            gene="BRAF",
            question="为什么推荐关注 BRAF V600E？有哪些论文图表和试验？",
        ),
        db=session,
    )

    assert result["case_id"] == "TCGA-ASSIST-001"
    assert result["selected_gene"] == "BRAF"
    assert result["intent"] == "clinical_trials"
    assert result["case_facts"]["variants"][0]["protein_change"] == "p.V600E"
    assert result["pathway"]["pathway"] == "MAPK / ERK"
    assert result["therapies"][0]["name"] == "Dabrafenib"
    assert result["evidence"][0]["figures"][0]["id"] == "fig1"
    assert result["evidence"][0]["tables"][0]["rows"][0][0] == "V600E"
    assert result["trials"][0]["nct_id"] == "NCT00000001"
    assert result["trace"][-1]["name"] == "compose_auditable_answer"
    assert any(action["type"] == "open_3d" for action in result["actions"])
    assert "not medical advice" in result["disclaimer"].lower()


@pytest.mark.asyncio
async def test_assistant_returns_404_for_unknown_case(session):
    with pytest.raises(Exception) as exc:
        await ask_ptc_assistant(
            PTCAssistantRequest(case_id="UNKNOWN", question="Explain this case"),
            db=session,
        )
    assert getattr(exc.value, "status_code", None) == 404
