"""
CIViC adapter — clinical evidence integration via CIViC REST API.

Provides:
- lookup_variant() by gene + coordinates
- lookup_gene() by symbol
- lookup_hgvs() by HGVS notation
- Evidence items, assertions, molecular profiles
- Disease, drug, evidence level/direction mapping

API: https://civicdb.org/api
License: CIViC data is CC-BY-4.0
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from src.backend.adapters.base import BaseAdapter, AdapterResult

logger = logging.getLogger(__name__)

CIVIC_API_BASE = "https://civicdb.org/api"
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 2

EVIDENCE_LEVEL_MAP = {
    "A": "Level_1",
    "B": "Level_2",
    "C": "Level_3",
    "D": "Level_4",
    "E": "Level_5",
}

EVIDENCE_DIRECTION_MAP = {
    "Supports": "supporting",
    "Does Not Support": "conflicting",
    "Conflicting": "conflicting",
}


class CIViCAdapter(BaseAdapter):
    """CIViC REST API adapter for clinical evidence."""

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._name = "civic"
        self._version = "2.0"
        self._api_base = config.get("api_base", CIVIC_API_BASE) if config else CIVIC_API_BASE
        self._timeout = config.get("timeout", DEFAULT_TIMEOUT) if config else DEFAULT_TIMEOUT

    async def health_check(self) -> dict:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self._api_base}/")
                return {"status": "ok", "version": self._version} if resp.status_code < 500 else {"status": "degraded"}
        except Exception as e:
            return {"status": "degraded", "detail": str(e)}

    def supports(self, query_type: str) -> bool:
        return query_type in ("variant", "gene", "hgvs", "evidence", "lookup")

    async def validate_input(self, payload: Any) -> list[str]:
        errors = []
        if isinstance(payload, dict):
            if not payload.get("gene") and not payload.get("hgvs") and not payload.get("coordinates"):
                errors.append("Must provide one of: gene, hgvs, coordinates")
        return errors

    async def lookup_gene(self, gene_symbol: str, request_id: str = "") -> AdapterResult:
        import httpx
        url = f"{self._api_base}/genes/{gene_symbol}"
        return await self._api_get(url, request_id)

    async def lookup_variant(self, gene_symbol: str, variant_name: str = "", request_id: str = "") -> AdapterResult:
        import httpx
        url = f"{self._api_base}/genes/{gene_symbol}/variants"
        params = {}
        if variant_name:
            params["name"] = variant_name
        return await self._api_get(url, request_id, params=params)

    async def lookup_hgvs(self, hgvs: str, request_id: str = "") -> AdapterResult:
        import httpx
        url = f"{self._api_base}/variants"
        params = {"hgvs": hgvs}
        return await self._api_get(url, request_id, params=params)

    async def lookup_coordinates(self, chromosome: str, position: int, reference: str, alternate: str, request_id: str = "") -> AdapterResult:
        import httpx
        region = f"{chromosome}:{position}:{reference}:{alternate}"
        url = f"{self._api_base}/variants"
        params = {"region": region}
        return await self._api_get(url, request_id, params=params)

    async def annotate(self, payload: Any, **kwargs) -> AdapterResult:
        request_id = kwargs.get("request_id", "unknown")
        if isinstance(payload, dict):
            gene = payload.get("gene", "")
            hgvs = payload.get("hgvs", "")
            chrom = payload.get("chromosome", "")
            pos = payload.get("position", 0)
            ref = payload.get("reference", "")
            alt = payload.get("alternate", "")
            if hgvs:
                return await self.lookup_hgvs(hgvs, request_id)
            if gene:
                return await self.lookup_variant(gene, payload.get("variant", ""), request_id)
            if chrom and pos:
                return await self.lookup_coordinates(chrom, pos, ref, alt, request_id)
        return AdapterResult(source="civic", source_version=self._version, retrieved_at="",
                             request_id=request_id, success=False, errors=["Invalid lookup payload"])

    async def _api_get(self, url: str, request_id: str, params: Optional[dict] = None) -> AdapterResult:
        import httpx
        request_params = params or {}
        request_hash = hashlib.sha256(f"{url}:{json.dumps(request_params, sort_keys=True)}".encode()).hexdigest()
        records = []
        errors = []
        warnings = []

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(MAX_RETRIES + 1):
                try:
                    resp = await client.get(url, params=request_params, headers={"Accept": "application/json"})
                    if resp.status_code == 200:
                        data = resp.json()
                        response_hash = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
                        records = self._normalize_results(data, url)
                        return AdapterResult(
                            source="civic", source_version=self._version,
                            retrieved_at=datetime.now(timezone.utc).isoformat(),
                            request_id=request_id, success=True, records=records,
                            metadata={"api_url": url, "request_hash": request_hash, "response_hash": response_hash, "license": "CC-BY-4.0"},
                        )
                    elif resp.status_code == 404:
                        return AdapterResult(source="civic", source_version=self._version, retrieved_at=datetime.now(timezone.utc).isoformat(),
                                             request_id=request_id, success=True, records=[], warnings=["Not found in CIViC"])
                    elif resp.status_code == 429:
                        if attempt < MAX_RETRIES:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        errors.append("Rate limited after retries")
                    else:
                        errors.append(f"CIViC API returned {resp.status_code}")
                        break
                except httpx.TimeoutException:
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(1)
                        continue
                    errors.append("Request timed out")
                except Exception as e:
                    errors.append(f"Request failed: {e}")
                    break

        return AdapterResult(source="civic", source_version=self._version, retrieved_at=datetime.now(timezone.utc).isoformat(),
                             request_id=request_id, success=False, records=records, warnings=warnings, errors=errors)

    def _normalize_results(self, data: Any, url: str) -> list[dict]:
        records = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("records", data.get("results", data.get("variants", data.get("genes", [data]))))
            if isinstance(items, dict):
                items = [items]
        else:
            return records

        for item in (items or []):
            record = {
                "source": "civic",
                "source_record_id": str(item.get("id", "")),
                "gene_symbol": item.get("gene_symbol", item.get("name", "")),
                "variant_name": item.get("variant_name", item.get("variant", "")),
                "disease": item.get("disease", {}).get("name", "") if isinstance(item.get("disease"), dict) else item.get("disease", ""),
                "drug_name": item.get("drug", {}).get("name", "") if isinstance(item.get("drug"), dict) else item.get("drug", ""),
                "evidence_type": item.get("evidence_type", item.get("evidence_type", "")),
                "evidence_direction": EVIDENCE_DIRECTION_MAP.get(item.get("evidence_direction", ""), item.get("evidence_direction", "").lower()),
                "evidence_level": EVIDENCE_LEVEL_MAP.get(item.get("evidence_level", ""), item.get("evidence_level", "")),
                "clinical_significance": item.get("clinical_significance", ""),
                "description": item.get("description", item.get("summary", "")),
                "citation": item.get("citation", ""),
                "pmid": str(item.get("pmid", "")) if item.get("pmid") else item.get("publication_id", ""),
                "url": f"https://civicdb.org/events/{item.get('id', '')}" if item.get("id") else url,
                "confidence": item.get("rating", "") if isinstance(item.get("rating"), str) else "",
            }
            records.append(record)
        return records

    def normalize_response(self, raw: Any) -> AdapterResult:
        return raw if isinstance(raw, AdapterResult) else AdapterResult(source="civic", source_version=self._version, retrieved_at="", request_id="", success=False)
