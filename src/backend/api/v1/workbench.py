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

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
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
from src.backend.workbench.repository import TumorBoardRepository, WorkbenchNoteModel
from src.backend.reasoning.service import ClinicalReasoningService
from src.backend.reasoning.models import ClinicalReasoningResult
from src.backend.reasoning.repository import ReasoningRunRepository, ReasoningRunModel
from src.backend.reasoning.llm import get_llm_adapter
from src.backend.domain.uploaded_file import UploadedFileModel

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
    review = await repo.create_review(
        case_id=case_id,
        reviewer_id=str(user.id),
        reviewer_name=getattr(user, 'display_name', '') or getattr(user, 'username', ''),
    )
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
    raise HTTPException(status_code=501, detail={"error": "not_implemented", "message": "Variant comparison not yet implemented"})


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
    """Add a vote to a tumor board review.
    Reviewer identity is always derived from the JWT token — client-supplied identity is ignored.
    """
    # Validate vote value
    valid_votes = {"approve", "reject", "abstain"}
    if vote.vote not in valid_votes:
        raise HTTPException(status_code=422, detail={
            "error": "invalid_vote",
            "message": f"Vote must be one of: {', '.join(valid_votes)}",
        })

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

    # All identity fields come from JWT — client values are NEVER used
    vote_data = {
        "reviewer_id": str(user.id),
        "reviewer_name": getattr(user, 'display_name', '') or getattr(user, 'username', ''),
        "vote": vote.vote,
        "rationale": vote.rationale,
        "created_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
    }

    # Write Audit Log
    try:
        from src.backend.domain.audit_log import AuditLogModel
        from datetime import datetime, timezone
        audit = AuditLogModel(
            actor=str(user.id),
            action="tumor_board_vote",
            resource_type="tumor_board_review",
            resource_id=str(review_id),
            details={"case_id": case_id, "vote": vote.vote, "rationale": vote.rationale},
            created_at=datetime.now(timezone.utc),
        )
        db.add(audit)
        await db.commit()
    except Exception as e:
        logger.warning("Failed to write audit log for vote: %s", e)

    await repo.add_comment(review_id, vote_data)
    return {"status": "ok", "review_id": str(review_id), "vote": vote_data}


class TumorBoardCommentIn(BaseModel):
    """Request model for tumor board comments — client supplies only business data."""
    content: str = ""
    comment_type: str = "general"


