"""
Unified response envelope for all adapter operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field


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
