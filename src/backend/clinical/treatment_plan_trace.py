"""
Treatment Plan Calculation Trace — records every step of the plan generation
pipeline for full auditability and debugging.

Each step captures:
- ``step_order`` — 0-based index in the pipeline.
- ``step_type`` — short identifier (e.g. ``"load_context"``).
- ``input_summary`` — snapshot of the data entering the step.
- ``output_summary`` — snapshot of the data produced by the step.
- ``rule_ids`` — list of rule identifiers consulted during the step.
- ``evidence_ids`` — list of evidence identifiers consulted.

This trace is independent of the database-backed trace model
(``TreatmentPlanTraceModel``); it is used in-memory during engine execution
and then persisted by the repository layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

TRACE_STEP_TYPES: list[str] = [
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

EXPECTED_STEP_COUNT = len(TRACE_STEP_TYPES)


# ═══════════════════════════════════════════════════════════════════════════════
# Step record
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class TreatmentPlanTraceStep:
    """A single step recorded during treatment plan generation.

    Parameters
    ----------
    step_order : int
        0-based index of this step in the pipeline.
    step_type : str
        Short identifier matching one of ``TRACE_STEP_TYPES``.
    input_summary : dict
        Snapshot of the data entering this step.
    output_summary : dict
        Snapshot of the data produced by this step.
    rule_ids : list[str]
        Rule identifiers that were consulted during this step.
    evidence_ids : list[str]
        Evidence identifiers that were consulted during this step.
    """

    step_order: int
    step_type: str
    input_summary: dict = field(default_factory=dict)
    output_summary: dict = field(default_factory=dict)
    rule_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dictionary representation."""
        return {
            "step_order": self.step_order,
            "step_type": self.step_type,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "rule_ids": list(self.rule_ids),
            "evidence_ids": list(self.evidence_ids),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Trace Builder
# ═══════════════════════════════════════════════════════════════════════════════


class TreatmentPlanTraceBuilder:
    """Accumulates ``TreatmentPlanTraceStep`` records in order.

    Usage::

        builder = TreatmentPlanTraceBuilder()
        builder.add_step(
            step_type="load_context",
            input_summary={"patient_id": "P-001"},
            output_summary={"status": "context_loaded"},
        )
        trace_list = builder.build()  # -> list[dict]

    The builder ensures steps are recorded in the order they are added and
    assigns sequential ``step_order`` values automatically.
    """

    def __init__(self) -> None:
        self._steps: list[TreatmentPlanTraceStep] = []

    # ── Public API ─────────────────────────────────────────────────────────

    def add_step(
        self,
        step_type: str,
        input_summary: dict | None = None,
        output_summary: dict | None = None,
        rule_ids: list[str] | None = None,
        evidence_ids: list[str] | None = None,
    ) -> TreatmentPlanTraceStep:
        """Append a step to the trace.

        Parameters
        ----------
        step_type : str
            Short identifier (e.g. ``"load_context"``).
        input_summary : dict, optional
            Snapshot of data entering the step.
        output_summary : dict, optional
            Snapshot of data produced by the step.
        rule_ids : list[str], optional
            Rule identifiers consulted.
        evidence_ids : list[str], optional
            Evidence identifiers consulted.

        Returns
        -------
        TreatmentPlanTraceStep
            The newly created step (also stored internally).
        """
        step = TreatmentPlanTraceStep(
            step_order=len(self._steps),
            step_type=step_type,
            input_summary=input_summary or {},
            output_summary=output_summary or {},
            rule_ids=rule_ids or [],
            evidence_ids=evidence_ids or [],
        )
        self._steps.append(step)
        return step

    def build(self) -> list[dict]:
        """Return the complete trace as a list of serialisable dicts.

        Returns
        -------
        list[dict]
            Ordered list of trace step dictionaries, ready for persistence.
        """
        return [s.to_dict() for s in self._steps]

    @property
    def steps(self) -> list[TreatmentPlanTraceStep]:
        """Return the internal step objects (read-only view)."""
        return list(self._steps)

    @property
    def step_count(self) -> int:
        """Number of steps recorded so far."""
        return len(self._steps)

    def reset(self) -> None:
        """Clear all recorded steps (for testing or re-run)."""
        self._steps.clear()


__all__ = [
    "TRACE_STEP_TYPES",
    "EXPECTED_STEP_COUNT",
    "TreatmentPlanTraceBuilder",
    "TreatmentPlanTraceStep",
]
