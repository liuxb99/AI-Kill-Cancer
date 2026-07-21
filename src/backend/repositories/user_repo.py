"""User repository for domain_users table."""
from typing import Optional
from sqlalchemy import select
from src.backend.repositories.base import BaseRepository
from src.backend.domain.user import UserModel


class UserRepository(BaseRepository[UserModel]):
    def __init__(self, db):
        super().__init__(UserModel, db)

    async def find_by_username(self, username: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.username == username)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_username(self, username: str) -> bool:
        stmt = select(UserModel).where(UserModel.username == username)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
