"""
AuthService — authentication and authorization service.

Provides token-based auth with role-based access control (RBAC).
"""

from __future__ import annotations

import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Request

from src.backend.auth.models import (
    User, Role, Permission, ROLE_PERMISSIONS,
    UserCreate, UserResponse, TokenResponse,
    AuthenticationError, PermissionDeniedError,
)


class AuthService:
    """
    Authentication and authorization service.

    Uses Bearer token authentication with SHA256-hashed tokens.
    In production, this should use a proper auth library (OAuth2, JWT).
    """

    def __init__(self):
        self._users: dict[str, User] = {}
        self._token_store: dict[str, str] = {}  # token_hash -> user_id
        self._secret_key = os.getenv("AUTH_SECRET_KEY", secrets.token_hex(32))
        self._token_ttl_hours = int(os.getenv("AUTH_TOKEN_TTL", "24"))

        # Create default admin user
        admin_id = str(uuid.uuid4())
        self._users["admin"] = User(
            id=admin_id,
            username="admin",
            email="admin@example.com",
            role=Role.ADMIN,
        )
        # Default admin token (for development only)
        admin_token = "akc-dev-token-change-in-production"
        self._token_store[hashlib.sha256(admin_token.encode()).hexdigest()] = admin_id

    def authenticate(self, token: str) -> User:
        """Authenticate a user by bearer token."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        user_id = self._token_store.get(token_hash)
        if not user_id:
            raise AuthenticationError("Invalid or expired token")

        for user in self._users.values():
            if user.id == user_id:
                if not user.is_active:
                    raise AuthenticationError("User account is disabled")
                return user

        raise AuthenticationError("User not found")

    def authorize(self, user: User, permission: Permission) -> bool:
        """Check if a user has a specific permission."""
        user_permissions = ROLE_PERMISSIONS.get(user.role, [])
        return permission in user_permissions

    def require_permission(self, user: User, permission: Permission):
        """Require a specific permission, raising if not granted."""
        if not self.authorize(user, permission):
            raise PermissionDeniedError(
                f"User {user.username} lacks permission: {permission.value}"
            )

    def create_user(self, user_create: UserCreate) -> UserResponse:
        """Create a new user (admin only)."""
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            username=user_create.username,
            email=user_create.email,
            role=user_create.role,
        )
        self._users[user_create.username] = user

        # Generate token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        self._token_store[token_hash] = user_id

        return UserResponse(
            id=user_id,
            username=user.username,
            email=user.email,
            role=user.role.value,
            is_active=user.is_active,
        )

    def get_user(self, username: str) -> Optional[User]:
        return self._users.get(username)


# Global auth service instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
