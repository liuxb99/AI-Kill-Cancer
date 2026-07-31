import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backend.database.models import Base
from src.backend.domain.ptc_knowledge import PTCClinicalTrialModel, PTCTherapyModel
from src.backend.services.ptc_knowledge_service import PTCKnowledgeService


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        yield db
    await engine.dispose()


@pytest.mark.asyncio
async def test_sync_clinical_trials_is_idempotent(session):
    payload = {
        "studies": [
            {
                "protocolSection": {
                    "identificationModule": {"nctId": "NCT00000001", "briefTitle": "PTC targeted therapy"},
                    "statusModule": {"overallStatus": "RECRUITING"},
                    "designModule": {"phases": ["PHASE2"], "studyType": "INTERVENTIONAL", "enrollmentInfo": {"count": 30}},
                    "conditionsModule": {"conditions": ["Papillary Thyroid Carcinoma"]},
                    "armsInterventionsModule": {"interventions": [{"name": "Example Drug", "type": "DRUG"}]},
                    "eligibilityModule": {"eligibilityCriteria": "Adults"},
                    "contactsLocationsModule": {"locations": [{"facility": "Center", "country": "Taiwan"}]},
                }
            }
        ]
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = PTCKnowledgeService(session, client)
        assert await service.sync_clinical_trials() == 1
        assert await service.sync_clinical_trials() == 1

    assert await session.scalar(select(func.count()).select_from(PTCClinicalTrialModel)) == 1
    trial = await session.scalar(select(PTCClinicalTrialModel))
    assert trial.nct_id == "NCT00000001"
    assert trial.interventions[0]["name"] == "Example Drug"


@pytest.mark.asyncio
async def test_sync_openfda_labels_persists_label_fields(session):
    payload = {
        "results": [
            {
                "id": "label-1",
                "effective_time": "20260101",
                "openfda": {"brand_name": ["Example"], "generic_name": ["example drug"]},
                "indications_and_usage": ["For selected patients."],
                "mechanism_of_action": ["Selective inhibitor."],
                "boxed_warning": ["Important warning."],
            }
        ]
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = PTCKnowledgeService(session, client)
        assert await service.sync_openfda_labels(["example drug"]) == 1

    therapy = await session.scalar(select(PTCTherapyModel))
    assert therapy.generic_name == "example drug"
    assert therapy.indications == ["For selected patients."]
    assert therapy.warnings == ["Important warning."]
