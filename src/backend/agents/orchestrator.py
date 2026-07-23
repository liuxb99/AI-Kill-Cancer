"""
AgentOrchestrator — parallel executor for the Phase 2b multi-agent system.

The orchestrator manages all six clinical decision-support agents, runs them
in parallel via ``asyncio.gather``, collects their structured opinions, and
provides convenience filtering by agent type.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.clinical.evidence_models import EvidenceBundle
from src.backend.clinical.models import ClinicalContext

from .base import BaseAgent
from .clinical_trial_agent import ClinicalTrialAgent
from .diagnosis_agent import DiagnosisAgent
from .drug_agent import DrugAgent
from .guideline_agent import GuidelineAgent
from .models import AgentOpinion
from .resistance_agent import ResistanceAgent
from .variant_agent import VariantAgent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Orchestrate parallel execution of all clinical decision-support agents.

    Maintains a registry of every available agent and provides methods to
    run them concurrently, handling per-agent failures gracefully so that
    one failing agent does not block the others.

    Parameters
    ----------
    db : AsyncSession
        SQLAlchemy asynchronous database session shared by all agents.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._agents: list[BaseAgent] = [
            DiagnosisAgent(db),
            VariantAgent(db),
            DrugAgent(db),
            ResistanceAgent(db),
            GuidelineAgent(db),
            ClinicalTrialAgent(db),
        ]

    # ── Public API ──────────────────────────────────────────────────────────

    async def run_all(
        self,
        context: ClinicalContext,
        evidence: EvidenceBundle,
    ) -> list[AgentOpinion]:
        """Run all registered agents in parallel and collect their opinions.

        Each agent receives the same ``context`` and ``evidence`` snapshot.
        Agents are executed concurrently via :func:`asyncio.gather`. If an
        individual agent raises an exception it is caught, logged, and
        replaced with an ``AgentOpinion`` carrying the error details so that
        other agents are not affected.

        Parameters
        ----------
        context : ClinicalContext
            Frozen patient / case snapshot for the agents to analyse.
        evidence : EvidenceBundle
            Aggregated evidence items from all knowledge sources.

        Returns
        -------
        list[AgentOpinion]
            One opinion per agent, in the same order as the registered
            agent list. Exceptions are converted to error-bearing opinions.
        """
        return await self._run_agents(self._agents, context, evidence)

    async def run_by_type(
        self,
        context: ClinicalContext,
        evidence: EvidenceBundle,
        agent_types: list[str],
    ) -> list[AgentOpinion]:
        """Run only agents whose ``agent_type`` matches one of the given types.

        Parameters
        ----------
        context : ClinicalContext
            Frozen patient / case snapshot for the agents to analyse.
        evidence : EvidenceBundle
            Aggregated evidence items from all knowledge sources.
        agent_types : list[str]
            Agent type identifiers to include (e.g. ``["drug", "variant"]``).

        Returns
        -------
        list[AgentOpinion]
            Opinions from the matching agents, in the order they were
            originally registered.
        """
        matched = [
            agent
            for agent in self._agents
            if agent.agent_type in agent_types
        ]
        return await self._run_agents(matched, context, evidence)

    # ── Internal helpers ───────────────────────────────────────────────────

    async def _run_agents(
        self,
        agents: list[BaseAgent],
        context: ClinicalContext,
        evidence: EvidenceBundle,
    ) -> list[AgentOpinion]:
        """Execute a list of agents in parallel and collect their opinions.

        Parameters
        ----------
        agents : list[BaseAgent]
            The subset of agents to execute.
        context : ClinicalContext
            Clinical context snapshot.
        evidence : EvidenceBundle
            Evidence bundle.

        Returns
        -------
        list[AgentOpinion]
            Opinions in the same order as *agents*.
        """
        coros = [agent.analyze(context, evidence) for agent in agents]
        results: list[AgentOpinion | BaseException] = await asyncio.gather(
            *coros,
            return_exceptions=True,
        )

        opinions: list[AgentOpinion] = []
        for agent, result in zip(agents, results, strict=False):
            if isinstance(result, AgentOpinion):
                opinions.append(result)
            else:
                # result is an Exception instance
                error_msg = _format_exception(result)
                logger.exception(
                    "Agent %s failed: %s", agent.agent_type, error_msg
                )
                opinions.append(
                    AgentOpinion(
                        agent_type=agent.agent_type,
                        agent_version=agent.agent_version,
                        summary=f"Agent encountered an error: {error_msg}",
                        confidence="low",
                        pros=[],
                        cons=[],
                        references=[],
                    )
                )

        return opinions


def _format_exception(exc: BaseException | None) -> str:
    """Format an exception into a human-readable error message.

    Parameters
    ----------
    exc : BaseException or None
        The exception to format.

    Returns
    -------
    str
        A human-readable error description.
    """
    if exc is None:
        return "Unknown error (None exception)"
    # typing.cast not needed: BaseException always has args
    return f"{type(exc).__name__}: {exc}"
