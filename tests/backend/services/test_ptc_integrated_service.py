import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backend.database.models import Base
from src.backend.domain.ptc_integrated import PTCHerbModel, PTCRecommendationSnapshotModel
from src.backend.domain.ptc_knowledge import PTCEvidenceRecordModel, PTCTherapyModel, PTCTherapyTargetModel
from src.backend.domain.ptc_research import PTCResearchCaseModel, PTCVariantModel
from src.backend.services.ptc_integrated_service import PTCIntegratedService


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        yield db
    await engine.dispose()


async def _seed_cases(session):
    first = PTCResearchCaseModel(case_id="TCGA-PTC-001", pathologic_stage="Stage I")
    second = PTCResearchCaseModel(case_id="TCGA-PTC-002", pathologic_stage="Stage I")
    third = PTCResearchCaseModel(case_id="TCGA-PTC-003", pathologic_stage="Stage III")
    session.add_all([first, second, third])
    await session.flush()
    session.add_all(
        [
            PTCVariantModel(variant_id="v1", research_case_id=first.id, case_id=first.case_id, gene="BRAF"),
            PTCVariantModel(variant_id="v2", research_case_id=first.id, case_id=first.case_id, gene="TERT"),
            PTCVariantModel(variant_id="v3", research_case_id=second.id, case_id=second.case_id, gene="BRAF"),
            PTCVariantModel(variant_id="v4", research_case_id=third.id, case_id=third.case_id, gene="RET"),
        ]
    )
    therapy = PTCTherapyModel(
        therapy_key="openfda:test-braf",
        name="BRAF research therapy",
        generic_name="dabrafenib",
        source_name="openFDA",
        source_record_id="test-braf",
        approval_status="FDA label available",
    )
    session.add(therapy)
    await session.flush()
    session.add(
        PTCTherapyTargetModel(
            therapy_id=therapy.id,
            gene_symbol="BRAF",
            variant="V600E",
            target_type="molecular_target",
        )
    )
    session.add(
        PTCEvidenceRecordModel(
            evidence_key="evidence-braf",
            source_name="PubMed",
            source_record_id="123",
            evidence_type="publication",
            evidence_level="clinical",
            gene_symbol="BRAF",
            title="BRAF evidence",
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_bootstrap_herbs_is_idempotent(session):
    service = PTCIntegratedService(session)
    first = await service.bootstrap_herbal_research()
    second = await service.bootstrap_herbal_research()
    assert first["herbs_created"] == 3
    assert second["herbs_created"] == 0
    assert len(list((await session.execute(__import__("sqlalchemy").select(PTCHerbModel))).scalars())) == 3


@pytest.mark.asyncio
async def test_similarity_and_recommendation(session):
    await _seed_cases(session)
    service = PTCIntegratedService(session)
    await service.bootstrap_herbal_research()

    similar = await service.calculate_similarities("TCGA-PTC-001")
    assert similar[0]["similar_case_id"] == "TCGA-PTC-002"
    assert "BRAF" in similar[0]["shared_genes"]

    result = await service.generate_research_recommendation("TCGA-PTC-001")
    assert result["ranked_therapies"][0]["generic_name"] == "dabrafenib"
    assert result["supporting_evidence"][0]["source_name"] == "PubMed"
    assert any(item["chinese_name"] for item in result["herb_research"])
    assert "not a prescription" in result["explanation"]
    snapshots = list((await session.execute(__import__("sqlalchemy").select(PTCRecommendationSnapshotModel))).scalars())
    assert len(snapshots) == 1


@pytest.mark.asyncio
async def test_dashboard_counts(session):
    await _seed_cases(session)
    await PTCIntegratedService(session).bootstrap_herbal_research()
    dashboard = await PTCIntegratedService(session).dashboard()
    assert dashboard.case_count == 3
    assert dashboard.variant_count == 4
    assert dashboard.therapy_count == 1
    assert dashboard.herb_count == 3
    assert dashboard.top_genes[0]["gene"] == "BRAF"
