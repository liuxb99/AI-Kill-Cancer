"""Phase 3G clinical safety gate coverage."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pytest

from src.backend.clinical.treatment_plan_safety_gate import (
    ClinicalSafetyGateError,
    SafetyGateLevel,
    TreatmentPlanSafetyGate,
)


@dataclass
class Item:
    item_id: str = "item-1"
    item_type: str = "medication"
    name: str = "Lenvatinib"
    planned_dose_text: str | None = "20 mg"
    route: str | None = "oral"
    frequency: str | None = "once daily"
    rationale: str | None = "Targeted systemic therapy"


@dataclass
class Monitor:
    monitoring_id: str = "mon-1"
    monitoring_type: str = "laboratory"
    name: str = "Liver function"
    schedule: str | None = "baseline and every 4 weeks"
    action_if_abnormal: str | None = "Hold treatment and reassess"
    baseline_required: bool = True


@dataclass
class Rule:
    rule_id: str = "rule-1"
    rule_type: str = "pause"
    condition: object = field(default_factory=lambda: {"ALT": ">5x ULN"})
    severity: str = "high"
    recommended_action: str | None = "Pause and investigate"
    requires_review: bool = False
    source: str | None = "Protocol v1"


@dataclass
class Plan:
    plan_id: str = "plan-1"
    plan_status: str = "under_review"
    summary: str | None = "Targeted treatment plan"
    clinical_rationale: str | None = "Evidence-supported option"
    approved_by: object | None = None
    approved_at: object | None = None
    items: list[Item] = field(default_factory=lambda: [Item()])
    monitoring: list[Monitor] = field(default_factory=lambda: [Monitor()])
    safety_rules: list[Rule] = field(default_factory=lambda: [Rule()])


def codes(report):
    return {finding.code for finding in report.findings}


def test_complete_plan_can_be_approved():
    report = TreatmentPlanSafetyGate().evaluate(Plan(), "approved")
    assert report.can_transition is True
    assert report.blockers == ()


def test_activation_requires_approval_attestation():
    report = TreatmentPlanSafetyGate().evaluate(Plan(), "active")
    assert report.can_transition is False
    assert "PLAN_APPROVAL_ATTESTATION_MISSING" in codes(report)


def test_approved_plan_can_be_activated():
    plan = Plan(approved_by="doctor-1", approved_at=datetime.utcnow())
    report = TreatmentPlanSafetyGate().evaluate(plan, "active")
    assert report.can_transition is True


def test_plan_without_items_is_blocked():
    report = TreatmentPlanSafetyGate().evaluate(Plan(items=[]), "approved")
    assert "PLAN_NO_TREATMENT_ITEMS" in codes(report)


def test_clinical_rationale_is_required():
    report = TreatmentPlanSafetyGate().evaluate(
        Plan(clinical_rationale="  "), "approved"
    )
    assert "PLAN_MISSING_CLINICAL_RATIONALE" in codes(report)


def test_missing_summary_is_warning_only():
    report = TreatmentPlanSafetyGate().evaluate(Plan(summary=None), "approved")
    assert report.can_transition is True
    assert report.warnings[0].level == SafetyGateLevel.WARNING
    assert "PLAN_MISSING_SUMMARY" in codes(report)


@pytest.mark.parametrize("field", ["planned_dose_text", "route", "frequency"])
def test_medication_administration_fields_are_required(field):
    item = Item()
    setattr(item, field, None)
    report = TreatmentPlanSafetyGate().evaluate(Plan(items=[item]), "approved")
    assert "MEDICATION_ADMINISTRATION_INCOMPLETE" in codes(report)


def test_medication_requires_monitoring():
    report = TreatmentPlanSafetyGate().evaluate(Plan(monitoring=[]), "approved")
    assert "MEDICATION_MONITORING_MISSING" in codes(report)


def test_non_medication_item_does_not_require_monitoring():
    item = Item(item_type="procedure", planned_dose_text=None, route=None, frequency=None)
    report = TreatmentPlanSafetyGate().evaluate(
        Plan(items=[item], monitoring=[]), "approved"
    )
    assert report.can_transition is True


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("schedule", "MONITORING_SCHEDULE_MISSING"),
        ("action_if_abnormal", "MONITORING_ACTION_MISSING"),
    ],
)
def test_monitoring_is_actionable(field, expected):
    monitor = Monitor()
    setattr(monitor, field, "")
    report = TreatmentPlanSafetyGate().evaluate(
        Plan(monitoring=[monitor]), "approved"
    )
    assert expected in codes(report)


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("condition", "HIGH_SEVERITY_RULE_CONDITION_MISSING"),
        ("recommended_action", "HIGH_SEVERITY_RULE_ACTION_MISSING"),
        ("source", "HIGH_SEVERITY_RULE_SOURCE_MISSING"),
    ],
)
def test_high_severity_rules_are_complete_and_traceable(field, expected):
    rule = Rule()
    setattr(rule, field, None)
    report = TreatmentPlanSafetyGate().evaluate(
        Plan(safety_rules=[rule]), "approved"
    )
    assert expected in codes(report)


def test_low_severity_rule_does_not_require_full_provenance():
    rule = Rule(
        severity="low", condition=None, recommended_action=None, source=None
    )
    report = TreatmentPlanSafetyGate().evaluate(
        Plan(safety_rules=[rule]), "approved"
    )
    assert report.can_transition is True


def test_required_review_is_visible_on_activation():
    plan = Plan(
        approved_by="doctor-1",
        approved_at=datetime.utcnow(),
        safety_rules=[Rule(requires_review=True)],
    )
    report = TreatmentPlanSafetyGate().evaluate(plan, "active")
    assert report.can_transition is True
    assert "SAFETY_REVIEW_ATTESTATION_REQUIRED" in codes(report)


def test_unrelated_transition_is_not_blocked():
    empty = Plan(items=[], monitoring=[], safety_rules=[], clinical_rationale=None)
    report = TreatmentPlanSafetyGate().evaluate(empty, "cancelled")
    assert report.can_transition is True
    assert report.findings == ()


def test_assert_can_transition_exposes_machine_readable_report():
    with pytest.raises(ClinicalSafetyGateError) as exc_info:
        TreatmentPlanSafetyGate().assert_can_transition(
            Plan(items=[]), "approved"
        )

    report = exc_info.value.report
    payload = report.as_dict()
    assert payload["can_transition"] is False
    assert payload["target_status"] == "approved"
    assert payload["blockers"][0]["code"] == "PLAN_NO_TREATMENT_ITEMS"
