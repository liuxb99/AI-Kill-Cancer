"""
Analysis run API routes.
"""
from __future__ import annotations

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.api.v1.deps import get_analysis_run_repo
from src.backend.auth.dependencies import require_auth, verify_case_access
from src.backend.database.session import get_db
from src.backend.domain.case_acl import CaseRole
from src.backend.domain.user import UserModel
from src.backend.domain.analysis_run import AnalysisRunCreate, AnalysisRunResponse
from src.backend.domain.drug_candidate import DrugCandidateListResponse
from src.backend.domain.evidence import EvidenceSearchResult
from src.backend.domain.visualization_graph import VisualizationGraph, GraphAnalysisResponse
from src.backend.domain.enums import AnalysisStatusEnum
from src.backend.repositories.analysis_run_repo import AnalysisRunRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post("", response_model=AnalysisRunResponse, status_code=201)
async def create_analysis(
    body: AnalysisRunCreate,
    user: UserModel = Depends(require_auth),
    repo: AnalysisRunRepository = Depends(get_analysis_run_repo),
    db: AsyncSession = Depends(get_db),
):
    # Verify EDITOR access on the case
    try:
        cid = uuid.UUID(body.case_id)
        await verify_case_access(cid, user, db, CaseRole.EDITOR)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid case_id")

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
    user: UserModel = Depends(require_auth),
    repo: AnalysisRunRepository = Depends(get_analysis_run_repo),
    db: AsyncSession = Depends(get_db),
):
    try:
        aid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID")

    analysis = await repo.get(aid)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Verify VIEWER access on the analysis's case
    if not analysis.case_id:
        logger.error("Analysis %s has no case_id — denying access", analysis_id)
        raise HTTPException(status_code=403, detail="Access denied")
    await verify_case_access(analysis.case_id, user, db, CaseRole.VIEWER)

    return AnalysisRunResponse.model_validate(analysis)


@router.get("/{analysis_id}/graph", response_model=GraphAnalysisResponse)
async def get_analysis_graph(
    analysis_id: str,
    user: UserModel = Depends(require_auth),
    repo: AnalysisRunRepository = Depends(get_analysis_run_repo),
    db: AsyncSession = Depends(get_db),
):
    """Return the visualization graph for an analysis run."""
    try:
        aid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID")

    analysis = await repo.get(aid)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if not analysis.case_id:
        raise HTTPException(status_code=403, detail="Access denied")
    await verify_case_access(analysis.case_id, user, db, CaseRole.VIEWER)

    if analysis.status != AnalysisStatusEnum.COMPLETED:
        return GraphAnalysisResponse(
            analysis_id=analysis_id,
            status=analysis.status.value,
            graph=VisualizationGraph(),
        )

    return GraphAnalysisResponse(
        analysis_id=analysis_id,
        status="not_configured",
        graph=VisualizationGraph(),
    )


@router.get("/{analysis_id}/drug-candidates", response_model=DrugCandidateListResponse)
async def get_analysis_drug_candidates(
    analysis_id: str,
    user: UserModel = Depends(require_auth),
    repo: AnalysisRunRepository = Depends(get_analysis_run_repo),
    db: AsyncSession = Depends(get_db),
):
    """Return drug candidates for an analysis run."""
    try:
        aid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID")

    analysis = await repo.get(aid)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if not analysis.case_id:
        raise HTTPException(status_code=403, detail="Access denied")
    await verify_case_access(analysis.case_id, user, db, CaseRole.VIEWER)

    return DrugCandidateListResponse(items=[], total=0)


@router.get("/{analysis_id}/evidence", response_model=EvidenceSearchResult)
async def get_analysis_evidence(
    analysis_id: str,
    user: UserModel = Depends(require_auth),
    repo: AnalysisRunRepository = Depends(get_analysis_run_repo),
    db: AsyncSession = Depends(get_db),
):
    """Return evidence for an analysis run."""
    try:
        aid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID")

    analysis = await repo.get(aid)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if not analysis.case_id:
        raise HTTPException(status_code=403, detail="Access denied")
    await verify_case_access(analysis.case_id, user, db, CaseRole.VIEWER)

    return EvidenceSearchResult(
        status="not_searched",
        items=[],
        total=0,
    )
