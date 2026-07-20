"""
Authentication & Authorization system for production deployment.
"""

from src.backend.auth.service import AuthService, get_auth_service
from src.backend.auth.models import (
    User, Role, Permission, Session, APIToken,
    UserCreate, UserResponse, TokenResponse,
    PermissionDeniedError, AuthenticationError,
)
from src.backend.auth.dependencies import (
    require_auth, require_role, require_permission,
    get_current_user,
)

__all__ = [
    "AuthService", "get_auth_service",
    "User", "Role", "Permission", "Session", "APIToken",
    "UserCreate", "UserResponse", "TokenResponse",
    "PermissionDeniedError", "AuthenticationError",
    "require_auth", "require_role", "require_permission",
    "get_current_user",
]
