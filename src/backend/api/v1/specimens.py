"""
Specimen API routes.
"""
from __future__ import annotations

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.api.v1.deps import get_specimen_repo
from src.backend.auth.dependencies import require_auth, verify_case_access
from src.backend.database.session import get_db
from src.backend.domain.case_acl import CaseRole
from src.backend.domain.user import UserModel
from src.backend.domain.specimen import SpecimenCreate, SpecimenResponse
from src.backend.repositories.specimen_repo import SpecimenRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/specimens", tags=["specimens"])


@router.post("", response_model=SpecimenResponse, status_code=201)
async def create_specimen(
    body: SpecimenCreate,
    user: UserModel = Depends(require_auth),
    repo: SpecimenRepository = Depends(get_specimen_repo),
):
    try:
        specimen = await repo.create(**body.model_dump(exclude_none=True))
        return SpecimenResponse.model_validate(specimen)
    except Exception as e:
        logger.exception("Failed to create specimen")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{specimen_id}", response_model=SpecimenResponse)
async def get_specimen(
    specimen_id: str,
    user: UserModel = Depends(require_auth),
    repo: SpecimenRepository = Depends(get_specimen_repo),
    db: AsyncSession = Depends(get_db),
):
    try:
        sid = uuid.UUID(specimen_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid specimen ID")

    specimen = await repo.get(sid)
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    # Check case-level access
    if hasattr(specimen, 'case_id') and specimen.case_id:
        await verify_case_access(specimen.case_id, user, db, CaseRole.VIEWER)
    return SpecimenResponse.model_validate(specimen)
