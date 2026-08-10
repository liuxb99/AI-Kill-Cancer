"""Tests for adapter interfaces and registry wiring."""
from __future__ import annotations

from src.backend.adapters.base import AdapterResult, BaseAdapter, NotConfiguredAdapter
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
        result = AdapterResult(
            source="test", source_version="1.0",
            retrieved_at="now", request_id="req-1",
            success=True,
        )
        assert result.records == []
        assert result.warnings == []
        assert result.errors == []
        assert result.license is None

    def test_to_dict(self):
        result = AdapterResult(
            source="test", source_version="1.0",
            retrieved_at="now", request_id="req-1",
            success=True,
            records=[{"id": 1}],
        )
        payload = result.to_dict()
        assert payload["source"] == "test"
        assert payload["records_count"] == 1
        assert payload["success"] is True


class _HealthyAdapter(BaseAdapter):
    def __init__(self, name: str, fail: bool = False):
        super().__init__()
        self._name = name
        self._version = "test"
        self.fail = fail

    async def health_check(self) -> dict:
        if self.fail:
            raise RuntimeError("boom")
        return {"status": "ok", "detail": self._name}

    def supports(self, query_type: str) -> bool:
        return True

    async def validate_input(self, payload):
        return []

    async def annotate(self, payload, **kwargs):
        return AdapterResult(
            source=self._name,
            source_version=self._version,
            retrieved_at="now",
            request_id="test",
            success=True,
        )

    def normalize_response(self, raw):
        return AdapterResult(
            source=self._name,
            source_version=self._version,
            retrieved_at="now",
            request_id="test",
            success=True,
        )


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

    async def test_health_all_awaits_and_isolates_adapter_failures(self):
        registry = AdapterRegistry()
        registry.register("good", _HealthyAdapter("good"))
        registry.register("bad", _HealthyAdapter("bad", fail=True))

        health = await registry.health_all()

        assert health["good"]["status"] == "ok"
        assert health["bad"]["status"] == "degraded"
        assert "boom" in health["bad"]["detail"]

    def test_default_registry_has_all_adapters(self):
        registry = get_registry()
        listing = registry.list()
        expected = [
            "ensembl_vep", "opencravat", "civic", "dgidb", "oncotree",
            "myvariant", "drkg", "pharmcat", "bcftools",
        ]
        for name in expected:
            assert name in listing, f"Missing adapter: {name}"

        # Public/implemented adapters must not silently resolve to the generic
        # NotConfiguredAdapter compatibility placeholder.
        for name in ["ensembl_vep", "opencravat", "civic", "dgidb", "myvariant", "bcftools"]:
            assert listing[name]["configured"] is True, f"{name} should use a concrete adapter"

        # These integrations intentionally require a local dataset/tool or a
        # future explicit implementation and therefore stay opt-in.
        for name in ["oncotree", "drkg", "pharmcat"]:
            assert listing[name]["configured"] is False, f"{name} should remain explicitly unavailable"
