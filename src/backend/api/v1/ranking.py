"""
Drug Ranking API — evidence-based drug ranking endpoints.

Provides:
- POST /api/v1/ranking/variant/{variant_id}
- POST /api/v1/ranking/case/{case_id}
- GET  /api/v1/ranking/run/{run_id}
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.session import get_db
from src.backend.evidence.merger import EvidenceMerger
from src.backend.ranking.engine import DrugRankingEngine
from src.backend.ranking.models import (
    DrugRankingResult, DrugRankingRunResponse, DrugRankingRunStatus,
)
from src.backend.ranking.repository import RankingRunRepository, RankingRunModel
from src.backend.repositories.variant_repo import VariantRepository
from src.backend.repositories.knowledge_source_repo import KnowledgeSourceRepository
from src.backend.api.v1.deps import get_variant_repo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ranking", tags=["ranking"])


@router.post("/variant/{variant_id}", response_model=DrugRankingRunResponse)
async def rank_variant(
    variant_id: str,
    repo: VariantRepository = Depends(get_variant_repo),
    db: AsyncSession = Depends(get_db),
):
    """Rank drugs for a specific variant."""
    try:
        vid = uuid.UUID(variant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "invalid_uuid", "message": "Invalid variant ID"})

    variant = await repo.get(vid)
    if not variant:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Variant not found"})

    # Gather evidence
    merger = EvidenceMerger(db=db)
    evidence_result = await merger.merge_variant_evidence(
        gene_symbol=variant.gene_symbol,
        hgvs=variant.hgvs_notation or "",
        chromosome=variant.chromosome,
        position=variant.position,
        reference=variant.reference,
        alternate=variant.alternate,
        request_id=f"rank-variant-{variant_id[:8]}",
    )

    evidence_items = evidence_result.get("evidence_items", [])
    drug_interactions = evidence_result.get("drug_interactions", [])
    match_level = evidence_result.get("match_level", "gene_level_only")

    if not evidence_items and not drug_interactions:
        return DrugRankingRunResponse(
            run_id="",
            status="no_evidence",
            message=f"No evidence found for variant {variant_id}",
        )

    # Run ranking
    engine = DrugRankingEngine()
    ranking_result = await engine.rank(
        gene_symbol=variant.gene_symbol,
        evidence_items=evidence_items,
        drug_interactions=drug_interactions,
        disease="",
        variant_match_level=match_level,
    )

    # Add variant_id to result
    ranking_result.variant_id = variant_id

    # Persist
    ranking_repo = RankingRunRepository(db)
    run_id = uuid.uuid4()
    ranking_result.id = str(run_id)
    try:
        await ranking_repo.create(ranking_result.model_dump())
    except Exception as e:
        logger.warning("Failed to persist ranking: %s", e)

    return DrugRankingRunResponse(
        run_id=str(run_id),
        status="completed",
        ranking=ranking_result,
    )


@router.post("/case/{case_id}", response_model=DrugRankingRunResponse)
async def rank_case(
    case_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Rank drugs for a cancer case (looks up variants from case)."""
    # For now, return not_implemented — full case-based ranking
    # will require the Case-to-Variants resolution
    raise HTTPException(
        status_code=501,
        detail={"error": "not_implemented", "message": "Case-based ranking not yet implemented"},
    )


@router.get("/run/{run_id}", response_model=DrugRankingRunResponse)
async def get_ranking_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a previously computed ranking run."""
    try:
        rid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "invalid_uuid", "message": "Invalid run ID"})

    ranking_repo = RankingRunRepository(db)
    run_model = await ranking_repo.get(rid)

    if not run_model:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Ranking run not found"})

    # Deserialize the stored JSON
    ranking_data = run_model.ranking_data if isinstance(run_model.ranking_data, dict) else {}
    ranking_result = DrugRankingResult(**ranking_data) if ranking_data else None

    return DrugRankingRunResponse(
        run_id=str(run_model.id),
        status=run_model.status,
        ranking=ranking_result,
    )
