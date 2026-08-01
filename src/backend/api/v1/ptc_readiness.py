"""PTC product readiness API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.session import get_db
from src.backend.services.ptc_readiness_service import PTCReadinessService

router = APIRouter(prefix="/ptc-readiness", tags=["ptc-readiness"])


@router.get("")
async def readiness(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Evaluate whether persisted PTC data is usable for demo or research."""
    return await PTCReadinessService(db).evaluate()


__all__ = ["router"]
