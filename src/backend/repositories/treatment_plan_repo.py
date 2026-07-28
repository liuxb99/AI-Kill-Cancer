"""
Treatment Plan repositories — persist treatment plans, phases, items,
monitoring schedules, safety rules, and reasoning traces.

Provides:
- ``TreatmentPlanRepository`` — CRUD for ``TreatmentPlanModel``
- ``TreatmentPhaseRepository`` — CRUD for ``TreatmentPhaseModel``
- ``TreatmentItemRepository`` — CRUD for ``TreatmentItemModel``
- ``TreatmentMonitoringRepository`` — CRUD for ``TreatmentMonitoringModel``
- ``TreatmentSafetyRuleRepository`` — CRUD for ``TreatmentSafetyRuleModel``
- ``TreatmentPlanTraceRepository`` — CRUD for ``TreatmentPlanTraceModel``

Following the project's repository pattern: inherit ``BaseRepository``,
inject session, do NOT manage transactions (no commit/rollback).  The
calling service is responsible for the transaction boundary.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.domain.treatment_plan import (
    TreatmentItemModel,
    TreatmentMonitoringModel,
    TreatmentPhaseModel,
    TreatmentPlanModel,
    TreatmentPlanTraceModel,
    TreatmentSafetyRuleModel,
)
from src.backend.repositories.base import BaseRepository

# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentPlanRepository
# ═══════════════════════════════════════════════════════════════════════════════


class TreatmentPlanRepository(BaseRepository[TreatmentPlanModel]):
    """Repository for ``TreatmentPlanModel`` persistence.

    Extends ``BaseRepository`` with domain-specific queries.
    Does **not** call commit — the service layer manages the transaction
    boundary.
    """

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(TreatmentPlanModel, db)

    async def create(
        self,
        model: TreatmentPlanModel,
    ) -> TreatmentPlanModel:
        """Persist a new treatment plan.

        Adds the instance to the session and flushes so the PK is populated
        without committing.  The caller (service layer) is responsible for
        calling ``db.commit()``.

        Parameters
        ----------
        model : TreatmentPlanModel
            The model instance to persist.

        Returns
        -------
        TreatmentPlanModel
            The same instance (now tracked by the session, PK populated).
        """
        self.db.add(model)
        await self.db.flush()
        return model

    async def get_by_id(
        self,
        id: str,
    ) -> Optional[TreatmentPlanModel]:
        """Retrieve a treatment plan by its UUID primary key (as hex).

        Parameters
        ----------
        id : str
            The hex-string representation of the plan's UUID primary key.

        Returns
        -------
        TreatmentPlanModel | None
        """
        stmt = select(TreatmentPlanModel).where(
            TreatmentPlanModel.id == uuid.UUID(id),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_plan_id(
        self,
        plan_id: str,
    ) -> Optional[TreatmentPlanModel]:
        """Retrieve a treatment plan by its business identifier.

        Parameters
        ----------
        plan_id : str
            The unique business identifier (``TreatmentPlanModel.plan_id``).

        Returns
        -------
        TreatmentPlanModel | None
        """
        stmt = select(TreatmentPlanModel).where(
            TreatmentPlanModel.plan_id == plan_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_current_by_patient_id(
        self,
        patient_id: uuid.UUID,
    ) -> Optional[TreatmentPlanModel]:
        """Retrieve the current (active) treatment plan for a patient.

        Parameters
        ----------
        patient_id : uuid.UUID
            The patient's UUID.

        Returns
        -------
        TreatmentPlanModel | None
        """
        stmt = (
            select(TreatmentPlanModel)
            .where(
                TreatmentPlanModel.patient_id == patient_id,
                TreatmentPlanModel.is_current == True,  # noqa: E712
            )
            .order_by(TreatmentPlanModel.version.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_patient_id(
        self,
        patient_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> List[TreatmentPlanModel]:
        """List treatment plans for a patient, newest first.

        Parameters
        ----------
        patient_id : uuid.UUID
            The patient's UUID.
        skip : int
            Number of records to skip (for pagination).
        limit : int
            Maximum number of records to return (default 20).

        Returns
        -------
        list[TreatmentPlanModel]
        """
        stmt = (
            select(TreatmentPlanModel)
            .where(TreatmentPlanModel.patient_id == patient_id)
            .order_by(TreatmentPlanModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_versions(
        self,
        plan_id: str,
    ) -> List[TreatmentPlanModel]:
        """List all versions of a treatment plan, newest version first.

        Parameters
        ----------
        plan_id : str
            The business identifier shared across versions.

        Returns
        -------
        list[TreatmentPlanModel]
        """
        stmt = (
            select(TreatmentPlanModel)
            .where(TreatmentPlanModel.plan_id == plan_id)
            .order_by(TreatmentPlanModel.version.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_patient_id(
        self,
        patient_id: uuid.UUID,
    ) -> int:
        """Count treatment plans for a patient.

        Parameters
        ----------
        patient_id : uuid.UUID
            The patient's UUID.

        Returns
        -------
        int
            Number of treatment plans for the patient.
        """
        stmt = (
            select(func.count())
            .select_from(TreatmentPlanModel)
            .where(TreatmentPlanModel.patient_id == patient_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def mark_superseded(
        self,
        plan_id: str,
        superseded_by_plan_id: str,
        revision_reason: str = "",
    ) -> None:
        """Mark the current version of a plan as superseded.

        Sets ``is_current`` to False, and records which plan supersedes it
        along with the reason for the revision.

        Parameters
        ----------
        plan_id : str
            The business identifier of the plan to supersede.
        superseded_by_plan_id : str
            The business identifier of the plan that supersedes it.
        revision_reason : str
            Optional explanation of why the revision was made.
        """
        stmt = (
            update(TreatmentPlanModel)
            .where(
                TreatmentPlanModel.plan_id == plan_id,
                TreatmentPlanModel.is_current == True,  # noqa: E712
            )
            .values(
                is_current=False,
                supersedes_plan_id=superseded_by_plan_id,
                revision_reason=revision_reason or None,
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentPhaseRepository
# ═══════════════════════════════════════════════════════════════════════════════


class TreatmentPhaseRepository(BaseRepository[TreatmentPhaseModel]):
    """Repository for ``TreatmentPhaseModel`` persistence.

    Does **not** call commit — the service layer manages the transaction
    boundary.
    """

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(TreatmentPhaseModel, db)

    async def create(
        self,
        model: TreatmentPhaseModel,
    ) -> TreatmentPhaseModel:
        """Persist a new treatment phase."""
        self.db.add(model)
        await self.db.flush()
        return model

    async def create_many(
        self,
        models: List[TreatmentPhaseModel],
    ) -> List[TreatmentPhaseModel]:
        """Persist multiple treatment phases in one batch."""
        self.db.add_all(models)
        await self.db.flush()
        return models

    async def list_by_plan_id(
        self,
        plan_id: uuid.UUID,
    ) -> List[TreatmentPhaseModel]:
        """List all phases for a given plan, ordered by phase order."""
        stmt = (
            select(TreatmentPhaseModel)
            .where(TreatmentPhaseModel.plan_id == plan_id)
            .order_by(TreatmentPhaseModel.phase_order.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_plan_id(
        self,
        plan_id: uuid.UUID,
    ) -> int:
        """Delete all phases for a given plan.

        Returns the number of rows deleted.
        """
        from sqlalchemy import delete as sa_delete

        stmt = (
            sa_delete(TreatmentPhaseModel)
            .where(TreatmentPhaseModel.plan_id == plan_id)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount  # type: ignore[union-attr]


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentItemRepository
# ═══════════════════════════════════════════════════════════════════════════════


class TreatmentItemRepository(BaseRepository[TreatmentItemModel]):
    """Repository for ``TreatmentItemModel`` persistence.

    Does **not** call commit — the service layer manages the transaction
    boundary.
    """

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(TreatmentItemModel, db)

    async def create(
        self,
        model: TreatmentItemModel,
    ) -> TreatmentItemModel:
        """Persist a new treatment item."""
        self.db.add(model)
        await self.db.flush()
        return model

    async def create_many(
        self,
        models: List[TreatmentItemModel],
    ) -> List[TreatmentItemModel]:
        """Persist multiple treatment items in one batch."""
        self.db.add_all(models)
        await self.db.flush()
        return models

    async def list_by_plan_id(
        self,
        plan_id: uuid.UUID,
    ) -> List[TreatmentItemModel]:
        """List all items for a given plan, ordered by item order."""
        stmt = (
            select(TreatmentItemModel)
            .where(TreatmentItemModel.plan_id == plan_id)
            .order_by(TreatmentItemModel.item_order.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_plan_id(
        self,
        plan_id: uuid.UUID,
    ) -> int:
        """Delete all items for a given plan.

        Returns the number of rows deleted.
        """
        from sqlalchemy import delete as sa_delete

        stmt = (
            sa_delete(TreatmentItemModel)
            .where(TreatmentItemModel.plan_id == plan_id)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount  # type: ignore[union-attr]


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentMonitoringRepository
# ═══════════════════════════════════════════════════════════════════════════════


class TreatmentMonitoringRepository(BaseRepository[TreatmentMonitoringModel]):
    """Repository for ``TreatmentMonitoringModel`` persistence.

    Does **not** call commit — the service layer manages the transaction
    boundary.
    """

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(TreatmentMonitoringModel, db)

    async def create(
        self,
        model: TreatmentMonitoringModel,
    ) -> TreatmentMonitoringModel:
        """Persist a new monitoring schedule."""
        self.db.add(model)
        await self.db.flush()
        return model

    async def create_many(
        self,
        models: List[TreatmentMonitoringModel],
    ) -> List[TreatmentMonitoringModel]:
        """Persist multiple monitoring schedules in one batch."""
        self.db.add_all(models)
        await self.db.flush()
        return models

    async def list_by_plan_id(
        self,
        plan_id: uuid.UUID,
    ) -> List[TreatmentMonitoringModel]:
        """List all monitoring schedules for a given plan."""
        stmt = (
            select(TreatmentMonitoringModel)
            .where(TreatmentMonitoringModel.plan_id == plan_id)
            .order_by(TreatmentMonitoringModel.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_plan_id(
        self,
        plan_id: uuid.UUID,
    ) -> int:
        """Delete all monitoring schedules for a given plan.

        Returns the number of rows deleted.
        """
        from sqlalchemy import delete as sa_delete

        stmt = (
            sa_delete(TreatmentMonitoringModel)
            .where(TreatmentMonitoringModel.plan_id == plan_id)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount  # type: ignore[union-attr]


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentSafetyRuleRepository
# ═══════════════════════════════════════════════════════════════════════════════


class TreatmentSafetyRuleRepository(BaseRepository[TreatmentSafetyRuleModel]):
    """Repository for ``TreatmentSafetyRuleModel`` persistence.

    Does **not** call commit — the service layer manages the transaction
    boundary.
    """

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(TreatmentSafetyRuleModel, db)

    async def create(
        self,
        model: TreatmentSafetyRuleModel,
    ) -> TreatmentSafetyRuleModel:
        """Persist a new safety rule."""
        self.db.add(model)
        await self.db.flush()
        return model

    async def create_many(
        self,
        models: List[TreatmentSafetyRuleModel],
    ) -> List[TreatmentSafetyRuleModel]:
        """Persist multiple safety rules in one batch."""
        self.db.add_all(models)
        await self.db.flush()
        return models

    async def list_by_plan_id(
        self,
        plan_id: uuid.UUID,
    ) -> List[TreatmentSafetyRuleModel]:
        """List all safety rules for a given plan."""
        stmt = (
            select(TreatmentSafetyRuleModel)
            .where(TreatmentSafetyRuleModel.plan_id == plan_id)
            .order_by(TreatmentSafetyRuleModel.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_plan_id(
        self,
        plan_id: uuid.UUID,
    ) -> int:
        """Delete all safety rules for a given plan.

        Returns the number of rows deleted.
        """
        from sqlalchemy import delete as sa_delete

        stmt = (
            sa_delete(TreatmentSafetyRuleModel)
            .where(TreatmentSafetyRuleModel.plan_id == plan_id)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount  # type: ignore[union-attr]


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentPlanTraceRepository
# ═══════════════════════════════════════════════════════════════════════════════


class TreatmentPlanTraceRepository(BaseRepository[TreatmentPlanTraceModel]):
    """Repository for ``TreatmentPlanTraceModel`` persistence.

    Does **not** call commit — the service layer manages the transaction
    boundary.
    """

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(TreatmentPlanTraceModel, db)

    async def create(
        self,
        model: TreatmentPlanTraceModel,
    ) -> TreatmentPlanTraceModel:
        """Persist a new treatment plan trace record."""
        self.db.add(model)
        await self.db.flush()
        return model

    async def create_many(
        self,
        models: List[TreatmentPlanTraceModel],
    ) -> List[TreatmentPlanTraceModel]:
        """Persist multiple trace records in one batch."""
        self.db.add_all(models)
        await self.db.flush()
        return models

    async def list_by_plan_id(
        self,
        plan_id: uuid.UUID,
    ) -> List[TreatmentPlanTraceModel]:
        """List all trace records for a given plan, ordered by step order."""
        stmt = (
            select(TreatmentPlanTraceModel)
            .where(TreatmentPlanTraceModel.plan_id == plan_id)
            .order_by(TreatmentPlanTraceModel.step_order.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_plan_id(
        self,
        plan_id: uuid.UUID,
    ) -> int:
        """Delete all trace records for a given plan.

        Returns the number of rows deleted.
        """
        from sqlalchemy import delete as sa_delete

        stmt = (
            sa_delete(TreatmentPlanTraceModel)
            .where(TreatmentPlanTraceModel.plan_id == plan_id)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount  # type: ignore[union-attr]
