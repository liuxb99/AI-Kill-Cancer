"""
Patient API routes.
"""
from __future__ import annotations

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from src.backend.api.v1.deps import get_patient_repo
from src.backend.auth.dependencies import require_auth
from src.backend.domain.user import UserModel
from src.backend.domain.patient import PatientCreate, PatientUpdate, PatientResponse, PatientListResponse
from src.backend.repositories.patient_repo import PatientRepository


def _to_patient_response(patient) -> PatientResponse:
    """Convert ORM model to Pydantic response with automatic UUID serialization."""
    return PatientResponse.model_validate(patient)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientResponse, status_code=201)
async def create_patient(
    body: PatientCreate,
    user: UserModel = Depends(require_auth),
    repo: PatientRepository = Depends(get_patient_repo),
):
    try:
        patient = await repo.create(**body.model_dump(exclude_none=True))
        return _to_patient_response(patient)
    except Exception as e:
        logger.exception("Failed to create patient")
        raise HTTPException(status_code=500, detail=str(e))


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
    user: UserModel = Depends(require_auth),
    repo: PatientRepository = Depends(get_patient_repo),
):
    try:
        pid = uuid.UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient ID")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    patient = await repo.update(pid, **updates)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return PatientResponse.model_validate(patient)


@router.delete("/{patient_id}", status_code=204)
async def delete_patient(
    patient_id: str,
    user: UserModel = Depends(require_auth),
    repo: PatientRepository = Depends(get_patient_repo),
):
    try:
        pid = uuid.UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient ID")

    deleted = await repo.delete(pid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Patient not found")
