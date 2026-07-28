"""
Treatment Plan domain models — Phase 3E treatment plan engine V1.

Defines the complete treatment plan data model including phases, items,
monitoring schedules, safety rules, and the reasoning trace that produced
the plan. All models follow the existing domain conventions.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from src.backend.database.models import Base as DBBase
from src.backend.database.models import CompatUUID


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class TreatmentPlanModel(DBBase):
    __tablename__ = "domain_treatment_plans"
    __table_args__ = (
        UniqueConstraint("plan_id", "version", name="uq_plan_id_version"),
    )

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    plan_id = Column(String(64), nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    patient_id = Column(
        CompatUUID,
        ForeignKey("domain_patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recommendation_id = Column(
        CompatUUID,
        ForeignKey("domain_recommendations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    clinical_decision_id = Column(
        CompatUUID,
        ForeignKey("domain_clinical_decisions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    consensus_id = Column(
        CompatUUID,
        ForeignKey("domain_tumor_board_consensus.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    plan_status = Column(String(32), nullable=False, default="draft")
    plan_intent = Column(String(256), nullable=True)
    treatment_goals = Column(JSON, nullable=True)
    summary = Column(Text, nullable=True)
    clinical_rationale = Column(Text, nullable=True)
    alternative_options = Column(JSON, nullable=True)
    start_date = Column(DateTime, nullable=True)
    target_end_date = Column(DateTime, nullable=True)
    review_date = Column(DateTime, nullable=True)
    previous_plan_id = Column(String(64), nullable=True, index=True)
    supersedes_plan_id = Column(String(64), nullable=True, index=True)
    is_current = Column(Boolean, default=True, nullable=False)
    revision_reason = Column(Text, nullable=True)
    created_by = Column(CompatUUID, ForeignKey("domain_users.id", ondelete="SET NULL"), nullable=True)
    approved_by = Column(CompatUUID, ForeignKey("domain_users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    activated_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    phases = relationship(
        "TreatmentPhaseModel",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    items = relationship(
        "TreatmentItemModel",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    monitoring = relationship(
        "TreatmentMonitoringModel",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    safety_rules = relationship(
        "TreatmentSafetyRuleModel",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    traces = relationship(
        "TreatmentPlanTraceModel",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self):
        return (
            f"<TreatmentPlanModel(id={self.id}, "
            f"plan_id={self.plan_id!r}, "
            f"version={self.version}, "
            f"plan_status={self.plan_status!r})>"
        )


class TreatmentPhaseModel(DBBase):
    __tablename__ = "domain_treatment_phases"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    phase_id = Column(String(64), unique=True, nullable=False, index=True)
    plan_id = Column(
        CompatUUID,
        ForeignKey("domain_treatment_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phase_order = Column(Integer, nullable=False)
    phase_type = Column(String(32), nullable=False)  # preparation, induction, primary_treatment, etc.
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    planned_start = Column(DateTime, nullable=True)
    planned_end = Column(DateTime, nullable=True)
    duration_days = Column(Integer, nullable=True)
    status = Column(String(32), nullable=False, default="planned")
    entry_criteria = Column(JSON, nullable=True)
    exit_criteria = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    plan = relationship("TreatmentPlanModel", back_populates="phases", lazy="selectin")
    items = relationship(
        "TreatmentItemModel",
        back_populates="phase",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self):
        return (
            f"<TreatmentPhaseModel(id={self.id}, "
            f"phase_id={self.phase_id!r}, "
            f"phase_type={self.phase_type!r}, "
            f"phase_order={self.phase_order})>"
        )


class TreatmentItemModel(DBBase):
    __tablename__ = "domain_treatment_items"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    item_id = Column(String(64), unique=True, nullable=False, index=True)
    plan_id = Column(
        CompatUUID,
        ForeignKey("domain_treatment_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phase_id = Column(
        CompatUUID,
        ForeignKey("domain_treatment_phases.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    item_order = Column(Integer, nullable=False)
    item_type = Column(String(32), nullable=False)  # medication, procedure, radiation, etc.
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    drug_id = Column(String(64), nullable=True)
    procedure_code = Column(String(64), nullable=True)
    frequency = Column(String(128), nullable=True)
    duration = Column(String(128), nullable=True)
    route = Column(String(64), nullable=True)
    planned_dose_text = Column(Text, nullable=True)
    priority = Column(Integer, nullable=True)
    status = Column(String(32), nullable=False, default="planned")
    rationale = Column(Text, nullable=True)
    source_recommendation = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    plan = relationship("TreatmentPlanModel", back_populates="items", lazy="selectin")
    phase = relationship("TreatmentPhaseModel", back_populates="items", lazy="selectin")

    def __repr__(self):
        return (
            f"<TreatmentItemModel(id={self.id}, "
            f"item_id={self.item_id!r}, "
            f"item_type={self.item_type!r}, "
            f"item_order={self.item_order})>"
        )


class TreatmentMonitoringModel(DBBase):
    __tablename__ = "domain_treatment_monitoring"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    monitoring_id = Column(String(64), unique=True, nullable=False, index=True)
    plan_id = Column(
        CompatUUID,
        ForeignKey("domain_treatment_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phase_id = Column(
        CompatUUID,
        ForeignKey("domain_treatment_phases.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    item_id = Column(
        CompatUUID,
        ForeignKey("domain_treatment_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    monitoring_type = Column(String(32), nullable=False)  # laboratory, imaging, symptom, etc.
    name = Column(String(256), nullable=False)
    schedule = Column(String(256), nullable=True)
    target_range = Column(JSON, nullable=True)
    warning_threshold = Column(JSON, nullable=True)
    critical_threshold = Column(JSON, nullable=True)
    action_if_abnormal = Column(Text, nullable=True)
    baseline_required = Column(Boolean, default=False, nullable=False)
    repeat_interval = Column(String(64), nullable=True)
    responsible_specialty = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    plan = relationship("TreatmentPlanModel", back_populates="monitoring", lazy="selectin")

    def __repr__(self):
        return (
            f"<TreatmentMonitoringModel(id={self.id}, "
            f"monitoring_id={self.monitoring_id!r}, "
            f"monitoring_type={self.monitoring_type!r})>"
        )


class TreatmentSafetyRuleModel(DBBase):
    __tablename__ = "domain_treatment_safety_rules"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    rule_id = Column(String(64), unique=True, nullable=False, index=True)
    plan_id = Column(
        CompatUUID,
        ForeignKey("domain_treatment_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phase_id = Column(
        CompatUUID,
        ForeignKey("domain_treatment_phases.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    item_id = Column(
        CompatUUID,
        ForeignKey("domain_treatment_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rule_type = Column(String(32), nullable=False)  # pause, stop, dose_review, etc.
    condition = Column(JSON, nullable=True)
    severity = Column(String(32), nullable=False, default="medium")
    recommended_action = Column(Text, nullable=True)
    requires_review = Column(Boolean, default=True, nullable=False)
    source = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    plan = relationship("TreatmentPlanModel", back_populates="safety_rules", lazy="selectin")

    def __repr__(self):
        return (
            f"<TreatmentSafetyRuleModel(id={self.id}, "
            f"rule_id={self.rule_id!r}, "
            f"rule_type={self.rule_type!r}, "
            f"severity={self.severity!r})>"
        )


class TreatmentPlanTraceModel(DBBase):
    __tablename__ = "domain_treatment_plan_traces"
    __table_args__ = (
        UniqueConstraint("trace_id", "step_order", name="uq_trace_step"),
    )

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    trace_id = Column(String(64), nullable=False, index=True)
    plan_id = Column(
        CompatUUID,
        ForeignKey("domain_treatment_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_order = Column(Integer, nullable=False)
    step_type = Column(String(64), nullable=False)
    input_summary = Column(JSON, nullable=True)
    output_summary = Column(JSON, nullable=True)
    rule_ids = Column(JSON, nullable=True)
    evidence_ids = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    plan = relationship("TreatmentPlanModel", back_populates="traces", lazy="selectin")

    def __repr__(self):
        return (
            f"<TreatmentPlanTraceModel(id={self.id}, "
            f"trace_id={self.trace_id!r}, "
            f"step_order={self.step_order}, "
            f"step_type={self.step_type!r})>"
        )
