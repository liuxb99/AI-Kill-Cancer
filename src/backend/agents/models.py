"""
AgentOpinion model — a structured opinion produced by any agent in the
Phase 2b multi-agent system.

Each agent returns an ``AgentOpinion`` that includes a summary, pros/cons,
confidence level, and optional references with provenance metadata.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentOpinion(BaseModel):
    """A structured opinion produced by a clinical decision-support agent.

    Encapsulates the agent's assessment of a treatment or clinical-action
    option, including a plain-text summary, supporting and opposing
    arguments, a confidence rating, and reference citations.
    """

    agent_type: str
    """Identifier for the agent type that produced this opinion
    (e.g. ``"guideline_agent"``, ``"trial_agent"``)."""

    agent_version: str
    """Semantic version of the agent that produced this opinion."""

    summary: str
    """Concise plain-text summary of the agent's assessment."""

    pros: list[str] = Field(default_factory=list)
    """Supporting arguments or reasons in favour of the proposed action."""

    cons: list[str] = Field(default_factory=list)
    """Opposing arguments, risks, or reasons against the proposed action."""

    confidence: str = "medium"
    """Agent's confidence in its opinion — ``"high"``, ``"medium"``, or
    ``"low"``."""

    references: list[dict] = Field(default_factory=list)
    """Supporting references. Each item is a dictionary with keys
    ``source`` (str), ``citation`` (str), and ``url`` (str, optional)."""

    context_hash: str | None = None
    """SHA256 hash of the :class:`ClinicalContext` snapshot that this
    opinion is based on, for full traceability."""

    created_at: str = ""
    """ISO-8601 timestamp of when the opinion was created."""


__all__ = [
    "AgentOpinion",
]
