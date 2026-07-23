"""
Upload API routes.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.api.v1.deps import get_upload_repo
from src.backend.auth.dependencies import require_auth, verify_case_access
from src.backend.database.session import get_db
from src.backend.domain.case_acl import CaseRole
from src.backend.domain.uploaded_file import UploadedFileCreate, UploadedFileResponse
from src.backend.domain.user import UserModel
from src.backend.repositories.sequencing_test_repo import SequencingTestRepository
from src.backend.repositories.specimen_repo import SpecimenRepository
from src.backend.repositories.uploaded_file_repo import UploadedFileRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/uploads", tags=["uploads"])


async def _resolve_upload_case_id(
    upload_id: uuid.UUID,
    repo: UploadedFileRepository,
    db: AsyncSession,
) -> uuid.UUID:
    """Resolve case_id from an upload record through sequencing_test → specimen → case."""
    upload = await repo.get(upload_id)
    if not upload or not upload.sequencing_test_id:
        raise HTTPException(status_code=404, detail="Upload not found")
    st_repo = SequencingTestRepository(db)
    st = await st_repo.get(upload.sequencing_test_id)
    if not st or not st.specimen_id:
        raise HTTPException(status_code=404, detail="Upload case context not found")
    spec_repo = SpecimenRepository(db)
    spec = await spec_repo.get(st.specimen_id)
    if not spec or not spec.case_id:
        raise HTTPException(status_code=404, detail="Upload case context not found")
    return spec.case_id


@router.post("", response_model=UploadedFileResponse, status_code=201)
async def create_upload(
    body: UploadedFileCreate,
    user: UserModel = Depends(require_auth),
    repo: UploadedFileRepository = Depends(get_upload_repo),
    db: AsyncSession = Depends(get_db),
):
    # Verify case access if sequencing_test_id is provided
    if body.sequencing_test_id:
        try:
            st_id = uuid.UUID(body.sequencing_test_id)
            st_repo = SequencingTestRepository(db)
            st = await st_repo.get(st_id)
            if st and st.specimen_id:
                spec_repo = SpecimenRepository(db)
                spec = await spec_repo.get(st.specimen_id)
                if spec and spec.case_id:
                    await verify_case_access(spec.case_id, user, db, CaseRole.EDITOR)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid sequencing_test_id")

    try:
        upload = await repo.create(**body.model_dump(exclude_none=True))
        return UploadedFileResponse.model_validate(upload)
    except Exception as e:
        logger.exception("Failed to create upload record")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{upload_id}", response_model=UploadedFileResponse)
async def get_upload(
    upload_id: str,
    user: UserModel = Depends(require_auth),
    repo: UploadedFileRepository = Depends(get_upload_repo),
    db: AsyncSession = Depends(get_db),
):
    try:
        uid = uuid.UUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID")

    # Resolve case and verify access
    case_id = await _resolve_upload_case_id(uid, repo, db)
    await verify_case_access(case_id, user, db, CaseRole.VIEWER)

    upload = await repo.get(uid)
    return UploadedFileResponse.model_validate(upload)
