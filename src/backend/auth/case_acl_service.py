"""
Case-level Access Control List service.

Provides authorization logic for case-scoped resources, resolving case_id
from various resource types (specimens, variants, reports, etc.).
"""
from __future__ import annotations

import uuid
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.auth.models import PermissionDeniedError
from src.backend.domain.case_acl import CaseACLModel, CaseRole, CASE_ROLE_HIERARCHY
from src.backend.domain.user import UserModel
from src.backend.repositories.case_acl_repo import CaseACLRepository
from src.backend.repositories.specimen_repo import SpecimenRepository
from src.backend.repositories.variant_repo import VariantRepository
from src.backend.repositories.report_repo import ReportRepository
from src.backend.repositories.evidence_repo import EvidenceRepository
from src.backend.repositories.analysis_run_repo import AnalysisRunRepository
from src.backend.repositories.sequencing_test_repo import SequencingTestRepository

logger = logging.getLogger(__name__)


class CaseACLService:
    """Handles case-level authorization checks."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.acl_repo = CaseACLRepository(db)

    async def get_user_role(self, case_id: uuid.UUID, user_id: uuid.UUID) -> Optional[CaseRole]:
        """Get the user's role on a specific case."""
        acl = await self.acl_repo.get_user_case_role(case_id, user_id)
        if acl is None:
            return None
        return CaseRole(acl.role)

    async def check_access(
        self,
        case_id: uuid.UUID,
        user: UserModel,
        required_role: CaseRole,
    ) -> bool:
        """Check if a user has at least the required role on a case.

        Admin users always have access to all cases.
        """
        # Admin users have global case access (RBAC-based)
        if user.role.value == "admin":
            return True

        role = await self.get_user_role(case_id, user.id)
        if role is None:
            return False

        return CASE_ROLE_HIERARCHY.get(role, 0) >= CASE_ROLE_HIERARCHY.get(required_role, 0)

    async def require_access(
        self,
        case_id: uuid.UUID,
        user: UserModel,
        required_role: CaseRole,
    ) -> None:
        """Raise PermissionDeniedError if user lacks access."""
        if not await self.check_access(case_id, user, required_role):
            raise PermissionDeniedError(
                f"User {user.username} lacks {required_role.value} access to case {case_id}"
            )

    async def resolve_case_id_from_resource(
        self,
        resource_type: str,
        resource_id: uuid.UUID,
    ) -> Optional[uuid.UUID]:
        """Resolve a case_id from a related resource (specimen, variant, report, etc.)."""
        if resource_type == "specimen":
            repo = SpecimenRepository(self.db)
            obj = await repo.get(resource_id)
            return obj.case_id if obj else None
        elif resource_type == "variant":
            repo = VariantRepository(self.db)
            obj = await repo.get(resource_id)
            return obj.case_id if obj else None
        elif resource_type == "report":
            repo = ReportRepository(self.db)
            obj = await repo.get(resource_id)
            return obj.case_id if obj else None
        elif resource_type == "evidence":
            repo = EvidenceRepository(self.db)
            obj = await repo.get(resource_id)
            return obj.case_id if obj else None
        elif resource_type == "analysis_run":
            repo = AnalysisRunRepository(self.db)
            obj = await repo.get(resource_id)
            return obj.case_id if obj else None
        elif resource_type == "sequencing_test":
            repo = SequencingTestRepository(self.db)
            obj = await repo.get(resource_id)
            return obj.case_id if obj else None
        return None

    async def grant_owner(self, case_id: uuid.UUID, user_id: uuid.UUID, granted_by: Optional[uuid.UUID] = None) -> CaseACLModel:
        """Grant owner role to a user on a case. Used when creating a case."""
        return await self.acl_repo.grant_permission(
            case_id=case_id,
            user_id=user_id,
            role=CaseRole.OWNER.value,
            granted_by=granted_by,
        )

    async def grant_access(
        self,
        case_id: uuid.UUID,
        grantor: UserModel,
        target_user_id: uuid.UUID,
        role: CaseRole,
    ) -> CaseACLModel:
        """Grant access to a user on a case. Only owner or admin may do this."""
        # Verify grantor has owner access
        await self.require_access(case_id, grantor, CaseRole.OWNER)
        return await self.acl_repo.grant_permission(
            case_id=case_id,
            user_id=target_user_id,
            role=role.value,
            granted_by=grantor.id,
        )

    async def revoke_access(
        self,
        case_id: uuid.UUID,
        grantor: UserModel,
        target_user_id: uuid.UUID,
    ) -> bool:
        """Revoke a user's access to a case. Only owner or admin may do this.

        Prevents removing the last owner.
        """
        await self.require_access(case_id, grantor, CaseRole.OWNER)

        # Prevent removing the last owner
        if target_user_id == grantor.id:
            # Check if there are other owners
            acl_entries = await self.acl_repo.list_case_permissions(case_id)
            owner_count = sum(
                1 for a in acl_entries if a.role == CaseRole.OWNER.value
            )
            if owner_count <= 1:
                raise PermissionDeniedError(
                    "Cannot remove the last owner of the case"
                )

        return await self.acl_repo.delete_case_permission(case_id, target_user_id)

    async def list_case_acls(self, case_id: uuid.UUID) -> list[CaseACLModel]:
        """List all ACL entries for a case."""
        return await self.acl_repo.list_case_permissions(case_id)

    async def list_user_cases(self, user_id: uuid.UUID) -> list[CaseACLModel]:
        """List all cases a user has access to."""
        return await self.acl_repo.list_user_cases(user_id)
