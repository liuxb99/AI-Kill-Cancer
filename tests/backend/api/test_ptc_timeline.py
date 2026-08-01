from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backend.api.v1.ptc_timeline import get_ptc_case_timeline
from src.backend.database.models import Base
from src.backend.domain.ptc_knowledge import (
    PTCEvidenceRecordModel,
    PTCTherapyModel,
    PTCTherapyTargetModel,
)
from src.backend.domain.ptc_research import (
    PTCImportBatchModel,
    PTCOutcomeModel,
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
async def test_timeline_labels_ingestion_observation_and_retrieval_dates(session):
    now = datetime.utcnow()
    case = PTCResearchCaseModel(
        case_id="TCGA-TIMELINE-001",
        source_dataset="TCGA-THCA",
        source_project="TCGA-THCA",
        pathologic_stage="Stage I",
        vital_status="Alive",
        created_at=now - timedelta(days=5),
        updated_at=now - timedelta(days=1),
    )
    session.add(case)
    await session.flush()
    session.add(
        PTCVariantModel(
            variant_id="timeline-braf",
            research_case_id=case.id,
            case_id=case.case_id,
            source_dataset="TCGA-THCA",
            gene="BRAF",
            protein_change="p.V600E",
            classification="Missense_Mutation",
            created_at=now - timedelta(days=4),
        )
    )
    session.add(
        PTCOutcomeModel(
            outcome_id="timeline-outcome",
            research_case_id=case.id,
            case_id=case.case_id,
            source_dataset="TCGA-THCA",
            outcome_type="vital_status",
            outcome_value="Alive",
            observed_at=now - timedelta(days=20),
            created_at=now - timedelta(days=3),
        )
    )
    therapy = PTCTherapyModel(
        therapy_key="openfda:dabrafenib",
        name="Dabrafenib",
        therapy_type="drug",
        source_name="openFDA",
        source_record_id="label-1",
        retrieved_at=now - timedelta(days=2),
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
            evidence_key="pubmed:timeline:braf",
            source_name="PubMed",
            source_record_id="123",
            title="BRAF timeline evidence",
            evidence_type="publication",
            gene_symbol="BRAF",
            retrieved_at=now - timedelta(hours=12),
            payload={"figures": [{"id": "fig1"}]},
        )
    )
    session.add(
        PTCImportBatchModel(
            batch_id="batch-timeline",
            source_dataset="TCGA-THCA",
            status="completed",
            record_count=10,
            started_at=now - timedelta(days=6),
            completed_at=now - timedelta(days=5, hours=23),
        )
    )
    await session.commit()

    result = await get_ptc_case_timeline("TCGA-TIMELINE-001", "BRAF", 250, session)

    assert result["selected_gene"] == "BRAF"
    types = {item["event_type"] for item in result["events"]}
    assert {"case_ingested", "case_updated", "variant_ingested", "outcome_recorded", "therapy_knowledge_ingested", "evidence_ingested", "import_batch"} <= types
    outcome = next(item for item in result["events"] if item["event_type"] == "outcome_recorded")
    assert outcome["date_semantics"] == "observed_at"
    evidence = next(item for item in result["events"] if item["event_type"] == "evidence_ingested")
    assert evidence["date_semantics"] == "retrieved_at"
    variant = next(item for item in result["events"] if item["event_type"] == "variant_ingested")
    assert variant["actions"][0]["type"] == "open_protein"
    assert result["trace"][-1]["name"] == "sort_and_limit_timeline"
    assert "not a patient chart" in result["disclaimer"]


@pytest.mark.asyncio
async def test_timeline_rejects_gene_not_in_case(session):
    session.add(PTCResearchCaseModel(case_id="TCGA-TIMELINE-EMPTY", source_dataset="TCGA-THCA", source_project="TCGA-THCA"))
    await session.commit()
    with pytest.raises(Exception) as exc:
        await get_ptc_case_timeline("TCGA-TIMELINE-EMPTY", "BRAF", 250, session)
    assert getattr(exc.value, "status_code", None) == 404
