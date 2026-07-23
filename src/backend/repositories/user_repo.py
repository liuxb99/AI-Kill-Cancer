"""User repository for domain_users table."""

from sqlalchemy import select

from src.backend.domain.user import UserModel
from src.backend.repositories.base import BaseRepository


class UserRepository(BaseRepository[UserModel]):
    def __init__(self, db):
        super().__init__(UserModel, db)

    async def find_by_username(self, username: str) -> UserModel | None:
        stmt = select(UserModel).where(UserModel.username == username)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str) -> UserModel | None:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_username(self, username: str) -> bool:
        stmt = select(UserModel).where(UserModel.username == username)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
