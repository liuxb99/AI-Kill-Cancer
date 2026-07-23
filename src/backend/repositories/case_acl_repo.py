"""Case ACL repository for domain_case_acl table."""

from sqlalchemy import and_, delete, select

from src.backend.domain.case_acl import CaseACLModel
from src.backend.repositories.base import BaseRepository


class CaseACLRepository(BaseRepository[CaseACLModel]):
    def __init__(self, db):
        super().__init__(CaseACLModel, db)

    async def get_user_case_role(self, case_id, user_id) -> CaseACLModel | None:
        stmt = select(CaseACLModel).where(
            and_(CaseACLModel.case_id == case_id, CaseACLModel.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_case_permissions(self, case_id) -> list[CaseACLModel]:
        stmt = select(CaseACLModel).where(CaseACLModel.case_id == case_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_user_cases(self, user_id) -> list[CaseACLModel]:
        stmt = select(CaseACLModel).where(CaseACLModel.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_case_permission(self, case_id, user_id) -> bool:
        stmt = delete(CaseACLModel).where(
            and_(CaseACLModel.case_id == case_id, CaseACLModel.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def grant_permission(self, case_id, user_id, role: str, granted_by=None) -> CaseACLModel:
        """Grant or update a permission."""
        existing = await self.get_user_case_role(case_id, user_id)
        if existing:
            existing.role = role
            if granted_by:
                existing.granted_by = granted_by
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        acl = CaseACLModel(
            case_id=case_id,
            user_id=user_id,
            role=role,
            granted_by=granted_by,
        )
        self.db.add(acl)
        await self.db.commit()
        await self.db.refresh(acl)
        return acl
