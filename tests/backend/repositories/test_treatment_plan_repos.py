"""
Tests for Treatment Plan repositories (Phase 3E).

Covers ``TreatmentPlanRepository``, ``TreatmentPhaseRepository``,
``TreatmentItemRepository``, ``TreatmentMonitoringRepository``,
``TreatmentSafetyRuleRepository``, and ``TreatmentPlanTraceRepository`` —
CRUD and domain-specific queries.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base


@pytest.fixture
async def db_session():
    """Create an in-memory SQLite database for testing."""
    # Ensure all dependent models are loaded before create_all
    from src.backend.domain.patient import PatientModel  # noqa: F401
    from src.backend.domain.treatment_plan import (  # noqa: F401
        TreatmentItemModel,
        TreatmentMonitoringModel,
        TreatmentPhaseModel,
        TreatmentPlanModel,
        TreatmentPlanTraceModel,
        TreatmentSafetyRuleModel,
    )

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def patient(db_session):
    """Create a minimal Patient for FK references."""
    from src.backend.domain.patient import PatientModel

    p = PatientModel(display_name="TPR-TEST-PATIENT")
    db_session.add(p)
    await db_session.flush()
    return p


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentPlanRepository Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTreatmentPlanRepository:
    """Tests for TreatmentPlanRepository — CRUD and queries."""

    async def _create_plan(
        self,
        db_session,
        patient,
        plan_id="tpr-plan-001",
        version=1,
        **kwargs,
    ):
        """Helper to create a plan via repository."""
        from src.backend.domain.treatment_plan import TreatmentPlanModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        repo = TreatmentPlanRepository(db_session)
        model = TreatmentPlanModel(
            plan_id=plan_id,
            version=version,
            patient_id=patient.id,
            plan_status=kwargs.get("plan_status", "draft"),
            plan_intent=kwargs.get("plan_intent"),
            is_current=kwargs.get("is_current", True),
        )
        await repo.create(model)
        return model

    async def test_create(self, db_session, patient) -> None:
        """Repository.create() adds a plan to the session."""
        from src.backend.domain.treatment_plan import TreatmentPlanModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        repo = TreatmentPlanRepository(db_session)
        model = TreatmentPlanModel(
            plan_id="tpr-create",
            patient_id=patient.id,
            plan_status="draft",
            plan_intent="Curative",
        )
        result = await repo.create(model)
        await db_session.flush()

        assert result is model
        assert result.id is not None
        assert result.plan_id == "tpr-create"

        await db_session.commit()
        await db_session.refresh(result)
        assert result.plan_status == "draft"
        assert result.plan_intent == "Curative"

    async def test_get_by_id_found(self, db_session, patient) -> None:
        """get_by_id returns the matching model by UUID string."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        model = await self._create_plan(db_session, patient)
        await db_session.commit()

        repo = TreatmentPlanRepository(db_session)
        fetched = await repo.get_by_id(str(model.id))
        assert fetched is not None
        assert fetched.plan_id == model.plan_id
        assert str(fetched.id) == str(model.id)

    async def test_get_by_id_not_found(self, db_session) -> None:
        """get_by_id returns None for non-existent UUID string."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        repo = TreatmentPlanRepository(db_session)
        result = await repo.get_by_id(str(uuid.uuid4()))
        assert result is None

    async def test_get_current_by_plan_id_returns_current(self, db_session, patient) -> None:
        """get_current_by_plan_id returns the is_current=true version when multiple exist."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        # Create version 1 (is_current=False, superseded)
        await self._create_plan(
            db_session, patient,
            plan_id="tpr-current-by-pid",
            version=1,
            is_current=False,
        )
        # Create version 2 (is_current=True, current)
        await self._create_plan(
            db_session, patient,
            plan_id="tpr-current-by-pid",
            version=2,
            is_current=True,
        )
        await db_session.commit()

        repo = TreatmentPlanRepository(db_session)
        fetched = await repo.get_current_by_plan_id("tpr-current-by-pid")
        assert fetched is not None
        assert fetched.plan_id == "tpr-current-by-pid"
        assert fetched.version == 2
        assert fetched.is_current is True

    async def test_get_current_by_plan_id_returns_none(self, db_session) -> None:
        """get_current_by_plan_id returns None for non-existent plan_id."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        repo = TreatmentPlanRepository(db_session)
        result = await repo.get_current_by_plan_id("non-existent-plan-id")
        assert result is None

    async def test_get_plan_version(self, db_session, patient) -> None:
        """get_plan_version returns a specific version by plan_id + version."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        await self._create_plan(
            db_session, patient,
            plan_id="tpr-ver",
            version=42,
        )
        await db_session.commit()

        repo = TreatmentPlanRepository(db_session)
        fetched = await repo.get_plan_version("tpr-ver", 42)
        assert fetched is not None
        assert fetched.plan_id == "tpr-ver"
        assert fetched.version == 42

    async def test_get_plan_version_not_found(self, db_session) -> None:
        """get_plan_version returns None for non-existent plan_id/version combo."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        repo = TreatmentPlanRepository(db_session)
        result = await repo.get_plan_version("non-existent", 99)
        assert result is None

    async def test_get_current_by_patient_id_found(self, db_session, patient) -> None:
        """get_current_by_patient_id returns the current plan for a patient."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        # Create a non-current plan first
        await self._create_plan(
            db_session, patient,
            plan_id="tpr-old",
            version=1,
            is_current=False,
        )
        # Create the current plan
        await self._create_plan(
            db_session, patient,
            plan_id="tpr-current",
            version=2,
            is_current=True,
        )
        await db_session.commit()

        repo = TreatmentPlanRepository(db_session)
        fetched = await repo.get_current_by_patient_id(patient.id)
        assert fetched is not None
        assert fetched.plan_id == "tpr-current"
        assert fetched.version == 2

    async def test_get_current_by_patient_id_not_found(self, db_session, patient) -> None:
        """get_current_by_patient_id returns None when no current plan exists."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        await self._create_plan(
            db_session, patient,
            plan_id="tpr-no-current",
            is_current=False,
        )
        await db_session.commit()

        repo = TreatmentPlanRepository(db_session)
        result = await repo.get_current_by_patient_id(patient.id)
        assert result is None

    async def test_get_current_by_patient_id_empty(self, db_session) -> None:
        """get_current_by_patient_id returns None for non-existent patient."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        repo = TreatmentPlanRepository(db_session)
        result = await repo.get_current_by_patient_id(uuid.uuid4())
        assert result is None

    async def test_list_by_patient_id(self, db_session, patient) -> None:
        """list_by_patient_id returns plans for a specific patient."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        for i in range(3):
            await self._create_plan(
                db_session, patient,
                plan_id=f"tpr-list-{i:02d}",
            )
        await db_session.commit()

        repo = TreatmentPlanRepository(db_session)
        results = await repo.list_by_patient_id(patient.id)
        assert len(results) == 3
        assert all(r.patient_id == patient.id for r in results)

    async def test_list_by_patient_id_empty(self, db_session) -> None:
        """list_by_patient_id returns empty list for non-existent patient."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        repo = TreatmentPlanRepository(db_session)
        results = await repo.list_by_patient_id(uuid.uuid4())
        assert results == []

    async def test_list_by_patient_id_pagination(self, db_session, patient) -> None:
        """list_by_patient_id supports skip and limit pagination."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        for i in range(5):
            await self._create_plan(
                db_session, patient,
                plan_id=f"tpr-page-{i:02d}",
            )
        await db_session.commit()

        repo = TreatmentPlanRepository(db_session)

        # With limit
        results = await repo.list_by_patient_id(patient.id, limit=3)
        assert len(results) == 3

        # With skip
        results_skip = await repo.list_by_patient_id(patient.id, skip=3)
        assert len(results_skip) == 2

        # Skip beyond total
        results_empty = await repo.list_by_patient_id(patient.id, skip=10)
        assert results_empty == []

    async def test_list_versions(self, db_session, patient) -> None:
        """list_versions returns the single matching plan (plan_id is unique)."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        await self._create_plan(
            db_session, patient,
            plan_id="tpr-versions",
            version=2,
        )
        await db_session.commit()

        repo = TreatmentPlanRepository(db_session)
        versions = await repo.list_versions("tpr-versions")
        assert len(versions) == 1
        assert versions[0].version == 2
        assert versions[0].plan_id == "tpr-versions"

    async def test_list_versions_empty(self, db_session) -> None:
        """list_versions returns empty list for non-existent plan_id."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        repo = TreatmentPlanRepository(db_session)
        results = await repo.list_versions("non-existent-plan")
        assert results == []

    async def test_count_by_patient_id_empty(self, db_session) -> None:
        """count_by_patient_id returns 0 when no plans exist."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        repo = TreatmentPlanRepository(db_session)
        count = await repo.count_by_patient_id(uuid.uuid4())
        assert count == 0

    async def test_count_by_patient_id_with_records(self, db_session, patient) -> None:
        """count_by_patient_id returns the correct count."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        for i in range(5):
            await self._create_plan(
                db_session, patient,
                plan_id=f"tpr-count-{i:02d}",
            )
        await db_session.commit()

        repo = TreatmentPlanRepository(db_session)
        count = await repo.count_by_patient_id(patient.id)
        assert count == 5

    async def test_count_by_patient_id_wrong_patient(self, db_session, patient) -> None:
        """count_by_patient_id returns 0 for unrelated patient."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        await self._create_plan(db_session, patient)
        await db_session.commit()

        repo = TreatmentPlanRepository(db_session)
        count = await repo.count_by_patient_id(uuid.uuid4())
        assert count == 0

    async def test_mark_superseded(self, db_session, patient) -> None:
        """mark_superseded sets is_current=False and records superseding info."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        await self._create_plan(
            db_session, patient,
            plan_id="tpr-supersede",
            version=1,
            is_current=True,
        )
        await db_session.commit()

        new_version_id = uuid.uuid4()
        repo = TreatmentPlanRepository(db_session)
        await repo.mark_superseded(
            plan_id="tpr-supersede",
            superseded_by_version_id=new_version_id,
            revision_reason="New evidence available",
        )
        await db_session.commit()

        # Verify
        fetched = await repo.get_plan_version("tpr-supersede", 1)
        assert fetched is not None
        assert fetched.is_current is False
        assert fetched.supersedes_version_id == new_version_id
        assert fetched.supersedes_plan_id == "tpr-supersede"  # 向後相容
        assert fetched.revision_reason == "New evidence available"

    async def test_mark_superseded_no_reason(self, db_session, patient) -> None:
        """mark_superseded works with empty revision_reason."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        await self._create_plan(
            db_session, patient,
            plan_id="tpr-sup-no-reason",
            is_current=True,
        )
        await db_session.commit()

        new_version_id = uuid.uuid4()
        repo = TreatmentPlanRepository(db_session)
        await repo.mark_superseded(
            plan_id="tpr-sup-no-reason",
            superseded_by_version_id=new_version_id,
        )
        await db_session.commit()

        fetched = await repo.get_plan_version("tpr-sup-no-reason", 1)
        assert fetched is not None
        assert fetched.is_current is False
        assert fetched.supersedes_version_id == new_version_id
        assert fetched.revision_reason is None  # empty string → None

    async def test_mark_superseded_only_current(self, db_session, patient) -> None:
        """mark_superseded only affects the current version (plan_id is unique)."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        await self._create_plan(
            db_session, patient,
            plan_id="tpr-sup-only",
            version=1,
            is_current=False,
        )
        await db_session.commit()

        new_version_id = uuid.uuid4()
        repo = TreatmentPlanRepository(db_session)
        await repo.mark_superseded(
            plan_id="tpr-sup-only",
            superseded_by_version_id=new_version_id,
        )
        await db_session.commit()

        # Since plan_id is unique, v1 had is_current=False and
        # mark_superseded updates only rows where is_current=True,
        # so no row matched — v1 should remain unchanged.
        fetched = await repo.get_plan_version("tpr-sup-only", 1)
        assert fetched is not None
        assert fetched.is_current is False  # was already False
        assert fetched.supersedes_version_id is None  # not updated

    async def test_transaction_rollback(self, db_session, patient) -> None:
        """If rolled back, no data should persist."""
        from src.backend.domain.treatment_plan import TreatmentPlanModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanRepository,
        )

        repo = TreatmentPlanRepository(db_session)
        model = TreatmentPlanModel(
            plan_id="tpr-rollback",
            patient_id=patient.id,
        )
        await repo.create(model)

        await db_session.rollback()

        fetched = await repo.get_current_by_plan_id("tpr-rollback")
        assert fetched is None


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentPhaseRepository Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTreatmentPhaseRepository:
    """Tests for TreatmentPhaseRepository — CRUD for phases."""

    async def _setup_plan(self, db_session, patient):
        """Helper: create a plan and return it."""
        from src.backend.domain.treatment_plan import TreatmentPlanModel

        plan = TreatmentPlanModel(
            plan_id="tpr-phase-repo",
            patient_id=patient.id,
        )
        db_session.add(plan)
        await db_session.flush()
        return plan

    async def test_create(self, db_session, patient) -> None:
        """PhaseRepository.create() adds a phase to the session."""
        from src.backend.domain.treatment_plan import TreatmentPhaseModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPhaseRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentPhaseRepository(db_session)

        phase = TreatmentPhaseModel(
            phase_id="tpr-phase-create",
            plan_id=plan.id,
            phase_order=1,
            phase_type="induction",
            name="Induction Chemotherapy",
        )
        result = await repo.create(phase)
        await db_session.flush()
        assert result is phase
        assert result.id is not None
        await db_session.commit()

    async def test_create_many(self, db_session, patient) -> None:
        """PhaseRepository.create_many persists multiple phases."""
        from src.backend.domain.treatment_plan import TreatmentPhaseModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPhaseRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentPhaseRepository(db_session)

        phases = [
            TreatmentPhaseModel(
                phase_id=f"tpr-phase-multi-{i}",
                plan_id=plan.id,
                phase_order=i,
                phase_type="test",
                name=f"Phase {i}",
            )
            for i in range(3)
        ]
        results = await repo.create_many(phases)
        await db_session.commit()

        assert len(results) == 3
        assert all(p.id is not None for p in results)

    async def test_list_by_plan_id(self, db_session, patient) -> None:
        """list_by_plan_id returns all phases for a plan, ordered."""
        from src.backend.domain.treatment_plan import TreatmentPhaseModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPhaseRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentPhaseRepository(db_session)

        for i in range(1, 4):
            phase = TreatmentPhaseModel(
                phase_id=f"tpr-phase-list-{i}",
                plan_id=plan.id,
                phase_order=i,
                phase_type="test",
                name=f"Phase {i}",
            )
            await repo.create(phase)
        await db_session.commit()

        results = await repo.list_by_plan_id(plan.id)
        assert len(results) == 3
        assert results[0].phase_order == 1
        assert results[1].phase_order == 2
        assert results[2].phase_order == 3

    async def test_list_by_plan_id_empty(self, db_session) -> None:
        """list_by_plan_id returns empty list for no phases."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPhaseRepository,
        )

        repo = TreatmentPhaseRepository(db_session)
        results = await repo.list_by_plan_id(uuid.uuid4())
        assert results == []

    async def test_delete_by_plan_id(self, db_session, patient) -> None:
        """delete_by_plan_id removes all phases for a plan."""
        from src.backend.domain.treatment_plan import TreatmentPhaseModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPhaseRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentPhaseRepository(db_session)

        for i in range(2):
            phase = TreatmentPhaseModel(
                phase_id=f"tpr-phase-del-{i}",
                plan_id=plan.id,
                phase_order=i,
                phase_type="test",
                name=f"Phase {i}",
            )
            await repo.create(phase)
        await db_session.commit()

        deleted = await repo.delete_by_plan_id(plan.id)
        await db_session.commit()
        assert deleted == 2

        # Verify they're gone
        remaining = await repo.list_by_plan_id(plan.id)
        assert remaining == []

    async def test_transaction_rollback(self, db_session, patient) -> None:
        """If rolled back, no phase data should persist."""
        from src.backend.domain.treatment_plan import TreatmentPhaseModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPhaseRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentPhaseRepository(db_session)

        phase = TreatmentPhaseModel(
            phase_id="tpr-phase-rollback",
            plan_id=plan.id,
            phase_order=1,
            phase_type="test",
            name="Rollback Phase",
        )
        await repo.create(phase)

        await db_session.rollback()

        results = await repo.list_by_plan_id(plan.id)
        assert results == []


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentItemRepository Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTreatmentItemRepository:
    """Tests for TreatmentItemRepository — CRUD for items."""

    async def _setup_plan(self, db_session, patient):
        """Helper: create a plan and return it."""
        from src.backend.domain.treatment_plan import TreatmentPlanModel

        plan = TreatmentPlanModel(
            plan_id="tpr-item-repo",
            patient_id=patient.id,
        )
        db_session.add(plan)
        await db_session.flush()
        return plan

    async def test_create(self, db_session, patient) -> None:
        """ItemRepository.create() adds an item to the session."""
        from src.backend.domain.treatment_plan import TreatmentItemModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentItemRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentItemRepository(db_session)

        item = TreatmentItemModel(
            item_id="tpr-item-create",
            plan_id=plan.id,
            item_order=1,
            item_type="medication",
            name="Osimertinib",
        )
        result = await repo.create(item)
        await db_session.flush()
        assert result is item
        assert result.id is not None
        await db_session.commit()

    async def test_create_many(self, db_session, patient) -> None:
        """ItemRepository.create_many persists multiple items."""
        from src.backend.domain.treatment_plan import TreatmentItemModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentItemRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentItemRepository(db_session)

        items = [
            TreatmentItemModel(
                item_id=f"tpr-item-multi-{i}",
                plan_id=plan.id,
                item_order=i,
                item_type="medication",
                name=f"Drug {i}",
            )
            for i in range(3)
        ]
        results = await repo.create_many(items)
        await db_session.commit()

        assert len(results) == 3
        assert all(i.id is not None for i in results)

    async def test_list_by_plan_id(self, db_session, patient) -> None:
        """list_by_plan_id returns all items for a plan, ordered."""
        from src.backend.domain.treatment_plan import TreatmentItemModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentItemRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentItemRepository(db_session)

        for i in range(1, 4):
            item = TreatmentItemModel(
                item_id=f"tpr-item-list-{i}",
                plan_id=plan.id,
                item_order=i,
                item_type="test",
                name=f"Item {i}",
            )
            await repo.create(item)
        await db_session.commit()

        results = await repo.list_by_plan_id(plan.id)
        assert len(results) == 3
        assert results[0].item_order == 1
        assert results[1].item_order == 2
        assert results[2].item_order == 3

    async def test_list_by_plan_id_empty(self, db_session) -> None:
        """list_by_plan_id returns empty list for no items."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentItemRepository,
        )

        repo = TreatmentItemRepository(db_session)
        results = await repo.list_by_plan_id(uuid.uuid4())
        assert results == []

    async def test_delete_by_plan_id(self, db_session, patient) -> None:
        """delete_by_plan_id removes all items for a plan."""
        from src.backend.domain.treatment_plan import TreatmentItemModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentItemRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentItemRepository(db_session)

        for i in range(2):
            item = TreatmentItemModel(
                item_id=f"tpr-item-del-{i}",
                plan_id=plan.id,
                item_order=i,
                item_type="test",
                name=f"Item {i}",
            )
            await repo.create(item)
        await db_session.commit()

        deleted = await repo.delete_by_plan_id(plan.id)
        await db_session.commit()
        assert deleted == 2

        remaining = await repo.list_by_plan_id(plan.id)
        assert remaining == []

    async def test_create_with_all_fields_and_persistence(self, db_session, patient) -> None:
        """建立 Item 後直接查 DB 逐欄驗證所有持久化欄位。

        驗證 drug_id, procedure_code, frequency, duration, route,
        planned_dose_text 已被正確寫入且與 Engine Output 一致。
        """
        from sqlalchemy import select

        from src.backend.domain.treatment_plan import TreatmentItemModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentItemRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentItemRepository(db_session)

        # ── 使用 engine output 風格的完整欄位建立 Item ──────────────────
        item = TreatmentItemModel(
            item_id="tpr-item-persist-all",
            plan_id=plan.id,
            item_order=1,
            item_type="medication",
            name="Lenvatinib",
            description="Primary medication for PTC",
            drug_id="DB09021",                          # DrugBank ID
            procedure_code=None,                         # 非 procedure 所以為 None
            frequency="once_daily",
            duration="24 weeks",
            route="oral",
            planned_dose_text="24 mg once daily with dose adjustments",
            priority=1,
            status="planned",
            rationale="Recommended for advanced PTC",
        )
        await repo.create(item)
        await db_session.commit()

        # ── 直接查 DB（避開 ORM session cache）逐欄驗證 ────────────────
        stmt = select(TreatmentItemModel).where(
            TreatmentItemModel.item_id == "tpr-item-persist-all",
        )
        row = (await db_session.execute(stmt)).scalar_one()

        # Engine output 欄位
        assert row.drug_id == "DB09021", f"drug_id mismatch: {row.drug_id}"
        assert row.procedure_code is None, f"procedure_code should be None: {row.procedure_code}"
        assert row.frequency == "once_daily", f"frequency mismatch: {row.frequency}"
        assert row.duration == "24 weeks", f"duration mismatch: {row.duration}"
        assert row.route == "oral", f"route mismatch: {row.route}"
        assert row.planned_dose_text == "24 mg once daily with dose adjustments", \
            f"planned_dose_text mismatch: {row.planned_dose_text}"

        # 同時驗證基本欄位也未遺失
        assert row.item_id == "tpr-item-persist-all"
        assert row.item_order == 1
        assert row.item_type == "medication"
        assert row.name == "Lenvatinib"
        assert row.priority == 1
        assert row.status == "planned"
        assert row.rationale == "Recommended for advanced PTC"

    async def test_transaction_rollback(self, db_session, patient) -> None:
        """If rolled back, no item data should persist."""
        from src.backend.domain.treatment_plan import TreatmentItemModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentItemRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentItemRepository(db_session)

        item = TreatmentItemModel(
            item_id="tpr-item-rollback",
            plan_id=plan.id,
            item_order=1,
            item_type="test",
            name="Rollback Item",
        )
        await repo.create(item)

        await db_session.rollback()

        results = await repo.list_by_plan_id(plan.id)
        assert results == []


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentMonitoringRepository Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTreatmentMonitoringRepository:
    """Tests for TreatmentMonitoringRepository — CRUD for monitoring schedules."""

    async def _setup_plan(self, db_session, patient):
        """Helper: create a plan and return it."""
        from src.backend.domain.treatment_plan import TreatmentPlanModel

        plan = TreatmentPlanModel(
            plan_id="tpr-mon-repo",
            patient_id=patient.id,
        )
        db_session.add(plan)
        await db_session.flush()
        return plan

    async def test_create(self, db_session, patient) -> None:
        """MonitoringRepository.create() adds a monitoring schedule."""
        from src.backend.domain.treatment_plan import TreatmentMonitoringModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentMonitoringRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentMonitoringRepository(db_session)

        mon = TreatmentMonitoringModel(
            monitoring_id="tpr-mon-create",
            plan_id=plan.id,
            monitoring_type="laboratory",
            name="CBC",
        )
        result = await repo.create(mon)
        await db_session.flush()
        assert result is mon
        assert result.id is not None
        await db_session.commit()

    async def test_create_many(self, db_session, patient) -> None:
        """MonitoringRepository.create_many persists multiple schedules."""
        from src.backend.domain.treatment_plan import TreatmentMonitoringModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentMonitoringRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentMonitoringRepository(db_session)

        monitors = [
            TreatmentMonitoringModel(
                monitoring_id=f"tpr-mon-multi-{i}",
                plan_id=plan.id,
                monitoring_type="imaging",
                name=f"Scan {i}",
            )
            for i in range(3)
        ]
        results = await repo.create_many(monitors)
        await db_session.commit()

        assert len(results) == 3
        assert all(m.id is not None for m in results)

    async def test_list_by_plan_id(self, db_session, patient) -> None:
        """list_by_plan_id returns all monitoring for a plan."""
        from src.backend.domain.treatment_plan import TreatmentMonitoringModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentMonitoringRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentMonitoringRepository(db_session)

        for i in range(3):
            mon = TreatmentMonitoringModel(
                monitoring_id=f"tpr-mon-list-{i}",
                plan_id=plan.id,
                monitoring_type="test",
                name=f"Monitor {i}",
            )
            await repo.create(mon)
        await db_session.commit()

        results = await repo.list_by_plan_id(plan.id)
        assert len(results) == 3

    async def test_list_by_plan_id_empty(self, db_session) -> None:
        """list_by_plan_id returns empty list for no monitoring."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentMonitoringRepository,
        )

        repo = TreatmentMonitoringRepository(db_session)
        results = await repo.list_by_plan_id(uuid.uuid4())
        assert results == []

    async def test_delete_by_plan_id(self, db_session, patient) -> None:
        """delete_by_plan_id removes all monitoring for a plan."""
        from src.backend.domain.treatment_plan import TreatmentMonitoringModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentMonitoringRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentMonitoringRepository(db_session)

        for i in range(2):
            mon = TreatmentMonitoringModel(
                monitoring_id=f"tpr-mon-del-{i}",
                plan_id=plan.id,
                monitoring_type="test",
                name=f"Mon {i}",
            )
            await repo.create(mon)
        await db_session.commit()

        deleted = await repo.delete_by_plan_id(plan.id)
        await db_session.commit()
        assert deleted == 2

        remaining = await repo.list_by_plan_id(plan.id)
        assert remaining == []

    async def test_transaction_rollback(self, db_session, patient) -> None:
        """If rolled back, no monitoring data should persist."""
        from src.backend.domain.treatment_plan import TreatmentMonitoringModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentMonitoringRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentMonitoringRepository(db_session)

        mon = TreatmentMonitoringModel(
            monitoring_id="tpr-mon-rollback",
            plan_id=plan.id,
            monitoring_type="test",
            name="Rollback Mon",
        )
        await repo.create(mon)

        await db_session.rollback()

        results = await repo.list_by_plan_id(plan.id)
        assert results == []


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentSafetyRuleRepository Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTreatmentSafetyRuleRepository:
    """Tests for TreatmentSafetyRuleRepository — CRUD for safety rules."""

    async def _setup_plan(self, db_session, patient):
        """Helper: create a plan and return it."""
        from src.backend.domain.treatment_plan import TreatmentPlanModel

        plan = TreatmentPlanModel(
            plan_id="tpr-rule-repo",
            patient_id=patient.id,
        )
        db_session.add(plan)
        await db_session.flush()
        return plan

    async def test_create(self, db_session, patient) -> None:
        """SafetyRuleRepository.create() adds a safety rule."""
        from src.backend.domain.treatment_plan import TreatmentSafetyRuleModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentSafetyRuleRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentSafetyRuleRepository(db_session)

        rule = TreatmentSafetyRuleModel(
            rule_id="tpr-rule-create",
            plan_id=plan.id,
            rule_type="dose_review",
            condition={"lab": "neutrophils", "operator": "<", "value": 1.0},
            severity="high",
        )
        result = await repo.create(rule)
        await db_session.flush()
        assert result is rule
        assert result.id is not None
        await db_session.commit()

    async def test_create_many(self, db_session, patient) -> None:
        """SafetyRuleRepository.create_many persists multiple rules."""
        from src.backend.domain.treatment_plan import TreatmentSafetyRuleModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentSafetyRuleRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentSafetyRuleRepository(db_session)

        rules = [
            TreatmentSafetyRuleModel(
                rule_id=f"tpr-rule-multi-{i}",
                plan_id=plan.id,
                rule_type="pause",
                condition={"test": i},
                severity="medium",
            )
            for i in range(3)
        ]
        results = await repo.create_many(rules)
        await db_session.commit()

        assert len(results) == 3
        assert all(r.id is not None for r in results)

    async def test_list_by_plan_id(self, db_session, patient) -> None:
        """list_by_plan_id returns all safety rules for a plan."""
        from src.backend.domain.treatment_plan import TreatmentSafetyRuleModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentSafetyRuleRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentSafetyRuleRepository(db_session)

        for i in range(3):
            rule = TreatmentSafetyRuleModel(
                rule_id=f"tpr-rule-list-{i}",
                plan_id=plan.id,
                rule_type="test",
                condition={"idx": i},
                severity="low",
            )
            await repo.create(rule)
        await db_session.commit()

        results = await repo.list_by_plan_id(plan.id)
        assert len(results) == 3

    async def test_list_by_plan_id_empty(self, db_session) -> None:
        """list_by_plan_id returns empty list for no rules."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentSafetyRuleRepository,
        )

        repo = TreatmentSafetyRuleRepository(db_session)
        results = await repo.list_by_plan_id(uuid.uuid4())
        assert results == []

    async def test_delete_by_plan_id(self, db_session, patient) -> None:
        """delete_by_plan_id removes all safety rules for a plan."""
        from src.backend.domain.treatment_plan import TreatmentSafetyRuleModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentSafetyRuleRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentSafetyRuleRepository(db_session)

        for i in range(2):
            rule = TreatmentSafetyRuleModel(
                rule_id=f"tpr-rule-del-{i}",
                plan_id=plan.id,
                rule_type="test",
                condition={"i": i},
                severity="low",
            )
            await repo.create(rule)
        await db_session.commit()

        deleted = await repo.delete_by_plan_id(plan.id)
        await db_session.commit()
        assert deleted == 2

        remaining = await repo.list_by_plan_id(plan.id)
        assert remaining == []

    async def test_transaction_rollback(self, db_session, patient) -> None:
        """If rolled back, no safety rule data should persist."""
        from src.backend.domain.treatment_plan import TreatmentSafetyRuleModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentSafetyRuleRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentSafetyRuleRepository(db_session)

        rule = TreatmentSafetyRuleModel(
            rule_id="tpr-rule-rollback",
            plan_id=plan.id,
            rule_type="test",
            condition={},
            severity="low",
        )
        await repo.create(rule)

        await db_session.rollback()

        results = await repo.list_by_plan_id(plan.id)
        assert results == []


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentPlanTraceRepository Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTreatmentPlanTraceRepository:
    """Tests for TreatmentPlanTraceRepository — CRUD for trace records."""

    async def _setup_plan(self, db_session, patient):
        """Helper: create a plan and return it."""
        from src.backend.domain.treatment_plan import TreatmentPlanModel

        plan = TreatmentPlanModel(
            plan_id="tpr-trace-repo",
            patient_id=patient.id,
        )
        db_session.add(plan)
        await db_session.flush()
        return plan

    async def test_create(self, db_session, patient) -> None:
        """TraceRepository.create() adds a trace record to the session."""
        from src.backend.domain.treatment_plan import TreatmentPlanTraceModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanTraceRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentPlanTraceRepository(db_session)

        trace = TreatmentPlanTraceModel(
            trace_id="tpr-trace-create",
            plan_id=plan.id,
            step_order=1,
            step_type="load_context",
        )
        result = await repo.create(trace)
        await db_session.flush()
        assert result is trace
        assert result.id is not None
        await db_session.commit()

    async def test_create_many(self, db_session, patient) -> None:
        """TraceRepository.create_many persists multiple traces."""
        from src.backend.domain.treatment_plan import TreatmentPlanTraceModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanTraceRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentPlanTraceRepository(db_session)

        traces = [
            TreatmentPlanTraceModel(
                trace_id=f"tpr-trace-multi-{i}",
                plan_id=plan.id,
                step_order=i,
                step_type=f"step_{i}",
            )
            for i in range(3)
        ]
        results = await repo.create_many(traces)
        await db_session.commit()

        assert len(results) == 3
        assert all(t.id is not None for t in results)

    async def test_list_by_plan_id(self, db_session, patient) -> None:
        """list_by_plan_id returns all traces for a plan, ordered by step."""
        from src.backend.domain.treatment_plan import TreatmentPlanTraceModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanTraceRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentPlanTraceRepository(db_session)

        for i in range(1, 4):
            trace = TreatmentPlanTraceModel(
                trace_id=f"tpr-trace-list-{i}",
                plan_id=plan.id,
                step_order=i,
                step_type=f"step_{i}",
            )
            await repo.create(trace)
        await db_session.commit()

        results = await repo.list_by_plan_id(plan.id)
        assert len(results) == 3
        assert results[0].step_order == 1
        assert results[1].step_order == 2
        assert results[2].step_order == 3

    async def test_list_by_plan_id_empty(self, db_session) -> None:
        """list_by_plan_id returns empty list for no traces."""
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanTraceRepository,
        )

        repo = TreatmentPlanTraceRepository(db_session)
        results = await repo.list_by_plan_id(uuid.uuid4())
        assert results == []

    async def test_delete_by_plan_id(self, db_session, patient) -> None:
        """delete_by_plan_id removes all traces for a plan."""
        from src.backend.domain.treatment_plan import TreatmentPlanTraceModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanTraceRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentPlanTraceRepository(db_session)

        for i in range(2):
            trace = TreatmentPlanTraceModel(
                trace_id=f"tpr-trace-del-{i}",
                plan_id=plan.id,
                step_order=i,
                step_type=f"step_{i}",
            )
            await repo.create(trace)
        await db_session.commit()

        deleted = await repo.delete_by_plan_id(plan.id)
        await db_session.commit()
        assert deleted == 2

        remaining = await repo.list_by_plan_id(plan.id)
        assert remaining == []

    async def test_transaction_rollback(self, db_session, patient) -> None:
        """If rolled back, no trace data should persist."""
        from src.backend.domain.treatment_plan import TreatmentPlanTraceModel
        from src.backend.repositories.treatment_plan_repo import (
            TreatmentPlanTraceRepository,
        )

        plan = await self._setup_plan(db_session, patient)
        repo = TreatmentPlanTraceRepository(db_session)

        trace = TreatmentPlanTraceModel(
            trace_id="tpr-trace-rollback",
            plan_id=plan.id,
            step_order=1,
            step_type="test",
        )
        await repo.create(trace)

        await db_session.rollback()

        results = await repo.list_by_plan_id(plan.id)
        assert results == []
