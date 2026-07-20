"""
Cancer case API routes.
"""
from __future__ import annotations

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from src.backend.api.v1.deps import get_cancer_case_repo
from src.backend.domain.cancer_case import CancerCaseCreate, CancerCaseUpdate, CancerCaseResponse, CancerCaseListResponse
from src.backend.repositories.cancer_case_repo import CancerCaseRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CancerCaseResponse, status_code=201)
async def create_case(
    body: CancerCaseCreate,
    repo: CancerCaseRepository = Depends(get_cancer_case_repo),
):
    try:
        case = await repo.create(**body.model_dump(exclude_none=True))
        return CancerCaseResponse.model_validate(case)
    except Exception as e:
        logger.exception("Failed to create cancer case")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{case_id}", response_model=CancerCaseResponse)
async def get_case(
    case_id: str,
    repo: CancerCaseRepository = Depends(get_cancer_case_repo),
):
    try:
        cid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid case ID")

    case = await repo.get(cid)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return CancerCaseResponse.model_validate(case)


@router.get("", response_model=CancerCaseListResponse)
async def list_cases(
    patient_id: str | None = Query(None),
    cancer_type: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    repo: CancerCaseRepository = Depends(get_cancer_case_repo),
):
    from sqlalchemy import select
    from src.backend.domain.cancer_case import CancerCaseModel

    filters = []
    if cancer_type:
        filters.append(CancerCaseModel.cancer_type == cancer_type)

    cases = await repo.list(skip=skip, limit=limit, filters=filters or None)

    if patient_id:
        try:
            pid = uuid.UUID(patient_id)
            cases = await repo.find_by_patient(pid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid patient ID")

    total = await repo.count(filters=filters or None)
    return CancerCaseListResponse(
        items=[CancerCaseResponse.model_validate(c) for c in cases],
        total=total,
        skip=skip,
        limit=limit,
    )
