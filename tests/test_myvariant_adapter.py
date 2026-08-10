import pytest

from src.backend.adapters.myvariant import MyVariantAdapter


@pytest.mark.asyncio
async def test_validate_input_accepts_hgvs_and_structured_variant():
    adapter = MyVariantAdapter()
    assert await adapter.validate_input({"hgvs": "chr7:g.140753336A>T"}) == []
    assert await adapter.validate_input(
        {
            "variants": [
                {
                    "chromosome": "chr7",
                    "position": 140753336,
                    "reference": "A",
                    "alternate": "T",
                }
            ]
        }
    ) == []


@pytest.mark.asyncio
async def test_validate_input_rejects_missing_identifier():
    adapter = MyVariantAdapter()
    errors = await adapter.validate_input({"variants": [{}]})
    assert errors
    assert "missing identifier" in errors[0].lower()


def test_structured_variant_builds_genomic_hgvs_identifier():
    identifier = MyVariantAdapter._variant_identifier(
        {
            "chromosome": "chr7",
            "position": 140753336,
            "reference": "A",
            "alternate": "T",
        }
    )
    assert identifier == "chr7:g.140753336A>T"


def test_normalize_query_response():
    adapter = MyVariantAdapter()
    result = adapter.normalize_response({"hits": [{"_id": "chr7:g.140753336A>T"}]})
    assert result.success is True
    assert result.records[0]["_id"] == "chr7:g.140753336A>T"


def test_normalize_empty_response_is_failure():
    adapter = MyVariantAdapter()
    result = adapter.normalize_response(None)
    assert result.success is False
    assert result.errors
