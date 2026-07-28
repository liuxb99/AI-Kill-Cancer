"""
Tests for Treatment Plan ORM models (Phase 3E).

Covers ``TreatmentPlanModel``, ``TreatmentPhaseModel``, ``TreatmentItemModel``,
``TreatmentMonitoringModel``, ``TreatmentSafetyRuleModel``, and
``TreatmentPlanTraceModel`` — fields, FK associations, cascade delete, unique
constraints, and JSON round-trip.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base


@pytest.fixture
async def db_session():
    """Create an in-memory SQLite database for testing SQLAlchemy models."""
    # Ensure all dependent models are loaded before create_all
    from src.backend.domain.patient import PatientModel  # noqa: F401
    from src.backend.domain.recommendation import RecommendationModel  # noqa: F401
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

    p = PatientModel(display_name="TPM-TEST-PATIENT")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentPlanModel Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTreatmentPlanModel:
    """Tests for TreatmentPlanModel — core fields, JSON, relations, versioning."""

    async def test_create_all_fields(self, db_session, patient) -> None:
        """TreatmentPlanModel can be created with all fields populated."""
        from src.backend.domain.treatment_plan import TreatmentPlanModel

        plan = TreatmentPlanModel(
            plan_id="tp-all-fields",
            version=1,
            patient_id=patient.id,
            plan_status="draft",
            plan_intent="Curative",
            treatment_goals={"primary": "Reduce tumor size", "secondary": ["Prevent metastasis"]},
            summary="Comprehensive treatment plan for NSCLC",
            clinical_rationale="EGFR L858R mutation detected",
            start_date=None,
            target_end_date=None,
            is_current=True,
        )
        db_session.add(plan)
        await db_session.commit()
        await db_session.refresh(plan)

        assert plan.id is not None
        assert plan.plan_id == "tp-all-fields"
        assert plan.version == 1
        assert plan.plan_status == "draft"
        assert plan.plan_intent == "Curative"
        assert plan.treatment_goals == {"primary": "Reduce tumor size", "secondary": ["Prevent metastasis"]}
        assert plan.summary == "Comprehensive treatment plan for NSCLC"
        assert plan.is_current is True
        assert plan.created_at is not None
        assert plan.updated_at is not None

    async def test_default_values(self, db_session, patient) -> None:
        """TreatmentPlanModel should have sensible defaults."""
        from src.backend.domain.treatment_plan import TreatmentPlanModel

        plan = TreatmentPlanModel(
            plan_id="tp-defaults",
            patient_id=patient.id,
        )
        db_session.add(plan)
        await db_session.commit()
        await db_session.refresh(plan)

        assert plan.version == 1  # default
        assert plan.plan_status == "draft"  # default
        assert plan.is_current is True  # default
        assert plan.treatment_goals is None
        assert plan.summary is None
        assert plan.clinical_rationale is None

    async def test_plan_id_version_unique(self, db_session, patient) -> None:
        """plan_id must be unique (column-level unique constraint)."""
        from sqlalchemy.exc import IntegrityError

        from src.backend.domain.treatment_plan import TreatmentPlanModel

        p1 = TreatmentPlanModel(
            plan_id="tp-uniq-ver",
            patient_id=patient.id,
        )
        db_session.add(p1)
        await db_session.commit()

        p2 = TreatmentPlanModel(
            plan_id="tp-uniq-ver",  # same plan_id → violates unique=True
            patient_id=patient.id,
        )
        db_session.add(p2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_json_fields_round_trip(self, db_session, patient) -> None:
        """JSON fields (treatment_goals) survive write-read."""
        from src.backend.domain.treatment_plan import TreatmentPlanModel

        complex_goals = {
            "primary": "Achieve remission",
            "secondary": [
                "Maintain quality of life",
                "Prevent recurrence",
            ],
            "metrics": {"target_reduction": "50%", "timeframe_months": 6},
        }

        plan = TreatmentPlanModel(
            plan_id="tp-json-rt",
            patient_id=patient.id,
            treatment_goals=complex_goals,
        )
        db_session.add(plan)
        await db_session.commit()
        await db_session.refresh(plan)

        assert plan.treatment_goals == complex_goals
        assert plan.treatment_goals["primary"] == "Achieve remission"
        assert plan.treatment_goals["metrics"]["target_reduction"] == "50%"

    async def test_phases_relation(self, db_session, patient) -> None:
        """Plan can be linked to phases."""
        from src.backend.domain.treatment_plan import (
            TreatmentPhaseModel,
            TreatmentPlanModel,
        )

        plan = TreatmentPlanModel(
            plan_id="tp-phase-rel",
            patient_id=patient.id,
        )
        db_session.add(plan)
        await db_session.flush()

        phase = TreatmentPhaseModel(
            phase_id="tp-phase-001",
            plan_id=plan.id,
            phase_order=1,
            phase_type="induction",
            name="Induction Chemotherapy",
        )
        db_session.add(phase)
        await db_session.commit()

        await db_session.refresh(plan)
        assert len(plan.phases) == 1
        assert plan.phases[0].phase_id == "tp-phase-001"
        assert plan.phases[0].phase_type == "induction"

    async def test_items_relation(self, db_session, patient) -> None:
        """Plan can be linked to items."""
        from src.backend.domain.treatment_plan import (
            TreatmentItemModel,
            TreatmentPlanModel,
        )

        plan = TreatmentPlanModel(
            plan_id="tp-item-rel",
            patient_id=patient.id,
        )
        db_session.add(plan)
        await db_session.flush()

        item = TreatmentItemModel(
            item_id="tp-item-001",
            plan_id=plan.id,
            item_order=1,
            item_type="medication",
            name="Osimertinib",
        )
        db_session.add(item)
        await db_session.commit()

        await db_session.refresh(plan)
        assert len(plan.items) == 1
        assert plan.items[0].item_id == "tp-item-001"

    async def test_monitoring_relation(self, db_session, patient) -> None:
        """Plan can be linked to monitoring schedules."""
        from src.backend.domain.treatment_plan import (
            TreatmentMonitoringModel,
            TreatmentPlanModel,
        )

        plan = TreatmentPlanModel(
            plan_id="tp-mon-rel",
            patient_id=patient.id,
        )
        db_session.add(plan)
        await db_session.flush()

        mon = TreatmentMonitoringModel(
            monitoring_id="tp-mon-001",
            plan_id=plan.id,
            monitoring_type="laboratory",
            name="CBC with differential",
        )
        db_session.add(mon)
        await db_session.commit()

        await db_session.refresh(plan)
        assert len(plan.monitoring) == 1
        assert plan.monitoring[0].monitoring_id == "tp-mon-001"

    async def test_safety_rules_relation(self, db_session, patient) -> None:
        """Plan can be linked to safety rules."""
        from src.backend.domain.treatment_plan import (
            TreatmentPlanModel,
            TreatmentSafetyRuleModel,
        )

        plan = TreatmentPlanModel(
            plan_id="tp-safety-rel",
            patient_id=patient.id,
        )
        db_session.add(plan)
        await db_session.flush()

        rule = TreatmentSafetyRuleModel(
            rule_id="tp-rule-001",
            plan_id=plan.id,
            rule_type="dose_review",
            condition={"lab": "neutrophils", "operator": "<", "value": 1.0},
            severity="high",
        )
        db_session.add(rule)
        await db_session.commit()

        await db_session.refresh(plan)
        assert len(plan.safety_rules) == 1
        assert plan.safety_rules[0].rule_id == "tp-rule-001"

    async def test_traces_relation(self, db_session, patient) -> None:
        """Plan can be linked to trace records."""
        from src.backend.domain.treatment_plan import (
            TreatmentPlanModel,
            TreatmentPlanTraceModel,
        )

        plan = TreatmentPlanModel(
            plan_id="tp-trace-rel",
            patient_id=patient.id,
        )
        db_session.add(plan)
        await db_session.flush()

        trace = TreatmentPlanTraceModel(
            trace_id="tp-trace-001",
            plan_id=plan.id,
            step_order=1,
            step_type="load_context",
        )
        db_session.add(trace)
        await db_session.commit()

        await db_session.refresh(plan)
        assert len(plan.traces) == 1
        assert plan.traces[0].trace_id == "tp-trace-001"

    async def test_cascade_delete_plan_deletes_children(self, db_session, patient) -> None:
        """Deleting a TreatmentPlanModel cascade-deletes all child records."""
        from src.backend.domain.treatment_plan import (
            TreatmentItemModel,
            TreatmentMonitoringModel,
            TreatmentPhaseModel,
            TreatmentPlanModel,
            TreatmentPlanTraceModel,
            TreatmentSafetyRuleModel,
        )

        plan = TreatmentPlanModel(
            plan_id="tp-cascade-del",
            patient_id=patient.id,
        )
        db_session.add(plan)
        await db_session.flush()

        # Add one of each child type
        phase = TreatmentPhaseModel(
            phase_id="tp-cas-phase", plan_id=plan.id, phase_order=1,
            phase_type="test", name="Test Phase",
        )
        db_session.add(phase)

        item = TreatmentItemModel(
            item_id="tp-cas-item", plan_id=plan.id, item_order=1,
            item_type="test", name="Test Item",
        )
        db_session.add(item)

        mon = TreatmentMonitoringModel(
            monitoring_id="tp-cas-mon", plan_id=plan.id,
            monitoring_type="test", name="Test Monitor",
        )
        db_session.add(mon)

        rule = TreatmentSafetyRuleModel(
            rule_id="tp-cas-rule", plan_id=plan.id,
            rule_type="test", condition={}, severity="low",
        )
        db_session.add(rule)

        trace = TreatmentPlanTraceModel(
            trace_id="tp-cas-trace", plan_id=plan.id,
            step_order=1, step_type="test",
        )
        db_session.add(trace)
        await db_session.commit()

        # Delete the plan
        await db_session.delete(plan)
        await db_session.commit()

        # Verify all children are gone
        for model_cls, id_field, id_val in [
            (TreatmentPhaseModel, TreatmentPhaseModel.phase_id, "tp-cas-phase"),
            (TreatmentItemModel, TreatmentItemModel.item_id, "tp-cas-item"),
            (TreatmentMonitoringModel, TreatmentMonitoringModel.monitoring_id, "tp-cas-mon"),
            (TreatmentSafetyRuleModel, TreatmentSafetyRuleModel.rule_id, "tp-cas-rule"),
            (TreatmentPlanTraceModel, TreatmentPlanTraceModel.trace_id, "tp-cas-trace"),
        ]:
            stmt = select(model_cls).where(id_field == id_val)
            result = await db_session.execute(stmt)
            assert result.scalar_one_or_none() is None, f"{model_cls.__name__} was not cascade-deleted"

    async def test_relations_empty_by_default(self, db_session, patient) -> None:
        """New plan should have empty relations."""
        from src.backend.domain.treatment_plan import TreatmentPlanModel

        plan = TreatmentPlanModel(
            plan_id="tp-empty-rels",
            patient_id=patient.id,
        )
        db_session.add(plan)
        await db_session.commit()
        await db_session.refresh(plan)

        assert plan.phases == []
        assert plan.items == []
        assert plan.monitoring == []
        assert plan.safety_rules == []
        assert plan.traces == []


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentPhaseModel Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTreatmentPhaseModel:
    """Tests for TreatmentPhaseModel — fields, FK, JSON."""

    async def test_create_all_fields(self, db_session, patient) -> None:
        """TreatmentPhaseModel can be created with all fields."""
        from src.backend.domain.treatment_plan import (
            TreatmentPhaseModel,
            TreatmentPlanModel,
        )

        plan = TreatmentPlanModel(plan_id="tp-phase-create", patient_id=patient.id)
        db_session.add(plan)
        await db_session.flush()

        phase = TreatmentPhaseModel(
            phase_id="phase-all-fields",
            plan_id=plan.id,
            phase_order=2,
            phase_type="consolidation",
            name="Consolidation Therapy",
            description="Follow-up consolidation phase",
            duration_days=90,
            status="planned",
            entry_criteria={"ecog_status": "<=2"},
            exit_criteria={"no_progression": True},
        )
        db_session.add(phase)
        await db_session.commit()
        await db_session.refresh(phase)

        assert phase.id is not None
        assert phase.phase_id == "phase-all-fields"
        assert phase.phase_order == 2
        assert phase.phase_type == "consolidation"
        assert phase.name == "Consolidation Therapy"
        assert phase.duration_days == 90
        assert phase.entry_criteria == {"ecog_status": "<=2"}
        assert phase.exit_criteria == {"no_progression": True}

    async def test_default_values(self, db_session, patient) -> None:
        """Phase should have sensible defaults."""
        from src.backend.domain.treatment_plan import (
            TreatmentPhaseModel,
            TreatmentPlanModel,
        )

        plan = TreatmentPlanModel(plan_id="tp-phase-default", patient_id=patient.id)
        db_session.add(plan)
        await db_session.flush()

        phase = TreatmentPhaseModel(
            phase_id="phase-defaults",
            plan_id=plan.id,
            phase_order=1,
            phase_type="test",
            name="Test Phase",
        )
        db_session.add(phase)
        await db_session.commit()
        await db_session.refresh(phase)

        assert phase.status == "planned"
        assert phase.duration_days is None
        assert phase.entry_criteria is None
        assert phase.exit_criteria is None

    async def test_plan_back_populates(self, db_session, patient) -> None:
        """Phase back-populates plan."""
        from src.backend.domain.treatment_plan import (
            TreatmentPhaseModel,
            TreatmentPlanModel,
        )

        plan = TreatmentPlanModel(plan_id="tp-phase-backpop", patient_id=patient.id)
        db_session.add(plan)
        await db_session.flush()

        phase = TreatmentPhaseModel(
            phase_id="phase-backpop",
            plan_id=plan.id,
            phase_order=1,
            phase_type="test",
            name="Backpop Phase",
        )
        db_session.add(phase)
        await db_session.commit()

        assert phase.plan is not None
        assert phase.plan.plan_id == "tp-phase-backpop"

    async def test_items_relation(self, db_session, patient) -> None:
        """Phase can be linked to items."""
        from src.backend.domain.treatment_plan import (
            TreatmentItemModel,
            TreatmentPhaseModel,
            TreatmentPlanModel,
        )

        plan = TreatmentPlanModel(plan_id="tp-phase-items", patient_id=patient.id)
        db_session.add(plan)
        await db_session.flush()

        phase = TreatmentPhaseModel(
            phase_id="phase-items-rel",
            plan_id=plan.id,
            phase_order=1,
            phase_type="test",
            name="Phase with Items",
        )
        db_session.add(phase)
        await db_session.flush()

        item = TreatmentItemModel(
            item_id="item-in-phase",
            plan_id=plan.id,
            phase_id=phase.id,
            item_order=1,
            item_type="medication",
            name="Drug A",
        )
        db_session.add(item)
        await db_session.commit()

        await db_session.refresh(phase)
        assert len(phase.items) == 1
        assert phase.items[0].item_id == "item-in-phase"


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentItemModel Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTreatmentItemModel:
    """Tests for TreatmentItemModel — fields, FK, JSON."""

    async def test_create_all_fields(self, db_session, patient) -> None:
        """TreatmentItemModel can be created with all fields."""
        from src.backend.domain.treatment_plan import (
            TreatmentItemModel,
            TreatmentPlanModel,
        )

        plan = TreatmentPlanModel(plan_id="tp-item-create", patient_id=patient.id)
        db_session.add(plan)
        await db_session.flush()

        item = TreatmentItemModel(
            item_id="item-all-fields",
            plan_id=plan.id,
            item_order=3,
            item_type="procedure",
            name="CT Scan",
            description="Chest CT with contrast",
            frequency="Every 3 months",
            duration="30 min",
            priority=1,
            status="planned",
            rationale="Monitor tumor response",
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        assert item.id is not None
        assert item.item_id == "item-all-fields"
        assert item.item_order == 3
        assert item.item_type == "procedure"
        assert item.name == "CT Scan"
        assert item.frequency == "Every 3 months"
        assert item.priority == 1

    async def test_default_values(self, db_session, patient) -> None:
        """Item should have sensible defaults."""
        from src.backend.domain.treatment_plan import (
            TreatmentItemModel,
            TreatmentPlanModel,
        )

        plan = TreatmentPlanModel(plan_id="tp-item-default", patient_id=patient.id)
        db_session.add(plan)
        await db_session.flush()

        item = TreatmentItemModel(
            item_id="item-defaults",
            plan_id=plan.id,
            item_order=1,
            item_type="medication",
            name="Default Item",
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        assert item.status == "planned"
        assert item.drug_id is None
        assert item.procedure_code is None
        assert item.priority is None

    async def test_plan_phase_back_populates(self, db_session, patient) -> None:
        """Item back-populates plan and phase."""
        from src.backend.domain.treatment_plan import (
            TreatmentItemModel,
            TreatmentPhaseModel,
            TreatmentPlanModel,
        )

        plan = TreatmentPlanModel(plan_id="tp-item-backpop", patient_id=patient.id)
        db_session.add(plan)
        await db_session.flush()

        phase = TreatmentPhaseModel(
            phase_id="phase-item-backpop",
            plan_id=plan.id,
            phase_order=1,
            phase_type="test",
            name="Phase",
        )
        db_session.add(phase)
        await db_session.flush()

        item = TreatmentItemModel(
            item_id="item-backpop",
            plan_id=plan.id,
            phase_id=phase.id,
            item_order=1,
            item_type="medication",
            name="Item",
        )
        db_session.add(item)
        await db_session.commit()

        assert item.plan is not None
        assert item.plan.plan_id == "tp-item-backpop"
        assert item.phase is not None
        assert item.phase.phase_id == "phase-item-backpop"


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentMonitoringModel Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTreatmentMonitoringModel:
    """Tests for TreatmentMonitoringModel — fields, FK, JSON."""

    async def test_create_all_fields(self, db_session, patient) -> None:
        """TreatmentMonitoringModel can be created with all fields."""
        from src.backend.domain.treatment_plan import (
            TreatmentMonitoringModel,
            TreatmentPlanModel,
        )

        plan = TreatmentPlanModel(plan_id="tp-mon-create", patient_id=patient.id)
        db_session.add(plan)
        await db_session.flush()

        mon = TreatmentMonitoringModel(
            monitoring_id="mon-all-fields",
            plan_id=plan.id,
            monitoring_type="laboratory",
            name="CBC with differential",
            schedule="Weekly",
            target_range={"WBC": "4.0-11.0", "Hemoglobin": "12-16"},
            warning_threshold={"WBC": "<3.0"},
            critical_threshold={"WBC": "<1.0"},
            action_if_abnormal="Hold chemotherapy and notify MD",
            baseline_required=True,
            repeat_interval="1 week",
            responsible_specialty="hematology",
        )
        db_session.add(mon)
        await db_session.commit()
        await db_session.refresh(mon)

        assert mon.id is not None
        assert mon.monitoring_id == "mon-all-fields"
        assert mon.monitoring_type == "laboratory"
        assert mon.name == "CBC with differential"
        assert mon.schedule == "Weekly"
        assert mon.target_range == {"WBC": "4.0-11.0", "Hemoglobin": "12-16"}
        assert mon.baseline_required is True
        assert mon.responsible_specialty == "hematology"

    async def test_default_values(self, db_session, patient) -> None:
        """Monitoring should have sensible defaults."""
        from src.backend.domain.treatment_plan import (
            TreatmentMonitoringModel,
            TreatmentPlanModel,
        )

        plan = TreatmentPlanModel(plan_id="tp-mon-default", patient_id=patient.id)
        db_session.add(plan)
        await db_session.flush()

        mon = TreatmentMonitoringModel(
            monitoring_id="mon-defaults",
            plan_id=plan.id,
            monitoring_type="imaging",
            name="Chest X-ray",
        )
        db_session.add(mon)
        await db_session.commit()
        await db_session.refresh(mon)

        assert mon.baseline_required is False
        assert mon.schedule is None
        assert mon.target_range is None
        assert mon.action_if_abnormal is None

    async def test_json_fields_round_trip(self, db_session, patient) -> None:
        """JSON fields on monitoring survive write-read."""
        from src.backend.domain.treatment_plan import (
            TreatmentMonitoringModel,
            TreatmentPlanModel,
        )

        plan = TreatmentPlanModel(plan_id="tp-mon-json", patient_id=patient.id)
        db_session.add(plan)
        await db_session.flush()

        target = {"WBC": "4.0-11.0", "ANC": ">1.5", "Platelets": ">100"}
        warning = {"WBC": "<3.0", "ANC": "<1.0"}
        critical = {"WBC": "<1.0", "ANC": "<0.5", "Platelets": "<50"}

        mon = TreatmentMonitoringModel(
            monitoring_id="mon-json-rt",
            plan_id=plan.id,
            monitoring_type="laboratory",
            name="Full Blood Count",
            target_range=target,
            warning_threshold=warning,
            critical_threshold=critical,
        )
        db_session.add(mon)
        await db_session.commit()
        await db_session.refresh(mon)

        assert mon.target_range == target
        assert mon.warning_threshold == warning
        assert mon.critical_threshold == critical


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentSafetyRuleModel Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTreatmentSafetyRuleModel:
    """Tests for TreatmentSafetyRuleModel — fields, FK, JSON."""

    async def test_create_all_fields(self, db_session, patient) -> None:
        """TreatmentSafetyRuleModel can be created with all fields."""
        from src.backend.domain.treatment_plan import (
            TreatmentPlanModel,
            TreatmentSafetyRuleModel,
        )

        plan = TreatmentPlanModel(plan_id="tp-rule-create", patient_id=patient.id)
        db_session.add(plan)
        await db_session.flush()

        rule = TreatmentSafetyRuleModel(
            rule_id="rule-all-fields",
            plan_id=plan.id,
            rule_type="pause",
            condition={"lab": "neutrophils", "operator": "<", "value": 1.0},
            severity="high",
            recommended_action="Hold treatment until ANC recovers",
            requires_review=True,
            source="NCCN Guidelines v3.2024",
        )
        db_session.add(rule)
        await db_session.commit()
        await db_session.refresh(rule)

        assert rule.id is not None
        assert rule.rule_id == "rule-all-fields"
        assert rule.rule_type == "pause"
        assert rule.condition == {"lab": "neutrophils", "operator": "<", "value": 1.0}
        assert rule.severity == "high"
        assert rule.requires_review is True
        assert rule.source == "NCCN Guidelines v3.2024"

    async def test_default_values(self, db_session, patient) -> None:
        """Safety rule should have sensible defaults."""
        from src.backend.domain.treatment_plan import (
            TreatmentPlanModel,
            TreatmentSafetyRuleModel,
        )

        plan = TreatmentPlanModel(plan_id="tp-rule-default", patient_id=patient.id)
        db_session.add(plan)
        await db_session.flush()

        rule = TreatmentSafetyRuleModel(
            rule_id="rule-defaults",
            plan_id=plan.id,
            rule_type="dose_review",
            condition={},
        )
        db_session.add(rule)
        await db_session.commit()
        await db_session.refresh(rule)

        assert rule.severity == "medium"
        assert rule.requires_review is True
        assert rule.recommended_action is None
        assert rule.source is None

    async def test_json_fields_round_trip(self, db_session, patient) -> None:
        """Condition JSON on safety rule survives write-read."""
        from src.backend.domain.treatment_plan import (
            TreatmentPlanModel,
            TreatmentSafetyRuleModel,
        )

        plan = TreatmentPlanModel(plan_id="tp-rule-json", patient_id=patient.id)
        db_session.add(plan)
        await db_session.flush()

        complex_condition = {
            "and": [
                {"lab": "neutrophils", "operator": "<", "value": 1.0},
                {"lab": "platelets", "operator": "<", "value": 50},
            ],
            "time_window_hours": 48,
        }

        rule = TreatmentSafetyRuleModel(
            rule_id="rule-json-rt",
            plan_id=plan.id,
            rule_type="stop",
            condition=complex_condition,
            severity="critical",
        )
        db_session.add(rule)
        await db_session.commit()
        await db_session.refresh(rule)

        assert rule.condition == complex_condition
        assert rule.condition["and"][0]["lab"] == "neutrophils"
        assert rule.severity == "critical"


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentPlanTraceModel Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTreatmentPlanTraceModel:
    """Tests for TreatmentPlanTraceModel — fields, FK, JSON."""

    async def test_create_all_fields(self, db_session, patient) -> None:
        """TreatmentPlanTraceModel can be created with all fields."""
        from src.backend.domain.treatment_plan import (
            TreatmentPlanModel,
            TreatmentPlanTraceModel,
        )

        plan = TreatmentPlanModel(plan_id="tp-trace-create", patient_id=patient.id)
        db_session.add(plan)
        await db_session.flush()

        trace = TreatmentPlanTraceModel(
            trace_id="trace-all-fields",
            plan_id=plan.id,
            step_order=2,
            step_type="generate_plan",
            input_summary={"phase_count": 3, "item_count": 10},
            output_summary={"plan_id": "generated-plan-001", "status": "draft"},
            rule_ids=["rule-001", "rule-002"],
            evidence_ids=["ev-001"],
        )
        db_session.add(trace)
        await db_session.commit()
        await db_session.refresh(trace)

        assert trace.id is not None
        assert trace.trace_id == "trace-all-fields"
        assert trace.step_order == 2
        assert trace.step_type == "generate_plan"
        assert trace.input_summary == {"phase_count": 3, "item_count": 10}
        assert trace.output_summary == {"plan_id": "generated-plan-001", "status": "draft"}
        assert trace.rule_ids == ["rule-001", "rule-002"]
        assert trace.evidence_ids == ["ev-001"]

    async def test_default_values(self, db_session, patient) -> None:
        """Trace should have sensible defaults."""
        from src.backend.domain.treatment_plan import (
            TreatmentPlanModel,
            TreatmentPlanTraceModel,
        )

        plan = TreatmentPlanModel(plan_id="tp-trace-default", patient_id=patient.id)
        db_session.add(plan)
        await db_session.flush()

        trace = TreatmentPlanTraceModel(
            trace_id="trace-defaults",
            plan_id=plan.id,
            step_order=1,
            step_type="load_context",
        )
        db_session.add(trace)
        await db_session.commit()
        await db_session.refresh(trace)

        assert trace.input_summary is None
        assert trace.output_summary is None
        assert trace.rule_ids is None
        assert trace.evidence_ids is None

    async def test_json_fields_round_trip(self, db_session, patient) -> None:
        """JSON fields on trace survive write-read."""
        from src.backend.domain.treatment_plan import (
            TreatmentPlanModel,
            TreatmentPlanTraceModel,
        )

        plan = TreatmentPlanModel(plan_id="tp-trace-json-rt", patient_id=patient.id)
        db_session.add(plan)
        await db_session.flush()

        complex_input = {
            "patient": {"age": 65, "cancer_type": "NSCLC", "stage": "IIIB"},
            "guidelines": ["NCCN-2024", "ESMO-2023"],
            "contraindications": [{"drug": "Pembrolizumab", "reason": "PD-L1 negative"}],
        }
        complex_output = {
            "phases": ["induction", "consolidation"],
            "total_duration_days": 180,
            "warnings": ["Monitor liver function"],
        }

        trace = TreatmentPlanTraceModel(
            trace_id="trace-json-rt",
            plan_id=plan.id,
            step_order=1,
            step_type="plan_generation",
            input_summary=complex_input,
            output_summary=complex_output,
            rule_ids=["R1", "R2"],
            evidence_ids=["E1", "E2", "E3"],
        )
        db_session.add(trace)
        await db_session.commit()
        await db_session.refresh(trace)

        assert trace.input_summary == complex_input
        assert trace.input_summary["patient"]["cancer_type"] == "NSCLC"
        assert trace.output_summary == complex_output
        assert trace.output_summary["total_duration_days"] == 180
        assert trace.rule_ids == ["R1", "R2"]
        assert trace.evidence_ids == ["E1", "E2", "E3"]

    async def test_plan_back_populates(self, db_session, patient) -> None:
        """Trace back-populates plan."""
        from src.backend.domain.treatment_plan import (
            TreatmentPlanModel,
            TreatmentPlanTraceModel,
        )

        plan = TreatmentPlanModel(plan_id="tp-trace-backpop", patient_id=patient.id)
        db_session.add(plan)
        await db_session.flush()

        trace = TreatmentPlanTraceModel(
            trace_id="trace-backpop",
            plan_id=plan.id,
            step_order=1,
            step_type="test",
        )
        db_session.add(trace)
        await db_session.commit()

        assert trace.plan is not None
        assert trace.plan.plan_id == "tp-trace-backpop"
