"""Public literature and CIViC evidence synchronization for PTC."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.services.ptc_knowledge_service import PTCKnowledgeService, infer_target_genes

NCBI_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
NCBI_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
CIVIC_GRAPHQL_URL = "https://civicdb.org/api/graphql"
_XLINK_HREF = "{http://www.w3.org/1999/xlink}href"


def _text(node: ET.Element | None, path: str) -> str | None:
    if node is None:
        return None
    target = node.find(path)
    if target is None:
        return None
    value = "".join(target.itertext()).strip()
    return value or None


def _node_text(node: ET.Element | None) -> str | None:
    if node is None:
        return None
    value = " ".join("".join(node.itertext()).split())
    return value or None


def parse_pubmed_xml(payload: str) -> list[dict[str, Any]]:
    root = ET.fromstring(payload)
    rows: list[dict[str, Any]] = []
    for article in root.findall(".//PubmedArticle"):
        citation = article.find("MedlineCitation")
        pmid = _text(citation, "PMID")
        article_node = citation.find("Article") if citation is not None else None
        title = _text(article_node, "ArticleTitle")
        abstract_parts = ["".join(node.itertext()).strip() for node in article.findall(".//Abstract/AbstractText")]
        abstract = "\n".join(part for part in abstract_parts if part)
        journal = _text(article_node, "Journal/Title")
        year = _text(article_node, "Journal/JournalIssue/PubDate/Year") or _text(
            article_node, "Journal/JournalIssue/PubDate/MedlineDate"
        )
        authors = []
        for author in article.findall(".//AuthorList/Author"):
            name = " ".join(part for part in [_text(author, "ForeName"), _text(author, "LastName")] if part)
            if name:
                authors.append(name)
        pmcid = None
        for identifier in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
            if identifier.attrib.get("IdType", "").lower() == "pmc":
                pmcid = _node_text(identifier)
                break
        if pmid:
            rows.append(
                {
                    "pmid": pmid,
                    "pmcid": pmcid,
                    "title": title,
                    "abstract": abstract or None,
                    "journal": journal,
                    "year": year,
                    "authors": authors,
                    "genes": infer_target_genes(title, abstract),
                }
            )
    return rows


def _asset_url(pmcid: str, href: str | None) -> str | None:
    if not href:
        return None
    if href.startswith(("http://", "https://")):
        return href
    return f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/bin/{href.lstrip('/')}"


def _table_rows(table: ET.Element) -> tuple[list[str], list[list[str]]]:
    header_nodes = table.findall("./thead/tr/th")
    headers = [_node_text(node) or "" for node in header_nodes]
    body_rows = table.findall("./tbody/tr") or table.findall("./tr")
    rows: list[list[str]] = []
    for row in body_rows[:50]:
        cells = row.findall("./td") or row.findall("./th")
        values = [_node_text(cell) or "" for cell in cells]
        if values:
            rows.append(values)
    return headers, rows


def parse_pmc_fulltext_xml(payload: str) -> dict[str, dict[str, Any]]:
    """Extract bounded figure/table assets from PMC open-access full text XML."""
    root = ET.fromstring(payload)
    articles = root.findall(".//article")
    if root.tag.endswith("article"):
        articles = [root]
    parsed: dict[str, dict[str, Any]] = {}
    for article in articles:
        pmcid_node = article.find(".//article-id[@pub-id-type='pmcid']")
        pmcid = _node_text(pmcid_node)
        if not pmcid:
            continue
        figures: list[dict[str, Any]] = []
        for figure in article.findall(".//fig")[:20]:
            graphic = figure.find(".//graphic")
            href = graphic.attrib.get(_XLINK_HREF) if graphic is not None else None
            figures.append(
                {
                    "figure_id": figure.attrib.get("id"),
                    "label": _node_text(figure.find("label")),
                    "caption": _node_text(figure.find("caption")),
                    "image_url": _asset_url(pmcid, href),
                    "source_href": href,
                }
            )
        tables: list[dict[str, Any]] = []
        for wrapper in article.findall(".//table-wrap")[:20]:
            table = wrapper.find(".//table")
            if table is None:
                continue
            headers, rows = _table_rows(table)
            tables.append(
                {
                    "table_id": wrapper.attrib.get("id"),
                    "label": _node_text(wrapper.find("label")),
                    "caption": _node_text(wrapper.find("caption")),
                    "headers": headers,
                    "rows": rows,
                    "row_count": len(rows),
                }
            )
        parsed[pmcid] = {
            "pmcid": pmcid,
            "full_text_url": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/",
            "figures": figures,
            "tables": tables,
        }
    return parsed


class PTCLiteratureService:
    def __init__(self, db: AsyncSession, client: httpx.AsyncClient | None = None):
        self.db = db
        self.client = client

    async def _http(self) -> httpx.AsyncClient:
        return self.client or httpx.AsyncClient(timeout=60.0, follow_redirects=True)

    async def _fetch_pmc_assets(
        self,
        client: httpx.AsyncClient,
        pmcids: list[str],
    ) -> dict[str, dict[str, Any]]:
        if not pmcids:
            return {}
        try:
            response = await client.get(
                NCBI_EFETCH_URL,
                params={"db": "pmc", "id": ",".join(sorted(set(pmcids))), "retmode": "xml"},
            )
            response.raise_for_status()
            return parse_pmc_fulltext_xml(response.text)
        except (httpx.HTTPError, ET.ParseError):
            return {}

    async def sync_pubmed(self, *, retmax: int = 100, query: str | None = None) -> int:
        client = await self._http()
        owned = self.client is None
        query = query or '"papillary thyroid carcinoma"[Title/Abstract]'
        try:
            search = await client.get(
                NCBI_ESEARCH_URL,
                params={"db": "pubmed", "term": query, "retmode": "json", "retmax": min(max(retmax, 1), 500)},
            )
            search.raise_for_status()
            ids = search.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return 0
            fetch = await client.get(
                NCBI_EFETCH_URL,
                params={"db": "pubmed", "id": ",".join(ids), "retmode": "xml"},
            )
            fetch.raise_for_status()
            rows = parse_pubmed_xml(fetch.text)
            assets_by_pmcid = await self._fetch_pmc_assets(
                client,
                [row["pmcid"] for row in rows if row.get("pmcid")],
            )
            knowledge = PTCKnowledgeService(self.db)
            count = 0
            for row in rows:
                assets = assets_by_pmcid.get(row.get("pmcid") or "", {})
                genes = row["genes"] or [None]
                for gene in genes:
                    await knowledge.create_evidence(
                        source_name="PubMed",
                        source_record_id=row["pmid"],
                        evidence_type="publication",
                        title=row["title"],
                        summary=row["abstract"],
                        evidence_level="published_literature",
                        direction="informational",
                        gene_symbol=gene,
                        publication_id=row["pmid"],
                        citation=f"{row['journal'] or ''} {row['year'] or ''}".strip(),
                        source_url=f"https://pubmed.ncbi.nlm.nih.gov/{row['pmid']}/",
                        payload={
                            "authors": row["authors"],
                            "query": query,
                            "pmcid": row.get("pmcid"),
                            "full_text_available": bool(assets),
                            "full_text_url": assets.get("full_text_url"),
                            "figures": assets.get("figures", []),
                            "tables": assets.get("tables", []),
                        },
                    )
                    count += 1
            return count
        finally:
            if owned:
                await client.aclose()

    async def sync_civic(self, *, gene_symbols: list[str]) -> int:
        """Fetch CIViC assertions through GraphQL when CIVIC_API_KEY is configured."""
        token = os.getenv("CIVIC_API_KEY")
        if not token:
            raise RuntimeError("CIVIC_API_KEY is not configured")
        client = await self._http()
        owned = self.client is None
        query = """
        query PTCGenes($names: [String!]!) {
          genes(name: $names) {
            nodes {
              id
              name
              evidenceItems(first: 100) {
                nodes {
                  id
                  description
                  evidenceLevel
                  evidenceType
                  evidenceDirection
                  status
                }
              }
            }
          }
        }
        """
        try:
            response = await client.post(
                CIVIC_GRAPHQL_URL,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"query": query, "variables": {"names": sorted(set(gene_symbols))}},
            )
            response.raise_for_status()
            body = response.json()
            if body.get("errors"):
                raise RuntimeError(f"CIViC GraphQL error: {body['errors']}")
            nodes = body.get("data", {}).get("genes", {}).get("nodes", [])
            knowledge = PTCKnowledgeService(self.db)
            count = 0
            for gene in nodes:
                for item in gene.get("evidenceItems", {}).get("nodes", []):
                    await knowledge.create_evidence(
                        source_name="CIViC",
                        source_record_id=str(item["id"]),
                        evidence_type=str(item.get("evidenceType") or "clinical_evidence"),
                        title=f"CIViC {gene.get('name')} evidence",
                        summary=item.get("description"),
                        evidence_level=str(item.get("evidenceLevel") or "unknown"),
                        direction=str(item.get("evidenceDirection") or "informational"),
                        gene_symbol=gene.get("name"),
                        source_url=f"https://civicdb.org/evidence/{item['id']}/summary",
                        payload={"status": item.get("status"), "retrieved_at": datetime.utcnow().isoformat()},
                    )
                    count += 1
            return count
        finally:
            if owned:
                await client.aclose()


__all__ = [
    "PTCLiteratureService",
    "parse_pubmed_xml",
    "parse_pmc_fulltext_xml",
    "NCBI_ESEARCH_URL",
    "NCBI_EFETCH_URL",
    "CIVIC_GRAPHQL_URL",
]
