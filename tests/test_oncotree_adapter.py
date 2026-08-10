import pytest

from src.backend.adapters.oncotree import OncoTreeAdapter


@pytest.mark.asyncio
async def test_validate_input_requires_lookup_selector():
    adapter = OncoTreeAdapter()
    assert await adapter.validate_input({}) == ["Provide code, name/search, main_type, or all=true"]
    assert await adapter.validate_input({"code": "THPA"}) == []
    assert await adapter.validate_input({"name": "Papillary Thyroid Cancer"}) == []
    assert await adapter.validate_input({"all": True}) == []


def test_normalize_list_response():
    adapter = OncoTreeAdapter()
    result = adapter.normalize_response([{"code": "THPA", "name": "Papillary Thyroid Cancer"}])
    assert result.success is True
    assert result.records[0]["code"] == "THPA"
    assert "CC BY 4.0" in result.license


def test_normalize_wrapped_response():
    adapter = OncoTreeAdapter()
    result = adapter.normalize_response({"items": [{"code": "THPA"}]})
    assert result.success is True
    assert result.records == [{"code": "THPA"}]


def test_normalize_empty_response_is_failure():
    adapter = OncoTreeAdapter()
    result = adapter.normalize_response(None)
    assert result.success is False
    assert result.errors
