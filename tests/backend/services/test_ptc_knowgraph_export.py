import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backend.database.models import Base
from src.backend.domain.ptc_integrated import PTCHerbDrugInteractionModel
from src.backend.services.ptc_knowgraph_export import PTCKnowGraphExportService, entity_uuid


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        yield db
    await engine.dispose()


@pytest.mark.asyncio
async def test_export_is_deterministic_and_fills_external_stubs(session):
    session.add(
        PTCHerbDrugInteractionModel(
            herb_key="missing-herb",
            therapy_key="missing-therapy",
            interaction_type="potential_interaction",
            severity="unknown",
            evidence_level="unknown",
            source_name="test",
        )
    )
    await session.commit()

    service = PTCKnowGraphExportService(session)
    first = await service.export()
    second = await service.export()

    assert first["entities"] == second["entities"]
    assert first["relations"] == second["relations"]
    assert first["metadata"]["entity_count"] == len(first["entities"])
    assert first["metadata"]["relation_count"] == len(first["relations"])
    ids = {item["id"] for item in first["entities"]}
    assert entity_uuid("therapy:missing-therapy") in ids
    assert entity_uuid("herb:missing-herb") in ids
    assert all(uuid.UUID(item["id"]) for item in first["entities"])
    assert all(item["from"] in ids and item["to"] in ids for item in first["relations"])
