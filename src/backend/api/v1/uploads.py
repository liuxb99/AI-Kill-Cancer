"""
Upload API routes.
"""
from __future__ import annotations

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException

from src.backend.api.v1.deps import get_upload_repo
from src.backend.domain.uploaded_file import UploadedFileCreate, UploadedFileResponse
from src.backend.repositories.uploaded_file_repo import UploadedFileRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadedFileResponse, status_code=201)
async def create_upload(
    body: UploadedFileCreate,
    repo: UploadedFileRepository = Depends(get_upload_repo),
):
    try:
        upload = await repo.create(**body.model_dump(exclude_none=True))
        return UploadedFileResponse.model_validate(upload)
    except Exception as e:
        logger.exception("Failed to create upload record")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{upload_id}", response_model=UploadedFileResponse)
async def get_upload(
    upload_id: str,
    repo: UploadedFileRepository = Depends(get_upload_repo),
):
    try:
        uid = uuid.UUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID")

    upload = await repo.get(uid)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return UploadedFileResponse.model_validate(upload)
