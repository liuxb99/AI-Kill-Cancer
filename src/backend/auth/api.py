"""
Auth API — user management and token endpoints.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from src.backend.auth.models import UserCreate, UserResponse, TokenResponse, Permission
from src.backend.auth.service import AuthService, get_auth_service
from src.backend.auth.dependencies import require_auth, require_permission

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(username: str, password: str, auth: AuthService = Depends(get_auth_service)):
    """Login (simplified — returns default token for development)."""
    return TokenResponse(
        access_token="akc-dev-token-change-in-production",
        token_type="bearer",
        user=UserResponse(
            id="admin-id",
            username="admin",
            role="admin",
            is_active=True,
        ),
    )


@router.post("/users", response_model=UserResponse)
async def create_user(
    user_create: UserCreate,
    auth: AuthService = Depends(get_auth_service),
    _=Depends(require_permission(Permission.MANAGE_USERS)),
):
    """Create a new user (admin only)."""
    return auth.create_user(user_create)
