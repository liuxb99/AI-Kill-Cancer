"""
Calculation Trace System — tracks every step of the recommendation pipeline
for full auditability and debugging.

Follows the spirit of the ``DecisionThread`` architecture (``decision_thread.py``)
but operates as a lightweight, independent in-memory trace store focused on
the calculation pipeline rather than clinical decision nodes.

Provides
--------
- ``TraceStep`` — a single atomic step in the calculation pipeline.
- ``CalculationTrace`` — a complete trace encompassing all steps for one
  patient recommendation run.
- ``TraceManager`` — manages creation, population, and retrieval of traces.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# TraceStep
# ═══════════════════════════════════════════════════════════════════════════════


class TraceStep(BaseModel):
    """A single atomic step recorded during the recommendation pipeline.

    Each step captures the inputs, outputs, and timing of one phase of
    the calculation (e.g. input collection, evidence aggregation, scoring,
    recommendation assembly, or final output).

    Attributes
    ----------
    step_name : str
        A short, descriptive name for this step (e.g. ``"collect_evidence"``).
    step_type : str
        The category of step. One of ``"input"``, ``"evidence"``,
        ``"score"``, ``"recommendation"``, or ``"output"``.
    input_data : dict
        Snapshot of the data entering this step (e.g. variants, context).
    output_data : dict
        Snapshot of the data produced by this step (e.g. aggregated scores,
        ranked results).
    timestamp : datetime
        When the step was recorded (UTC).
    duration_ms : float | None
        Wall-clock duration of the step in milliseconds, if available.
    parent_trace_id : str | None
        Optional link to a parent trace for hierarchical tracing (e.g.
        sub-traces spawned for individual drug scoring).
    """

    step_name: str = Field(
        ...,
        description="Short descriptive name for this step.",
    )
    step_type: str = Field(
        ...,
        description=(
            "Step category: input | evidence | score | recommendation | output"
        ),
    )
    input_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Snapshot of data entering this step.",
    )
    output_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Snapshot of data produced by this step.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the step was recorded (UTC).",
    )
    duration_ms: Optional[float] = Field(
        default=None,
        description="Wall-clock duration in milliseconds, if measured.",
    )
    parent_trace_id: Optional[str] = Field(
        default=None,
        description="Optional parent trace ID for hierarchical tracing.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CalculationTrace
# ═══════════════════════════════════════════════════════════════════════════════


class CalculationTrace(BaseModel):
    """Complete calculation trace for one patient recommendation run.

    Aggregates all ``TraceStep`` instances recorded during a single
    invocation of the recommendation pipeline, together with metadata
    about the patient and overall status.

    Attributes
    ----------
    trace_id : str
        Unique identifier for this trace (UUID v4 string).
    patient_id : str
        Identifier of the patient this trace belongs to.
    started_at : datetime
        When the trace was started (UTC).
    completed_at : datetime | None
        When the trace was completed or failed (UTC). ``None`` while the
        trace is still running.
    steps : list[TraceStep]
        Ordered list of steps recorded during this trace.
    status : str
        Current status: ``"running"``, ``"completed"``, or ``"failed"``.
    """

    trace_id: str = Field(
        ...,
        description="Unique trace identifier (UUID v4).",
    )
    patient_id: str = Field(
        ...,
        description="Patient identifier.",
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the trace was started (UTC).",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When the trace was completed/failed (UTC).",
    )
    steps: list[TraceStep] = Field(
        default_factory=list,
        description="Ordered list of recorded steps.",
    )
    status: str = Field(
        default="running",
        description='Status: "running" | "completed" | "failed".',
    )

    @property
    def total_duration_ms(self) -> float:
        """Return the total wall-clock duration of this trace in milliseconds.

        Returns
        -------
        float
            Milliseconds between ``started_at`` and ``completed_at``.
            Returns ``0.0`` if the trace is still running.
        """
        if self.completed_at is None:
            return 0.0
        delta = self.completed_at - self.started_at
        return delta.total_seconds() * 1000.0

    @property
    def step_count(self) -> int:
        """Return the number of steps recorded."""
        return len(self.steps)

    def add_step(self, step: TraceStep) -> None:
        """Append a step to the trace's step list (in-place).

        Parameters
        ----------
        step : TraceStep
            The step to append.
        """
        self.steps.append(step)


# ═══════════════════════════════════════════════════════════════════════════════
# TraceManager
# ═══════════════════════════════════════════════════════════════════════════════


class TraceManager:
    """In-memory manager for ``CalculationTrace`` instances.

    Provides CRUD-style operations for creating, populating, completing,
    and querying calculation traces.  All traces are held in memory; for
    production use, subclasses or wrappers can persist to a database.

    This manager is designed to be independent of the database-backed
    ``DecisionThreadRepository`` — it can be used standalone or alongside
    it for different granularity levels.

    Usage::

        mgr = TraceManager()
        trace = mgr.start_trace(patient_id="P-001")
        mgr.add_step(trace.trace_id, TraceStep(step_name="collect", ...))
        mgr.complete_trace(trace.trace_id)
    """

    def __init__(self) -> None:
        """Initialise an empty trace manager."""
        self._traces: dict[str, CalculationTrace] = {}

    # ── Public API ─────────────────────────────────────────────────────────

    def start_trace(
        self,
        patient_id: str,
        *,
        trace_id: str | None = None,
    ) -> CalculationTrace:
        """Start a new calculation trace for a patient.

        Parameters
        ----------
        patient_id : str
            The patient identifier this trace belongs to.
        trace_id : str, optional
            Explicit trace ID (auto-generated UUID v4 if not provided).

        Returns
        -------
        CalculationTrace
            The newly created trace in ``"running"`` status.
        """
        tid = trace_id or uuid.uuid4().hex
        trace = CalculationTrace(
            trace_id=tid,
            patient_id=patient_id,
            started_at=datetime.now(UTC),
            status="running",
        )
        self._traces[tid] = trace
        return trace

    def add_step(
        self,
        trace_id: str,
        step: TraceStep,
    ) -> None:
        """Record a step in an existing trace.

        Parameters
        ----------
        trace_id : str
            The trace identifier (must exist).
        step : TraceStep
            The step to append.

        Raises
        ------
        KeyError
            If *trace_id* does not correspond to a known trace.
        ValueError
            If the trace is not in ``"running"`` status.
        """
        trace = self._get_trace_or_raise(trace_id)
        if trace.status != "running":
            raise ValueError(
                f"Cannot add step to trace {trace_id!r}: "
                f"status is {trace.status!r} (must be 'running')."
            )
        trace.add_step(step)

    def complete_trace(
        self,
        trace_id: str,
        *,
        status: str = "completed",
    ) -> CalculationTrace:
        """Mark a trace as completed or failed.

        Parameters
        ----------
        trace_id : str
            The trace identifier (must exist and be in ``"running"`` status).
        status : str, optional
            Final status — ``"completed"`` (default) or ``"failed"``.

        Returns
        -------
        CalculationTrace
            The updated trace with ``completed_at`` set and ``status``
            updated.

        Raises
        ------
        KeyError
            If *trace_id* does not exist.
        ValueError
            If the trace is not in ``"running"`` status.
        """
        if status not in ("completed", "failed"):
            raise ValueError(
                f"Invalid final status {status!r}: "
                'must be "completed" or "failed".'
            )
        trace = self._get_trace_or_raise(trace_id)
        if trace.status != "running":
            raise ValueError(
                f"Cannot complete trace {trace_id!r}: "
                f"status is {trace.status!r} (must be 'running')."
            )
        trace.completed_at = datetime.now(UTC)
        trace.status = status
        return trace

    def get_trace(self, trace_id: str) -> CalculationTrace | None:
        """Retrieve a trace by its ID.

        Parameters
        ----------
        trace_id : str
            The trace identifier.

        Returns
        -------
        CalculationTrace | None
            The trace if found, otherwise ``None``.
        """
        return self._traces.get(trace_id)

    def list_traces(
        self,
        *,
        patient_id: str | None = None,
        status: str | None = None,
    ) -> list[CalculationTrace]:
        """List all known traces, optionally filtered.

        Parameters
        ----------
        patient_id : str, optional
            When set, only return traces for this patient.
        status : str, optional
            When set, only return traces with this status.

        Returns
        -------
        list[CalculationTrace]
            Matching traces, newest first (by ``started_at``).
        """
        traces = list(self._traces.values())

        if patient_id is not None:
            traces = [t for t in traces if t.patient_id == patient_id]
        if status is not None:
            traces = [t for t in traces if t.status == status]

        # Sort newest first
        traces.sort(key=lambda t: t.started_at, reverse=True)
        return traces

    def clear(self) -> None:
        """Remove all stored traces (for testing or reset)."""
        self._traces.clear()

    # ── Internal helpers ──────────────────────────────────────────────────

    def _get_trace_or_raise(self, trace_id: str) -> CalculationTrace:
        """Return the trace or raise ``KeyError`` with a descriptive message."""
        trace = self._traces.get(trace_id)
        if trace is None:
            raise KeyError(
                f"Trace {trace_id!r} not found. "
                f"Known traces: {list(self._traces)}"
            )
        return trace


__all__ = [
    "CalculationTrace",
    "TraceManager",
    "TraceStep",
]
