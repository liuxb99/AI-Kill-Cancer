"""
Authentication & Authorization system for production deployment.
"""
from src.backend.auth.dependencies import (
    get_current_user,
    require_auth,
    require_case_access,
    require_permission,
    verify_case_access,
)
from src.backend.auth.models import (
    ROLE_PERMISSIONS,
    AuthenticationError,
    DuplicateUserError,
    Permission,
    PermissionDeniedError,
    Role,
    UserNotFoundError,
)
from src.backend.auth.service import AuthService, get_auth_service

__all__ = [
    "AuthService", "get_auth_service",
    "Role", "Permission", "ROLE_PERMISSIONS",
    "AuthenticationError", "PermissionDeniedError",
    "UserNotFoundError", "DuplicateUserError",
    "require_auth", "require_permission",
    "require_case_access", "verify_case_access",
    "get_current_user",
]
