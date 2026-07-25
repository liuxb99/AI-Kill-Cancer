"""
Clinical Decision & Trace repositories — persist clinical decision outputs.

Provides:
- ``ClinicalDecisionRepository`` — CRUD for ``ClinicalDecisionModel``
- ``ClinicalDecisionTraceRepository`` — CRUD for ``ClinicalDecisionTraceModel``

Following the project's repository pattern: inherit ``BaseRepository``,
inject session, do NOT manage transactions (no commit/rollback).  The
calling service is responsible for the transaction boundary.
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.domain.clinical_decision import (
    ClinicalDecisionModel,
    ClinicalDecisionTraceModel,
)
from src.backend.repositories.base import BaseRepository

# ═══════════════════════════════════════════════════════════════════════════════
# ClinicalDecisionRepository
# ═══════════════════════════════════════════════════════════════════════════════


class ClinicalDecisionRepository(BaseRepository[ClinicalDecisionModel]):
    """Repository for ``ClinicalDecisionModel`` persistence.

    Extends ``BaseRepository`` with domain-specific queries.
    Does **not** call commit — the service layer manages the transaction
    boundary.
    """

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(ClinicalDecisionModel, db)

    async def create(
        self,
        model: ClinicalDecisionModel,
    ) -> ClinicalDecisionModel:
        """Persist a new clinical decision record.

        Adds the instance to the session without committing.  The caller
        (service layer) is responsible for calling ``db.commit()`` and
        ``db.refresh()``.

        Parameters
        ----------
        model : ClinicalDecisionModel
            The model instance to persist.

        Returns
        -------
        ClinicalDecisionModel
            The same instance (now tracked by the session).
        """
        self.db.add(model)
        return model

    async def get_by_id(
        self,
        decision_id: str,
    ) -> Optional[ClinicalDecisionModel]:
        """Retrieve a clinical decision by its business identifier.

        Parameters
        ----------
        decision_id : str
            The hex-string UUID returned by the POST endpoint
            (``ClinicalDecisionModel.decision_id``).

        Returns
        -------
        ClinicalDecisionModel | None
        """
        stmt = select(ClinicalDecisionModel).where(
            ClinicalDecisionModel.decision_id == decision_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_uuid(
        self,
        uuid: uuid.UUID,
    ) -> Optional[ClinicalDecisionModel]:
        """Retrieve a clinical decision by its primary key (UUID id).

        Parameters
        ----------
        uuid : uuid.UUID
            The primary key of the clinical decision record.

        Returns
        -------
        ClinicalDecisionModel | None
        """
        stmt = select(ClinicalDecisionModel).where(
            ClinicalDecisionModel.id == uuid,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_patient_id(
        self,
        patient_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ClinicalDecisionModel]:
        """List clinical decisions for a patient, newest first.

        Parameters
        ----------
        patient_id : uuid.UUID
            The patient's UUID.
        skip : int
            Number of records to skip (for pagination).
        limit : int
            Maximum number of records to return (default 50).

        Returns
        -------
        list[ClinicalDecisionModel]
        """
        stmt = (
            select(ClinicalDecisionModel)
            .where(ClinicalDecisionModel.patient_id == patient_id)
            .order_by(ClinicalDecisionModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_recommendation_id(
        self,
        recommendation_id: uuid.UUID,
    ) -> list[ClinicalDecisionModel]:
        """List clinical decisions associated with a recommendation,
        newest first.

        Parameters
        ----------
        recommendation_id : uuid.UUID
            The recommendation's UUID.

        Returns
        -------
        list[ClinicalDecisionModel]
        """
        stmt = (
            select(ClinicalDecisionModel)
            .where(ClinicalDecisionModel.recommendation_id == recommendation_id)
            .order_by(ClinicalDecisionModel.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════════════════════════
# ClinicalDecisionTraceRepository
# ═══════════════════════════════════════════════════════════════════════════════


class ClinicalDecisionTraceRepository(BaseRepository[ClinicalDecisionTraceModel]):
    """Repository for ``ClinicalDecisionTraceModel`` persistence.

    Extends ``BaseRepository`` with domain-specific queries.
    Does **not** call commit — the service layer manages the transaction
    boundary.
    """

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(ClinicalDecisionTraceModel, db)

    async def create(
        self,
        model: ClinicalDecisionTraceModel,
    ) -> ClinicalDecisionTraceModel:
        """Persist a new clinical decision trace record.

        Adds the instance to the session without committing.  The caller
        (service layer) is responsible for calling ``db.commit()`` and
        ``db.refresh()``.

        Parameters
        ----------
        model : ClinicalDecisionTraceModel
            The model instance to persist.

        Returns
        -------
        ClinicalDecisionTraceModel
            The same instance (now tracked by the session).
        """
        self.db.add(model)
        return model

    async def get_by_decision_id(
        self,
        clinical_decision_id: uuid.UUID,
    ) -> list[ClinicalDecisionTraceModel]:
        """Retrieve all trace steps for a given clinical decision,
        ordered by step order.

        Parameters
        ----------
        clinical_decision_id : uuid.UUID
            The clinical decision's UUID (primary key of
            ``ClinicalDecisionModel``).

        Returns
        -------
        list[ClinicalDecisionTraceModel]
        """
        stmt = (
            select(ClinicalDecisionTraceModel)
            .where(
                ClinicalDecisionTraceModel.clinical_decision_id
                == clinical_decision_id,
            )
            .order_by(ClinicalDecisionTraceModel.step_order.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_recommendation_id(
        self,
        recommendation_id: uuid.UUID,
    ) -> list[ClinicalDecisionTraceModel]:
        """Retrieve trace steps associated with a recommendation,
        ordered by step order.

        Parameters
        ----------
        recommendation_id : uuid.UUID
            The recommendation's UUID.

        Returns
        -------
        list[ClinicalDecisionTraceModel]
        """
        stmt = (
            select(ClinicalDecisionTraceModel)
            .where(
                ClinicalDecisionTraceModel.recommendation_id
                == recommendation_id,
            )
            .order_by(ClinicalDecisionTraceModel.step_order.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_trace_id(
        self,
        trace_id: str,
    ) -> Optional[ClinicalDecisionTraceModel]:
        """Retrieve a trace step by its unique trace identifier.

        Parameters
        ----------
        trace_id : str
            The calculation trace identifier.

        Returns
        -------
        ClinicalDecisionTraceModel | None
        """
        stmt = select(ClinicalDecisionTraceModel).where(
            ClinicalDecisionTraceModel.trace_id == trace_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
