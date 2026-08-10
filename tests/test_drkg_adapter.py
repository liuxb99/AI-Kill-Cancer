from pathlib import Path

import pytest

from src.backend.adapters.drkg import DRKGAdapter


@pytest.fixture
def drkg_file(tmp_path: Path) -> Path:
    path = tmp_path / "drkg.tsv"
    path.write_text(
        "Gene::BRAF\tDGIDB::INHIBITOR::Gene:Compound\tCompound::DB001\n"
        "Gene::RET\tSTRING::INTERACTS::Gene:Gene\tGene::NTRK1\n",
        encoding="utf-8",
    )
    return path


@pytest.mark.asyncio
async def test_health_check_requires_local_dataset(monkeypatch):
    adapter = DRKGAdapter()
    assert (await adapter.health_check())["status"] == "unavailable"


@pytest.mark.asyncio
async def test_query_matches_head_or_tail(drkg_file: Path):
    adapter = DRKGAdapter({"path": str(drkg_file)})
    result = await adapter.annotate({"query": "BRAF", "limit": 10}, request_id="drkg-test")
    assert result.success is True
    assert result.records == [
        {
            "head": "Gene::BRAF",
            "relation": "DGIDB::INHIBITOR::Gene:Compound",
            "tail": "Compound::DB001",
        }
    ]
    assert result.metadata["scanned_rows"] >= 1


@pytest.mark.asyncio
async def test_relation_only_query(drkg_file: Path):
    adapter = DRKGAdapter({"path": str(drkg_file)})
    result = await adapter.annotate({"relation": "STRING", "match": "contains"})
    assert result.success is True
    assert len(result.records) == 1
    assert result.records[0]["head"] == "Gene::RET"


@pytest.mark.asyncio
async def test_limit_validation(drkg_file: Path):
    adapter = DRKGAdapter({"path": str(drkg_file)})
    errors = await adapter.validate_input({"query": "BRAF", "limit": 0})
    assert errors == ["limit must be between 1 and 5000"]
