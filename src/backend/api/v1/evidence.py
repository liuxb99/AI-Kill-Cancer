"""
Evidence API routes — query clinical evidence from CIViC, DGIdb with persistence.

Provides:
- GET  /api/v1/evidence/variant/{id}        — variant evidence (cache-first, refresh on miss)
- GET  /api/v1/evidence/gene/{symbol}        — gene evidence (cache-first, refresh on miss)
- POST /api/v1/evidence/refresh              — full refresh: query all sources, merge, persist
- POST /api/v1/evidence/cache/invalidate      — clear in-memory cache only
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.api.v1.deps import get_variant_repo
from src.backend.auth.dependencies import require_auth, verify_case_access
from src.backend.database.session import get_db
from src.backend.domain.case_acl import CaseRole
from src.backend.domain.user import UserModel
from src.backend.evidence.cache import gene_cache, variant_cache
from src.backend.evidence.domain import (
    DrugInteractionResponse,
    EvidenceCacheInvalidateResponse,
    EvidenceGeneResponse,
    EvidenceItemResponse,
    EvidenceRefreshResponse,
    EvidenceVariantResponse,
)
from src.backend.evidence.merger import EvidenceMerger
from src.backend.repositories.variant_repo import VariantRepository

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
        source_native_level=item.get("source_native_level", item.get("evidence_level", "")),
        match_level=item.get("_match_level", "gene_level_only"),
        conflict_status=item.get("_conflict_status", "not_evaluable"),
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
    user: UserModel = Depends(require_auth),
    repo: VariantRepository = Depends(get_variant_repo),
    db: AsyncSession = Depends(get_db),
):
    """Get clinical evidence for a variant by its internal variant ID."""
    try:
        vid = uuid.UUID(variant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "invalid_uuid", "message": "Invalid variant ID"})

    variant = await repo.get(vid)
    if not variant:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Variant not found"})

    # Verify VIEWER access on the variant's case
    if variant.sequencing_test_id:
        from src.backend.repositories.sequencing_test_repo import SequencingTestRepository
        from src.backend.repositories.specimen_repo import SpecimenRepository
        st_repo = SequencingTestRepository(db)
        st = await st_repo.get(variant.sequencing_test_id)
        if st and st.specimen_id:
            spec_repo = SpecimenRepository(db)
            spec = await spec_repo.get(st.specimen_id)
            if spec and spec.case_id:
                await verify_case_access(spec.case_id, user, db, CaseRole.VIEWER)

    # Check cache
    cache_key = f"variant:{variant_id}"
    cached = variant_cache.get(cache_key)
    if cached:
        return EvidenceVariantResponse(**cached)

    # Query sources with persistence
    merger = EvidenceMerger(db=db)
    result = await merger.merge_variant_evidence(
        gene_symbol=variant.gene_symbol,
        hgvs=variant.hgvs_notation or "",
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
        match_level=result.get("match_level", "gene_level_only"),
        retrieved_at=result.get("retrieved_at", datetime.now(UTC).isoformat()),
    )

    variant_cache.set(cache_key, response.model_dump())
    return response


@router.get("/gene/{gene_symbol}", response_model=EvidenceGeneResponse)
async def get_gene_evidence(
    gene_symbol: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get clinical evidence for a gene symbol."""
    cache_key = f"gene:{gene_symbol.upper()}"
    cached = gene_cache.get(cache_key)
    if cached:
        return EvidenceGeneResponse(**cached)

    merger = EvidenceMerger(db=db)
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
        retrieved_at=result.get("retrieved_at", datetime.now(UTC).isoformat()),
    )

    gene_cache.set(cache_key, response.model_dump())
    return response


@router.post("/refresh", response_model=EvidenceRefreshResponse)
async def refresh_evidence(
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Full evidence refresh: query all sources, merge, persist to DB,
    invalidate caches, return summary.
    """
    started = datetime.now(UTC)
    merger = EvidenceMerger(db=db)
    errors = []
    sources_updated = []
    total_evidence = 0
    total_interactions = 0

    # Query common cancer genes
    cancer_genes = ["BRAF", "EGFR", "KRAS", "NRAS", "PIK3CA", "TP53", "ERBB2",
                     "ALK", "ROS1", "RET", "MET", "NTRK1", "IDH1", "IDH2",
                     "BRCA1", "BRCA2", "KIT", "PDGFRA", "FGFR1", "FGFR2",
                     "FGFR3", "AR", "ESR1", "MYC", "CTNNB1", "CDKN2A", "PTEN",
                     "NF1", "RB1", "SMAD4", "STK11", "TERT", "AKT1", "CTCF",
                     "FOXA1", "GATA3", "MAP2K1", "MAP2K2", "NOTCH1", "SF3B1",
                     "U2AF1", "DNMT3A", "NPM1", "FLT3", "CEBPA", "RUNX1",
                     "ASXL1", "EZH2", "IDH1", "IDH2", "JAK2", "MPL", "CALR",
                     "BCR", "ABL1", "JAK3", "IL7R", "PHF6", "WT1", "PTPN11"]

    len(cancer_genes)
    for i, gene in enumerate(cancer_genes):
        try:
            result = await merger.refresh_all(
                gene_symbol=gene,
                request_id=f"refresh-batch-{i}",
            )
            if result.get("evidence_count", 0) > 0:
                total_evidence += result.get("evidence_count", 0)
            if result.get("drug_count", 0) > 0:
                total_interactions += result.get("drug_count", 0)
            if result.get("errors"):
                errors.extend(result["errors"])
        except Exception as e:
            errors.append(f"Failed to refresh {gene}: {e}")
            logger.warning("Refresh error for %s: %s", gene, e)

    sources_updated = ["civic", "dgidb"] if not errors else ["civic", "dgidb", "partial"]

    # Invalidate caches
    gene_cache.clear()
    variant_cache.clear()

    finished = datetime.now(UTC)

    return EvidenceRefreshResponse(
        status="completed" if not errors else "completed_with_errors",
        sources_updated=sources_updated,
        total_evidence=total_evidence,
        total_interactions=total_interactions,
        errors=errors[:20],  # Limit error reporting
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
    )


@router.post("/cache/invalidate", response_model=EvidenceCacheInvalidateResponse)
async def invalidate_evidence_cache(
    user: UserModel = Depends(require_auth),
):
    """Invalidate in-memory evidence cache only. Does not query sources."""
    cleared = datetime.now(UTC)
    gene_cache.clear()
    variant_cache.clear()

    return EvidenceCacheInvalidateResponse(
        status="completed",
        cache_type="gene_cache,variant_cache",
        cleared_at=cleared.isoformat(),
    )
