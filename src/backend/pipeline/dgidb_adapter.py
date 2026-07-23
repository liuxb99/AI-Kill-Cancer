"""
DGIdb adapter — drug-gene interaction integration via DGIdb REST API.

Provides:
- lookup_gene() by symbol
- Drug interactions, interaction types, source databases
- Evidence, PMIDs, interaction scores

API: https://dgidb.org/api/v2
License: DGIdb data usage per their terms
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from src.backend.adapters.base import AdapterResult, BaseAdapter

logger = logging.getLogger(__name__)

DGIDB_API_BASE = "https://dgidb.org/api/v2"
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 2


class DGIdbAdapter(BaseAdapter):
    """DGIdb REST API adapter for drug-gene interactions."""

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self._name = "dgidb"
        self._version = "v2"
        self._api_base = config.get("api_base", DGIDB_API_BASE) if config else DGIDB_API_BASE
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
        return query_type in ("gene", "drug", "interaction", "lookup")

    async def validate_input(self, payload: Any) -> list[str]:
        errors = []
        if isinstance(payload, dict):
            if not payload.get("genes") and not payload.get("gene"):
                errors.append("Must provide gene symbol(s)")
        return errors

    async def lookup_gene(self, gene_symbol: str, request_id: str = "") -> AdapterResult:
        """Look up drug interactions for a gene."""
        import httpx
        url = f"{self._api_base}/interactions.json"
        params = {"genes": gene_symbol}
        request_hash = hashlib.sha256(f"{url}:{json.dumps(params, sort_keys=True)}".encode()).hexdigest()

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(MAX_RETRIES + 1):
                try:
                    resp = await client.post(url, json={"genes": [gene_symbol]})
                    if resp.status_code == 200:
                        data = resp.json()
                        response_hash = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
                        records = self._normalize_results(data)
                        return AdapterResult(
                            source="dgidb", source_version=self._version,
                            retrieved_at=datetime.now(UTC).isoformat(),
                            request_id=request_id, success=True, records=records,
                            metadata={"api_url": url, "request_hash": request_hash, "response_hash": response_hash},
                        )
                    elif resp.status_code == 404:
                        return AdapterResult(source="dgidb", source_version=self._version, retrieved_at=datetime.now(UTC).isoformat(),
                                             request_id=request_id, success=True, records=[], warnings=["Gene not found in DGIdb"])
                    elif resp.status_code == 429:
                        if attempt < MAX_RETRIES:
                            await asyncio.sleep(2 ** attempt)
                            continue
                    else:
                        return AdapterResult(source="dgidb", source_version=self._version, retrieved_at=datetime.now(UTC).isoformat(),
                                             request_id=request_id, success=False, errors=[f"DGIdb returned {resp.status_code}"])
                except httpx.TimeoutException:
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(1)
                        continue
                    return AdapterResult(source="dgidb", source_version=self._version, retrieved_at=datetime.now(UTC).isoformat(),
                                         request_id=request_id, success=False, errors=["Request timed out"])
                except Exception as e:
                    return AdapterResult(source="dgidb", source_version=self._version, retrieved_at=datetime.now(UTC).isoformat(),
                                         request_id=request_id, success=False, errors=[f"Request failed: {e}"])

        return AdapterResult(source="dgidb", source_version=self._version, retrieved_at=datetime.now(UTC).isoformat(),
                             request_id=request_id, success=False, errors=["Max retries exceeded"])

    async def annotate(self, payload: Any, **kwargs) -> AdapterResult:
        request_id = kwargs.get("request_id", "unknown")
        gene = ""
        if isinstance(payload, dict):
            gene = payload.get("gene", payload.get("genes", ""))
        if isinstance(payload, str):
            gene = payload
        if not gene:
            return AdapterResult(source="dgidb", source_version=self._version, retrieved_at="", request_id=request_id, success=False, errors=["No gene provided"])
        return await self.lookup_gene(gene, request_id)

    def _normalize_results(self, data: dict) -> list[dict]:
        records = []
        matched_terms = data.get("matchedTerms", [])
        for term in matched_terms or []:
            gene_symbol = term.get("geneName", "")
            for interaction in term.get("interactions", []):
                record = {
                    "source": "dgidb",
                    "gene_symbol": gene_symbol,
                    "drug_name": interaction.get("drugName", ""),
                    "interaction_type": interaction.get("interactionType", ""),
                    "interaction_score": interaction.get("interactionScore"),
                    "source_db_name": interaction.get("sourceDbName", ""),
                    "pmids": interaction.get("pmids", []),
                    "source_db_url": interaction.get("sourceDbUrl", ""),
                    "drug_concept_id": interaction.get("drugConceptId", ""),
                    "gene_concept_id": interaction.get("geneConceptId", ""),
                }
                records.append(record)
        return records

    def normalize_response(self, raw: Any) -> AdapterResult:
        return raw if isinstance(raw, AdapterResult) else AdapterResult(source="dgidb", source_version=self._version, retrieved_at="", request_id="", success=False)
