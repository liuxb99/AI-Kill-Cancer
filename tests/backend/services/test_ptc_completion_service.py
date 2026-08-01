from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backend.database.models import Base
from src.backend.domain.ptc_integrated import PTCHerbDrugInteractionModel
from src.backend.domain.ptc_knowledge import (
    PTCClinicalTrialModel,
    PTCEvidenceRecordModel,
    PTCTherapyModel,
    PTCTherapyTargetModel,
)
from src.backend.domain.ptc_research import PTCOutcomeModel, PTCResearchCaseModel, PTCVariantModel
from src.backend.importers.ptc_tcga.downloader import GDCClient
from src.backend.services.ptc_completion_service import PTCCompletionService
from src.backend.services.ptc_integrated_service import PTCIntegratedService
from src.backend.services.ptc_knowledge_service import PTCKnowledgeService
from src.backend.services.ptc_literature_service import PTCLiteratureService


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        yield db
    await engine.dispose()


async def seed(session):
    case = PTCResearchCaseModel(case_id="TCGA-PTC-COMPLETE", pathologic_stage="Stage II", vital_status="Alive")
    session.add(case)
    await session.flush()
    session.add(
        PTCVariantModel(
            variant_id="braf-v600e",
            research_case_id=case.id,
            case_id=case.case_id,
            gene="BRAF",
            protein_change="p.V600E",
            classification="Missense_Mutation",
        )
    )
    session.add(
        PTCOutcomeModel(
            outcome_id="alive-followup",
            research_case_id=case.id,
            case_id=case.case_id,
            outcome_type="vital_status",
            outcome_value="Alive",
        )
    )
    therapy = PTCTherapyModel(
        therapy_key="openfda:dabrafenib",
        name="Dabrafenib",
        generic_name="dabrafenib",
        source_name="openFDA",
        source_record_id="dabrafenib-label",
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
            evidence_key="pubmed:braf-ptc",
            source_name="PubMed",
            source_record_id="12345",
            evidence_type="publication",
            evidence_level="published_literature",
            gene_symbol="BRAF",
            therapy_id=therapy.id,
            title="BRAF evidence in PTC",
        )
    )
    session.add(
        PTCClinicalTrialModel(
            nct_id="NCT00000001",
            brief_title="BRAF targeted PTC trial",
            target_genes=["BRAF"],
            phases=["PHASE2"],
            overall_status="RECRUITING",
        )
    )
    await session.commit()
    await PTCIntegratedService(session).bootstrap_herbal_research()
    session.add(
        PTCHerbDrugInteractionModel(
            herb_key="tcm:herb:curcuma-longa:rhizome",
            therapy_key="openfda:dabrafenib",
            interaction_type="potential_pharmacokinetic",
            severity="unknown",
            evidence_level="preclinical",
            source_name="test",
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_status_outcomes_and_full_graph(session):
    await seed(session)
    service = PTCCompletionService(session)

    status = await service.source_status()
    assert status["cases"] == 1
    assert status["variants"] == 1
    assert status["therapies"] == 1
    assert status["herbs"] == 3

    outcomes = await service.outcome_by_gene()
    assert outcomes[0]["gene"] == "BRAF"
    assert outcomes[0]["vital_status"]["Alive"] == 1

    graph = await service.full_graph()
    node_types = {node["type"] for node in graph["nodes"]}
    relations = {edge["relation"] for edge in graph["edges"]}
    assert {"ResearchCase", "Variant", "Gene", "Therapy", "Evidence", "ClinicalTrial", "ChineseHerb"} <= node_types
    assert {"HAS_VARIANT", "AFFECTS_GENE", "TARGETS", "SUPPORTED_BY", "STUDIES_GENE", "INTERACTS_WITH"} <= relations
    assert graph["node_count"] == len(graph["nodes"])
    assert graph["edge_count"] == len(graph["edges"])


@pytest.mark.asyncio
async def test_sync_all_rolls_back_failed_source_and_continues(session, monkeypatch):
    def fail_gdc(*args, **kwargs):
        raise RuntimeError("GDC unavailable")

    monkeypatch.setattr(GDCClient, "fetch_ptc_cases_with_mutations", fail_gdc)
    monkeypatch.setattr(PTCKnowledgeService, "sync_clinical_trials", AsyncMock(return_value=0))
    monkeypatch.setattr(PTCKnowledgeService, "sync_openfda_labels", AsyncMock(return_value=0))
    monkeypatch.setattr(PTCLiteratureService, "sync_pubmed", AsyncMock(return_value=0))
    monkeypatch.setattr(
        PTCIntegratedService,
        "bootstrap_herbal_research",
        AsyncMock(return_value={"herbs_created": 0, "compounds_created": 0}),
    )
    rollback = AsyncMock(wraps=session.rollback)
    monkeypatch.setattr(session, "rollback", rollback)

    result = await PTCCompletionService(session).sync_all(
        gdc_size=1,
        gdc_mutation_files=1,
        trial_size=1,
        pubmed_size=1,
        drug_names=["dabrafenib"],
    )

    assert result["status"] == "completed_with_errors"
    assert result["stages"]["gdc_tcga_thca"]["status"] == "failed"
    assert result["stages"]["clinical_trials"]["status"] == "success"
    assert result["stages"]["openfda"]["status"] == "success"
    assert result["stages"]["pubmed"]["status"] == "success"
    assert result["stages"]["scientific_chinese_medicine_seed"]["status"] == "success"
    assert rollback.await_count >= 1
    assert result["summary"]["cases"] == 0
