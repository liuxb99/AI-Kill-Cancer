"""
Pydantic domain models for drug ranking engine results.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class ScoreBreakdown(BaseModel):
    """Per-scorer score breakdown for a single drug."""
    evidence_score: float = 0.0
    sensitivity_score: float = 0.0
    resistance_score: float = 0.0
    guideline_score: float = 0.0
    regulatory_score: float = 0.0
    clinical_trial_score: float = 0.0
    conflict_penalty: float = 0.0
    uncertainty_penalty: float = 0.0

    def total(self) -> float:
        return (self.evidence_score + self.sensitivity_score + self.resistance_score
                + self.guideline_score + self.regulatory_score + self.clinical_trial_score
                + self.conflict_penalty + self.uncertainty_penalty)


class DrugRankItem(BaseModel):
    """A single drug in a ranking result."""
    drug_name: str
    rank: int
    total_score: float
    score_breakdown: ScoreBreakdown
    supporting_evidence_ids: list[str] = []
    conflicting_evidence_ids: list[str] = []
    resistance_evidence_ids: list[str] = []
    disease_match: str = ""  # "exact", "related", "different", "unknown"
    variant_match_scope: str = ""  # "exact_variant", "gene_level_only", etc.
    source_count: int = 0
    independent_source_count: int = 0
    guideline_support: bool = False
    regulatory_approval: bool = False
    confidence: str = ""  # "high", "medium", "low"
    limitations: list[str] = []


class DrugRankingResult(BaseModel):
    """Complete ranking result with metadata."""
    model_config = ConfigDict(from_attributes=True)

    id: str = ""
    variant_id: Optional[str] = None
    variant_ids: list[str] = []
    case_id: Optional[str] = None
    gene_symbol: Optional[str] = None
    disease: Optional[str] = None
    rankings: list[DrugRankItem] = []
    ranking_count: int = 0
    ranking_algorithm_version: str = "0.5.0"
    normalization_rule_version: str = "1.0.0"
    evidence_snapshot_id: Optional[str] = None
    source_versions: dict = {}
    git_commit: str = ""
    status: str = "completed"
    warnings: list[str] = []
    errors: list[str] = []
    created_at: str = ""


class DrugRankingRunResponse(BaseModel):
    """API response for a ranking run."""
    run_id: str
    status: str
    ranking: Optional[DrugRankingResult] = None
    message: str = ""


class DrugRankingRunStatus(BaseModel):
    """Status of a ranking run."""
    run_id: str
    status: str
    progress: str = ""
    created_at: str = ""
