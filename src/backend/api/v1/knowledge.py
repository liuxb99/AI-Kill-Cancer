"""
Knowledge API — extended oncology knowledge layer endpoints.

Provides:
- GET  /api/v1/knowledge/variant/{id}
- GET  /api/v1/knowledge/gene/{symbol}
- GET  /api/v1/knowledge/drug/{id}
- GET  /api/v1/knowledge/disease/{id}
- GET  /api/v1/knowledge/publication/{pmid}
- GET  /api/v1/knowledge/trial/{nct_id}
- POST /api/v1/knowledge/refresh
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.session import get_db
from src.backend.knowledge.service import KnowledgeService
from src.backend.knowledge.models import (
    KnowledgeEntityResponse, KnowledgeSearchResponse,
    KnowledgeEntity, Publication, ClinicalTrial,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/variant/{variant_id}", response_model=KnowledgeEntityResponse)
async def get_variant_knowledge(
    variant_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all knowledge about a variant."""
    service = KnowledgeService(db)
    result = await service.get_variant_knowledge(variant_id)
    if not result.entity:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Variant not found in knowledge base"})
    return result


@router.get("/gene/{gene_symbol}", response_model=KnowledgeEntityResponse)
async def get_gene_knowledge(
    gene_symbol: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all knowledge about a gene."""
    service = KnowledgeService(db)
    result = await service.get_gene_knowledge(gene_symbol.upper())
    if not result.entity:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Gene not found in knowledge base"})
    return result


@router.get("/drug/{drug_id}", response_model=KnowledgeEntityResponse)
async def get_drug_knowledge(drug_id: str):
    """Get knowledge about a drug. (Not yet implemented)"""
    raise HTTPException(status_code=501, detail={"error": "not_implemented"})


@router.get("/disease/{disease_id}", response_model=KnowledgeEntityResponse)
async def get_disease_knowledge(disease_id: str):
    """Get knowledge about a disease. (Not yet implemented)"""
    raise HTTPException(status_code=501, detail={"error": "not_implemented"})


@router.get("/publication/{pmid}", response_model=KnowledgeEntityResponse)
async def get_publication(pmid: str):
    """Get publication details. (Not yet implemented)"""
    raise HTTPException(status_code=501, detail={"error": "not_implemented"})


@router.get("/trial/{nct_id}", response_model=KnowledgeEntityResponse)
async def get_trial(nct_id: str):
    """Get clinical trial details. (Not yet implemented)"""
    raise HTTPException(status_code=501, detail={"error": "not_implemented"})


@router.post("/refresh")
async def refresh_knowledge(
    db: AsyncSession = Depends(get_db),
):
    """Refresh knowledge base (placeholder — source-specific adapters pending)."""
    return {
        "status": "not_configured",
        "message": "Knowledge sources not configured. Configure PUBMED_API_KEY, etc.",
        "configured_sources": [],
        "not_configured_sources": [
            "ClinVar", "COSMIC", "CancerHotspots", "PharmGKB",
            "PubMed", "ClinicalTrials.gov", "OncoKB", "MyCancerGenome",
        ],
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
    }
