"""Clinical safety gate for treatment-plan lifecycle transitions.

The gate is deliberately framework independent.  It evaluates an already
materialised treatment-plan aggregate and returns a deterministic report that
can be persisted, rendered by an API, or used to block unsafe transitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Iterable, Protocol, Sequence


class SafetyGateLevel(StrEnum):
    BLOCKER = "blocker"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class SafetyGateFinding:
    code: str
    level: SafetyGateLevel
    message: str
    subject_id: str | None = None


@dataclass(frozen=True, slots=True)
class SafetyGateReport:
    target_status: str
    findings: tuple[SafetyGateFinding, ...]

    @property
    def blockers(self) -> tuple[SafetyGateFinding, ...]:
        return tuple(f for f in self.findings if f.level == SafetyGateLevel.BLOCKER)

    @property
    def warnings(self) -> tuple[SafetyGateFinding, ...]:
        return tuple(f for f in self.findings if f.level == SafetyGateLevel.WARNING)

    @property
    def can_transition(self) -> bool:
        return not self.blockers

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_status": self.target_status,
            "can_transition": self.can_transition,
            "blockers": [finding_to_dict(f) for f in self.blockers],
            "warnings": [finding_to_dict(f) for f in self.warnings],
        }


class ClinicalSafetyGateError(ValueError):
    """Raised when a treatment plan fails a safety transition gate."""

    def __init__(self, report: SafetyGateReport) -> None:
        self.report = report
        codes = ", ".join(f.code for f in report.blockers)
        super().__init__(
            f"Treatment plan cannot transition to '{report.target_status}': {codes}"
        )


class TreatmentItemView(Protocol):
    item_id: str
    item_type: str
    name: str
    planned_dose_text: str | None
    route: str | None
    frequency: str | None
    rationale: str | None


class MonitoringView(Protocol):
    monitoring_id: str
    monitoring_type: str
    name: str
    schedule: str | None
    action_if_abnormal: str | None
    baseline_required: bool


class SafetyRuleView(Protocol):
    rule_id: str
    rule_type: str
    condition: Any
    severity: str
    recommended_action: str | None
    requires_review: bool
    source: str | None


class TreatmentPlanView(Protocol):
    plan_id: str
    plan_status: str
    summary: str | None
    clinical_rationale: str | None
    approved_by: Any
    approved_at: Any
    items: Sequence[TreatmentItemView]
    monitoring: Sequence[MonitoringView]
    safety_rules: Sequence[SafetyRuleView]


def finding_to_dict(finding: SafetyGateFinding) -> dict[str, str | None]:
    return {
        "code": finding.code,
        "level": finding.level.value,
        "message": finding.message,
        "subject_id": finding.subject_id,
    }


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _iter(value: Any) -> Iterable[Any]:
    return value if isinstance(value, (list, tuple)) else ()


class TreatmentPlanSafetyGate:
    """Evaluate approval and activation readiness for a treatment plan."""

    _HIGH_SEVERITIES = frozenset({"high", "critical"})
    _MEDICATION_TYPES = frozenset({"medication", "drug", "systemic_therapy"})

    def evaluate(self, plan: TreatmentPlanView, target_status: str) -> SafetyGateReport:
        target = _text(target_status).lower()
        if target not in {"approved", "active"}:
            return SafetyGateReport(target_status=target, findings=())

        findings: list[SafetyGateFinding] = []
        items = tuple(_iter(getattr(plan, "items", ())))
        monitoring = tuple(_iter(getattr(plan, "monitoring", ())))
        safety_rules = tuple(_iter(getattr(plan, "safety_rules", ())))

        if not items:
            findings.append(
                SafetyGateFinding(
                    code="PLAN_NO_TREATMENT_ITEMS",
                    level=SafetyGateLevel.BLOCKER,
                    message="A plan must contain at least one treatment item.",
                )
            )

        if not _text(getattr(plan, "clinical_rationale", None)):
            findings.append(
                SafetyGateFinding(
                    code="PLAN_MISSING_CLINICAL_RATIONALE",
                    level=SafetyGateLevel.BLOCKER,
                    message="Clinical rationale is required before approval.",
                )
            )

        if not _text(getattr(plan, "summary", None)):
            findings.append(
                SafetyGateFinding(
                    code="PLAN_MISSING_SUMMARY",
                    level=SafetyGateLevel.WARNING,
                    message="A concise treatment-plan summary should be recorded.",
                )
            )

        medication_items = [
            item
            for item in items
            if _text(getattr(item, "item_type", None)).lower() in self._MEDICATION_TYPES
        ]
        for item in medication_items:
            item_id = _text(getattr(item, "item_id", None)) or None
            missing = [
                field
                for field in ("planned_dose_text", "route", "frequency")
                if not _text(getattr(item, field, None))
            ]
            if missing:
                findings.append(
                    SafetyGateFinding(
                        code="MEDICATION_ADMINISTRATION_INCOMPLETE",
                        level=SafetyGateLevel.BLOCKER,
                        message="Medication administration fields are incomplete: "
                        + ", ".join(missing),
                        subject_id=item_id,
                    )
                )

        if medication_items and not monitoring:
            findings.append(
                SafetyGateFinding(
                    code="MEDICATION_MONITORING_MISSING",
                    level=SafetyGateLevel.BLOCKER,
                    message="Medication treatment requires a monitoring plan.",
                )
            )

        for monitor in monitoring:
            monitor_id = _text(getattr(monitor, "monitoring_id", None)) or None
            if not _text(getattr(monitor, "schedule", None)):
                findings.append(
                    SafetyGateFinding(
                        code="MONITORING_SCHEDULE_MISSING",
                        level=SafetyGateLevel.BLOCKER,
                        message="Every monitoring requirement needs a schedule.",
                        subject_id=monitor_id,
                    )
                )
            if not _text(getattr(monitor, "action_if_abnormal", None)):
                findings.append(
                    SafetyGateFinding(
                        code="MONITORING_ACTION_MISSING",
                        level=SafetyGateLevel.BLOCKER,
                        message="Every monitoring requirement needs an abnormal-result action.",
                        subject_id=monitor_id,
                    )
                )

        for rule in safety_rules:
            severity = _text(getattr(rule, "severity", None)).lower()
            rule_id = _text(getattr(rule, "rule_id", None)) or None
            if severity not in self._HIGH_SEVERITIES:
                continue
            if not getattr(rule, "condition", None):
                findings.append(
                    SafetyGateFinding(
                        code="HIGH_SEVERITY_RULE_CONDITION_MISSING",
                        level=SafetyGateLevel.BLOCKER,
                        message="High-severity safety rules require an explicit condition.",
                        subject_id=rule_id,
                    )
                )
            if not _text(getattr(rule, "recommended_action", None)):
                findings.append(
                    SafetyGateFinding(
                        code="HIGH_SEVERITY_RULE_ACTION_MISSING",
                        level=SafetyGateLevel.BLOCKER,
                        message="High-severity safety rules require a recommended action.",
                        subject_id=rule_id,
                    )
                )
            if not _text(getattr(rule, "source", None)):
                findings.append(
                    SafetyGateFinding(
                        code="HIGH_SEVERITY_RULE_SOURCE_MISSING",
                        level=SafetyGateLevel.BLOCKER,
                        message="High-severity safety rules require a provenance source.",
                        subject_id=rule_id,
                    )
                )

        if target == "active":
            if not getattr(plan, "approved_by", None) or not getattr(plan, "approved_at", None):
                findings.append(
                    SafetyGateFinding(
                        code="PLAN_APPROVAL_ATTESTATION_MISSING",
                        level=SafetyGateLevel.BLOCKER,
                        message="Activation requires approver identity and approval timestamp.",
                    )
                )
            if any(bool(getattr(rule, "requires_review", False)) for rule in safety_rules):
                findings.append(
                    SafetyGateFinding(
                        code="SAFETY_REVIEW_ATTESTATION_REQUIRED",
                        level=SafetyGateLevel.WARNING,
                        message="One or more safety rules require explicit clinical review.",
                    )
                )

        return SafetyGateReport(target_status=target, findings=tuple(findings))

    def assert_can_transition(
        self, plan: TreatmentPlanView, target_status: str
    ) -> SafetyGateReport:
        report = self.evaluate(plan, target_status)
        if not report.can_transition:
            raise ClinicalSafetyGateError(report)
        return report
