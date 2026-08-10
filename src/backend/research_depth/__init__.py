"""Research-only depth-analysis primitives for AI-Kill-Cancer."""

from .engine import (
    build_hypotheses,
    cohort_biomarker_stratification,
    evidence_conflict_summary,
    outcome_feedback_summary,
)

__all__ = [
    "outcome_feedback_summary",
    "cohort_biomarker_stratification",
    "evidence_conflict_summary",
    "build_hypotheses",
]
