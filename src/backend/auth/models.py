"""
Auth models — Role/Permission (re-exported), ROLE_PERMISSIONS mapping, and error classes.

Role and Permission enums are defined in src/backend/domain/enums.py to avoid
circular imports between auth and domain packages.
"""
from __future__ import annotations

from src.backend.domain.enums import Role, Permission

# Re-export for convenience
__all__ = [
    "Role",
    "Permission",
    "ROLE_PERMISSIONS",
    "AuthenticationError",
    "PermissionDeniedError",
    "UserNotFoundError",
    "DuplicateUserError",
]


# Role -> Permission mapping
ROLE_PERMISSIONS: dict[Role, list[Permission]] = {
    Role.ADMIN: [
        Permission.READ_PATIENT, Permission.WRITE_PATIENT, Permission.DELETE_PATIENT,
        Permission.READ_EVIDENCE, Permission.REFRESH_EVIDENCE,
        Permission.READ_RANKING, Permission.RUN_RANKING,
        Permission.READ_REASONING, Permission.RUN_REASONING,
        Permission.READ_REPORT, Permission.CREATE_REPORT, Permission.DOWNLOAD_REPORT,
        Permission.MANAGE_USERS, Permission.MANAGE_SETTINGS,
        Permission.VIEW_AUDIT,
        Permission.READ, Permission.UPDATE, Permission.DELETE, Permission.EXPORT, Permission.SHARE,
        Permission.CONSENT_GRANT, Permission.CONSENT_REVOKE,
        Permission.ANALYSIS_START, Permission.ANALYSIS_COMPLETE,
    ],
    Role.CLINICIAN: [
        Permission.READ_PATIENT, Permission.WRITE_PATIENT,
        Permission.READ_EVIDENCE, Permission.REFRESH_EVIDENCE,
        Permission.READ_RANKING, Permission.RUN_RANKING,
        Permission.READ_REASONING, Permission.RUN_REASONING,
        Permission.READ_REPORT, Permission.CREATE_REPORT, Permission.DOWNLOAD_REPORT,
    ],
    Role.RESEARCHER: [
        Permission.READ_PATIENT,
        Permission.READ_EVIDENCE, Permission.REFRESH_EVIDENCE,
        Permission.READ_RANKING, Permission.RUN_RANKING,
        Permission.READ_REASONING, Permission.RUN_REASONING,
        Permission.READ_REPORT, Permission.CREATE_REPORT,
    ],
    Role.REVIEWER: [
        Permission.READ_PATIENT,
        Permission.READ_EVIDENCE,
        Permission.READ_RANKING,
        Permission.READ_REASONING,
        Permission.READ_REPORT, Permission.DOWNLOAD_REPORT,
    ],
    Role.VIEWER: [
        Permission.READ_PATIENT,
        Permission.READ_EVIDENCE,
        Permission.READ_RANKING,
        Permission.READ_REPORT,
    ],
    Role.SERVICE: [
        Permission.READ_EVIDENCE, Permission.REFRESH_EVIDENCE,
        Permission.READ_RANKING, Permission.RUN_RANKING,
        Permission.READ_REASONING, Permission.RUN_REASONING,
        Permission.CREATE_REPORT,
    ],
}


class AuthenticationError(Exception):
    """Raised when token validation fails."""
    pass


class PermissionDeniedError(Exception):
    """Raised when a user lacks the required permission."""
    pass


class UserNotFoundError(Exception):
    """Raised when a user is not found."""
    pass


class DuplicateUserError(Exception):
    """Raised when a username or email already exists."""
    pass
