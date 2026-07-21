"""
Sequencing test API routes.
"""
from __future__ import annotations

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.api.v1.deps import get_sequencing_repo
from src.backend.auth.dependencies import require_auth, verify_case_access
from src.backend.database.session import get_db
from src.backend.domain.case_acl import CaseRole
from src.backend.domain.user import UserModel
from src.backend.domain.sequencing import SequencingTestCreate, SequencingTestResponse
from src.backend.repositories.sequencing_test_repo import SequencingTestRepository
from src.backend.repositories.specimen_repo import SpecimenRepository

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
    user: UserModel = Depends(require_auth),
    repo: SequencingTestRepository = Depends(get_sequencing_repo),
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

    try:
        test_obj = await repo.create(**body.model_dump(exclude_none=True))
        return SequencingTestResponse.model_validate(test_obj)
    except Exception as e:
        logger.exception("Failed to create sequencing test")
        raise HTTPException(status_code=500, detail=str(e))


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
