"""
Treatment Plan Engine — pure domain logic for generating treatment plans.

The engine consumes clinical context (patient, recommendation, decision,
consensus) and produces a structured ``EngineOutput`` containing phases,
treatment items, monitoring schedules, safety rules, and alternatives.

**Constraints**
- No database session, API client, or I/O is accepted.
- All inputs arrive as serialisable dicts/lists via ``EngineInput``.
- All outputs are serialisable dicts/lists — no SQLAlchemy model instances.
- Rule logic is delegated to ``TreatmentPlanRuleSet``.
- Status transitions are validated by ``TreatmentPlanStateMachine``.
- Every pipeline step is recorded in the calculation trace.

Pipeline steps
--------------
0. load_context
1. validate_links
2. extract_consensus
3. identify_treatment_goals
4. build_phases
5. build_treatment_items
6. build_monitoring
7. build_safety_rules
8. build_alternatives
9. finalize_plan
10. prepare_persistence
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from src.backend.clinical.treatment_plan_rules import TreatmentPlanRuleSet
from src.backend.clinical.treatment_plan_trace import TreatmentPlanTraceBuilder

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Data Transfer Objects (pure data, no SQLAlchemy)
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class EngineInput:
    """Input payload for ``TreatmentPlanEngine.generate()``.

    All fields are serialisable types (dicts, lists, strings).
    """

    patient_id: str
    recommendation_id: str
    clinical_decision_id: str
    consensus_id: str
    plan_intent: str
    treatment_goals: list[str]
    clinical_context: dict
    patient: dict
    recommendation: dict
    clinical_decision: dict
    consensus: dict
    evidence_summary: list[dict]
    contraindications: list[dict]
    monitoring_requirements: list[dict]


@dataclass
class EngineOutput:
    """Structured output of the treatment plan engine.

    Every field is a serialisable dict or list — ready for JSON encoding.
    """

    summary: str = ""
    clinical_rationale: str = ""
    phases: list[dict] = field(default_factory=list)
    items: list[dict] = field(default_factory=list)
    monitoring: list[dict] = field(default_factory=list)
    safety_rules: list[dict] = field(default_factory=list)
    alternatives: list[dict] = field(default_factory=list)
    review_date: Optional[str] = None
    trace: list[dict] = field(default_factory=list)
    plan_status: str = "draft"


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentPlanEngine
# ═══════════════════════════════════════════════════════════════════════════════


class TreatmentPlanEngine:
    """Rule-based engine that generates a structured treatment plan.

    The engine is *stateless* — all state is carried in the pipeline
    context dictionary that flows through each step.  This makes it safe
    to reuse and trivially testable.

    Parameters
    ----------
    rule_set : TreatmentPlanRuleSet, optional
        The rule set to use for phase sequencing, monitoring, etc.
        Defaults to a fresh ``TreatmentPlanRuleSet()``.
    """

    def __init__(
        self,
        rule_set: TreatmentPlanRuleSet | None = None,
    ) -> None:
        """Initialise the treatment plan engine.

        Parameters
        ----------
        rule_set : TreatmentPlanRuleSet, optional
            Custom rule set instance.  Defaults to a fresh
            ``TreatmentPlanRuleSet()``.
        """
        self._rule_set = rule_set or TreatmentPlanRuleSet()

    # ── Public API ─────────────────────────────────────────────────────────

    def generate(self, input_data: EngineInput) -> EngineOutput:
        """Generate a complete treatment plan from the given input.

        This is the main entry point.  It runs the full pipeline and
        returns a fully populated ``EngineOutput``.

        Parameters
        ----------
        input_data : EngineInput
            All clinical context needed to generate the plan.

        Returns
        -------
        EngineOutput
            The structured treatment plan with all derived fields.
        """
        trace_builder = TreatmentPlanTraceBuilder()
        ctx: dict[str, Any] = {}  # mutable pipeline context

        # ── Step 0: Load context ──────────────────────────────────────
        self._step_load_context(input_data, ctx, trace_builder)

        # ── Step 1: Validate links ────────────────────────────────────
        self._step_validate_links(input_data, ctx, trace_builder)

        # ── Step 2: Extract consensus ─────────────────────────────────
        self._step_extract_consensus(input_data, ctx, trace_builder)

        # ── Step 3: Identify treatment goals ──────────────────────────
        self._step_identify_treatment_goals(input_data, ctx, trace_builder)

        # ── Step 4: Build phases ──────────────────────────────────────
        self._step_build_phases(input_data, ctx, trace_builder)

        # ── Step 5: Build treatment items ─────────────────────────────
        self._step_build_treatment_items(input_data, ctx, trace_builder)

        # ── Step 6: Build monitoring ──────────────────────────────────
        self._step_build_monitoring(input_data, ctx, trace_builder)

        # ── Step 7: Build safety rules ────────────────────────────────
        self._step_build_safety_rules(input_data, ctx, trace_builder)

        # ── Step 8: Build alternatives ────────────────────────────────
        self._step_build_alternatives(input_data, ctx, trace_builder)

        # ── Step 9: Finalize plan ─────────────────────────────────────
        self._step_finalize_plan(input_data, ctx, trace_builder)

        # ── Step 10: Prepare persistence output ───────────────────────
        output = self._step_prepare_persistence(input_data, ctx, trace_builder)

        return output

    # ═══════════════════════════════════════════════════════════════════════
    # Step implementations
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _step_load_context(
        input_data: EngineInput,
        ctx: dict,
        trace: TreatmentPlanTraceBuilder,
    ) -> None:
        """Record input context summary as the first trace step."""
        ctx["plan_intent"] = input_data.plan_intent
        ctx["treatment_goals"] = list(input_data.treatment_goals)
        ctx["cancer_type"] = input_data.clinical_context.get("cancer_type", "unknown")

        trace.add_step(
            step_type="load_context",
            input_summary={
                "patient_id": input_data.patient_id,
                "recommendation_id": input_data.recommendation_id,
                "clinical_decision_id": input_data.clinical_decision_id,
                "consensus_id": input_data.consensus_id,
                "plan_intent": input_data.plan_intent,
                "cancer_type": input_data.clinical_context.get("cancer_type"),
                "treatment_goals_count": len(input_data.treatment_goals),
                "evidence_summary_count": len(input_data.evidence_summary),
                "contraindications_count": len(input_data.contraindications),
            },
            output_summary={
                "status": "context_loaded",
            },
        )

    @staticmethod
    def _step_validate_links(
        input_data: EngineInput,
        ctx: dict,
        trace: TreatmentPlanTraceBuilder,
    ) -> None:
        """Validate that required reference IDs are present.

        Raises
        ------
        ValueError
            If any required link field is empty.
        """
        errors: list[str] = []
        if not input_data.patient_id:
            errors.append("patient_id is required")
        if not input_data.recommendation_id:
            errors.append("recommendation_id is required")
        if not input_data.clinical_decision_id:
            errors.append("clinical_decision_id is required")

        trace.add_step(
            step_type="validate_links",
            input_summary={
                "patient_id": input_data.patient_id,
                "recommendation_id": input_data.recommendation_id,
                "clinical_decision_id": input_data.clinical_decision_id,
            },
            output_summary={
                "valid": len(errors) == 0,
                "errors": errors,
            },
            rule_ids=[],
        )

        if errors:
            raise ValueError(
                f"Treatment plan link validation failed: {'; '.join(errors)}"
            )

    @staticmethod
    def _step_extract_consensus(
        input_data: EngineInput,
        ctx: dict,
        trace: TreatmentPlanTraceBuilder,
    ) -> None:
        """Extract consensus information from the consensus data."""
        consensus = input_data.consensus or {}
        ctx["consensus_status"] = consensus.get("consensus_status", "unknown")
        ctx["consensus_score"] = consensus.get("consensus_score", 0.0)
        ctx["consensus_rationale"] = consensus.get("supporting_rationale", "")

        trace.add_step(
            step_type="extract_consensus",
            input_summary={
                "consensus_id": input_data.consensus_id,
                "consensus_status": consensus.get("consensus_status"),
            },
            output_summary={
                "consensus_status": ctx["consensus_status"],
                "consensus_score": ctx["consensus_score"],
            },
            evidence_ids=[input_data.consensus_id] if input_data.consensus_id else [],
        )

    @staticmethod
    def _step_identify_treatment_goals(
        input_data: EngineInput,
        ctx: dict,
        trace: TreatmentPlanTraceBuilder,
    ) -> None:
        """Identify and normalise treatment goals from input."""
        goals = list(input_data.treatment_goals) or []
        ctx["goals"] = goals

        trace.add_step(
            step_type="identify_treatment_goals",
            input_summary={
                "raw_goals": input_data.treatment_goals,
            },
            output_summary={
                "goal_count": len(goals),
                "goals": goals,
            },
        )

    def _step_build_phases(
        self,
        input_data: EngineInput,
        ctx: dict,
        trace: TreatmentPlanTraceBuilder,
    ) -> None:
        """Build ordered treatment phases using the rule set."""
        cancer_type = ctx.get("cancer_type", "unknown")
        plan_intent = ctx.get("plan_intent", "curative")

        phases = self._rule_set.get_phase_sequence(
            cancer_type=cancer_type,
            treatment_intent=plan_intent,
        )
        ctx["phases"] = phases

        trace.add_step(
            step_type="build_phases",
            input_summary={
                "cancer_type": cancer_type,
                "treatment_intent": plan_intent,
            },
            output_summary={
                "phase_count": len(phases),
                "phase_types": [p.get("phase_type") for p in phases],
            },
            rule_ids=["phase_sequence_default"],
        )

    def _step_build_treatment_items(
        self,
        input_data: EngineInput,
        ctx: dict,
        trace: TreatmentPlanTraceBuilder,
    ) -> None:
        """Build treatment items from recommendation and decision data."""
        recommendation = input_data.recommendation or {}
        clinical_decision = input_data.clinical_decision or {}
        items: list[dict] = []

        # Extract top drug from recommendation as the primary item
        top_drug = self._extract_top_drug(recommendation)
        if top_drug:
            items.append(top_drug)

        # Add additional items from recommendation ranked list
        ranked_drugs = self._extract_ranked_drugs(recommendation)
        for drug in ranked_drugs[1:]:  # skip top drug already added
            items.append({
                "item_type": "medication",
                "name": drug.get("drug_name", "Unknown Drug"),
                "description": f"Alternative medication: {drug.get('drug_name', '')}",
                "priority": drug.get("rank", 99),
                "rationale": f"Ranked #{drug.get('rank', '?')} by evidence score",
                "source_recommendation": "recommendation_engine",
                "phase_type": "primary_treatment",
            })

        # Add items from clinical decision alternatives
        alternatives = clinical_decision.get("alternatives", [])
        for alt in alternatives:
            items.append({
                "item_type": "medication",
                "name": alt.get("drug_name", "Unknown"),
                "description": f"Clinical decision alternative: {alt.get('drug_name', '')}",
                "priority": alt.get("rank", 99),
                "rationale": alt.get("rationale", ""),
                "source_recommendation": "clinical_decision",
                "phase_type": "primary_treatment",
            })

        ctx["items"] = items

        trace.add_step(
            step_type="build_treatment_items",
            input_summary={
                "recommendation_drugs_count": len(ranked_drugs),
                "alternatives_count": len(alternatives),
            },
            output_summary={
                "items_count": len(items),
                "item_types": list({i.get("item_type") for i in items}),
            },
            rule_ids=[],
            evidence_ids=[input_data.recommendation_id] if input_data.recommendation_id else [],
        )

    def _step_build_monitoring(
        self,
        input_data: EngineInput,
        ctx: dict,
        trace: TreatmentPlanTraceBuilder,
    ) -> None:
        """Build monitoring schedule using the rule set."""
        phases = ctx.get("phases", [])
        items = ctx.get("items", [])
        all_monitoring: list[dict] = []

        # Include any pre-existing monitoring requirements from input
        for req in input_data.monitoring_requirements:
            all_monitoring.append(dict(req))

        # Generate monitoring per phase using rule set
        for phase in phases:
            phase_type = phase.get("phase_type", "unknown")
            phase_monitoring = self._rule_set.get_required_monitoring(
                phase_type=phase_type,
                items=items,
            )
            for m in phase_monitoring:
                m["phase_type"] = phase_type
                all_monitoring.append(m)

        ctx["monitoring"] = all_monitoring

        trace.add_step(
            step_type="build_monitoring",
            input_summary={
                "phase_count": len(phases),
                "input_monitoring_count": len(input_data.monitoring_requirements),
            },
            output_summary={
                "monitoring_count": len(all_monitoring),
                "monitoring_types": list({m.get("monitoring_type") for m in all_monitoring}),
            },
            rule_ids=["monitoring_default"],
        )

    def _step_build_safety_rules(
        self,
        input_data: EngineInput,
        ctx: dict,
        trace: TreatmentPlanTraceBuilder,
    ) -> None:
        """Build safety rules from contraindications and clinical context."""
        safety_rules: list[dict] = []

        # Convert contraindications to safety rules
        for ci in input_data.contraindications:
            severity = ci.get("severity", "medium")
            escalation = self._rule_set.get_safety_escalation(severity)
            safety_rules.append({
                "rule_type": escalation.get("action_type", "review"),
                "condition": {
                    "type": ci.get("type", "contraindication"),
                    "detail": ci.get("detail", ""),
                    "drug": ci.get("drug", ""),
                },
                "severity": severity,
                "recommended_action": escalation.get("recommended_action", ""),
                "requires_review": escalation.get("requires_review", True),
                "source": ci.get("type", "contraindication"),
            })

        # Add safety rules from clinical decision contraindications
        decision = input_data.clinical_decision or {}
        for ci in decision.get("contraindications", []):
            severity = ci.get("severity", "medium")
            escalation = self._rule_set.get_safety_escalation(severity)
            safety_rules.append({
                "rule_type": escalation.get("action_type", "review"),
                "condition": {
                    "type": ci.get("type", "contraindication"),
                    "detail": ci.get("detail", ""),
                    "drug": ci.get("drug", ""),
                },
                "severity": severity,
                "recommended_action": escalation.get("recommended_action", ""),
                "requires_review": escalation.get("requires_review", True),
                "source": "clinical_decision",
            })

        ctx["safety_rules"] = safety_rules

        trace.add_step(
            step_type="build_safety_rules",
            input_summary={
                "contraindications_count": len(input_data.contraindications),
                "decision_contraindications_count": len(decision.get("contraindications", [])),
            },
            output_summary={
                "safety_rules_count": len(safety_rules),
                "severity_distribution": {
                    s: sum(1 for r in safety_rules if r["severity"] == s)
                    for s in {"high", "medium", "low"}
                },
            },
            rule_ids=["safety_escalation_default"],
        )

    def _step_build_alternatives(
        self,
        input_data: EngineInput,
        ctx: dict,
        trace: TreatmentPlanTraceBuilder,
    ) -> None:
        """Build alternative treatment options."""
        alternatives: list[dict] = []

        # Extract alternatives from clinical decision
        decision = input_data.clinical_decision or {}
        for alt in decision.get("alternatives", []):
            priority = self._rule_set.get_alternative_priority(
                trigger_condition="patient_preference",
            )
            alternatives.append({
                "drug_name": alt.get("drug_name", "Unknown"),
                "rank": alt.get("rank", 99),
                "overall_score": alt.get("overall_score", 0.0),
                "rationale": alt.get("rationale", ""),
                "priority": priority,
            })

        # Add alternatives from ranked drugs (position 2+)
        recommendation = input_data.recommendation or {}
        ranked = self._extract_ranked_drugs(recommendation)
        for drug in ranked[1:6]:  # up to 5 alternatives
            drug_name = drug.get("drug_name", "Unknown")
            # Avoid duplicates with decision alternatives
            if any(a.get("drug_name") == drug_name for a in alternatives):
                continue
            alternatives.append({
                "drug_name": drug_name,
                "rank": drug.get("rank", 99),
                "overall_score": drug.get("overall_score", 0.0),
                "rationale": (
                    f"Alternative treatment option ranked #{drug.get('rank', '?')} "
                    f"by evidence-based recommendation engine."
                ),
                "priority": 50,
            })

        ctx["alternatives"] = alternatives

        trace.add_step(
            step_type="build_alternatives",
            input_summary={
                "decision_alternatives_count": len(decision.get("alternatives", [])),
                "recommendation_drugs_count": len(ranked),
            },
            output_summary={
                "alternatives_count": len(alternatives),
                "alternative_drugs": [a.get("drug_name") for a in alternatives],
            },
            rule_ids=["alternative_priority_default"],
        )

    def _step_finalize_plan(
        self,
        input_data: EngineInput,
        ctx: dict,
        trace: TreatmentPlanTraceBuilder,
    ) -> None:
        """Finalise the plan: compute summary, rationale, and review date."""
        phases = ctx.get("phases", [])
        items = ctx.get("items", [])
        safety_rules = ctx.get("safety_rules", [])
        goals = ctx.get("goals", [])
        consensus_rationale = ctx.get("consensus_rationale", "")

        # Build summary
        summary_parts: list[str] = []
        if goals:
            summary_parts.append(f"Treatment goals: {'; '.join(goals)}.")
        summary_parts.append(
            f"Plan includes {len(phases)} phase(s), {len(items)} treatment item(s), "
            f"and {len(safety_rules)} safety rule(s)."
        )
        ctx["summary"] = " ".join(summary_parts)

        # Build clinical rationale
        rationale_parts: list[str] = []
        if consensus_rationale:
            rationale_parts.append(f"Tumor board consensus: {consensus_rationale}")
        top_drug = self._extract_top_drug(input_data.recommendation or {})
        if top_drug:
            rationale_parts.append(
                f"Primary recommendation: {top_drug.get('name', top_drug.get('item_type', 'unknown'))}."
            )
        rationale_parts.append(
            f"Treatment intent is '{ctx.get('plan_intent', 'not_specified')}'."
        )
        ctx["clinical_rationale"] = " ".join(rationale_parts)

        # Compute review date interval
        phase_count = len(phases)
        review_interval = self._rule_set.get_review_interval(
            plan_status="draft",
            phase_count=phase_count,
        )
        ctx["review_interval_days"] = review_interval

        trace.add_step(
            step_type="finalize_plan",
            input_summary={
                "phase_count": phase_count,
                "items_count": len(items),
                "safety_rules_count": len(safety_rules),
            },
            output_summary={
                "summary": ctx["summary"],
                "review_interval_days": review_interval,
            },
            rule_ids=["review_interval_default"],
        )

    @staticmethod
    def _step_prepare_persistence(
        input_data: EngineInput,
        ctx: dict,
        trace: TreatmentPlanTraceBuilder,
    ) -> EngineOutput:
        """Assemble the final ``EngineOutput`` from accumulated context."""
        output = EngineOutput(
            summary=ctx.get("summary", ""),
            clinical_rationale=ctx.get("clinical_rationale", ""),
            phases=ctx.get("phases", []),
            items=ctx.get("items", []),
            monitoring=ctx.get("monitoring", []),
            safety_rules=ctx.get("safety_rules", []),
            alternatives=ctx.get("alternatives", []),
            review_date=None,  # set by service layer after persist
            trace=[],  # placeholder, replaced below
            plan_status="draft",
        )

        trace.add_step(
            step_type="prepare_persistence",
            input_summary={
                "plan_status": output.plan_status,
                "phases_count": len(output.phases),
                "items_count": len(output.items),
                "monitoring_count": len(output.monitoring),
                "safety_rules_count": len(output.safety_rules),
                "alternatives_count": len(output.alternatives),
            },
            output_summary={
                "output_summary": output.summary[:120] if output.summary else "",
                "trace_step_count": len(trace.steps) + 1,
            },
        )

        # Build the full trace AFTER adding the final step
        output.trace = trace.build()
        return output

    # ═══════════════════════════════════════════════════════════════════════
    # Internal helpers (static utility methods)
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _extract_top_drug(recommendation: dict) -> dict | None:
        """Extract the top-ranked drug from a recommendation structure."""
        drugs = (recommendation.get("recommendations")
                 or recommendation.get("drugs_ranked")
                 or [])
        if drugs:
            drug = drugs[0]
            return {
                "item_type": "medication",
                "name": drug.get("drug_name", "Unknown Drug"),
                "description": (
                    f"Primary recommendation: {drug.get('drug_name', 'Unknown Drug')}"
                ),
                "priority": 1,
                "rationale": (
                    f"Top-ranked drug with evidence score "
                    f"{drug.get('overall_score', drug.get('total_weight', 0.0)):.4f}"
                ),
                "source_recommendation": "recommendation_engine",
                "phase_type": "primary_treatment",
            }
        if "drug_name" in recommendation:
            return {
                "item_type": "medication",
                "name": recommendation["drug_name"],
                "description": f"Primary recommendation: {recommendation['drug_name']}",
                "priority": 1,
                "rationale": "Single drug recommendation.",
                "source_recommendation": "recommendation_engine",
                "phase_type": "primary_treatment",
            }
        return None

    @staticmethod
    def _extract_ranked_drugs(recommendation: dict) -> list[dict]:
        """Extract the ranked drug list from a recommendation structure."""
        drugs = (recommendation.get("recommendations")
                 or recommendation.get("drugs_ranked")
                 or [])
        if not drugs and "drug_name" in recommendation:
            drugs = [recommendation]
        return drugs


__all__ = [
    "EngineInput",
    "EngineOutput",
    "TreatmentPlanEngine",
]
