"""
PubMed adapter — free public API via NCBI E-Utilities.

API: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed
License: PubMed is public domain
Rate limit: 3 requests/second
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from xml.etree import ElementTree

import httpx

logger = logging.getLogger(__name__)

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DEFAULT_TIMEOUT = 30
RATE_LIMIT = 0.35


class PubMedAdapter:
    """PubMed E-Utilities adapter for publication search."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self._name = "pubmed"
        self._version = "1.0"
        self._base = self.config.get("api_base", PUBMED_BASE)
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
                resp = await client.get(f"{self._base}/einfo.fcgi?db=pubmed")
                return {"status": "ok", "version": self._version} if resp.status_code < 500 else {"status": "degraded"}
        except Exception as e:
            return {"status": "degraded", "detail": str(e)}

    def supports(self, query_type: str) -> bool:
        return query_type in ("pubmed", "publication", "pmid", "search")

    async def search(self, query: str, max_results: int = 10) -> list[dict]:
        """Search PubMed for publications."""
        await self._rate_limit()
        results = []

        params = {
            "db": "pubmed",
            "term": query,
            "retmax": str(max_results),
            "retmode": "json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(f"{self._base}/esearch.fcgi", params=params)
                if resp.status_code != 200:
                    return results

                data = resp.json()
                ids = data.get("esearchresult", {}).get("idlist", [])
                if not ids:
                    return results

                await self._rate_limit()
                summary_params = {
                    "db": "pubmed",
                    "id": ",".join(ids),
                    "retmode": "xml",
                }
                summary_resp = await client.get(f"{self._base}/esummary.fcgi", params=summary_params)
                if summary_resp.status_code == 200:
                    results = self._normalize_xml(summary_resp.text)

        except httpx.TimeoutException:
            logger.warning("PubMed request timed out")
        except Exception as e:
            logger.warning("PubMed request failed: %s", e)

        return results

    def _normalize_xml(self, xml_text: str) -> list[dict]:
        """Parse PubMed esummary XML into unified format."""
        records = []
        try:
            root = ElementTree.fromstring(xml_text)
            for doc in root.findall(".//DocumentSummary"):
                pmid = doc.findtext("Id", "")
                title = doc.findtext("Title", "")
                source = doc.findtext("Source", "")
                pubdate = doc.findtext("PubDate", "")
                authors_el = doc.find("Authors")
                authors = []
                if authors_el is not None:
                    for author in authors_el.findall("Author"):
                        name = author.findtext("Name", "")
                        if name:
                            authors.append(name)

                record = {
                    "source": "pubmed",
                    "source_record_id": pmid,
                    "pmid": pmid,
                    "title": title,
                    "journal": source,
                    "publication_date": pubdate,
                    "authors": authors,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                    "retrieved_at": datetime.now(UTC).isoformat(),
                }
                records.append(record)
        except Exception as e:
            logger.warning("Failed to parse PubMed XML: %s", e)

        return records

    async def annotate(self, payload: dict, **kwargs) -> list[dict]:
        query = payload.get("query", payload.get("pmid", payload.get("gene", "")))
        return await self.search(str(query)) if query else []
