"""
OpenCRAVAT adapter — not configured in Phase 2A.

OpenCRAVAT is a multi-source variant annotation tool that provides
gene, transcript, protein, and consequence information.

This adapter will be implemented when OpenCRAVAT is installed.
Phase 2A: Returns not_configured status.
"""

from __future__ import annotations

from typing import Any, Optional

from src.backend.adapters.base import NotConfiguredAdapter, AdapterResult, BaseAdapter


class OpenCRAVATAdapter(BaseAdapter):
    """OpenCRAVAT adapter — not configured in Phase 2A."""

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._name = "opencravat"
        self._version = "not_configured"
        self._fallback = NotConfiguredAdapter(name="opencravat")

    async def health_check(self) -> dict:
        """OpenCRAVAT is not available — return unavailable."""
        return {
            "status": "unavailable",
            "detail": "OpenCRAVAT is not installed or configured in Phase 2A. "
                      "Install open-cravat package and configure path to enable.",
            "version": self._version,
        }

    def supports(self, query_type: str) -> bool:
        return query_type in ("annotate", "variant", "gene")

    async def validate_input(self, payload: Any) -> list[str]:
        return await self._fallback.validate_input(payload)

    async def annotate(self, payload: Any, **kwargs) -> AdapterResult:
        """OpenCRAVAT is not configured — return not_configured status.

        Never returns success=True or synthetic data.
        """
        from datetime import datetime, timezone
        return AdapterResult(
            source="opencravat",
            source_version="not_configured",
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            request_id=kwargs.get("request_id", "unknown"),
            success=False,
            errors=["OpenCRAVAT is not configured. Install open-cravat and set OPENCVT_PATH."],
            warnings=["Variant annotation via OpenCRAVAT is not available in Phase 2A"],
        )

    def normalize_response(self, raw: Any) -> AdapterResult:
        return AdapterResult(source="opencravat", source_version="not_configured",
                             retrieved_at="", request_id="", success=False,
                             errors=["OpenCRAVAT not configured"])
