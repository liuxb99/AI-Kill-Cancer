"""
Tests for adapter interfaces.
"""
from __future__ import annotations

import pytest

from src.backend.adapters.base import BaseAdapter, NotConfiguredAdapter, AdapterResult
from src.backend.adapters.registry import AdapterRegistry, get_registry


class TestNotConfiguredAdapter:
    async def test_health_check_returns_unavailable(self):
        adapter = NotConfiguredAdapter(name="test_adapter")
        health = await adapter.health_check()
        assert health["status"] == "unavailable"
        assert "not configured" in health["detail"]

    def test_supports_returns_false(self):
        adapter = NotConfiguredAdapter(name="test")
        assert adapter.supports("anything") is False

    async def test_annotate_returns_error(self):
        adapter = NotConfiguredAdapter(name="test")
        result = await adapter.annotate({})
        assert result.success is False
        assert "not configured" in str(result.errors[0]).lower()

    async def test_validate_input_returns_error(self):
        adapter = NotConfiguredAdapter(name="test")
        errors = await adapter.validate_input({})
        assert len(errors) > 0
        assert "not configured" in errors[0].lower()


class TestAdapterResult:
    def test_result_defaults(self):
        r = AdapterResult(
            source="test", source_version="1.0",
            retrieved_at="now", request_id="req-1",
            success=True,
        )
        assert r.records == []
        assert r.warnings == []
        assert r.errors == []
        assert r.license is None

    def test_to_dict(self):
        r = AdapterResult(
            source="test", source_version="1.0",
            retrieved_at="now", request_id="req-1",
            success=True,
            records=[{"id": 1}],
        )
        d = r.to_dict()
        assert d["source"] == "test"
        assert d["records_count"] == 1
        assert d["success"] is True


class TestAdapterRegistry:
    def test_registry_register_and_get(self):
        registry = AdapterRegistry()
        adapter = NotConfiguredAdapter(name="test")
        registry.register("test", adapter)
        assert registry.get("test") is adapter

    def test_registry_list(self):
        registry = AdapterRegistry()
        adapter = NotConfiguredAdapter(name="test")
        registry.register("test", adapter)
        listing = registry.list()
        assert "test" in listing
        assert listing["test"]["configured"] is False

    def test_default_registry_has_all_adapters(self):
        registry = get_registry()
        listing = registry.list()
        expected = ["ensembl_vep", "opencravat", "civic", "dgidb", "oncotree", "myvariant", "drkg", "pharmcat"]
        for name in expected:
            assert name in listing, f"Missing adapter: {name}"
            assert listing[name]["configured"] is False
