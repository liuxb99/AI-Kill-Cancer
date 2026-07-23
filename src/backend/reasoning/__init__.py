"""
Clinical Reasoning Layer — LLM-Assisted, Evidence-Grounded Clinical Reasoning.

LLM may only: summarize, explain, compare, identify conflicts, draft reasoning.
LLM must NOT: create evidence, create PMIDs, create drugs, modify evidence,
              replace DrugRankingEngine, prescribe, generate dosages.
"""

from src.backend.reasoning.conflicts import ConflictAnalyzer
from src.backend.reasoning.context import ReasoningContextBuilder
from src.backend.reasoning.llm import (
    DisabledLLMAdapter,
    LLMAdapter,
    LocalLLMAdapter,
    OpenAILikeAdapter,
    get_llm_adapter,
)
from src.backend.reasoning.models import (
    ClinicalReasoningResult,
    ReasoningDrugExplanation,
    ReasoningEvidenceCitation,
    ReasoningRunResponse,
    SafetyNotice,
)
from src.backend.reasoning.repository import ReasoningRunModel, ReasoningRunRepository
from src.backend.reasoning.service import ClinicalReasoningService
from src.backend.reasoning.validator import EvidenceCitationValidator, HallucinationGuard

__all__ = [
    "ClinicalReasoningService",
    "ReasoningContextBuilder",
    "EvidenceCitationValidator", "HallucinationGuard",
    "ConflictAnalyzer",
    "ReasoningRunRepository", "ReasoningRunModel",
    "ClinicalReasoningResult", "ReasoningRunResponse",
    "ReasoningEvidenceCitation", "ReasoningDrugExplanation",
    "SafetyNotice",
    "LLMAdapter", "OpenAILikeAdapter", "LocalLLMAdapter", "DisabledLLMAdapter",
    "get_llm_adapter",
]
