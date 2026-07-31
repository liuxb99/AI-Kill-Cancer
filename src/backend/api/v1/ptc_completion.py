"""PTC command-center API for end-to-end synchronization and visualization."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.session import get_db
from src.backend.services.ptc_completion_service import DEFAULT_PTC_DRUGS, PTCCompletionService
from src.backend.services.ptc_knowgraph_export import PTCKnowGraphExportService

router = APIRouter(prefix="/ptc-completion", tags=["ptc-completion"])


class CompleteSyncRequest(BaseModel):
    gdc_size: int = Field(default=100, ge=1, le=1000)
    gdc_mutation_files: int = Field(default=1, ge=0, le=20)
    trial_size: int = Field(default=100, ge=1, le=1000)
    pubmed_size: int = Field(default=100, ge=1, le=500)
    drug_names: list[str] = Field(default_factory=lambda: list(DEFAULT_PTC_DRUGS))
    include_civic: bool = False


@router.post("/sync-all")
async def sync_all(
    body: CompleteSyncRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await PTCCompletionService(db).sync_all(
        gdc_size=body.gdc_size,
        gdc_mutation_files=body.gdc_mutation_files,
        trial_size=body.trial_size,
        pubmed_size=body.pubmed_size,
        drug_names=body.drug_names,
        include_civic=body.include_civic,
    )


@router.get("/status")
async def source_status(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await PTCCompletionService(db).source_status()


@router.get("/outcomes/by-gene")
async def outcomes_by_gene(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    return await PTCCompletionService(db).outcome_by_gene()


@router.get("/graph")
async def complete_graph(
    case_limit: int = Query(default=500, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await PTCCompletionService(db).full_graph(case_limit=case_limit)


@router.get("/graph/knowgraph")
async def knowgraph_export(
    case_limit: int = Query(default=500, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return deterministic GraphData that KnowGraphGo can import directly."""
    return await PTCKnowGraphExportService(db).export(case_limit=case_limit)


__all__ = ["router"]
