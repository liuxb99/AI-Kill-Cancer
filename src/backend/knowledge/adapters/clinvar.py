"""
ClinVar adapter — free public API, no API key required.

API: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=clinvar
      https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=clinvar
Rate limit: 3 requests/second (NCBI standard)
License: ClinVar data is public domain
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime

import httpx

logger = logging.getLogger(__name__)

CLINVAR_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DEFAULT_TIMEOUT = 30
RATE_LIMIT = 0.35  # seconds between requests (< 3/sec)


class ClinVarAdapter:
    """ClinVar E-Utilities adapter for variant clinical assertions."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self._name = "clinvar"
        self._version = "1.0"
        self._base = self.config.get("api_base", CLINVAR_BASE)
        self._timeout = self.config.get("timeout", DEFAULT_TIMEOUT)
        self._last_request: float = 0.0

    async def _rate_limit(self):
        """Ensure we don't exceed NCBI rate limits."""
        now = time.monotonic()
        elapsed = now - self._last_request
        if elapsed < RATE_LIMIT:
            await asyncio.sleep(RATE_LIMIT - elapsed)
        self._last_request = time.monotonic()

    async def health_check(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self._base}/einfo.fcgi?db=clinvar")
                return {"status": "ok", "version": self._version} if resp.status_code < 500 else {"status": "degraded"}
        except Exception as e:
            return {"status": "degraded", "detail": str(e)}

    def supports(self, query_type: str) -> bool:
        return query_type in ("variant", "gene", "hgvs", "clinvar_id")

    async def search_variant(self, query: str, max_results: int = 10) -> list[dict]:
        """Search ClinVar by gene symbol or HGVS."""
        await self._rate_limit()
        results = []

        params = {
            "db": "clinvar",
            "term": query,
            "retmax": str(max_results),
            "retmode": "json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(f"{self._base}/esearch.fcgi", params=params)
                if resp.status_code != 200:
                    logger.warning("ClinVar search failed: %d", resp.status_code)
                    return results

                data = resp.json()
                ids = data.get("esearchresult", {}).get("idlist", [])
                if not ids:
                    return results

                # Fetch summaries
                await self._rate_limit()
                summary_params = {
                    "db": "clinvar",
                    "id": ",".join(ids),
                    "retmode": "json",
                }
                summary_resp = await client.get(f"{self._base}/esummary.fcgi", params=summary_params)
                if summary_resp.status_code == 200:
                    summary_data = summary_resp.json()
                    results = self._normalize_summaries(summary_data)

        except httpx.TimeoutException:
            logger.warning("ClinVar request timed out")
        except Exception as e:
            logger.warning("ClinVar request failed: %s", e)

        return results

    def _normalize_summaries(self, data: dict) -> list[dict]:
        """Normalize esummary JSON into our unified format."""
        records = []
        result_map = data.get("result", {})
        uids = result_map.get("uids", [])

        for uid in uids:
            item = result_map.get(uid, {})
            record = {
                "source": "clinvar",
                "source_record_id": str(uid),
                "gene_symbol": (item.get("genes", [{}])[0].get("symbol", "") if item.get("genes") else ""),
                "variant_name": item.get("title", ""),
                "clinical_significance": item.get("clinical_significance", {}).get("description", "") if isinstance(item.get("clinical_significance"), dict) else "",
                "disease": (item.get("trait_set", [{}])[0].get("trait_name", "") if item.get("trait_set") else ""),
                "review_status": item.get("review_status", ""),
                "url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/",
                "retrieved_at": datetime.now(UTC).isoformat(),
            }
            records.append(record)

        return records

    async def annotate(self, payload: dict, **kwargs) -> list[dict]:
        """Main entry point: accepts gene_symbol or hgvs."""
        gene = payload.get("gene", "")
        hgvs = payload.get("hgvs", "")
        query = hgvs or gene
        if not query:
            return []
        return await self.search_variant(query)
