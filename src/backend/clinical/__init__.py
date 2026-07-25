"""Clinical context package — frozen snapshot models for reasoning & reporting."""

# Calculation trace (P3A-05)
from src.backend.clinical.calculation_trace import (
    CalculationTrace,
    TraceManager,
    TraceStep,
)

# Clinical decision engine (P3B-C1)
from src.backend.clinical.clinical_decision_engine import (
    ClinicalDecisionEngine,
    ClinicalDecisionResult,
)

# Decision rule set (P3B-C3)
from src.backend.clinical.decision_rules import DecisionRuleSet

# Drug ranking system (P3A-03)
from src.backend.clinical.drug_ranking import (
    ConflictScore,
    DrugRankingEngine,
    DrugRankingResult,
    EvidenceScore,
    OverallScore,
    Resistance,
    Sensitivity,
)

# Evidence weight / tier / confidence models
from src.backend.clinical.evidence_weight import (
    ConfidenceLevel,
    EvidenceLevel,
    EvidenceTier,
    EvidenceWeightConfig,
    WeightRegistry,
)

# Explainable recommendation (P3A-04)
from src.backend.clinical.explainable_recommendation import (
    ExplainableEngine,
    ExplanationFormatter,
    ReasonItem,
    RecommendationReason,
)
from src.backend.clinical.models import ClinicalContext

# Recommendation engine (P3A-01)
from src.backend.clinical.recommendation_engine import (
    DrugRanker,
    EvidenceAggregator,
    RecommendationEngine,
    RecommendationRule,
)

__all__ = [
    "ClinicalContext",
    "ClinicalDecisionEngine",
    "ClinicalDecisionResult",
    "ConfidenceLevel",
    # decision_rules
    "DecisionRuleSet",
    "EvidenceLevel",
    "EvidenceTier",
    "EvidenceWeightConfig",
    "WeightRegistry",
    # recommendation_engine
    "DrugRanker",
    "EvidenceAggregator",
    "RecommendationEngine",
    "RecommendationRule",
    # drug_ranking
    "ConflictScore",
    "DrugRankingEngine",
    "DrugRankingResult",
    "EvidenceScore",
    "OverallScore",
    "Resistance",
    "Sensitivity",
    # explainable_recommendation
    "ExplainableEngine",
    "ExplanationFormatter",
    "ReasonItem",
    "RecommendationReason",
    # calculation_trace
    "CalculationTrace",
    "TraceManager",
    "TraceStep",
]
