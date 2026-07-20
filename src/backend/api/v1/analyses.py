"""
Analysis run API routes.
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from src.backend.api.v1.deps import get_analysis_run_repo, get_variant_repo, get_drug_repo, get_evidence_repo
from src.backend.domain.analysis_run import AnalysisRunCreate, AnalysisRunResponse
from src.backend.domain.drug_candidate import DrugCandidateResponse, DrugCandidateListResponse
from src.backend.domain.evidence import EvidenceResponse, EvidenceSearchResult, EvidenceDirectionEnum, EvidenceLevelEnum
from src.backend.domain.visualization_graph import VisualizationGraph, GraphNode, GraphEdge, GraphAnalysisResponse
from src.backend.domain.enums import AnalysisStatusEnum
from src.backend.repositories.analysis_run_repo import AnalysisRunRepository
from src.backend.repositories.variant_repo import VariantRepository
from src.backend.repositories.drug_repo import DrugRepository
from src.backend.repositories.evidence_repo import EvidenceRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post("", response_model=AnalysisRunResponse, status_code=201)
async def create_analysis(
    body: AnalysisRunCreate,
    repo: AnalysisRunRepository = Depends(get_analysis_run_repo),
):
    try:
        data = body.model_dump(exclude_none=True)
        data["status"] = AnalysisStatusEnum.PENDING
        analysis = await repo.create(**data)
        return AnalysisRunResponse.model_validate(analysis)
    except Exception as e:
        logger.exception("Failed to create analysis run")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{analysis_id}", response_model=AnalysisRunResponse)
async def get_analysis(
    analysis_id: str,
    repo: AnalysisRunRepository = Depends(get_analysis_run_repo),
):
    try:
        aid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID")

    analysis = await repo.get(aid)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return AnalysisRunResponse.model_validate(analysis)


@router.get("/{analysis_id}/graph", response_model=GraphAnalysisResponse)
async def get_analysis_graph(
    analysis_id: str,
    repo: AnalysisRunRepository = Depends(get_analysis_run_repo),
):
    """Return the visualization graph for an analysis run.
    In Phase 1, this returns the analysis status — graph data is
    only populated when a real analysis pipeline is configured.
    """
    try:
        aid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID")

    analysis = await repo.get(aid)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if analysis.status != AnalysisStatusEnum.COMPLETED:
        return GraphAnalysisResponse(
            analysis_id=analysis_id,
            status=analysis.status.value,
            graph=VisualizationGraph(),
        )

    # In Phase 1, graph is empty (no real pipeline yet)
    return GraphAnalysisResponse(
        analysis_id=analysis_id,
        status="not_configured",
        graph=VisualizationGraph(),
    )


@router.get("/{analysis_id}/drug-candidates", response_model=DrugCandidateListResponse)
async def get_analysis_drug_candidates(
    analysis_id: str,
    repo: AnalysisRunRepository = Depends(get_analysis_run_repo),
):
    """Return drug candidates for an analysis run.
    In Phase 1, returns empty list since no real analysis pipeline is configured.
    """
    try:
        aid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID")

    analysis = await repo.get(aid)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return DrugCandidateListResponse(items=[], total=0)


@router.get("/{analysis_id}/evidence", response_model=EvidenceSearchResult)
async def get_analysis_evidence(
    analysis_id: str,
    repo: AnalysisRunRepository = Depends(get_analysis_run_repo),
):
    """Return evidence for an analysis run.
    In Phase 1, returns not_searched status.
    """
    try:
        aid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID")

    analysis = await repo.get(aid)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return EvidenceSearchResult(
        status="not_searched",
        items=[],
        total=0,
    )
