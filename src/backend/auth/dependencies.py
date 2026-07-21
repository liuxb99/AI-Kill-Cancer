"""
FastAPI dependencies for authentication and authorization.

Provides dependency injection for:
- get_current_user: Decodes JWT from Bearer header, returns UserModel or None
- require_auth: Requires a valid access token (returns 401)
- require_permission: Requires a specific permission (returns 403)
- require_case_access: Requires a specific role on a case (returns 403)
"""
from __future__ import annotations

import uuid
from typing import Optional, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.auth.models import Permission, PermissionDeniedError
from src.backend.auth.service import AuthService, get_auth_service
from src.backend.auth.case_acl_service import CaseACLService
from src.backend.database.session import get_db
from src.backend.domain.user import UserModel
from src.backend.domain.case_acl import CaseRole

_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
    auth: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
) -> Optional[UserModel]:
    """Decode Bearer JWT and return the user, or None if unauthenticated."""
    if credentials is None:
        return None
    try:
        return await auth.authenticate(db, credentials.credentials)
    except Exception:
        return None


async def require_auth(
    user: Optional[UserModel] = Depends(get_current_user),
) -> UserModel:
    """Require a valid access token. Returns 401 if missing or invalid."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_permission(required_permission: Permission):
    """Return a dependency that checks a specific permission. Returns 403 if not granted."""
    async def permission_checker(
        user: UserModel = Depends(require_auth),
        auth: AuthService = Depends(get_auth_service),
    ) -> UserModel:
        try:
            auth.require_permission(user, required_permission)
            return user
        except PermissionDeniedError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )
    return permission_checker


def require_case_access(required_role: Union[CaseRole, str]):
    """Return a dependency that checks case-level access.

    The route must have a `case_id` path parameter of type str.
    Returns 403 if the user lacks the required role on the case.

    Usage:
        @router.get("/cases/{case_id}")
        async def get_case(
            case_id: str,
            user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
        ):
    """
    role = CaseRole(required_role) if isinstance(required_role, str) else required_role

    async def case_access_checker(
        case_id: str,
        user: UserModel = Depends(require_auth),
        db: AsyncSession = Depends(get_db),
    ) -> UserModel:
        try:
            cid = uuid.UUID(case_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

        acl_service = CaseACLService(db)
        try:
            await acl_service.require_access(cid, user, role)
        except PermissionDeniedError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this case",
            )
        return user
    return case_access_checker


async def verify_case_access(
    case_id: uuid.UUID,
    user: UserModel,
    db: AsyncSession,
    required_role: Union[CaseRole, str] = CaseRole.VIEWER,
) -> None:
    """Utility function for routes that resolve case_id from other resources.

    Raises HTTPException 403 if access is denied.
    """
    role = CaseRole(required_role) if isinstance(required_role, str) else required_role
    acl_service = CaseACLService(db)
    try:
        await acl_service.require_access(case_id, user, role)
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this resource",
        )
