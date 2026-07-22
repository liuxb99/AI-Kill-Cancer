"""Agents package — Phase 2b multi-agent system with BaseAgent abstractions."""

from src.backend.agents.base import BaseAgent
from src.backend.agents.consensus import ConsensusEngine, ConsensusResult
from src.backend.agents.models import AgentOpinion
from src.backend.agents.orchestrator import AgentOrchestrator

__all__ = [
    "AgentOrchestrator",
    "BaseAgent",
    "AgentOpinion",
    "ConsensusEngine",
    "ConsensusResult",
]
