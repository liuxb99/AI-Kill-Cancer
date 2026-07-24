"""
Recommendation & Trace repositories — persist recommendation pipeline results.

Provides:
- ``RecommendationRepository`` — CRUD for ``RecommendationModel``
- ``TraceRepository`` — CRUD for ``RecommendationTraceModel`` and
  ``RecommendationTraceStepModel``

Following the project's repository pattern: inherit ``BaseRepository``,
inject session, do NOT manage transactions (no commit/rollback).  The
calling service is responsible for the transaction boundary.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.domain.recommendation import (
    RecommendationModel,
    RecommendationTraceModel,
    RecommendationTraceStepModel,
)
from src.backend.repositories.base import BaseRepository


# ═══════════════════════════════════════════════════════════════════════════════
# RecommendationRepository
# ═══════════════════════════════════════════════════════════════════════════════


class RecommendationRepository(BaseRepository[RecommendationModel]):
    """Repository for ``RecommendationModel`` persistence.

    Extends ``BaseRepository`` with domain-specific queries.
    Does **not** call commit — the service layer manages the transaction
    boundary.
    """

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(RecommendationModel, db)

    async def create(self, recommendation: RecommendationModel) -> RecommendationModel:
        """Persist a new recommendation record.

        Adds the instance to the session without committing.  The caller
        (service layer) is responsible for calling ``db.commit()`` and
        ``db.refresh()``.

        Parameters
        ----------
        recommendation : RecommendationModel
            The model instance to persist.

        Returns
        -------
        RecommendationModel
            The same instance (now tracked by the session).
        """
        self.db.add(recommendation)
        return recommendation

    async def get_by_id(
        self,
        recommendation_id: str,
    ) -> Optional[RecommendationModel]:
        """Retrieve a recommendation by its business identifier.

        Parameters
        ----------
        recommendation_id : str
            The hex-string UUID returned by the POST endpoint
            (``RecommendationModel.recommendation_id``).

        Returns
        -------
        RecommendationModel | None
        """
        stmt = select(RecommendationModel).where(
            RecommendationModel.recommendation_id == recommendation_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_trace_id(self, trace_id: str) -> Optional[RecommendationModel]:
        """Retrieve a recommendation by its associated trace ID.

        Parameters
        ----------
        trace_id : str
            The calculation trace identifier.

        Returns
        -------
        RecommendationModel | None
        """
        stmt = select(RecommendationModel).where(
            RecommendationModel.trace_id == trace_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_patient_id(
        self,
        patient_id: str,
        limit: int = 20,
    ) -> list[RecommendationModel]:
        """List recommendations for a patient, newest first.

        Parameters
        ----------
        patient_id : str
            The patient's UUID string.
        limit : int
            Maximum number of records to return (default 20).

        Returns
        -------
        list[RecommendationModel]
        """
        stmt = (
            select(RecommendationModel)
            .where(RecommendationModel.patient_id == patient_id)
            .order_by(RecommendationModel.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════════════════════════
# TraceRepository
# ═══════════════════════════════════════════════════════════════════════════════


class TraceRepository(BaseRepository[RecommendationTraceModel]):
    """Repository for ``RecommendationTraceModel`` and
    ``RecommendationTraceStepModel`` persistence.

    Trace and step models share a single repository to keep related logic
    co-located.  Does **not** call commit — the service layer manages the
    transaction boundary.
    """

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(RecommendationTraceModel, db)

    # ── Trace CRUD ─────────────────────────────────────────────────────────

    async def create_trace(
        self,
        trace: RecommendationTraceModel,
    ) -> RecommendationTraceModel:
        """Persist a new calculation trace record.

        Adds the instance to the session without committing.  The caller
        must commit and refresh.

        Parameters
        ----------
        trace : RecommendationTraceModel
            The trace instance (not yet persisted).

        Returns
        -------
        RecommendationTraceModel
        """
        self.db.add(trace)
        return trace

    async def get_trace_by_recommendation_id(
        self,
        recommendation_id: str,
    ) -> Optional[RecommendationTraceModel]:
        """Retrieve a trace by its associated recommendation ID.

        Parameters
        ----------
        recommendation_id : str
            The recommendation's UUID string.

        Returns
        -------
        RecommendationTraceModel | None
        """
        from sqlalchemy import cast, String

        stmt = select(RecommendationTraceModel).where(
            cast(RecommendationTraceModel.recommendation_id, String)
            == recommendation_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_trace_by_trace_id(
        self,
        trace_id: str,
    ) -> Optional[RecommendationTraceModel]:
        """Retrieve a trace by its unique trace identifier.

        Parameters
        ----------
        trace_id : str
            The calculation trace identifier.

        Returns
        -------
        RecommendationTraceModel | None
        """
        stmt = select(RecommendationTraceModel).where(
            RecommendationTraceModel.trace_id == trace_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Step CRUD ──────────────────────────────────────────────────────────

    async def create_step(
        self,
        step: RecommendationTraceStepModel,
    ) -> RecommendationTraceStepModel:
        """Persist a new trace step record.

        Adds the instance to the session without committing.

        Parameters
        ----------
        step : RecommendationTraceStepModel
            The step instance (not yet persisted).

        Returns
        -------
        RecommendationTraceStepModel
        """
        self.db.add(step)
        return step

    async def get_steps_by_trace_id(
        self,
        trace_id: str,
    ) -> list[RecommendationTraceStepModel]:
        """Retrieve all steps for a given trace, ordered by step order.

        Parameters
        ----------
        trace_id : str
            The trace's UUID string (primary key of
            ``RecommendationTraceModel``).

        Returns
        -------
        list[RecommendationTraceStepModel]
        """
        from sqlalchemy import cast, String

        stmt = (
            select(RecommendationTraceStepModel)
            .where(
                cast(RecommendationTraceStepModel.trace_id, String) == trace_id,
            )
            .order_by(RecommendationTraceStepModel.step_order.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
