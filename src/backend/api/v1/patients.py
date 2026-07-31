"""
Patient API routes.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.api.v1.deps import get_patient_repo
from src.backend.auth.dependencies import require_auth
from src.backend.database.session import get_db
from src.backend.domain.patient import PatientCreate, PatientListResponse, PatientResponse, PatientUpdate
from src.backend.domain.user import UserModel
from src.backend.repositories.patient_repo import PatientRepository
from src.backend.services.patient_service import PatientService


def _to_patient_response(patient) -> PatientResponse:
    """Convert ORM model to Pydantic response with automatic UUID serialization."""
    return PatientResponse.model_validate(patient)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientResponse, status_code=201)
async def create_patient(
    body: PatientCreate,
    request: Request,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    error_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    service = PatientService(db)
    try:
        patient = await service.create(**body.model_dump(exclude_none=True))
        return _to_patient_response(patient)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create patient (error_id=%s)", error_id)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "error_id": error_id,
                "message": "Internal server error",
            },
        )


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    user: UserModel = Depends(require_auth),
    repo: PatientRepository = Depends(get_patient_repo),
):
    try:
        pid = uuid.UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient ID")

    patient = await repo.get(pid)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return _to_patient_response(patient)


@router.get("", response_model=PatientListResponse)
async def list_patients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user: UserModel = Depends(require_auth),
    repo: PatientRepository = Depends(get_patient_repo),
):
    patients = await repo.list(skip=skip, limit=limit)
    total = await repo.count()
    items = [_to_patient_response(p) for p in patients]
    return PatientListResponse(items=items, total=total, skip=skip, limit=limit)


@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    body: PatientUpdate,
    request: Request,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    try:
        pid = uuid.UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient ID")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    error_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    service = PatientService(db)
    try:
        patient = await service.update(pid, **updates)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update patient (error_id=%s)", error_id)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "error_id": error_id,
                "message": "Internal server error",
            },
        )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return PatientResponse.model_validate(patient)


@router.delete("/{patient_id}", status_code=204)
async def delete_patient(
    patient_id: str,
    request: Request,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    try:
        pid = uuid.UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient ID")

    error_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    service = PatientService(db)
    try:
        deleted = await service.delete(pid)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete patient (error_id=%s)", error_id)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "error_id": error_id,
                "message": "Internal server error",
            },
        )
    if not deleted:
        raise HTTPException(status_code=404, detail="Patient not found")
