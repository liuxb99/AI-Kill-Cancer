"""
Case ACL management API — grant, revoke, and list case permissions.
"""
from __future__ import annotations

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.auth.dependencies import require_case_access
from src.backend.auth.case_acl_service import CaseACLService
from src.backend.auth.models import PermissionDeniedError
from src.backend.database.session import get_db
from src.backend.domain.case_acl import (
    CaseACLModel, CaseRole, CaseACLCreate, CaseACLResponse,
)
from src.backend.domain.user import UserModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cases/{case_id}/acl", tags=["case-acl"])


def _to_acl_response(acl: CaseACLModel) -> CaseACLResponse:
    return CaseACLResponse(
        id=str(acl.id),
        case_id=str(acl.case_id),
        user_id=str(acl.user_id),
        role=acl.role,
        created_at=acl.created_at,
    )


@router.get("", response_model=list[CaseACLResponse])
async def list_case_acls(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    """List all ACL entries for a case (requires VIEWER access)."""
    try:
        cid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Case not found")

    acl_service = CaseACLService(db)
    acls = await acl_service.list_case_acls(cid)
    return [_to_acl_response(a) for a in acls]


@router.post("", response_model=CaseACLResponse, status_code=status.HTTP_201_CREATED)
async def grant_case_access(
    case_id: str,
    body: CaseACLCreate,
    user: UserModel = Depends(require_case_access(CaseRole.OWNER)),
    db: AsyncSession = Depends(get_db),
):
    """Grant access to a user on a case (requires OWNER access)."""
    try:
        cid = uuid.UUID(case_id)
        target_user_id = uuid.UUID(body.user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")

    acl_service = CaseACLService(db)
    try:
        acl = await acl_service.grant_access(
            case_id=cid,
            grantor=user,
            target_user_id=target_user_id,
            role=CaseRole(body.role),
        )
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return _to_acl_response(acl)


@router.delete("/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_case_access(
    case_id: str,
    target_user_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.OWNER)),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a user's access to a case (requires OWNER access)."""
    try:
        cid = uuid.UUID(case_id)
        tid = uuid.UUID(target_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")

    acl_service = CaseACLService(db)
    try:
        await acl_service.revoke_access(case_id=cid, grantor=user, target_user_id=tid)
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
