"""
Doctor Workbench API — workbench and tumor board endpoints (v1.1).

Provides:
- GET    /api/v1/workbench/graph/variant/{variant_id}
- GET    /api/v1/workbench/graph/case/{case_id}
- POST   /api/v1/workbench/tumor-board/{case_id}/review
- GET    /api/v1/workbench/tumor-board/{case_id}/timeline
- POST   /api/v1/workbench/compare/cases
- POST   /api/v1/workbench/compare/variants
- GET    /api/v1/workbench/patient/{case_id}/summary      (NEW)
- GET    /api/v1/workbench/activity/{case_id}              (NEW)
- GET    /api/v1/workbench/treatment/{case_id}             (NEW)
- POST   /api/v1/workbench/tumor-board/{case_id}/vote      (NEW)
- POST   /api/v1/workbench/tumor-board/{case_id}/comment   (NEW)
- GET    /api/v1/workbench/state/{case_id}                 (NEW)
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.session import get_db
from src.backend.auth.dependencies import require_auth, require_case_access, verify_case_access
from src.backend.domain.case_acl import CaseRole
from src.backend.domain.user import UserModel
from src.backend.workbench.service import WorkbenchService
from src.backend.workbench.models import (
    KnowledgeGraph, WorkbenchTimeline, CaseComparisonResult,
    PatientSummary, TreatmentRecommendation, ActivityLog,
    TumorBoardVote,
)
from src.backend.workbench.repository import TumorBoardRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workbench", tags=["workbench"])


# ─── Existing endpoints (upgraded) ───────────────────────────────────────────


@router.get("/graph/variant/{variant_id}", response_model=KnowledgeGraph)
async def get_variant_graph(
    variant_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get knowledge graph data for a variant."""
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


# ─── NEW v1.1 endpoints ──────────────────────────────────────────────────────


@router.get("/patient/{case_id}/summary", response_model=PatientSummary)
async def get_patient_summary(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    """Get consolidated patient summary for a case."""
    service = WorkbenchService(db)
    return await service.get_patient_summary(case_id)


@router.get("/activity/{case_id}", response_model=ActivityLog)
async def get_activity_log(
    case_id: str,
    limit: int = Query(50, ge=1, le=200),
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    """Get activity log for a case."""
    service = WorkbenchService(db)
    return await service.get_activity_log(case_id, limit=limit)


@router.get("/treatment/{case_id}", response_model=TreatmentRecommendation)
async def get_treatment_recommendation(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    """Get treatment recommendation for a case."""
    service = WorkbenchService(db)
    return await service.get_treatment_recommendation(case_id)


@router.post("/tumor-board/{case_id}/vote")
async def add_tumor_board_vote(
    case_id: str,
    vote: TumorBoardVote,
    user: UserModel = Depends(require_case_access(CaseRole.REVIEWER)),
    db: AsyncSession = Depends(get_db),
):
    """Add a vote to a tumor board review."""
    repo = TumorBoardRepository(db)
    reviews = await repo.get_reviews_by_case(case_id)
    if not reviews:
        # Auto-create a review if none exists
        review = await repo.create_review(
            case_id=case_id,
            reviewer_id=str(user.id),
            reviewer_name=getattr(user, 'display_name', '') or getattr(user, 'username', ''),
        )
        review_id = review.id
    else:
        review_id = reviews[0].id

    vote_data = {
        "reviewer_id": vote.reviewer_id or str(user.id),
        "reviewer_name": vote.reviewer_name or getattr(user, 'display_name', '') or getattr(user, 'username', ''),
        "vote": vote.vote,
        "rationale": vote.rationale,
        "created_at": vote.created_at or __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
    }
    await repo.add_comment(review_id, vote_data)
    return {"status": "ok", "review_id": str(review_id), "vote": vote_data}


@router.post("/tumor-board/{case_id}/comment")
async def add_tumor_board_comment(
    case_id: str,
    comment: dict,
    user: UserModel = Depends(require_case_access(CaseRole.REVIEWER)),
    db: AsyncSession = Depends(get_db),
):
    """Add a comment to a tumor board review."""
    repo = TumorBoardRepository(db)
    reviews = await repo.get_reviews_by_case(case_id)
    if not reviews:
        review = await repo.create_review(
            case_id=case_id,
            reviewer_id=str(user.id),
            reviewer_name=getattr(user, 'display_name', '') or getattr(user, 'username', ''),
        )
        review_id = review.id
    else:
        review_id = reviews[0].id

    comment_data = {
        "user_id": str(user.id),
        "user_name": getattr(user, 'display_name', '') or getattr(user, 'username', ''),
        "content": comment.get("content", ""),
        "comment_type": comment.get("comment_type", "general"),
        "created_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
    }
    await repo.add_comment(review_id, comment_data)
    return {"status": "ok", "review_id": str(review_id)}


@router.get("/state/{case_id}")
async def get_workbench_state(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    """Get full workbench initial state for a case."""
    service = WorkbenchService(db)
    patient_summary, timeline, treatment, activity = await __import__('asyncio').gather(
        service.get_patient_summary(case_id),
        service.get_case_timeline(case_id),
        service.get_treatment_recommendation(case_id),
        service.get_activity_log(case_id, limit=20),
    )
    return {
        "patient_summary": patient_summary.model_dump() if hasattr(patient_summary, 'model_dump') else patient_summary,
        "timeline": timeline.model_dump() if hasattr(timeline, 'model_dump') else timeline,
        "treatment": treatment.model_dump() if hasattr(treatment, 'model_dump') else treatment,
        "activity": activity.model_dump() if hasattr(activity, 'model_dump') else activity,
    }