@router.post("/tumor-board/{case_id}/comment")
async def add_tumor_board_comment(
    case_id: str,
    comment: TumorBoardCommentIn,
    user: UserModel = Depends(require_case_access(CaseRole.REVIEWER)),
    db: AsyncSession = Depends(get_db),
):
    """Add a comment to a tumor board review.
    User identity is always derived from the JWT token.
    """
    if not comment.content or not comment.content.strip():
        raise HTTPException(status_code=422, detail={
            "error": "empty_comment",
            "message": "Comment content cannot be empty",
        })

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
        "content": comment.content,
        "comment_type": comment.comment_type,
        "created_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
    }

    # Write Audit Log
    try:
        from src.backend.domain.audit_log import AuditLogModel
        from datetime import datetime, timezone
        audit = AuditLogModel(
            actor=str(user.id),
            action="tumor_board_comment",
            resource_type="tumor_board_review",
            resource_id=str(review_id),
            details={"case_id": case_id, "comment_type": comment.comment_type},
            created_at=datetime.now(timezone.utc),
        )
        db.add(audit)
        await db.commit()
    except Exception as e:
        logger.warning("Failed to write audit log for comment: %s", e)

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
    patient_summary, timeline, treatment, activity = await asyncio.gather(
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


# ─── Notes CRUD ──────────────────────────────────────────────────────────────



class NoteCreate(BaseModel):
    content: str
    note_type: str = "general"


class NoteUpdate(BaseModel):
    content: str


@router.get("/case/{case_id}/notes")
async def get_notes(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    """Get all notes for a case."""
    from sqlalchemy import select
    stmt = (select(WorkbenchNoteModel)
            .where(WorkbenchNoteModel.case_id == case_id)
            .order_by(WorkbenchNoteModel.created_at.desc()))
    result = await db.execute(stmt)
    notes = list(result.scalars().all())
    return [
        {
            "id": str(n.id),
            "case_id": n.case_id,
            "user_id": n.user_id or "",
            "content": n.content,
            "note_type": n.note_type or "general",
            "created_at": n.created_at.isoformat() if hasattr(n.created_at, 'isoformat') else str(n.created_at),
        }
        for n in notes
    ]


@router.post("/case/{case_id}/notes", status_code=201)
async def create_note(
    case_id: str,
    note: NoteCreate,
    user: UserModel = Depends(require_case_access(CaseRole.EDITOR)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new note for a case."""
    if not note.content or not note.content.strip():
        raise HTTPException(status_code=422, detail={"error": "empty_content", "message": "Note content cannot be empty"})

    from datetime import datetime, timezone
    model = WorkbenchNoteModel(
        case_id=case_id,
        user_id=str(user.id),
        content=note.content,
        note_type=note.note_type,
        created_at=datetime.now(timezone.utc),
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)

    # Audit log
    try:
        from src.backend.domain.audit_log import AuditLogModel
        audit = AuditLogModel(
            actor=str(user.id),
            action="note_created",
            resource_type="workbench_note",
            resource_id=case_id,
            details={"note_id": str(model.id)},
            created_at=datetime.now(timezone.utc),
        )
        db.add(audit)
        await db.commit()
    except Exception as e:
        logger.debug("Failed to write audit log for note creation: %s", e)

    return {
        "id": str(model.id),
        "case_id": model.case_id,
        "user_id": model.user_id or "",
        "content": model.content,
        "note_type": model.note_type or "general",
        "created_at": model.created_at.isoformat() if hasattr(model.created_at, 'isoformat') else str(model.created_at),
    }


@router.patch("/case/{case_id}/notes/{note_id}")
async def update_note(
    case_id: str,
    note_id: str,
    note: NoteUpdate,
    user: UserModel = Depends(require_case_access(CaseRole.EDITOR)),
    db: AsyncSession = Depends(get_db),
):
    """Update a note."""
    try:
        nid = uuid.UUID(note_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "invalid_uuid", "message": "Invalid note ID"})

    if not note.content or not note.content.strip():
        raise HTTPException(status_code=422, detail={"error": "empty_content", "message": "Note content cannot be empty"})

    from sqlalchemy import select
    stmt = select(WorkbenchNoteModel).where(
        WorkbenchNoteModel.id == nid,
        WorkbenchNoteModel.case_id == case_id,
    )
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Note not found"})

    model.content = note.content
    await db.commit()
    await db.refresh(model)

    return {
        "id": str(model.id),
        "case_id": model.case_id,
        "user_id": model.user_id or "",
        "content": model.content,
        "note_type": model.note_type or "general",
        "created_at": model.created_at.isoformat() if hasattr(model.created_at, 'isoformat') else str(model.created_at),
    }


@router.delete("/case/{case_id}/notes/{note_id}")
async def delete_note(
    case_id: str,
    note_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.EDITOR)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a note."""
    try:
        nid = uuid.UUID(note_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "invalid_uuid", "message": "Invalid note ID"})

    from sqlalchemy import select
    stmt = select(WorkbenchNoteModel).where(
        WorkbenchNoteModel.id == nid,
        WorkbenchNoteModel.case_id == case_id,
    )
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Note not found"})

    await db.delete(model)
    await db.commit()

    return {"status": "deleted"}


# ─── Reasoning Session ──────────────────────────────────────────────────────



class ReasoningQuestion(BaseModel):
    question: str


@router.post("/case/{case_id}/reasoning", status_code=201)
async def create_reasoning_session(
    case_id: str,
    question: ReasoningQuestion,
    user: UserModel = Depends(require_case_access(CaseRole.EDITOR)),
    db: AsyncSession = Depends(get_db),
):
    """Create a reasoning session and get AI response."""
    if not question.question or not question.question.strip():
        raise HTTPException(status_code=422, detail={"error": "empty_question", "message": "Question cannot be empty"})

    llm_adapter = get_llm_adapter()
    service = ClinicalReasoningService(db=db, llm_adapter=llm_adapter)

    result = await service.reason(
        case_id=case_id,
        gene_symbol="",
        disease="",
    )

    # Create reasoning run in DB
    repo = ReasoningRunRepository(db)
    run = await repo.create(
        case_id=case_id,
        status="completed",
        reasoning_data=result.model_dump() if hasattr(result, 'model_dump') else {},
    )

    messages = [
        {
            "id": str(run.id) + "-user",
            "role": "user",
            "content": question.question,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": str(run.id),
            "role": "assistant",
            "content": result.summary if hasattr(result, 'summary') and result.summary else "Analysis completed.",
            "confidence": result.confidence_score if hasattr(result, 'confidence_score') else None,
            "evidence": [
                {"id": e.evidence_id, "summary": e.summary, "source": e.source}
                for e in (result.supporting_evidence or [])
            ] if hasattr(result, 'supporting_evidence') else [],
            "references": result.references if hasattr(result, 'references') else [],
            "decision_trace": result.decision_trace if hasattr(result, 'decision_trace') else [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    ]

    return {
        "id": str(run.id),
        "case_id": case_id,
        "messages": messages,
        "created_at": run.created_at.isoformat() if hasattr(run.created_at, 'isoformat') else str(run.created_at),
        "updated_at": run.updated_at.isoformat() if hasattr(run.updated_at, 'isoformat') else str(run.updated_at),
    }


@router.get("/case/{case_id}/reasoning")
async def list_reasoning_sessions(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    """List all reasoning sessions for a case."""
    from sqlalchemy import select
    stmt = (select(ReasoningRunModel)
            .where(ReasoningRunModel.case_id == case_id)
            .order_by(ReasoningRunModel.created_at.desc())
            .limit(20))
    result = await db.execute(stmt)
    runs = list(result.scalars().all())
    return [
        {
            "id": str(r.id),
            "case_id": r.case_id,
            "messages": [],
            "created_at": r.created_at.isoformat() if hasattr(r.created_at, 'isoformat') else str(r.created_at),
            "updated_at": r.updated_at.isoformat() if hasattr(r.updated_at, 'isoformat') else str(r.updated_at),
        }
        for r in runs
    ]


@router.get("/case/{case_id}/reasoning/{session_id}")
async def get_reasoning_session(
    case_id: str,
    session_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific reasoning session with its messages."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "invalid_uuid", "message": "Invalid session ID"})

    from sqlalchemy import select
    stmt = select(ReasoningRunModel).where(
        ReasoningRunModel.id == sid,
        ReasoningRunModel.case_id == case_id,
    )
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Reasoning session not found"})

    reasoning_data = run.reasoning_data if isinstance(run.reasoning_data, dict) else {}
    reasoning_result = ClinicalReasoningResult(**reasoning_data) if reasoning_data else None

    messages = []
    if reasoning_result:
        messages.append({
            "id": str(run.id),
            "role": "assistant",
            "content": reasoning_result.summary if hasattr(reasoning_result, 'summary') and reasoning_result.summary else "",
            "confidence": reasoning_result.confidence_score if hasattr(reasoning_result, 'confidence_score') else None,
            "evidence": [
                {"id": e.evidence_id, "summary": e.summary, "source": e.source}
                for e in (reasoning_result.supporting_evidence or [])
            ] if hasattr(reasoning_result, 'supporting_evidence') else [],
            "references": reasoning_result.references if hasattr(reasoning_result, 'references') else [],
            "decision_trace": reasoning_result.decision_trace if hasattr(reasoning_result, 'decision_trace') else [],
            "created_at": run.created_at.isoformat() if hasattr(run.created_at, 'isoformat') else str(run.created_at),
        })

    return {
        "id": str(run.id),
        "case_id": run.case_id,
        "messages": messages,
        "created_at": run.created_at.isoformat() if hasattr(run.created_at, 'isoformat') else str(run.created_at),
        "updated_at": run.updated_at.isoformat() if hasattr(run.updated_at, 'isoformat') else str(run.updated_at),
    }


# ─── Attachments ─────────────────────────────────────────────────────────────



@router.get("/case/{case_id}/attachments")
async def get_attachments(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    """Get all attachments (uploaded files) for a case.
    Traverses case → specimen → sequencing_test → uploaded_file relationship.
    """
    from sqlalchemy import select
    from src.backend.domain.specimen import SpecimenModel
    from src.backend.domain.sequencing import SequencingTestModel

    # Find specimens for this case
    spec_stmt = select(SpecimenModel).where(SpecimenModel.case_id == uuid.UUID(case_id))
    spec_result = await db.execute(spec_stmt)
    specimens = list(spec_result.scalars().all())

    attachments = []
    for spec in specimens:
        # Find sequencing tests for this specimen
        seq_stmt = select(SequencingTestModel).where(SequencingTestModel.specimen_id == spec.id)
        seq_result = await db.execute(seq_stmt)
        seq_tests = list(seq_result.scalars().all())

        for seq in seq_tests:
            # Find uploaded files for this sequencing test
            up_stmt = select(UploadedFileModel).where(UploadedFileModel.sequencing_test_id == seq.id)
            up_result = await db.execute(up_stmt)
            files = list(up_result.scalars().all())

            for f in files:
                attachments.append({
                    "id": str(f.id),
                    "case_id": case_id,
                    "filename": f.original_filename,
                    "file_type": f.file_type or "",
                    "media_type": f.media_type or "",
                    "size_bytes": f.size_bytes or 0,
                    "uploaded_by": "",
                    "upload_status": f.upload_status or "unknown",
                    "created_at": f.uploaded_at.isoformat() if hasattr(f.uploaded_at, 'isoformat') else str(f.uploaded_at),
                })

    return attachments


# ─── Variants for Case ──────────────────────────────────────────────────────


@router.get("/case/{case_id}/variants")
async def get_case_variants(
    case_id: str,
    gene: str = Query("", description="Filter by gene symbol"),
    pathogenicity: str = Query("", description="Filter by pathogenicity"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    """Get variants for a case with search, filter, and pagination."""
    try:
        cid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "invalid_uuid", "message": "Invalid case ID"})

    from src.backend.repositories.variant_repo import VariantRepository
    vrepo = VariantRepository(db)
    all_variants = await vrepo.find_by_case(cid)

    # Apply filters
    filtered = all_variants
    if gene:
        filtered = [v for v in filtered if gene.upper() in (getattr(v, 'gene_symbol', '') or '').upper()]
    if pathogenicity:
        filtered = [v for v in filtered if pathogenicity.lower() in (getattr(v, 'clinical_significance', '') or '').lower()]

    # Pagination
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    page_variants = filtered[start:end]

    return {
        "variants": [
            {
                "id": str(v.id),
                "gene_symbol": getattr(v, 'gene_symbol', '') or '',
                "hgvs_notation": getattr(v, 'hgvs_notation', '') or '',
                "protein_change": getattr(v, 'protein_change', '') or '',
                "variant_type": getattr(v, 'variant_type', '') or '',
                "clinical_significance": getattr(v, 'clinical_significance', '') or '',
                "vaf": float(getattr(v, 'vaf', 0) or 0),
                "pathogenicity": getattr(v, 'clinical_significance', '') or '',
                "evidence_level": getattr(v, 'evidence_level', '') or '',
                "population_frequency": float(getattr(v, 'af', 0) or 0),
                "annotation_source": getattr(v, 'annotation_source', '') or '',
                "created_at": v.created_at.isoformat() if hasattr(v, 'created_at') and v.created_at and hasattr(v.created_at, 'isoformat') else str(getattr(v, 'created_at', '')),
            }
            for v in page_variants
        ],
        "total": total,
    }
