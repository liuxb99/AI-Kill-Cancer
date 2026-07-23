"""
Cancer case API routes with case-level ACL.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.api.v1.deps import get_cancer_case_repo
from src.backend.auth.case_acl_service import CaseACLService
from src.backend.auth.dependencies import require_auth, require_case_access
from src.backend.database.session import get_db
from src.backend.domain.cancer_case import (
    CancerCaseCreate,
    CancerCaseListResponse,
    CancerCaseResponse,
    CancerCaseUpdate,
)
from src.backend.domain.case_acl import CaseRole
from src.backend.domain.user import UserModel
from src.backend.repositories.cancer_case_repo import CancerCaseRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CancerCaseResponse, status_code=201)
async def create_case(
    body: CancerCaseCreate,
    user: UserModel = Depends(require_auth),
    repo: CancerCaseRepository = Depends(get_cancer_case_repo),
    db: AsyncSession = Depends(get_db),
):
    """Create a new cancer case. Creator becomes the owner."""
    try:
        case = await repo.create(**body.model_dump(exclude_none=True))
        # Auto-grant owner role to the creator
        acl_service = CaseACLService(db)
        await acl_service.grant_owner(case.id, user.id)
        return CancerCaseResponse(
            id=str(case.id),
            patient_id=str(case.patient_id),
            oncotree_code=case.oncotree_code,
            cancer_type=case.cancer_type.value if hasattr(case.cancer_type, "value") else case.cancer_type,
            histology=case.histology,
            stage=case.stage,
            diagnosis_date=case.diagnosis_date,
            radioiodine_status=case.radioiodine_status,
            recurrence_status=case.recurrence_status,
            metastatic_sites=case.metastatic_sites or [],
            treatment_history=case.treatment_history or [],
            current_medications=case.current_medications or [],
            clinical_notes=case.clinical_notes,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )
    except Exception as e:
        logger.exception("Failed to create cancer case")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{case_id}", response_model=CancerCaseResponse)
async def get_case(
    case_id: str,
    _: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    repo: CancerCaseRepository = Depends(get_cancer_case_repo),
):
    """Get a cancer case (requires VIEWER access)."""
    try:
        cid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Case not found")

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
    user: UserModel = Depends(require_auth),
    repo: CancerCaseRepository = Depends(get_cancer_case_repo),
    db: AsyncSession = Depends(get_db),
):
    """List cancer cases the user has access to."""
    from src.backend.domain.cancer_case import CancerCaseModel

    filters = []
    if cancer_type:
        filters.append(CancerCaseModel.cancer_type == cancer_type)

    # Filter to only cases the user has access to
    acl_service = CaseACLService(db)
    user_acls = await acl_service.list_user_cases(user.id)
    accessible_case_ids = [acl.case_id for acl in user_acls]

    # Admin can see all cases
    if user.role.value != "admin":
        if accessible_case_ids:
            filters.append(CancerCaseModel.id.in_(accessible_case_ids))
        else:
            # No accessible cases, return empty
            return CancerCaseListResponse(items=[], total=0, skip=skip, limit=limit)

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


@router.put("/{case_id}", response_model=CancerCaseResponse)
async def update_case(
    case_id: str,
    body: CancerCaseUpdate,
    _: UserModel = Depends(require_case_access(CaseRole.EDITOR)),
    repo: CancerCaseRepository = Depends(get_cancer_case_repo),
):
    """Update a cancer case (requires EDITOR access)."""
    try:
        cid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Case not found")

    case = await repo.update(cid, **body.model_dump(exclude_none=True))
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return CancerCaseResponse.model_validate(case)


@router.delete("/{case_id}", status_code=204)
async def delete_case(
    case_id: str,
    _: UserModel = Depends(require_case_access(CaseRole.OWNER)),
    repo: CancerCaseRepository = Depends(get_cancer_case_repo),
):
    """Delete a cancer case (requires OWNER access)."""
    try:
        cid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Case not found")

    deleted = await repo.delete(cid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Case not found")
