"""
Auth API — registration, login, token refresh, logout, and user info.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.auth.dependencies import require_auth, require_permission
from src.backend.auth.models import (
    AuthenticationError,
    DuplicateUserError,
    Permission,
    Role,
)
from src.backend.auth.service import AuthService, get_auth_service
from src.backend.database.session import get_db
from src.backend.domain.user import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserModel,
    UserResponse,
)

_security = HTTPBearer(auto_error=False)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _to_user_response(user: UserModel) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else user.role,
        is_active=user.is_active,
        display_name=user.display_name,
        created_at=user.created_at,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(get_auth_service),
):
    """Register a new user account. Users are always created as VIEWER."""
    try:
        # Force non-admin role — public registration cannot set role
        body.role = Role.VIEWER
        return await auth.register_user(db, body)
    except DuplicateUserError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(get_auth_service),
):
    """Authenticate and receive access + refresh tokens."""
    try:
        return await auth.login(db, body)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(get_auth_service),
):
    """Exchange a valid refresh token for a new token pair."""
    try:
        return await auth.refresh_token(db, body.refresh_token)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_auth),
    auth: AuthService = Depends(get_auth_service),
):
    """Revoke the current session's tokens."""
    access_token = credentials.credentials if credentials else ""
    await auth.logout(db, access_token=access_token, refresh_token=body.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: UserModel = Depends(require_auth),
):
    """Return the currently authenticated user's profile."""
    return _to_user_response(current_user)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(get_auth_service),
    _=Depends(require_permission(Permission.MANAGE_USERS)),
):
    """Create a new user (admin only)."""
    try:
        return await auth.register_user(db, body)
    except DuplicateUserError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
