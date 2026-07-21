"""
Adapter registry — central registry for all third-party data source integrations.
"""

from __future__ import annotations

from typing import Optional
from src.backend.adapters.base import BaseAdapter, NotConfiguredAdapter


class AdapterRegistry:
    """Registry of all data source adapters."""

    def __init__(self):
        self._adapters: dict[str, BaseAdapter] = {}

    def register(self, name: str, adapter: BaseAdapter) -> None:
        self._adapters[name] = adapter

    def get(self, name: str) -> Optional[BaseAdapter]:
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

    def health_all(self) -> dict[str, dict]:
        """Return health status for all registered adapters."""
        return {name: adapter.health_check() for name, adapter in self._adapters.items()}


# Global registry instance
_registry: Optional[AdapterRegistry] = None


def get_registry() -> AdapterRegistry:
    global _registry
    if _registry is None:
        _registry = AdapterRegistry()
        _register_defaults(_registry)
    return _registry


def _register_defaults(registry: AdapterRegistry) -> None:
    """Register all adapters. Phase 2A: VEP is REST API, OpenCRAVAT not_configured."""
    from src.backend.adapters.civic import CIViCAdapter
    from src.backend.adapters.dgidb import DGIdbAdapter
    from src.backend.adapters.oncotree import OncoTreeAdapter
    from src.backend.adapters.myvariant import MyVariantAdapter
    from src.backend.adapters.drkg import DRKGAdapter
    from src.backend.adapters.pharmcat import PharmCATAdapter
    from src.backend.pipeline.vep_adapter import VEPAdapter
    from src.backend.pipeline.opencravat_adapter import OpenCRAVATAdapter
    from src.backend.pipeline.normalization import BcftoolsAdapter

    registry.register("ensembl_vep", VEPAdapter())
    registry.register("opencravat", OpenCRAVATAdapter())
    registry.register("civic", CIViCAdapter(name="civic"))
    registry.register("dgidb", DGIdbAdapter(name="dgidb"))
    registry.register("oncotree", OncoTreeAdapter(name="oncotree"))
    registry.register("myvariant", MyVariantAdapter(name="myvariant"))
    registry.register("drkg", DRKGAdapter(name="drkg"))
    registry.register("pharmcat", PharmCATAdapter(name="pharmcat"))
    registry.register("bcftools", BcftoolsAdapter())
