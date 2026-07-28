"""
Treatment Plan Rule Set — centralised rules for treatment plan generation.

Uses a ``RuleRegistry`` (Registry pattern) so that every rule has a unique ID,
is independently testable, and does not directly touch the database.

``TreatmentPlanRuleSet`` exposes domain methods that delegate to registered
rules via the registry, keeping the codebase free of scattered if/elif chains.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Rule & Registry
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Rule:
    """A single registered rule.

    Attributes
    ----------
    rule_id : str
        Unique identifier (e.g. ``"phase_sequence_curative"``).
    name : str
        Human-readable short name.
    description : str
        Longer description explaining the rule's intent.
    fn : Callable
        The rule implementation — a pure function taking only the parameters
        it needs and returning a result.
    source : str
        Origin / owner (e.g. ``"internal"``, ``"nccn_guidelines"``).
    """

    rule_id: str
    name: str
    description: str
    fn: Callable[..., Any]
    source: str = "internal"


class RuleRegistry:
    """Decorator-based registry for treatment plan rules.

    Usage::

        @RuleRegistry.register("my_rule", name="My Rule")
        def my_rule(param1: str) -> list[dict]:
            ...

        rule = RuleRegistry.get("my_rule")
        result = rule.fn(param1="value")
    """

    _rules: dict[str, Rule] = {}

    # ── Registration ───────────────────────────────────────────────────────

    @classmethod
    def register(
        cls,
        rule_id: str,
        *,
        name: str = "",
        description: str = "",
        source: str = "internal",
    ) -> Callable[[Callable], Callable]:
        """Decorator: register a callable as a rule.

        Parameters
        ----------
        rule_id : str
            Unique identifier for this rule.
        name : str, optional
            Human-readable name (defaults to the function name).
        description : str, optional
            Longer description (defaults to the function's docstring).
        source : str, optional
            Origin of the rule (default ``"internal"``).

        Returns
        -------
        Callable
            The original function (unchanged).
        """
        def decorator(fn: Callable) -> Callable:
            cls._rules[rule_id] = Rule(
                rule_id=rule_id,
                name=name or fn.__name__,
                description=description or (fn.__doc__ or "").strip(),
                fn=fn,
                source=source,
            )
            return fn
        return decorator

    # ── Lookup ─────────────────────────────────────────────────────────────

    @classmethod
    def get(cls, rule_id: str) -> Rule:
        """Retrieve a registered rule by its *rule_id*.

        Parameters
        ----------
        rule_id : str
            The unique rule identifier.

        Returns
        -------
        Rule
            The registered rule.

        Raises
        ------
        KeyError
            If no rule with that ID is registered.
        """
        if rule_id not in cls._rules:
            raise KeyError(
                f"Rule {rule_id!r} not found in registry. "
                f"Registered: {sorted(cls._rules)}"
            )
        return cls._rules[rule_id]

    @classmethod
    def list_rules(cls) -> list[str]:
        """Return a sorted list of all registered rule IDs."""
        return sorted(cls._rules.keys())

    @classmethod
    def clear(cls) -> None:
        """Remove all registered rules (primarily for testing)."""
        cls._rules.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentPlanRuleSet
# ═══════════════════════════════════════════════════════════════════════════════


class TreatmentPlanRuleSet:
    """Domain rule set for treatment plan generation.

    Each method delegates to a registered rule in the ``RuleRegistry``.
    This indirection keeps the domain logic clean while allowing individual
    rules to be registered, replaced, or tested independently.

    The default constructor uses the global ``RuleRegistry``; a custom
    registry can be injected for testing or extension.
    """

    def __init__(self, registry: type[RuleRegistry] = RuleRegistry) -> None:
        """Initialise the rule set.

        Parameters
        ----------
        registry : type[RuleRegistry], optional
            The registry class to consult for rule lookups.
            Defaults to ``RuleRegistry``.
        """
        self._registry = registry

    # ── Phase sequencing ──────────────────────────────────────────────────

    def get_phase_sequence(
        self,
        cancer_type: str,
        treatment_intent: str,
    ) -> list[dict]:
        """Determine the ordered list of treatment phases.

        Parameters
        ----------
        cancer_type : str
            Cancer type identifier (e.g. ``"PTC"``).
        treatment_intent : str
            Intent (e.g. ``"curative"``, ``"palliative"``).

        Returns
        -------
        list[dict]
            Each dict contains ``phase_type``, ``name``, ``order``,
            and optional ``duration_days``.
        """
        rule = self._registry.get("phase_sequence_default")
        return rule.fn(cancer_type=cancer_type, treatment_intent=treatment_intent)

    # ── Monitoring ────────────────────────────────────────────────────────

    def get_required_monitoring(
        self,
        phase_type: str,
        items: list[dict],
    ) -> list[dict]:
        """Determine required monitoring for a phase and its items.

        Parameters
        ----------
        phase_type : str
            Type of phase (e.g. ``"medication"``, ``"radiation"``).
        items : list[dict]
            Treatment items in this phase (each dict has at minimum
            an ``item_type`` key).

        Returns
        -------
        list[dict]
            Monitoring specifications (``monitoring_type``, ``name``,
            ``schedule``, etc.).
        """
        rule = self._registry.get("monitoring_default")
        return rule.fn(phase_type=phase_type, items=items)

    # ── Review interval ───────────────────────────────────────────────────

    def get_review_interval(
        self,
        plan_status: str,
        phase_count: int,
    ) -> int:
        """Calculate the review interval in days from today.

        Parameters
        ----------
        plan_status : str
            Current plan status (e.g. ``"active"``, ``"under_review"``).
        phase_count : int
            Number of phases in the plan (more phases may warrant
            shorter intervals).

        Returns
        -------
        int
            Number of days until the next review.
        """
        rule = self._registry.get("review_interval_default")
        return rule.fn(plan_status=plan_status, phase_count=phase_count)

    # ── Safety escalation ─────────────────────────────────────────────────

    def get_safety_escalation(self, severity: str) -> dict:
        """Get the recommended action for a given severity level.

        Parameters
        ----------
        severity : str
            One of ``"high"``, ``"medium"``, ``"low"``.

        Returns
        -------
        dict
            Contains ``recommended_action`` and optionally
            ``requires_review``, ``action_type``.
        """
        rule = self._registry.get("safety_escalation_default")
        return rule.fn(severity=severity)

    # ── Alternative priority ──────────────────────────────────────────────

    def get_alternative_priority(self, trigger_condition: str) -> int:
        """Return a numeric priority for an alternative treatment option.

        Higher numbers = higher priority.  Used to order alternative
        plans when multiple options exist.

        Parameters
        ----------
        trigger_condition : str
            The condition that triggered consideration of alternatives
            (e.g. ``"contraindication"``, ``"resistance"``,
            ``"patient_preference"``).

        Returns
        -------
        int
            Priority score (higher is better).
        """
        rule = self._registry.get("alternative_priority_default")
        return rule.fn(trigger_condition=trigger_condition)


# ═══════════════════════════════════════════════════════════════════════════════
# Default rule implementations
# ═══════════════════════════════════════════════════════════════════════════════


@RuleRegistry.register(
    "phase_sequence_default",
    name="Default Phase Sequence",
    description="Maps cancer type + treatment intent to an ordered list of phase definitions.",
)
def _phase_sequence_default(
    *,
    cancer_type: str,
    treatment_intent: str,
) -> list[dict]:
    """Default phase sequencing logic.

    For curative intent, returns phases leading to surveillance.
    For palliative intent, returns phases focused on quality of life.
    """
    _ = cancer_type  # reserved for future cancer-specific overrides

    if treatment_intent == "curative":
        return [
            {"phase_type": "preparation", "name": "Preparation", "order": 1, "duration_days": 14},
            {"phase_type": "primary_treatment", "name": "Primary Treatment", "order": 2, "duration_days": 90},
            {"phase_type": "adjuvant", "name": "Adjuvant Therapy", "order": 3, "duration_days": 180},
            {"phase_type": "surveillance", "name": "Surveillance", "order": 4, "duration_days": 365},
        ]

    if treatment_intent == "palliative":
        return [
            {"phase_type": "preparation", "name": "Preparation", "order": 1, "duration_days": 7},
            {"phase_type": "primary_treatment", "name": "Primary Treatment", "order": 2, "duration_days": 30},
            {"phase_type": "maintenance", "name": "Maintenance", "order": 3, "duration_days": 90},
            {"phase_type": "supportive_care", "name": "Supportive Care", "order": 4, "duration_days": 365},
        ]

    # Default / unknown intent
    return [
        {"phase_type": "preparation", "name": "Preparation", "order": 1, "duration_days": 14},
        {"phase_type": "primary_treatment", "name": "Primary Treatment", "order": 2, "duration_days": 90},
        {"phase_type": "follow_up", "name": "Follow-up", "order": 3, "duration_days": 180},
    ]


@RuleRegistry.register(
    "monitoring_default",
    name="Default Monitoring Rules",
    description="Maps phase type and items to required monitoring schedules.",
)
def _monitoring_default(
    *,
    phase_type: str,
    items: list[dict],
) -> list[dict]:
    """Default monitoring logic based on phase type and treatment items.

    - ``medication`` phases: lab work, drug-level monitoring, symptom checks.
    - ``radiation`` phases: imaging, skin assessment, fatigue monitoring.
    - ``surgery`` phases: wound check, vital signs, pain monitoring.
    - Default: general clinical assessment.
    """
    base_monitoring: list[dict] = []

    if phase_type == "medication" or phase_type == "primary_treatment":
        base_monitoring = [
            {
                "monitoring_type": "laboratory",
                "name": "Complete Blood Count",
                "schedule": "weekly",
                "baseline_required": True,
                "repeat_interval": "7d",
            },
            {
                "monitoring_type": "laboratory",
                "name": "Liver Function Tests",
                "schedule": "biweekly",
                "baseline_required": True,
                "repeat_interval": "14d",
            },
            {
                "monitoring_type": "symptom",
                "name": "Treatment Toxicity Assessment",
                "schedule": "weekly",
                "baseline_required": True,
                "repeat_interval": "7d",
            },
        ]
    elif phase_type == "radiation":
        base_monitoring = [
            {
                "monitoring_type": "imaging",
                "name": "Response Imaging",
                "schedule": "monthly",
                "baseline_required": True,
                "repeat_interval": "30d",
            },
            {
                "monitoring_type": "symptom",
                "name": "Radiation Dermatitis Assessment",
                "schedule": "weekly",
                "baseline_required": False,
                "repeat_interval": "7d",
            },
        ]
    elif phase_type == "surgery":
        base_monitoring = [
            {
                "monitoring_type": "vital_signs",
                "name": "Post-operative Vital Signs",
                "schedule": "daily",
                "baseline_required": True,
                "repeat_interval": "1d",
            },
            {
                "monitoring_type": "wound",
                "name": "Surgical Wound Assessment",
                "schedule": "daily",
                "baseline_required": True,
                "repeat_interval": "1d",
            },
        ]
    else:
        base_monitoring = [
            {
                "monitoring_type": "clinical_assessment",
                "name": "General Clinical Assessment",
                "schedule": "monthly",
                "baseline_required": True,
                "repeat_interval": "30d",
            },
        ]

    # Augment monitoring based on specific item types in the phase
    item_types = {item.get("item_type", "") for item in items if isinstance(item, dict)}

    if "medication" in item_types or "chemotherapy" in item_types:
        base_monitoring.append({
            "monitoring_type": "laboratory",
            "name": "Renal Function Tests",
            "schedule": "biweekly",
            "baseline_required": True,
            "repeat_interval": "14d",
        })

    if "targeted_therapy" in item_types:
        base_monitoring.append({
            "monitoring_type": "laboratory",
            "name": "Thyroid Function Tests",
            "schedule": "monthly",
            "baseline_required": True,
            "repeat_interval": "30d",
        })

    return base_monitoring


@RuleRegistry.register(
    "review_interval_default",
    name="Default Review Interval",
    description="Calculates the number of days until the next plan review based on status and phase count.",
)
def _review_interval_default(
    *,
    plan_status: str,
    phase_count: int,
) -> int:
    """Default review interval logic.

    Base intervals by status:
    - ``draft``: 7 days
    - ``under_review``: 14 days
    - ``active``: 30 days (more phases = shorter interval, min 14 days)
    - ``paused``: 14 days
    - Others: 90 days
    """
    base_intervals = {
        "draft": 7,
        "proposed": 14,
        "under_review": 14,
        "approved": 30,
        "active": 30,
        "paused": 14,
    }

    interval = base_intervals.get(plan_status, 90)

    # More phases warrant more frequent reviews
    if plan_status in ("active", "approved") and phase_count > 3:
        interval = max(interval - 7 * (phase_count - 3), 14)

    return interval


@RuleRegistry.register(
    "safety_escalation_default",
    name="Default Safety Escalation",
    description="Maps severity level to recommended action.",
)
def _safety_escalation_default(*, severity: str) -> dict:
    """Default safety escalation logic.

    - ``high``: pause treatment, immediate clinical review required.
    - ``medium``: dose adjustment, close monitoring, review within 48h.
    - ``low``: continue monitoring, inform clinician at next review.
    """
    if severity == "high":
        return {
            "action_type": "pause",
            "recommended_action": "Immediately pause treatment and notify attending physician for urgent clinical review.",
            "requires_review": True,
            "priority": 1,
        }
    if severity == "medium":
        return {
            "action_type": "dose_review",
            "recommended_action": "Adjust dose or schedule as per protocol; escalate for clinical review within 48 hours.",
            "requires_review": True,
            "priority": 2,
        }
    if severity == "low":
        return {
            "action_type": "continue_monitoring",
            "recommended_action": "Continue current treatment; inform clinician at next scheduled review.",
            "requires_review": False,
            "priority": 3,
        }

    # Unknown severity
    return {
        "action_type": "review",
        "recommended_action": f"Review severity level '{severity}' and determine appropriate action.",
        "requires_review": True,
        "priority": 99,
    }


@RuleRegistry.register(
    "alternative_priority_default",
    name="Default Alternative Priority",
    description="Maps trigger conditions to numeric priority scores for alternative treatment options.",
)
def _alternative_priority_default(*, trigger_condition: str) -> int:
    """Default alternative priority logic.

    Higher priority = alternative is more strongly recommended.
    """
    priority_map = {
        "contraindication": 100,
        "adverse_event": 90,
        "resistance": 80,
        "patient_preference": 60,
        "treatment_failure": 70,
        "drug_interaction": 85,
        "lack_of_efficacy": 65,
        "clinical_trial_available": 50,
    }
    return priority_map.get(trigger_condition, 10)


__all__ = [
    "Rule",
    "RuleRegistry",
    "TreatmentPlanRuleSet",
]
