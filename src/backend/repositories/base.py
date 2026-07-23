"""
Base repository with common CRUD operations.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from src.backend.database.models import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic repository with common CRUD operations."""

    def __init__(self, model_class: type[ModelT], db: AsyncSession):
        self.model_class = model_class
        self.db = db

    async def create(self, **kwargs) -> ModelT:
        instance = self.model_class(**kwargs)
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def get(self, id: uuid.UUID) -> ModelT | None:
        stmt = select(self.model_class).where(self.model_class.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: Any | None = None,
        filters: list | None = None,
    ) -> list[ModelT]:
        stmt: Select = select(self.model_class)
        if filters:
            for f in filters:
                stmt = stmt.where(f)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        else:
            stmt = stmt.order_by(self.model_class.created_at.desc())
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(self, filters: list | None = None) -> int:
        stmt: Select = select(func.count(self.model_class.id))
        if filters:
            for f in filters:
                stmt = stmt.where(f)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def update(self, id: uuid.UUID, **kwargs) -> ModelT | None:
        instance = await self.get(id)
        if not instance:
            return None
        for field, value in kwargs.items():
            if hasattr(instance, field) and value is not None:
                setattr(instance, field, value)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def delete(self, id: uuid.UUID) -> bool:
        instance = await self.get(id)
        if not instance:
            return False
        await self.db.delete(instance)
        await self.db.commit()
        return True
