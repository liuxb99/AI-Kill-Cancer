"""
Tumor Board repositories — persist consensus, opinions, and trace records.

Provides:
- ``TumorBoardConsensusRepository`` — CRUD for ``TumorBoardConsensusModel``
- ``TumorBoardOpinionRepository`` — CRUD for ``TumorBoardOpinionModel``
- ``TumorBoardConsensusTraceRepository`` — CRUD for ``TumorBoardConsensusTraceModel``

Following the project's repository pattern: inject session, do NOT manage
transactions (no commit/rollback).  The calling service is responsible for
the transaction boundary.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.domain.tumor_board import (
    TumorBoardConsensusModel,
    TumorBoardConsensusTraceModel,
    TumorBoardOpinionModel,
)
from src.backend.repositories.base import BaseRepository

# ═══════════════════════════════════════════════════════════════════════════════
# TumorBoardConsensusRepository
# ═══════════════════════════════════════════════════════════════════════════════


class TumorBoardConsensusRepository(BaseRepository[TumorBoardConsensusModel]):
    """Repository for ``TumorBoardConsensusModel`` persistence.

    Extends ``BaseRepository`` with domain-specific queries.
    Does **not** call commit — the service layer manages the transaction
    boundary.
    """

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(TumorBoardConsensusModel, db)

    async def create(
        self,
        model: TumorBoardConsensusModel,
    ) -> TumorBoardConsensusModel:
        """Persist a new tumor board consensus record.

        Adds the instance to the session and flushes so the PK is populated
        without committing.  The caller (service layer) is responsible for
        calling ``db.commit()``.

        Parameters
        ----------
        model : TumorBoardConsensusModel
            The model instance to persist.

        Returns
        -------
        TumorBoardConsensusModel
            The same instance (now tracked by the session, PK populated).
        """
        self.db.add(model)
        await self.db.flush()
        return model

    async def get_by_id(
        self,
        id: str,
    ) -> Optional[TumorBoardConsensusModel]:
        """Retrieve a tumor board consensus by its UUID primary key (as hex).

        Parameters
        ----------
        id : str
            The hex-string representation of the consensus record's UUID
            primary key (``TumorBoardConsensusModel.id``).

        Returns
        -------
        TumorBoardConsensusModel | None
        """
        stmt = select(TumorBoardConsensusModel).where(
            TumorBoardConsensusModel.id == uuid.UUID(id),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_uuid(
        self,
        consensus_id: str,
    ) -> Optional[TumorBoardConsensusModel]:
        """Retrieve a tumor board consensus by its business identifier.

        Parameters
        ----------
        consensus_id : str
            The unique business identifier
            (``TumorBoardConsensusModel.consensus_id``).

        Returns
        -------
        TumorBoardConsensusModel | None
        """
        stmt = select(TumorBoardConsensusModel).where(
            TumorBoardConsensusModel.consensus_id == consensus_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_patient_id(
        self,
        patient_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> List[TumorBoardConsensusModel]:
        """List consensus records for a patient, newest first.

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
        list[TumorBoardConsensusModel]
        """
        stmt = (
            select(TumorBoardConsensusModel)
            .where(TumorBoardConsensusModel.patient_id == patient_id)
            .order_by(TumorBoardConsensusModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_clinical_decision_id(
        self,
        clinical_decision_id: uuid.UUID,
    ) -> List[TumorBoardConsensusModel]:
        """List consensus records associated with a clinical decision,
        newest first.

        Parameters
        ----------
        clinical_decision_id : uuid.UUID
            The clinical decision's UUID.

        Returns
        -------
        list[TumorBoardConsensusModel]
        """
        stmt = (
            select(TumorBoardConsensusModel)
            .where(
                TumorBoardConsensusModel.clinical_decision_id
                == clinical_decision_id,
            )
            .order_by(TumorBoardConsensusModel.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_patient_id(
        self,
        patient_id: uuid.UUID,
    ) -> int:
        """Count consensus records for a patient.

        Parameters
        ----------
        patient_id : uuid.UUID
            The patient's UUID.

        Returns
        -------
        int
            Number of consensus records for the patient.
        """
        stmt = (
            select(func.count())
            .select_from(TumorBoardConsensusModel)
            .where(TumorBoardConsensusModel.patient_id == patient_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0


# ═══════════════════════════════════════════════════════════════════════════════
# TumorBoardOpinionRepository
# ═══════════════════════════════════════════════════════════════════════════════


class TumorBoardOpinionRepository(BaseRepository[TumorBoardOpinionModel]):
    """Repository for ``TumorBoardOpinionModel`` persistence.

    Extends ``BaseRepository`` with domain-specific queries.
    Does **not** call commit — the service layer manages the transaction
    boundary.
    """

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(TumorBoardOpinionModel, db)

    async def create(
        self,
        model: TumorBoardOpinionModel,
    ) -> TumorBoardOpinionModel:
        """Persist a new tumor board opinion record.

        Adds the instance to the session without committing.  The caller
        (service layer) is responsible for calling ``db.commit()`` and
        ``db.refresh()``.

        Parameters
        ----------
        model : TumorBoardOpinionModel
            The model instance to persist.

        Returns
        -------
        TumorBoardOpinionModel
            The same instance (now tracked by the session).
        """
        self.db.add(model)
        return model

    async def create_many(
        self,
        models: List[TumorBoardOpinionModel],
    ) -> List[TumorBoardOpinionModel]:
        """Persist multiple opinion records in one batch.

        Adds all instances to the session and flushes to populate PKs
        without committing.  The caller (service layer) is responsible
        for calling ``db.commit()``.

        Parameters
        ----------
        models : list[TumorBoardOpinionModel]
            The model instances to persist.

        Returns
        -------
        list[TumorBoardOpinionModel]
            The same instances (now tracked by the session).
        """
        self.db.add_all(models)
        await self.db.flush()
        return models

    async def list_by_consensus_id(
        self,
        consensus_id: uuid.UUID,
    ) -> List[TumorBoardOpinionModel]:
        """List all opinions for a given consensus, ordered by creation time.

        Parameters
        ----------
        consensus_id : uuid.UUID
            The consensus record's UUID primary key.

        Returns
        -------
        list[TumorBoardOpinionModel]
        """
        stmt = (
            select(TumorBoardOpinionModel)
            .where(TumorBoardOpinionModel.consensus_id == consensus_id)
            .order_by(TumorBoardOpinionModel.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════════════════════════
# TumorBoardConsensusTraceRepository
# ═══════════════════════════════════════════════════════════════════════════════


class TumorBoardConsensusTraceRepository(
    BaseRepository[TumorBoardConsensusTraceModel],
):
    """Repository for ``TumorBoardConsensusTraceModel`` persistence.

    Extends ``BaseRepository`` with domain-specific queries.
    Does **not** call commit — the service layer manages the transaction
    boundary.
    """

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(TumorBoardConsensusTraceModel, db)

    async def create(
        self,
        model: TumorBoardConsensusTraceModel,
    ) -> TumorBoardConsensusTraceModel:
        """Persist a new consensus trace record.

        Adds the instance to the session without committing.  The caller
        (service layer) is responsible for calling ``db.commit()`` and
        ``db.refresh()``.

        Parameters
        ----------
        model : TumorBoardConsensusTraceModel
            The model instance to persist.

        Returns
        -------
        TumorBoardConsensusTraceModel
            The same instance (now tracked by the session).
        """
        self.db.add(model)
        return model

    async def create_many(
        self,
        models: List[TumorBoardConsensusTraceModel],
    ) -> List[TumorBoardConsensusTraceModel]:
        """Persist multiple consensus trace records in one batch.

        Adds all instances to the session and flushes to populate PKs
        without committing.  The caller (service layer) is responsible
        for calling ``db.commit()``.

        Parameters
        ----------
        models : list[TumorBoardConsensusTraceModel]
            The model instances to persist.

        Returns
        -------
        list[TumorBoardConsensusTraceModel]
            The same instances (now tracked by the session).
        """
        self.db.add_all(models)
        await self.db.flush()
        return models

    async def list_by_consensus_id(
        self,
        consensus_id: uuid.UUID,
    ) -> List[TumorBoardConsensusTraceModel]:
        """List all trace steps for a given consensus, ordered by step order.

        Parameters
        ----------
        consensus_id : uuid.UUID
            The consensus record's UUID primary key.

        Returns
        -------
        list[TumorBoardConsensusTraceModel]
        """
        stmt = (
            select(TumorBoardConsensusTraceModel)
            .where(
                TumorBoardConsensusTraceModel.consensus_id == consensus_id,
            )
            .order_by(TumorBoardConsensusTraceModel.step_order.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_trace_id(
        self,
        trace_id: str,
    ) -> List[TumorBoardConsensusTraceModel]:
        """List all trace steps sharing a given trace identifier,
        ordered by step order.

        Parameters
        ----------
        trace_id : str
            The trace step identifier (business key).

        Returns
        -------
        list[TumorBoardConsensusTraceModel]
        """
        stmt = (
            select(TumorBoardConsensusTraceModel)
            .where(
                TumorBoardConsensusTraceModel.trace_id == trace_id,
            )
            .order_by(TumorBoardConsensusTraceModel.step_order.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
