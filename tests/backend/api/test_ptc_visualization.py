from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backend.api.v1 import ptc_visualization
from src.backend.database.models import Base
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
async def test_latest_cases_are_sorted_by_update_time(session):
    older = PTCResearchCaseModel(
        case_id="TCGA-OLD-001",
        source_dataset="TCGA-THCA",
        updated_at=datetime.utcnow() - timedelta(days=2),
    )
    latest = PTCResearchCaseModel(
        case_id="TCGA-NEW-001",
        source_dataset="TCGA-THCA",
        updated_at=datetime.utcnow(),
    )
    session.add_all([older, latest])
    await session.flush()
    session.add(
        PTCVariantModel(
            variant_id="TCGA-NEW-001:BRAF:V600E",
            research_case_id=latest.id,
            case_id=latest.case_id,
            source_dataset="TCGA-THCA",
            gene="BRAF",
            protein_change="p.V600E",
        )
    )
    await session.commit()

    result = await ptc_visualization.latest_cases(limit=100, db=session)

    assert result["count"] == 2
    assert [item["case_id"] for item in result["cases"]] == ["TCGA-NEW-001", "TCGA-OLD-001"]
    assert result["cases"][0]["variants"][0]["gene"] == "BRAF"
    assert result["cases"][0]["updated_at"] is not None


@pytest.mark.asyncio
async def test_protein_structure_uses_static_files_and_builtin_renderer():
    result = await ptc_visualization.protein_structure("braf")

    assert result["gene"] == "BRAF"
    assert result["uniprot"] == "P15056"
    assert result["pdb_url"] == "https://alphafold.ebi.ac.uk/files/AF-P15056-F1-model_v6.pdb"
    assert result["pdb_urls"] == [
        "https://alphafold.ebi.ac.uk/files/AF-P15056-F1-model_v6.pdb",
        "https://alphafold.ebi.ac.uk/files/AF-P15056-F1-model_v4.pdb",
    ]
    assert result["cif_url"].endswith("model_v6.cif")
    assert result["renderer"] == "builtin-threejs-pdb"
    assert result["uses_alphafold_api"] is False
    assert result["default_pdb_id"] == "1UWH"
    assert result["experimental_structures"][0]["pdb_url"].endswith("/1UWH.pdb")
    assert "4MNE" in result["experimental_pdb_ids"]


def test_visualization_module_has_no_alphafold_api_client():
    assert not hasattr(ptc_visualization, "_fetch_alphafold_metadata")
    assert not hasattr(ptc_visualization, "_ALPHAFOLD_CACHE")


@pytest.mark.asyncio
async def test_unknown_gene_returns_404():
    with pytest.raises(Exception) as exc:
        await ptc_visualization.protein_structure("UNKNOWN_GENE")
    assert getattr(exc.value, "status_code", None) == 404
