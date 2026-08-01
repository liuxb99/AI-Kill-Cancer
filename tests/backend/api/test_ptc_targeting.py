import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backend.api.v1 import ptc_targeting
from src.backend.database.models import Base
from src.backend.domain.ptc_knowledge import (
    PTCEvidenceRecordModel,
    PTCTherapyModel,
    PTCTherapyTargetModel,
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
async def test_braf_targeting_returns_pathway_therapy_and_evidence(session):
    therapy = PTCTherapyModel(
        therapy_key="openfda:dabrafenib",
        name="Dabrafenib",
        generic_name="dabrafenib",
        therapy_type="drug",
        approval_status="approved",
        indications=["BRAF V600E"],
        mechanism="BRAF kinase inhibitor",
        source_name="openFDA",
        source_record_id="dabrafenib",
    )
    session.add(therapy)
    await session.flush()
    session.add(
        PTCTherapyTargetModel(
            therapy_id=therapy.id,
            gene_symbol="BRAF",
            variant="V600E",
            interaction_type="inhibits",
            evidence_level="A",
        )
    )
    session.add(
        PTCEvidenceRecordModel(
            evidence_key="test:braf:v600e",
            source_name="test",
            source_record_id="braf-v600e",
            title="BRAF V600E targeted evidence",
            evidence_type="clinical",
            evidence_level="A",
            direction="supports",
            gene_symbol="BRAF",
            variant="V600E",
            therapy_id=therapy.id,
        )
    )
    await session.commit()

    result = await ptc_targeting.gene_targeting("braf", db=session)

    assert result["gene"] == "BRAF"
    assert result["pathway"]["pathway"] == "MAPK / ERK"
    assert result["pathway"]["domain_range"] == [457, 717]
    assert result["pathway"]["hotspots"]["V600E"] == 600
    assert result["counts"]["therapies"] == 1
    assert result["therapies"][0]["name"] == "Dabrafenib"
    assert result["therapies"][0]["matched_targets"][0]["variant"] == "V600E"
    assert result["counts"]["evidence"] == 1


@pytest.mark.asyncio
async def test_uncurated_gene_returns_empty_safe_chain(session):
    result = await ptc_targeting.gene_targeting("unknown", db=session)

    assert result["gene"] == "UNKNOWN"
    assert result["pathway"]["pathway"] == "Uncurated PTC pathway"
    assert result["counts"] == {"therapies": 0, "evidence": 0, "trials": 0}
