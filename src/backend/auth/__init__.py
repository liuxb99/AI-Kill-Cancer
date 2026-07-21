"""
Authentication & Authorization system for production deployment.
"""
from src.backend.auth.service import AuthService, get_auth_service
from src.backend.auth.models import (
    Role, Permission, ROLE_PERMISSIONS,
    AuthenticationError, PermissionDeniedError,
    UserNotFoundError, DuplicateUserError,
)
from src.backend.auth.dependencies import (
    require_auth, require_permission,
    get_current_user, require_case_access, verify_case_access,
)

__all__ = [
    "AuthService", "get_auth_service",
    "Role", "Permission", "ROLE_PERMISSIONS",
    "AuthenticationError", "PermissionDeniedError",
    "UserNotFoundError", "DuplicateUserError",
    "require_auth", "require_permission",
    "get_current_user",
]
