"""
Doctor Workbench API — workbench and tumor board endpoints.

Provides:
- GET  /api/v1/workbench/graph/variant/{variant_id}
- GET  /api/v1/workbench/graph/case/{case_id}
- POST /api/v1/workbench/tumor-board/{case_id}/review
- GET  /api/v1/workbench/tumor-board/{case_id}/timeline
- POST /api/v1/workbench/compare/cases
- POST /api/v1/workbench/compare/variants
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.session import get_db
from src.backend.auth.dependencies import require_auth, require_case_access
from src.backend.domain.case_acl import CaseRole
from src.backend.domain.user import UserModel
from src.backend.workbench.service import WorkbenchService
from src.backend.workbench.models import (
    KnowledgeGraph, WorkbenchTimeline,
    CaseComparisonResult,
)
from src.backend.workbench.repository import TumorBoardRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workbench", tags=["workbench"])


@router.get("/graph/variant/{variant_id}", response_model=KnowledgeGraph)
async def get_variant_graph(
    variant_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get knowledge graph data for a variant."""
    # Verify VIEWER access on the variant's case
    try:
        vid = uuid.UUID(variant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid variant ID")
    from src.backend.repositories.variant_repo import VariantRepository
    vrepo = VariantRepository(db)
    v = await vrepo.get(vid)
    if v and v.sequencing_test_id:
        from src.backend.repositories.sequencing_test_repo import SequencingTestRepository
        from src.backend.repositories.specimen_repo import SpecimenRepository
        st_repo = SequencingTestRepository(db)
        st = await st_repo.get(v.sequencing_test_id)
        if st and st.specimen_id:
            spec_repo = SpecimenRepository(db)
            spec = await spec_repo.get(st.specimen_id)
            if spec and spec.case_id:
                await verify_case_access(spec.case_id, user, db, CaseRole.VIEWER)
    service = WorkbenchService(db)
    graph = await service.build_knowledge_graph(variant_id=variant_id)
    return graph


@router.get("/graph/case/{case_id}", response_model=KnowledgeGraph)
async def get_case_graph(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    """Get knowledge graph data for a case."""
    service = WorkbenchService(db)
    graph = await service.build_knowledge_graph(case_id=case_id)
    return graph


@router.post("/tumor-board/{case_id}/review")
async def create_tumor_board_review(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.REVIEWER)),
    db: AsyncSession = Depends(get_db),
):
    """Create a tumor board review for a case."""
    repo = TumorBoardRepository(db)
    review = await repo.create_review(case_id=case_id)
    return {"review_id": str(review.id), "status": "draft", "case_id": case_id}


@router.get("/tumor-board/{case_id}/timeline", response_model=WorkbenchTimeline)
async def get_case_timeline(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    """Get timeline of events for a case."""
    service = WorkbenchService(db)
    timeline = await service.get_case_timeline(case_id)
    return timeline


@router.post("/compare/cases", response_model=CaseComparisonResult)
async def compare_cases(
    case_ids: list[str],
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Compare multiple cases."""
    if not case_ids or len(case_ids) < 2:
        raise HTTPException(status_code=400, detail={"error": "need_at_least_2_cases"})
    # Verify VIEWER access on all cases
    for cid_str in case_ids:
        try:
            cid = uuid.UUID(cid_str)
            await verify_case_access(cid, user, db, CaseRole.VIEWER)
        except ValueError:
            raise HTTPException(status_code=400, detail={"error": "invalid_uuid", "message": f"Invalid case ID: {cid_str}"})

    service = WorkbenchService(db)
    result = await service.compare_cases(case_ids)
    return result


@router.post("/compare/variants")
async def compare_variants(
    variant_ids: list[str],
    user: UserModel = Depends(require_auth),
):
    """Compare variants (placeholder)."""
    return {"status": "not_implemented", "message": "Variant comparison not yet implemented"}
