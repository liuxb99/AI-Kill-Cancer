from copy import deepcopy

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backend.api.v1.ptc_snapshots import create_case_snapshot, verify_snapshot_document
from src.backend.database.models import Base
from src.backend.domain.ptc_knowledge import PTCEvidenceRecordModel
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
async def test_snapshot_is_reproducible_and_detects_tampering(session):
    case = PTCResearchCaseModel(
        case_id="TCGA-SNAPSHOT-001",
        source_dataset="TCGA-THCA",
        source_project="TCGA-THCA",
        pathologic_stage="Stage I",
    )
    session.add(case)
    await session.flush()
    session.add(
        PTCVariantModel(
            variant_id="snapshot-braf-v600e",
            research_case_id=case.id,
            case_id=case.case_id,
            source_dataset="TCGA-THCA",
            gene="BRAF",
            protein_change="p.V600E",
            classification="Missense_Mutation",
        )
    )
    session.add(
        PTCEvidenceRecordModel(
            evidence_key="pubmed:snapshot:braf",
            source_name="PubMed",
            source_record_id="snapshot-pmid",
            title="BRAF snapshot evidence",
            evidence_type="publication",
            evidence_level="A",
            direction="supports",
            gene_symbol="BRAF",
            source_url="https://pubmed.ncbi.nlm.nih.gov/1/",
            payload={"figures": [{"id": "fig1"}]},
        )
    )
    await session.commit()

    first = await create_case_snapshot("TCGA-SNAPSHOT-001", "BRAF", session)
    second = await create_case_snapshot("TCGA-SNAPSHOT-001", "BRAF", session)

    assert first["schema"] == "ptc-research-snapshot-v1"
    assert first["content"]["case"]["case_id"] == "TCGA-SNAPSHOT-001"
    assert first["content"]["variants"][0]["protein_change"] == "p.V600E"
    assert first["content"]["evidence"][0]["title"] == "BRAF snapshot evidence"
    assert first["checksum_sha256"] == second["checksum_sha256"]
    assert verify_snapshot_document(first)["valid"] is True

    tampered = deepcopy(first)
    tampered["content"]["variants"][0]["protein_change"] = "p.V601E"
    verification = verify_snapshot_document(tampered)
    assert verification["valid"] is False
    assert verification["actual"] != verification["expected"]


def test_snapshot_verifier_rejects_missing_content():
    result = verify_snapshot_document({"checksum_sha256": "abc"})
    assert result["valid"] is False
    assert result["reason"]
