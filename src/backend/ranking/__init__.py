"""
Drug Ranking Engine — deterministic, evidence-based drug ranking.

Components:
- EvidenceScorer: scores evidence items by match quality
- ResistanceScorer: penalizes resistance evidence
- SensitivityScorer: rewards sensitivity evidence
- GuidelineScorer: rewards guideline-backed evidence
- RegulatoryScorer: rewards FDA/EMA approved drugs
- ClinicalTrialScorer: rewards clinical trial evidence
- ConflictPenalty: penalizes conflicting evidence
- UncertaintyPenalty: penalizes uncertain evidence
- DrugRankingEngine: orchestrates all scorers into final rankings
"""

from src.backend.ranking.engine import DrugRankingEngine
from src.backend.ranking.models import (
    DrugRankingResult,
    DrugRankingRunResponse,
    DrugRankingRunStatus,
    DrugRankItem,
    ScoreBreakdown,
)
from src.backend.ranking.penalties import ConflictPenalty, UncertaintyPenalty
from src.backend.ranking.scorers import (
    ClinicalTrialScorer,
    EvidenceScorer,
    GuidelineScorer,
    RegulatoryScorer,
    ResistanceScorer,
    SensitivityScorer,
)

__all__ = [
    "EvidenceScorer", "ResistanceScorer", "SensitivityScorer",
    "GuidelineScorer", "RegulatoryScorer", "ClinicalTrialScorer",
    "ConflictPenalty", "UncertaintyPenalty",
    "DrugRankingEngine",
    "DrugRankingResult", "DrugRankItem", "ScoreBreakdown",
    "DrugRankingRunResponse", "DrugRankingRunStatus",
]
