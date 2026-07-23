"""
Base adapter interface for all external data sources.

Each third-party integration (VEP, OpenCRAVAT, CIViC, DGIdb, OncoTree, ...)
implements this base class to ensure consistent health check, input validation,
annotation/query, response normalization, and provenance tracking.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class AdapterResult:
    """Unified result envelope for all adapter operations."""
    source: str
    source_version: str
    retrieved_at: str
    request_id: str
    success: bool
    records: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    license: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "source_version": self.source_version,
            "retrieved_at": self.retrieved_at,
            "request_id": self.request_id,
            "success": self.success,
            "records_count": len(self.records),
            "warnings": self.warnings,
            "errors": self.errors,
            "license": self.license,
        }


class BaseAdapter(ABC):
    """Abstract base adapter for external data source integration."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self._name: str = "base_adapter"
        self._version: str = "0.0.0"

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    @abstractmethod
    async def health_check(self) -> dict:
        """Check if the adapter is properly configured and reachable.
        Returns: {"status": "ok"|"degraded"|"unavailable", "detail": str}
        """
        ...

    @abstractmethod
    def supports(self, query_type: str) -> bool:
        """Check if this adapter supports a given query type (e.g., 'variant', 'gene', 'drug')."""
        ...

    @abstractmethod
    async def validate_input(self, payload: Any) -> list[str]:
        """Validate input payload. Returns list of error messages (empty = valid)."""
        ...

    @abstractmethod
    async def annotate(self, payload: Any, **kwargs) -> AdapterResult:
        """Run annotation or query against the external source."""
        ...

    @abstractmethod
    def normalize_response(self, raw: Any) -> AdapterResult:
        """Normalize raw external response into unified AdapterResult format."""
        ...

    def provenance(self, request_id: str) -> dict:
        """Return provenance metadata for this adapter call."""
        return {
            "source": self._name,
            "source_version": self._version,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "request_id": request_id,
        }


class NotConfiguredAdapter(BaseAdapter):
    """Placeholder for adapters that are not yet configured."""

    def __init__(self, name: str = "not_configured", config: dict | None = None):
        super().__init__(config)
        self._name = name
        self._version = "0.0.0"

    async def health_check(self) -> dict:
        return {"status": "unavailable", "detail": f"Adapter '{self._name}' is not configured"}

    def supports(self, query_type: str) -> bool:
        return False

    async def validate_input(self, payload: Any) -> list[str]:
        return [f"Adapter '{self._name}' is not configured"]

    async def annotate(self, payload: Any, **kwargs) -> AdapterResult:
        return AdapterResult(
            source=self._name,
            source_version=self._version,
            retrieved_at=datetime.now(UTC).isoformat(),
            request_id="none",
            success=False,
            errors=[f"Adapter '{self._name}' is not configured"],
        )

    def normalize_response(self, raw: Any) -> AdapterResult:
        return AdapterResult(
            source=self._name,
            source_version=self._version,
            retrieved_at=datetime.now(UTC).isoformat(),
            request_id="none",
            success=False,
            errors=["Not configured"],
        )
