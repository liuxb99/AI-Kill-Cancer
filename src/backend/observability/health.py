"""
HealthChecker — health/readiness/liveness checks for all dependencies.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class HealthStatus:
    """Health check result."""
    def __init__(self, service: str, status: str, version: str = "",
                 latency_ms: float = 0.0, detail: str = ""):
        self.service = service
        self.status = status  # ok, degraded, unavailable
        self.version = version
        self.latency_ms = latency_ms
        self.detail = detail

    def to_dict(self) -> dict:
        d = {"service": self.service, "status": self.status}
        if self.version:
            d["version"] = self.version
        if self.latency_ms:
            d["latency_ms"] = round(self.latency_ms, 2)
        if self.detail:
            d["detail"] = self.detail
        return d


class HealthChecker:
    """
    Checks health of all system dependencies.
    """

    def __init__(self):
        self._db_available: bool = False
        self._model_available: bool = False

    def set_db_status(self, available: bool):
        self._db_available = available

    async def check_database(self) -> HealthStatus:
        """Check database connectivity."""
        start = time.monotonic()
        try:
            if self._db_available:
                return HealthStatus(
                    service="database", status="ok",
                    latency_ms=(time.monotonic() - start) * 1000,
                )
            return HealthStatus(
                service="database", status="degraded",
                detail="DB status not confirmed",
            )
        except Exception as e:
            return HealthStatus(
                service="database", status="unavailable",
                detail=str(e),
            )

    async def check_all(self) -> list[dict]:
        """Check all dependencies."""
        results = []
        results.append((await self.check_database()).to_dict())
        # Add other checks as they become available
        results.append({
            "service": "api", "status": "ok", "version": "1.0.0",
        })
        return results

    async def liveness(self) -> dict:
        """Basic liveness check."""
        return {"status": "alive", "timestamp": time.time()}

    async def readiness(self) -> dict:
        """Readiness check — all dependencies must be available."""
        checks = await self.check_all()
        all_ok = all(c.get("status") == "ok" for c in checks)
        return {
            "status": "ready" if all_ok else "not_ready",
            "checks": checks,
        }


# Global health checker
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker
