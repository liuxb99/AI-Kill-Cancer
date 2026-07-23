"""
ClinicalTrials.gov adapter — free public API, no key required.

API: https://clinicaltrials.gov/api/v2/studies
Rate limit: reasonable use
License: Public government data
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime

import httpx

logger = logging.getLogger(__name__)

CT_BASE = "https://clinicaltrials.gov/api/v2"
DEFAULT_TIMEOUT = 30
RATE_LIMIT = 0.2


class ClinicalTrialsAdapter:
    """ClinicalTrials.gov API v2 adapter."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self._name = "clinicaltrials"
        self._version = "v2"
        self._base = self.config.get("api_base", CT_BASE)
        self._timeout = self.config.get("timeout", DEFAULT_TIMEOUT)
        self._last_request: float = 0.0

    async def _rate_limit(self):
        now = time.monotonic()
        elapsed = now - self._last_request
        if elapsed < RATE_LIMIT:
            await asyncio.sleep(RATE_LIMIT - elapsed)
        self._last_request = time.monotonic()

    async def health_check(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self._base}/studies?pageSize=1")
                return {"status": "ok", "version": self._version} if resp.status_code < 500 else {"status": "degraded"}
        except Exception as e:
            return {"status": "degraded", "detail": str(e)}

    def supports(self, query_type: str) -> bool:
        return query_type in ("trial", "clinical_trial", "nct", "condition", "intervention")

    async def search(self, query: str, max_results: int = 10) -> list[dict]:
        """Search trials by condition, intervention, or NCT ID."""
        await self._rate_limit()

        params = {
            "query.term": query,
            "pageSize": str(max_results),
            "format": "json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(f"{self._base}/studies", params=params)
                if resp.status_code != 200:
                    return []

                data = resp.json()
                studies = data.get("studies", [])
                return self._normalize(studies)

        except httpx.TimeoutException:
            logger.warning("ClinicalTrials.gov request timed out")
        except Exception as e:
            logger.warning("ClinicalTrials.gov request failed: %s", e)

        return []

    def _normalize(self, studies: list[dict]) -> list[dict]:
        records = []
        for study in studies:
            protocol = study.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            design_module = protocol.get("designModule", {})
            conditions_module = protocol.get("conditionsModule", {})

            nct_id = id_module.get("nctId", "")
            records.append({
                "source": "clinicaltrials",
                "source_record_id": nct_id,
                "nct_id": nct_id,
                "title": id_module.get("briefTitle", ""),
                "status": status_module.get("overallStatus", ""),
                "phase": design_module.get("phases", [""])[0] if design_module.get("phases") else "",
                "conditions": conditions_module.get("conditions", []),
                "sponsor": id_module.get("organization", {}).get("fullName", ""),
                "url": f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else "",
                "retrieved_at": datetime.now(UTC).isoformat(),
            })

        return records

    async def annotate(self, payload: dict, **kwargs) -> list[dict]:
        query = payload.get("query", payload.get("condition", payload.get("gene", "")))
        return await self.search(str(query)) if query else []
