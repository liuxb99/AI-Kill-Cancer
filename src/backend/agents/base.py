"""
BaseAgent abstract base class for all clinical decision-support agents.

Every agent in the Phase 2b multi-agent system implements this interface,
providing an ``analyze`` method that accepts a :class:`ClinicalContext` and
an :class:`EvidenceBundle` and returns a structured :class:`AgentOpinion`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.clinical.evidence_models import EvidenceBundle
from src.backend.clinical.models import ClinicalContext

from .models import AgentOpinion


class BaseAgent(ABC):
    """Abstract base for all clinical decision-support agents.

    Subclasses must set ``agent_type`` and ``agent_version`` as class
    attributes and implement :meth:`analyze`.

    Parameters
    ----------
    db : AsyncSession
        SQLAlchemy asynchronous database session used for any persistence
        or lookup the agent requires.
    """

    agent_type: str = "base"
    """Identifier for the agent type (e.g. ``"guideline_agent"``)."""

    agent_version: str = "1.0.0"
    """Semantic version of the agent implementation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @abstractmethod
    async def analyze(
        self,
        context: ClinicalContext,
        evidence: EvidenceBundle,
    ) -> AgentOpinion:
        """Analyse the clinical context and evidence, returning an opinion.

        Every concrete agent must implement this method. It receives a
        frozen snapshot of the patient's clinical data and an aggregated
        bundle of evidence items, and must return a fully populated
        :class:`AgentOpinion`.

        Parameters
        ----------
        context : ClinicalContext
            Frozen patient / case snapshot including diagnosis, biomarkers,
            variants, treatment history, and performance status.
        evidence : EvidenceBundle
            Aggregated evidence items from all configured knowledge sources.

        Returns
        -------
        AgentOpinion
            The agent's structured opinion on the proposed clinical action.
        """
        ...

    def validate_opinion(self, opinion: AgentOpinion) -> list[str]:
        """Validate the completeness and integrity of an agent opinion.

        Checks that required fields are populated, ``confidence`` is one of
        the recognised values, and each reference entry carries the
        mandatory keys.

        Parameters
        ----------
        opinion : AgentOpinion
            The opinion to validate.

        Returns
        -------
        list[str]
            A list of validation-error messages. An empty list means the
            opinion is valid.
        """
        errors: list[str] = []

        if not opinion.agent_type:
            errors.append("agent_type must not be empty")

        if not opinion.agent_version:
            errors.append("agent_version must not be empty")

        if not opinion.summary:
            errors.append("summary must not be empty")

        valid_confidences = {"high", "medium", "low"}
        if opinion.confidence not in valid_confidences:
            errors.append(
                f"confidence must be one of {sorted(valid_confidences)}, "
                f"got {opinion.confidence!r}"
            )

        if not opinion.created_at:
            errors.append("created_at must be set (ISO-8601 timestamp)")

        for i, ref in enumerate(opinion.references):
            if not isinstance(ref, dict):
                errors.append(f"references[{i}] must be a dict, got {type(ref).__name__}")
                continue
            if "source" not in ref:
                errors.append(f"references[{i}] is missing required key 'source'")
            if "citation" not in ref:
                errors.append(f"references[{i}] is missing required key 'citation'")

        return errors


__all__ = [
    "BaseAgent",
]
