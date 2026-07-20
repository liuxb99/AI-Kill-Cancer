"""
Auth models — User, Role, Permission, Session, APIToken.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Role(str, enum.Enum):
    ADMIN = "admin"
    CLINICIAN = "clinician"
    RESEARCHER = "researcher"
    REVIEWER = "reviewer"
    VIEWER = "viewer"
    SERVICE = "service"


class Permission(str, enum.Enum):
    # Patient/Case permissions
    READ_PATIENT = "read:patient"
    WRITE_PATIENT = "write:patient"
    DELETE_PATIENT = "delete:patient"
    # Evidence permissions
    READ_EVIDENCE = "read:evidence"
    REFRESH_EVIDENCE = "refresh:evidence"
    # Ranking permissions
    READ_RANKING = "read:ranking"
    RUN_RANKING = "run:ranking"
    # Reasoning permissions
    READ_REASONING = "read:reasoning"
    RUN_REASONING = "run:reasoning"
    # Report permissions
    READ_REPORT = "read:report"
    CREATE_REPORT = "create:report"
    DOWNLOAD_REPORT = "download:report"
    # Admin permissions
    MANAGE_USERS = "manage:users"
    MANAGE_SETTINGS = "manage:settings"
    VIEW_AUDIT = "view:audit"


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


class User(BaseModel):
    id: str = ""
    username: str = ""
    email: str = ""
    role: Role = Role.VIEWER
    is_active: bool = True
    created_at: str = ""


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = ""
    password: str = Field(..., min_length=8)
    role: Role = Role.VIEWER


class UserResponse(BaseModel):
    id: str = ""
    username: str = ""
    email: str = ""
    role: str = ""
    is_active: bool = True


class TokenResponse(BaseModel):
    access_token: str = ""
    token_type: str = "bearer"
    user: UserResponse


class Session(BaseModel):
    id: str = ""
    user_id: str = ""
    token_hash: str = ""
    expires_at: str = ""
    created_at: str = ""


class APIToken(BaseModel):
    id: str = ""
    user_id: str = ""
    name: str = ""
    token_hash: str = ""
    permissions: list[str] = []
    expires_at: str = ""
    created_at: str = ""


class AuthenticationError(Exception):
    pass


class PermissionDeniedError(Exception):
    pass
