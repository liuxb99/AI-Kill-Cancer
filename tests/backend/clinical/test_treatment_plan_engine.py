"""
Tests for Treatment Plan Engine components (Phase 3E Batch 1).

Covers:
- ``TreatmentPlanStateMachine`` — all valid and invalid transitions.
- ``RuleRegistry`` / ``TreatmentPlanRuleSet`` — registration, query, independence.
- ``TreatmentPlanEngine`` — full pipeline with 9 scenario tests.
- ``TreatmentPlanTraceBuilder`` — step recording and structure.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.backend.clinical.treatment_plan_engine import (
    EngineInput,
    EngineOutput,
    TreatmentPlanEngine,
)
from src.backend.clinical.treatment_plan_rules import (
    RuleRegistry,
    TreatmentPlanRuleSet,
)
from src.backend.clinical.treatment_plan_state_machine import (
    IllegalTransitionError,
    PlanStatus,
    TreatmentPlanStateMachine,
)
from src.backend.clinical.treatment_plan_trace import (
    TRACE_STEP_TYPES,
    TreatmentPlanTraceBuilder,
    TreatmentPlanTraceStep,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _make_minimal_input(overrides: dict | None = None) -> EngineInput:
    """Create a minimal EngineInput with sensible defaults."""
    defaults = {
        "patient_id": "patient-001",
        "recommendation_id": "rec-001",
        "clinical_decision_id": "cd-001",
        "consensus_id": "cons-001",
        "plan_intent": "curative",
        "treatment_goals": ["tumor_resection", "prevent_recurrence"],
        "clinical_context": {"cancer_type": "PTC"},
        "patient": {"age": 45, "sex": "F", "allergies": []},
        "recommendation": {
            "drugs_ranked": [
                {"drug_name": "Lenvatinib", "rank": 1, "overall_score": 0.95},
                {"drug_name": "Sorafenib", "rank": 2, "overall_score": 0.72},
            ],
        },
        "clinical_decision": {
            "decision_type": "approved",
            "confidence": "high",
            "alternatives": [
                {"drug_name": "Sorafenib", "rank": 2, "overall_score": 0.72, "rationale": "Alternative option"},
            ],
            "contraindications": [],
        },
        "consensus": {
            "consensus_status": "unanimous",
            "consensus_score": 1.0,
            "supporting_rationale": "All specialists agree on Lenvatinib as first-line therapy.",
        },
        "evidence_summary": [
            {"drug_name": "Lenvatinib", "source": "nccn", "evidence_level": "Level_1"},
        ],
        "contraindications": [],
        "monitoring_requirements": [],
    }
    if overrides:
        defaults.update(overrides)
    return EngineInput(**defaults)


# ═══════════════════════════════════════════════════════════════════════════════
# State Machine Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTreatmentPlanStateMachine:
    """All valid and invalid transitions for ``TreatmentPlanStateMachine``."""

    # ── Valid transitions ──────────────────────────────────────────────

    @pytest.mark.parametrize("current,target", [
        (PlanStatus.DRAFT, PlanStatus.PROPOSED),
        (PlanStatus.DRAFT, PlanStatus.CANCELLED),
        (PlanStatus.PROPOSED, PlanStatus.UNDER_REVIEW),
        (PlanStatus.PROPOSED, PlanStatus.CANCELLED),
        (PlanStatus.UNDER_REVIEW, PlanStatus.APPROVED),
        (PlanStatus.UNDER_REVIEW, PlanStatus.CANCELLED),
        (PlanStatus.APPROVED, PlanStatus.ACTIVE),
        (PlanStatus.APPROVED, PlanStatus.SUPERSEDED),
        (PlanStatus.APPROVED, PlanStatus.CANCELLED),
        (PlanStatus.ACTIVE, PlanStatus.PAUSED),
        (PlanStatus.ACTIVE, PlanStatus.COMPLETED),
        (PlanStatus.ACTIVE, PlanStatus.SUPERSEDED),
        (PlanStatus.PAUSED, PlanStatus.ACTIVE),
        (PlanStatus.PAUSED, PlanStatus.CANCELLED),
    ])
    def test_valid_transition(self, current: PlanStatus, target: PlanStatus) -> None:
        """A registered transition should succeed."""
        assert TreatmentPlanStateMachine.can_transition(current, target)
        result = TreatmentPlanStateMachine.transition(current, target)
        assert result == target

    # ── Invalid transitions ────────────────────────────────────────────

    @pytest.mark.parametrize("current,target", [
        (PlanStatus.DRAFT, PlanStatus.ACTIVE),
        (PlanStatus.DRAFT, PlanStatus.COMPLETED),
        (PlanStatus.DRAFT, PlanStatus.SUPERSEDED),
        (PlanStatus.PROPOSED, PlanStatus.ACTIVE),
        (PlanStatus.PROPOSED, PlanStatus.COMPLETED),
        (PlanStatus.UNDER_REVIEW, PlanStatus.ACTIVE),
        (PlanStatus.UNDER_REVIEW, PlanStatus.COMPLETED),
        (PlanStatus.APPROVED, PlanStatus.PROPOSED),
        (PlanStatus.APPROVED, PlanStatus.UNDER_REVIEW),
        (PlanStatus.ACTIVE, PlanStatus.APPROVED),
        (PlanStatus.ACTIVE, PlanStatus.DRAFT),
        (PlanStatus.PAUSED, PlanStatus.COMPLETED),
        (PlanStatus.PAUSED, PlanStatus.APPROVED),
        (PlanStatus.COMPLETED, PlanStatus.DRAFT),  # terminal
        (PlanStatus.CANCELLED, PlanStatus.DRAFT),  # terminal
        (PlanStatus.SUPERSEDED, PlanStatus.ACTIVE),  # terminal
    ])
    def test_invalid_transition_raises(self, current: PlanStatus, target: PlanStatus) -> None:
        """An unregistered transition should raise ``IllegalTransitionError``."""
        assert not TreatmentPlanStateMachine.can_transition(current, target)
        with pytest.raises(IllegalTransitionError):
            TreatmentPlanStateMachine.transition(current, target)

    # ── Terminal states ────────────────────────────────────────────────

    @pytest.mark.parametrize("terminal", [
        PlanStatus.COMPLETED,
        PlanStatus.CANCELLED,
        PlanStatus.SUPERSEDED,
    ])
    def test_terminal_state_allowed_transitions_empty(self, terminal: PlanStatus) -> None:
        """Terminal states should have no allowed transitions."""
        allowed = TreatmentPlanStateMachine.get_allowed_transitions(terminal)
        assert allowed == []

    # ── get_allowed_transitions ────────────────────────────────────────

    def test_get_allowed_transitions_draft(self) -> None:
        allowed = TreatmentPlanStateMachine.get_allowed_transitions(PlanStatus.DRAFT)
        assert PlanStatus.PROPOSED in allowed
        assert PlanStatus.CANCELLED in allowed
        assert len(allowed) == 2

    def test_get_allowed_transitions_approved(self) -> None:
        allowed = TreatmentPlanStateMachine.get_allowed_transitions(PlanStatus.APPROVED)
        assert PlanStatus.ACTIVE in allowed
        assert PlanStatus.SUPERSEDED in allowed
        assert PlanStatus.CANCELLED in allowed


# ═══════════════════════════════════════════════════════════════════════════════
# RuleSet & Registry Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestRuleRegistry:
    """``RuleRegistry`` registration, lookup, and listing."""

    def setup_method(self) -> None:
        # Save existing rules (including defaults from module-level decorators)
        # so we can restore them in teardown.
        self._saved_rules = dict(RuleRegistry._rules)
        # Start each test with a clean slate
        RuleRegistry.clear()

    def teardown_method(self) -> None:
        # Restore default rules so other test classes still see them
        RuleRegistry._rules.clear()
        RuleRegistry._rules.update(self._saved_rules)

    def test_register_and_get(self) -> None:
        @RuleRegistry.register("test_rule_1", name="Test Rule")
        def my_rule(*, x: int) -> int:
            return x * 2

        rule = RuleRegistry.get("test_rule_1")
        assert rule.rule_id == "test_rule_1"
        assert rule.name == "Test Rule"
        assert rule.fn(x=5) == 10

    def test_register_duplicate_overwrites(self) -> None:
        @RuleRegistry.register("dup_rule")
        def first(*, val: str) -> str:
            return f"first:{val}"

        @RuleRegistry.register("dup_rule")
        def second(*, val: str) -> str:
            return f"second:{val}"

        rule = RuleRegistry.get("dup_rule")
        assert rule.fn(val="test") == "second:test"

    def test_get_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            RuleRegistry.get("nonexistent")

    def test_list_rules(self) -> None:
        @RuleRegistry.register("alpha")
        def _a(): ...

        @RuleRegistry.register("beta")
        def _b(): ...

        @RuleRegistry.register("gamma")
        def _c(): ...

        listed = RuleRegistry.list_rules()
        assert "alpha" in listed
        assert "beta" in listed
        assert "gamma" in listed
        assert listed == sorted(listed)

    def test_clear(self) -> None:
        @RuleRegistry.register("temp_rule")
        def _t(): ...

        assert len(RuleRegistry.list_rules()) >= 1
        RuleRegistry.clear()
        assert RuleRegistry.list_rules() == []


class TestTreatmentPlanRuleSet:
    """``TreatmentPlanRuleSet`` domain methods."""

    def setup_method(self) -> None:
        # Default rules are already registered at module load;
        # we just use the rule set with the global registry.
        self.rule_set = TreatmentPlanRuleSet()

    # ── Phase sequence ─────────────────────────────────────────────────

    def test_get_phase_sequence_curative(self) -> None:
        phases = self.rule_set.get_phase_sequence(
            cancer_type="PTC",
            treatment_intent="curative",
        )
        assert len(phases) == 4
        assert phases[0]["phase_type"] == "preparation"
        assert phases[1]["phase_type"] == "primary_treatment"
        assert phases[2]["phase_type"] == "adjuvant"
        assert phases[3]["phase_type"] == "surveillance"
        for i, phase in enumerate(phases):
            assert phase["order"] == i + 1

    def test_get_phase_sequence_palliative(self) -> None:
        phases = self.rule_set.get_phase_sequence(
            cancer_type="PTC",
            treatment_intent="palliative",
        )
        assert len(phases) == 4
        assert phases[0]["phase_type"] == "preparation"
        assert phases[-1]["phase_type"] == "supportive_care"

    def test_get_phase_sequence_unknown_intent(self) -> None:
        phases = self.rule_set.get_phase_sequence(
            cancer_type="PTC",
            treatment_intent="unknown",
        )
        assert len(phases) == 3  # fallback

    # ── Monitoring ─────────────────────────────────────────────────────

    def test_get_required_monitoring_medication(self) -> None:
        monitoring = self.rule_set.get_required_monitoring(
            phase_type="medication",
            items=[{"item_type": "medication"}],
        )
        assert len(monitoring) >= 3
        types = {m["monitoring_type"] for m in monitoring}
        assert "laboratory" in types
        assert "symptom" in types

    def test_get_required_monitoring_radiation(self) -> None:
        monitoring = self.rule_set.get_required_monitoring(
            phase_type="radiation",
            items=[],
        )
        assert len(monitoring) >= 2
        types = {m["monitoring_type"] for m in monitoring}
        assert "imaging" in types

    def test_get_required_monitoring_surgery(self) -> None:
        monitoring = self.rule_set.get_required_monitoring(
            phase_type="surgery",
            items=[],
        )
        assert len(monitoring) >= 2
        types = {m["monitoring_type"] for m in monitoring}
        assert "vital_signs" in types
        assert "wound" in types

    # ── Review interval ────────────────────────────────────────────────

    def test_get_review_interval_draft(self) -> None:
        interval = self.rule_set.get_review_interval(
            plan_status="draft",
            phase_count=2,
        )
        assert interval == 7

    def test_get_review_interval_active_few_phases(self) -> None:
        interval = self.rule_set.get_review_interval(
            plan_status="active",
            phase_count=2,
        )
        assert interval == 30

    def test_get_review_interval_active_many_phases(self) -> None:
        interval = self.rule_set.get_review_interval(
            plan_status="active",
            phase_count=5,
        )
        # 30 - 7*(5-3) = 16
        assert interval == 16

    # ── Safety escalation ──────────────────────────────────────────────

    def test_get_safety_escalation_high(self) -> None:
        result = self.rule_set.get_safety_escalation("high")
        assert result["action_type"] == "pause"
        assert result["requires_review"] is True
        assert result["priority"] == 1

    def test_get_safety_escalation_medium(self) -> None:
        result = self.rule_set.get_safety_escalation("medium")
        assert result["action_type"] == "dose_review"
        assert result["requires_review"] is True

    def test_get_safety_escalation_low(self) -> None:
        result = self.rule_set.get_safety_escalation("low")
        assert result["action_type"] == "continue_monitoring"
        assert result["requires_review"] is False

    # ── Alternative priority ───────────────────────────────────────────

    def test_get_alternative_priority_known(self) -> None:
        priority = self.rule_set.get_alternative_priority("contraindication")
        assert priority == 100

    def test_get_alternative_priority_unknown(self) -> None:
        priority = self.rule_set.get_alternative_priority("unknown_condition")
        assert priority == 10  # default fallback


# ═══════════════════════════════════════════════════════════════════════════════
# Trace Builder Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTreatmentPlanTraceBuilder:
    """``TreatmentPlanTraceBuilder`` step recording and output."""

    def test_add_step_increments_order(self) -> None:
        builder = TreatmentPlanTraceBuilder()
        s1 = builder.add_step("load_context")
        s2 = builder.add_step("validate_links")
        assert s1.step_order == 0
        assert s2.step_order == 1

    def test_build_returns_list_of_dicts(self) -> None:
        builder = TreatmentPlanTraceBuilder()
        builder.add_step("load_context", input_summary={"key": "val"})
        builder.add_step("finalize_plan", output_summary={"ok": True})
        result = builder.build()
        assert len(result) == 2
        assert result[0]["step_type"] == "load_context"
        assert result[0]["input_summary"] == {"key": "val"}
        assert result[1]["step_type"] == "finalize_plan"
        assert result[1]["output_summary"] == {"ok": True}

    def test_step_to_dict_includes_all_fields(self) -> None:
        step = TreatmentPlanTraceStep(
            step_order=0,
            step_type="test_step",
            input_summary={"a": 1},
            output_summary={"b": 2},
            rule_ids=["rule_1"],
            evidence_ids=["ev_1"],
        )
        d = step.to_dict()
        assert d["step_order"] == 0
        assert d["step_type"] == "test_step"
        assert d["rule_ids"] == ["rule_1"]
        assert d["evidence_ids"] == ["ev_1"]

    def test_reset_clears_steps(self) -> None:
        builder = TreatmentPlanTraceBuilder()
        builder.add_step("load_context")
        assert builder.step_count == 1
        builder.reset()
        assert builder.step_count == 0

    def test_trace_step_types_are_defined(self) -> None:
        """The module-level TRACE_STEP_TYPES list should contain the expected
        pipeline step identifiers."""
        expected = {
            "load_context",
            "validate_links",
            "extract_consensus",
            "identify_treatment_goals",
            "build_phases",
            "build_treatment_items",
            "build_monitoring",
            "build_safety_rules",
            "build_alternatives",
            "finalize_plan",
            "prepare_persistence",
        }
        assert set(TRACE_STEP_TYPES) == expected


# ═══════════════════════════════════════════════════════════════════════════════
# Engine Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTreatmentPlanEngine:
    """Full pipeline tests for ``TreatmentPlanEngine.generate()``."""

    def setup_method(self) -> None:
        self.engine = TreatmentPlanEngine()

    # ── Test 1: Valid plan generation ──────────────────────────────────

    def test_valid_plan_generation(self) -> None:
        """A fully populated input should produce a complete output."""
        inp = _make_minimal_input()
        output = self.engine.generate(inp)

        assert isinstance(output, EngineOutput)
        assert output.summary
        assert output.clinical_rationale
        assert len(output.phases) > 0
        assert len(output.items) > 0
        assert len(output.monitoring) > 0
        assert output.plan_status == "draft"
        assert len(output.trace) > 0

    # ── Test 2: Phase ordering ─────────────────────────────────────────

    def test_phase_ordering(self) -> None:
        """Phases should be returned in the correct sequential order."""
        inp = _make_minimal_input({"plan_intent": "curative"})
        output = self.engine.generate(inp)

        assert len(output.phases) == 4
        for i, phase in enumerate(output.phases):
            assert phase["order"] == i + 1

    # ── Test 3: Monitoring generation ──────────────────────────────────

    def test_monitoring_generation(self) -> None:
        """Monitoring items should be generated for each phase."""
        inp = _make_minimal_input()
        output = self.engine.generate(inp)

        assert len(output.monitoring) > 0
        # At least one monitoring item should reference a phase type
        phase_types = {p["phase_type"] for p in output.phases}
        monitoring_phase_types = {
            m.get("phase_type") for m in output.monitoring
            if m.get("phase_type")
        }
        assert monitoring_phase_types.issubset(phase_types) or not monitoring_phase_types

    # ── Test 4: Safety rule generation ─────────────────────────────────

    def test_safety_rule_generation_with_contraindications(self) -> None:
        """Contraindications in the input should produce safety rules."""
        inp = _make_minimal_input({
            "contraindications": [
                {
                    "drug": "Lenvatinib",
                    "type": "allergy",
                    "detail": "Patient allergic to Lenvatinib",
                    "severity": "high",
                },
            ],
        })
        output = self.engine.generate(inp)

        assert len(output.safety_rules) > 0
        high_rules = [r for r in output.safety_rules if r["severity"] == "high"]
        assert len(high_rules) > 0
        assert high_rules[0]["source"] == "allergy"

    def test_safety_rule_generation_no_contraindications(self) -> None:
        """No contraindications should result in an empty safety rules list."""
        inp = _make_minimal_input()
        output = self.engine.generate(inp)

        # Input has no contraindications and decision has none → expect empty
        assert len(output.safety_rules) == 0

    # ── Test 5: Alternative generation ─────────────────────────────────

    def test_alternative_generation(self) -> None:
        """Alternatives from both recommendation and decision should be included."""
        inp = _make_minimal_input()
        output = self.engine.generate(inp)

        assert len(output.alternatives) > 0
        drug_names = {a["drug_name"] for a in output.alternatives}
        assert "Sorafenib" in drug_names

    # ── Test 6: Missing consensus ──────────────────────────────────────

    def test_missing_consensus(self) -> None:
        """Engine should handle empty/absent consensus gracefully."""
        inp = _make_minimal_input({
            "consensus_id": "",
            "consensus": {},
        })
        output = self.engine.generate(inp)

        assert output.summary
        assert output.clinical_rationale
        # Rationale should not reference consensus when it's absent
        assert "consensus" not in output.clinical_rationale.lower()

    # ── Test 7: Contraindication handling ──────────────────────────────

    def test_contraindication_handling(self) -> None:
        """Multiple contraindications should all be reflected in safety rules."""
        inp = _make_minimal_input({
            "contraindications": [
                {
                    "drug": "Lenvatinib",
                    "type": "variant_resistance",
                    "detail": "BRAF V600E resistance",
                    "severity": "high",
                },
                {
                    "drug": "Sorafenib",
                    "type": "drug_interaction",
                    "detail": "Interaction with current medication",
                    "severity": "medium",
                },
            ],
        })
        output = self.engine.generate(inp)

        assert len(output.safety_rules) == 2
        severities = {r["severity"] for r in output.safety_rules}
        assert "high" in severities
        assert "medium" in severities

    # ── Test 8: Empty evidence ─────────────────────────────────────────

    def test_empty_evidence_summary(self) -> None:
        """Engine should handle empty evidence_summary without crashing."""
        inp = _make_minimal_input({
            "evidence_summary": [],
            "recommendation": {
                "drugs_ranked": [
                    {"drug_name": "Lenvatinib", "rank": 1, "overall_score": 0.95},
                ],
            },
        })
        output = self.engine.generate(inp)

        assert output.summary
        assert len(output.items) >= 1  # still should have the top drug

    # ── Test 9: Deterministic output ───────────────────────────────────

    def test_deterministic_output(self) -> None:
        """Same input twice should produce identical output."""
        inp = _make_minimal_input()
        output1 = self.engine.generate(inp)
        output2 = self.engine.generate(inp)

        # Phases, items, safety_rules, alternatives should be identical
        assert output1.phases == output2.phases
        assert output1.items == output2.items
        assert output1.monitoring == output2.monitoring
        assert output1.safety_rules == output2.safety_rules
        assert output1.alternatives == output2.alternatives
        assert output1.trace == output2.trace

    # ── Trace completeness ─────────────────────────────────────────────

    def test_trace_includes_all_steps(self) -> None:
        """The output trace should contain all 11 pipeline steps."""
        inp = _make_minimal_input()
        output = self.engine.generate(inp)

        step_types = [s["step_type"] for s in output.trace]
        expected_steps = [
            "load_context",
            "validate_links",
            "extract_consensus",
            "identify_treatment_goals",
            "build_phases",
            "build_treatment_items",
            "build_monitoring",
            "build_safety_rules",
            "build_alternatives",
            "finalize_plan",
            "prepare_persistence",
        ]
        assert step_types == expected_steps, f"Got {step_types}"

    # ── Validation: missing required links ─────────────────────────────

    def test_validation_missing_patient_id(self) -> None:
        """Missing patient_id should raise ``ValueError``."""
        inp = _make_minimal_input({"patient_id": ""})
        with pytest.raises(ValueError, match="patient_id"):
            self.engine.generate(inp)

    def test_validation_missing_recommendation_id(self) -> None:
        """Missing recommendation_id should raise ``ValueError``."""
        inp = _make_minimal_input({"recommendation_id": ""})
        with pytest.raises(ValueError, match="recommendation_id"):
            self.engine.generate(inp)

    def test_validation_missing_clinical_decision_id(self) -> None:
        """Missing clinical_decision_id should raise ``ValueError``."""
        inp = _make_minimal_input({"clinical_decision_id": ""})
        with pytest.raises(ValueError, match="clinical_decision_id"):
            self.engine.generate(inp)


__all__: list[str] = []
