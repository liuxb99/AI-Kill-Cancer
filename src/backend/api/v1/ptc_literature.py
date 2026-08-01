"""PTC PubMed and CIViC synchronization endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.session import get_db
from src.backend.domain.ptc_knowledge import PTCEvidenceRecordModel
from src.backend.services.ptc_literature_service import PTCLiteratureService

router = APIRouter(prefix="/ptc-literature", tags=["ptc-literature"])


class CIViCSyncRequest(BaseModel):
    gene_symbols: list[str] = Field(min_length=1)


@router.post("/sync/pubmed")
async def sync_pubmed(
    retmax: int = Query(default=100, ge=1, le=500),
    query: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    count = await PTCLiteratureService(db).sync_pubmed(retmax=retmax, query=query)
    return {"source": "PubMed", "records": count}


@router.post("/sync/civic")
async def sync_civic(body: CIViCSyncRequest, db: AsyncSession = Depends(get_db)) -> dict[str, int | str]:
    try:
        count = await PTCLiteratureService(db).sync_civic(gene_symbols=body.gene_symbols)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"source": "CIViC", "records": count}


def _publication_payload(rows: list[PTCEvidenceRecordModel]) -> dict[str, Any]:
    first = rows[0]
    payload = first.payload or {}
    genes = sorted({row.gene_symbol for row in rows if row.gene_symbol})
    return {
        "pmid": first.publication_id or first.source_record_id,
        "pmcid": payload.get("pmcid"),
        "title": first.title,
        "abstract": first.summary,
        "citation": first.citation,
        "source_url": first.source_url,
        "full_text_available": bool(payload.get("full_text_available")),
        "full_text_url": payload.get("full_text_url"),
        "authors": payload.get("authors", []),
        "genes": genes,
        "figures": payload.get("figures", []),
        "tables": payload.get("tables", []),
        "figure_count": len(payload.get("figures", [])),
        "table_count": len(payload.get("tables", [])),
    }


@router.get("/publications")
async def list_publications(
    gene: str | None = Query(default=None),
    full_text_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    stmt = (
        select(PTCEvidenceRecordModel)
        .where(PTCEvidenceRecordModel.source_name == "PubMed")
        .order_by(PTCEvidenceRecordModel.created_at.desc())
        .limit(limit * 10)
    )
    if gene:
        stmt = stmt.where(PTCEvidenceRecordModel.gene_symbol == gene.upper())
    rows = list((await db.execute(stmt)).scalars())
    grouped: dict[str, list[PTCEvidenceRecordModel]] = {}
    for row in rows:
        pmid = row.publication_id or row.source_record_id
        grouped.setdefault(pmid, []).append(row)
    publications = [_publication_payload(group) for group in grouped.values()]
    if full_text_only:
        publications = [item for item in publications if item["full_text_available"]]
    publications = publications[:limit]
    return {"count": len(publications), "publications": publications}


@router.get("/publications/{pmid}")
async def publication_detail(pmid: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    rows = list((await db.execute(
        select(PTCEvidenceRecordModel).where(
            PTCEvidenceRecordModel.source_name == "PubMed",
            PTCEvidenceRecordModel.source_record_id == pmid,
        )
    )).scalars())
    if not rows:
        raise HTTPException(status_code=404, detail="PubMed publication not found")
    return _publication_payload(rows)


__all__ = ["router"]
