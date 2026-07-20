"""
Evidence API routes — query clinical evidence from CIViC, DGIdb.

Provides:
- GET /api/v1/evidence/variant/{id}
- GET /api/v1/evidence/gene/{symbol}
- POST /api/v1/evidence/refresh
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.backend.evidence.merger import EvidenceMerger
from src.backend.evidence.cache import gene_cache, variant_cache
from src.backend.evidence.domain import EvidenceVariantResponse, EvidenceGeneResponse, EvidenceRefreshResponse, EvidenceItemResponse, DrugInteractionResponse
from src.backend.repositories.variant_repo import VariantRepository
from src.backend.api.v1.deps import get_variant_repo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/evidence", tags=["evidence"])


def _to_item_response(item: dict) -> EvidenceItemResponse:
    return EvidenceItemResponse(
        id=item.get("id", ""),
        source_name=item.get("_source", item.get("source", "")),
        source_record_id=item.get("_source_record_id", item.get("source_record_id", "")),
        gene_symbol=item.get("gene_symbol", ""),
        disease=item.get("disease", ""),
        drug_name=item.get("drug_name", ""),
        evidence_type=item.get("evidence_type", ""),
        evidence_direction=item.get("evidence_direction", ""),
        evidence_level=item.get("evidence_level", ""),
        clinical_significance=item.get("clinical_significance", ""),
        description=item.get("description", ""),
        citation=item.get("citation", ""),
        pmid=item.get("pmid", ""),
        url=item.get("url", ""),
        confidence=item.get("confidence", ""),
    )


def _to_interaction_response(item: dict) -> DrugInteractionResponse:
    return DrugInteractionResponse(
        id=item.get("id", ""),
        gene_symbol=item.get("gene_symbol", ""),
        drug_name=item.get("drug_name", ""),
        interaction_type=item.get("interaction_type", ""),
        interaction_score=item.get("interaction_score"),
        source_db_name=item.get("source_db_name", ""),
        pmids=item.get("pmids", []),
    )


@router.get("/variant/{variant_id}", response_model=EvidenceVariantResponse)
async def get_variant_evidence(
    variant_id: str,
    repo: VariantRepository = Depends(get_variant_repo),
):
    """Get clinical evidence for a variant by its internal variant ID."""
    try:
        vid = uuid.UUID(variant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "invalid_uuid", "message": "Invalid variant ID"})

    variant = await repo.get(vid)
    if not variant:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Variant not found"})

    # Check cache
    cache_key = f"variant:{variant_id}"
    cached = variant_cache.get(cache_key)
    if cached:
        return EvidenceVariantResponse(**cached)

    merger = EvidenceMerger()
    result = await merger.merge_variant_evidence(
        gene_symbol=variant.gene_symbol,
        chromosome=variant.chromosome,
        position=variant.position,
        reference=variant.reference,
        alternate=variant.alternate,
        request_id=f"api-variant-{variant_id[:8]}",
    )

    response = EvidenceVariantResponse(
        variant_id=variant_id,
        gene_symbol=variant.gene_symbol,
        evidence_items=[_to_item_response(i) for i in result.get("evidence_items", [])],
        drug_interactions=[_to_interaction_response(i) for i in result.get("drug_interactions", [])],
        evidence_count=result.get("evidence_count", 0),
        drug_count=result.get("drug_count", 0),
        highest_evidence_level=result.get("highest_evidence_level"),
        retrieved_at=result.get("retrieved_at", datetime.now(timezone.utc).isoformat()),
    )

    variant_cache.set(cache_key, response.model_dump())
    return response


@router.get("/gene/{gene_symbol}", response_model=EvidenceGeneResponse)
async def get_gene_evidence(gene_symbol: str):
    """Get clinical evidence for a gene symbol."""
    cache_key = f"gene:{gene_symbol.upper()}"
    cached = gene_cache.get(cache_key)
    if cached:
        return EvidenceGeneResponse(**cached)

    merger = EvidenceMerger()
    result = await merger.merge_gene_evidence(
        gene_symbol=gene_symbol,
        request_id=f"api-gene-{gene_symbol}",
    )

    response = EvidenceGeneResponse(
        gene_symbol=gene_symbol,
        evidence_items=[_to_item_response(i) for i in result.get("evidence_items", [])],
        drug_interactions=[_to_interaction_response(i) for i in result.get("drug_interactions", [])],
        evidence_count=result.get("evidence_count", 0),
        drug_count=result.get("drug_count", 0),
        retrieved_at=result.get("retrieved_at", datetime.now(timezone.utc).isoformat()),
    )

    gene_cache.set(cache_key, response.model_dump())
    return response


@router.post("/refresh", response_model=EvidenceRefreshResponse)
async def refresh_evidence():
    """Invalidate all cached evidence and return status."""
    started = datetime.now(timezone.utc)
    gene_cache.clear()
    variant_cache.clear()
    finished = datetime.now(timezone.utc)

    return EvidenceRefreshResponse(
        status="completed",
        sources_updated=["gene_cache", "variant_cache"],
        total_evidence=gene_cache.size + variant_cache.size,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
    )
