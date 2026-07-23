"""
User domain model for production authentication.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy import Enum as SAEnum

from src.backend.database.models import Base as DBBase
from src.backend.database.models import CompatUUID
from src.backend.domain.enums import Role


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class UserModel(DBBase):
    """Persistent user with bcrypt-hashed password."""
    __tablename__ = "domain_users"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(256), nullable=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(SAEnum(Role), nullable=False, default=Role.VIEWER)
    is_active = Column(Boolean, default=True, nullable=False)
    display_name = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<UserModel(id={self.id}, username={self.username!r}, role={self.role})>"


class TokenBlacklistModel(DBBase):
    """Blacklisted (revoked) tokens."""
    __tablename__ = "domain_token_blacklist"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    jti = Column(String(256), unique=True, nullable=False, index=True)
    token_type = Column(String(16), nullable=False)  # access, refresh
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    username: str = Field(..., min_length=3, max_length=64)
    email: str | None = None
    password: str = Field(..., min_length=8)
    role: Role = Role.VIEWER
    display_name: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    username: str
    email: str | None = None
    role: str
    is_active: bool
    display_name: str | None = None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None
