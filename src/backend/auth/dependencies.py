"""
FastAPI dependencies for authentication and authorization.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.backend.auth.models import User, Permission, PermissionDeniedError
from src.backend.auth.service import AuthService, get_auth_service

_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
    auth: AuthService = Depends(get_auth_service),
) -> Optional[User]:
    """Get the current authenticated user from the bearer token."""
    if credentials is None:
        return None
    try:
        return auth.authenticate(credentials.credentials)
    except Exception:
        return None


async def require_auth(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """Require authentication. Returns 401 if not authenticated."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(required_role: str):
    """Require a specific role. Returns 403 if role mismatch."""
    async def role_checker(user: User = Depends(require_auth)) -> User:
        if user.role.value != required_role and user.role.value != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return user
    return role_checker


def require_permission(required_permission: Permission):
    """Require a specific permission. Returns 403 if not granted."""
    async def permission_checker(
        user: User = Depends(require_auth),
        auth: AuthService = Depends(get_auth_service),
    ) -> User:
        try:
            auth.require_permission(user, required_permission)
            return user
        except PermissionDeniedError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )
    return permission_checker
