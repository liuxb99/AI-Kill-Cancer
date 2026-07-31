"""
Sequencing test API routes.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.api.v1.deps import get_sequencing_repo
from src.backend.auth.dependencies import require_auth, verify_case_access
from src.backend.database.session import get_db
from src.backend.domain.case_acl import CaseRole
from src.backend.domain.sequencing import SequencingTestCreate, SequencingTestResponse
from src.backend.domain.user import UserModel
from src.backend.repositories.sequencing_test_repo import SequencingTestRepository
from src.backend.repositories.specimen_repo import SpecimenRepository
from src.backend.services.sequencing_test_service import SequencingTestService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sequencing-tests", tags=["sequencing-tests"])


async def _resolve_sequencing_case_id(
    test: object,
    db: AsyncSession,
) -> uuid.UUID:
    """Resolve case_id from a sequencing test record (sequencing_test → specimen → case)."""
    if not hasattr(test, 'specimen_id') or not test.specimen_id:
        raise HTTPException(status_code=404, detail="Sequencing test case context not found")
    spec_repo = SpecimenRepository(db)
    spec = await spec_repo.get(test.specimen_id)
    if not spec or not spec.case_id:
        raise HTTPException(status_code=404, detail="Sequencing test case context not found")
    return spec.case_id


@router.post("", response_model=SequencingTestResponse, status_code=201)
async def create_sequencing_test(
    body: SequencingTestCreate,
    request: Request,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    # Verify EDITOR access on the specimen's case
    try:
        spec_id = uuid.UUID(body.specimen_id)
        spec_repo = SpecimenRepository(db)
        spec = await spec_repo.get(spec_id)
        if not spec or not spec.case_id:
            raise HTTPException(status_code=400, detail="Specimen not found or missing case association")
        await verify_case_access(spec.case_id, user, db, CaseRole.EDITOR)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid specimen_id")

    error_id = (
        getattr(request.state, "request_id", None)
        or request.headers.get("X-Request-ID")
        or str(uuid.uuid4())
    )
    service = SequencingTestService(db)
    try:
        test_obj = await service.create(**body.model_dump(exclude_none=True))
        return SequencingTestResponse.model_validate(test_obj)
    except HTTPException:
        # 4xx 業務錯誤（如權限不足）透傳，不轉 500
        raise
    except Exception:
        # REVIEW-PHASE3F0-R3-P0-01 模式：不洩漏 str(e)，
        # 對外回傳固定訊息 + 可追蹤 error_id；完整例外寫入 server log。
        logger.exception("Failed to create sequencing test [error_id=%s]", error_id)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "error_id": error_id,
                "message": "Internal server error",
            },
        )


@router.get("/{test_id}", response_model=SequencingTestResponse)
async def get_sequencing_test(
    test_id: str,
    user: UserModel = Depends(require_auth),
    repo: SequencingTestRepository = Depends(get_sequencing_repo),
    db: AsyncSession = Depends(get_db),
):
    try:
        tid = uuid.UUID(test_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid test ID")

    test_obj = await repo.get(tid)
    if not test_obj:
        raise HTTPException(status_code=404, detail="Sequencing test not found")

    # Resolve case and verify VIEWER access
    case_id = await _resolve_sequencing_case_id(test_obj, db)
    await verify_case_access(case_id, user, db, CaseRole.VIEWER)

    return SequencingTestResponse.model_validate(test_obj)
