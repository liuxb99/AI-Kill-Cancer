"""Adapter registry — central registry for all third-party data source integrations."""

from __future__ import annotations

import asyncio

from src.backend.adapters.base import BaseAdapter, NotConfiguredAdapter


class AdapterRegistry:
    """Registry of all data source adapters."""

    def __init__(self):
        self._adapters: dict[str, BaseAdapter] = {}

    def register(self, name: str, adapter: BaseAdapter) -> None:
        self._adapters[name] = adapter

    def get(self, name: str) -> BaseAdapter | None:
        return self._adapters.get(name)

    def list(self) -> dict[str, dict]:
        return {
            name: {
                "name": adapter.name,
                "version": adapter.version,
                "configured": not isinstance(adapter, NotConfiguredAdapter),
            }
            for name, adapter in self._adapters.items()
        }

    async def health_all(self) -> dict[str, dict]:
        """Return resolved health status for all registered adapters.

        ``BaseAdapter.health_check`` is asynchronous.  The previous registry
        returned coroutine objects, which made the aggregate health endpoint
        unusable and could leak un-awaited coroutine warnings.  Health checks
        now execute concurrently and failures are isolated per adapter.
        """
        names = list(self._adapters)

        async def check(name: str) -> dict:
            try:
                result = await self._adapters[name].health_check()
                return result if isinstance(result, dict) else {
                    "status": "degraded",
                    "detail": "Adapter returned a non-object health result",
                }
            except Exception as exc:  # pragma: no cover - defensive boundary
                return {"status": "degraded", "detail": str(exc)}

        results = await asyncio.gather(*(check(name) for name in names))
        return dict(zip(names, results, strict=True))


# Global registry instance
_registry: AdapterRegistry | None = None


def get_registry() -> AdapterRegistry:
    global _registry
    if _registry is None:
        _registry = AdapterRegistry()
        _register_defaults(_registry)
    return _registry


def _register_defaults(registry: AdapterRegistry) -> None:
    """Register implemented adapters and explicit optional integrations."""
    from src.backend.adapters.civic import CIViCAdapter
    from src.backend.adapters.dgidb import DGIdbAdapter
    from src.backend.adapters.drkg import DRKGAdapter
    from src.backend.adapters.myvariant import MyVariantAdapter
    from src.backend.adapters.oncotree import OncoTreeAdapter
    from src.backend.adapters.pharmcat import PharmCATAdapter
    from src.backend.pipeline.normalization import BcftoolsAdapter
    from src.backend.pipeline.opencravat_adapter import OpenCRAVATAdapter
    from src.backend.pipeline.vep_adapter import VEPAdapter

    registry.register("ensembl_vep", VEPAdapter())
    registry.register("opencravat", OpenCRAVATAdapter())
    registry.register("civic", CIViCAdapter())
    registry.register("dgidb", DGIdbAdapter())
    registry.register("oncotree", OncoTreeAdapter(name="oncotree"))
    registry.register("myvariant", MyVariantAdapter())
    registry.register("drkg", DRKGAdapter(name="drkg"))
    registry.register("pharmcat", PharmCATAdapter(name="pharmcat"))
    registry.register("bcftools", BcftoolsAdapter())
