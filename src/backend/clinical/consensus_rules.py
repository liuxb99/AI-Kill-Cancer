"""
Consensus Rule Set — centralized thresholds for Tumor Board Consensus calculation.

All threshold values live here; the Consensus Engine reads from this module.
Changing a value here takes effect across the entire system on next load.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class SpecialtyWeight:
    """Default weights per specialty."""

    MEDICAL_ONCOLOGY: float = 1.0
    SURGICAL_ONCOLOGY: float = 0.9
    RADIATION_ONCOLOGY: float = 0.9
    PATHOLOGY: float = 0.8
    RADIOLOGY: float = 0.8
    GENOMICS: float = 0.7
    PHARMACY: float = 0.7
    NURSING: float = 0.5
    PALLIATIVE_CARE: float = 0.6


@dataclass(frozen=True)
class ConfidenceWeight:
    """Weight multipliers for confidence levels."""

    HIGH: float = 1.0
    MEDIUM: float = 0.7
    LOW: float = 0.4


@dataclass(frozen=True)
class ConsensusThresholds:
    """Thresholds that determine consensus outcome classification."""

    UNANIMOUS: float = 1.0  # 100%
    STRONG_CONSENSUS: float = 0.8  # >= 80%
    MAJORITY_CONSENSUS: float = 0.6  # >= 60%
    SPLIT_DECISION_UPPER: float = 0.55  # support between 40-55% is split
    MIN_OPINIONS: int = 2  # minimum opinions for valid consensus
    MIN_CONFIDENCE: float = 0.1  # minimum confidence to count
    ABSTAIN_WEIGHT: float = 0.0


@dataclass(frozen=True)
class ConsensusRuleSet:
    """Immutable rule set for consensus calculation.

    This is the primary entry point for consensus engine configuration.
    All thresholds are frozen after construction to ensure consistency.
    """

    specialty_weights: Dict[str, float] = field(default_factory=lambda: {
        "medical_oncology": 1.0,
        "surgical_oncology": 0.9,
        "radiation_oncology": 0.9,
        "pathology": 0.8,
        "radiology": 0.8,
        "genomics": 0.7,
        "pharmacy": 0.7,
        "nursing": 0.5,
        "palliative_care": 0.6,
    })
    confidence_high: float = 1.0
    confidence_medium: float = 0.7
    confidence_low: float = 0.4
    unanimous_threshold: float = 1.0
    strong_consensus_threshold: float = 0.8
    majority_consensus_threshold: float = 0.6
    split_decision_upper: float = 0.55
    min_opinions: int = 2
    min_confidence: float = 0.1
    abstain_weight: float = 0.0


# Singleton instance — import this across the application.
DEFAULT_RULES = ConsensusRuleSet()
