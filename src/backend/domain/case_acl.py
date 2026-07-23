"""
Case-level Access Control List domain model.

Defines which users have what level of access to which cancer cases.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint

from src.backend.database.models import Base as DBBase
from src.backend.database.models import CompatUUID


class CaseRole(str, enum.Enum):
    """Role a user can have on a specific case."""
    OWNER = "owner"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    VIEWER = "viewer"
    ADMIN = "admin"


# Permission hierarchy: viewer < reviewer < editor < owner
CASE_ROLE_HIERARCHY: dict[CaseRole, int] = {
    CaseRole.VIEWER: 1,
    CaseRole.REVIEWER: 2,
    CaseRole.EDITOR: 3,
    CaseRole.OWNER: 4,
    CaseRole.ADMIN: 5,
}

# Minimum role required for each action
CASE_REQUIRED_ROLES: dict[str, CaseRole] = {
    "view": CaseRole.VIEWER,
    "edit": CaseRole.EDITOR,
    "delete": CaseRole.OWNER,
    "share": CaseRole.OWNER,
    "add_evidence": CaseRole.REVIEWER,
    "run_analysis": CaseRole.EDITOR,
    "create_report": CaseRole.REVIEWER,
    "download_report": CaseRole.VIEWER,
    "view_audit": CaseRole.REVIEWER,
}


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class CaseACLModel(DBBase):
    """Links a user to a case with a specific role."""
    __tablename__ = "domain_case_acl"
    __table_args__ = (
        UniqueConstraint("case_id", "user_id", name="uq_case_user"),
    )

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    case_id = Column(CompatUUID, ForeignKey("domain_cancer_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(CompatUUID, ForeignKey("domain_users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(16), nullable=False, default="viewer")
    granted_by = Column(CompatUUID, ForeignKey("domain_users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<CaseACLModel(case={self.case_id}, user={self.user_id}, role={self.role})>"


class CaseACLCreate(BaseModel):
    case_id: str
    user_id: str
    role: str = "viewer"
    granted_by: str | None = None


class CaseACLResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    user_id: str
    role: str
    created_at: datetime


class CasePermissionCheck(BaseModel):
    user_id: str
    case_id: str
    required_role: str
    granted: bool
    current_role: str | None = None
