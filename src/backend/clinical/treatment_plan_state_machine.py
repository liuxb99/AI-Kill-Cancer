"""
Treatment Plan State Machine — manages status transitions for treatment plans.

Provides ``PlanStatus`` enum and ``TreatmentPlanStateMachine`` that enforces
legal transitions.  API layer maps ``IllegalTransitionError`` to HTTP 409.
"""

from __future__ import annotations

import enum
from typing import List


class PlanStatus(str, enum.Enum):
    """Status values for a treatment plan lifecycle.

    Terminal states: ``COMPLETED``, ``CANCELLED``, ``SUPERSEDED``.
    """

    DRAFT = "draft"
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"


class IllegalTransitionError(ValueError):
    """Raised when a status transition is not allowed.

    The API layer should catch this and return HTTP 409 Conflict.
    """

    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Cannot transition from status {current!r} to {target!r}."
        )


class TreatmentPlanStateMachine:
    """Stateless state machine that validates plan status transitions.

    All methods are class-level — no instance state is needed.
    The transition table is immutable by design.
    """

    TRANSITIONS: dict[PlanStatus, list[PlanStatus]] = {
        PlanStatus.DRAFT: [PlanStatus.PROPOSED, PlanStatus.CANCELLED],
        PlanStatus.PROPOSED: [PlanStatus.UNDER_REVIEW, PlanStatus.CANCELLED],
        PlanStatus.UNDER_REVIEW: [PlanStatus.APPROVED, PlanStatus.CANCELLED],
        PlanStatus.APPROVED: [PlanStatus.ACTIVE, PlanStatus.SUPERSEDED, PlanStatus.CANCELLED],
        PlanStatus.ACTIVE: [PlanStatus.PAUSED, PlanStatus.COMPLETED, PlanStatus.SUPERSEDED, PlanStatus.CANCELLED],
        PlanStatus.PAUSED: [PlanStatus.ACTIVE, PlanStatus.CANCELLED],
        PlanStatus.COMPLETED: [],  # terminal state
        PlanStatus.CANCELLED: [],  # terminal state
        PlanStatus.SUPERSEDED: [],  # terminal state
    }

    # ── Public API ─────────────────────────────────────────────────────────

    @classmethod
    def can_transition(cls, current: PlanStatus, target: PlanStatus) -> bool:
        """Check whether a transition from *current* to *target* is allowed.

        Parameters
        ----------
        current : PlanStatus
            The current status of the plan.
        target : PlanStatus
            The desired target status.

        Returns
        -------
        bool
            ``True`` if the transition is registered in the transition table.
        """
        return target in cls.TRANSITIONS.get(current, [])

    @classmethod
    def transition(cls, current: PlanStatus, target: PlanStatus) -> PlanStatus:
        """Attempt a status transition.

        Parameters
        ----------
        current : PlanStatus
            The current status of the plan.
        target : PlanStatus
            The desired target status.

        Returns
        -------
        PlanStatus
            The *target* status on success (the plan's caller updates the
            persisted status).

        Raises
        ------
        IllegalTransitionError
            If the transition is not allowed.
        """
        if not cls.can_transition(current, target):
            raise IllegalTransitionError(current.value, target.value)
        return target

    @classmethod
    def get_allowed_transitions(cls, current: PlanStatus) -> list[PlanStatus]:
        """Return all legal target statuses from *current*.

        Parameters
        ----------
        current : PlanStatus
            The current status of the plan.

        Returns
        -------
        list[PlanStatus]
            A (shallow-copied) list of allowed targets.  Empty for terminal
            states.
        """
        return list(cls.TRANSITIONS.get(current, []))


__all__ = [
    "IllegalTransitionError",
    "PlanStatus",
    "TreatmentPlanStateMachine",
]
