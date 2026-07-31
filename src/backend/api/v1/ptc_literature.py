"""PTC PubMed and CIViC synchronization endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.session import get_db
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


__all__ = ["router"]
