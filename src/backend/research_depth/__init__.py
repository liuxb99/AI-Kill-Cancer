"""Research-only depth-analysis primitives for AI-Kill-Cancer."""

from .engine import (
    build_hypotheses,
    cohort_biomarker_stratification,
    evidence_conflict_summary,
    outcome_feedback_summary,
)
from .orchestrator import execute_research_loop, research_input_fingerprint

__all__ = [
    "outcome_feedback_summary",
    "cohort_biomarker_stratification",
    "evidence_conflict_summary",
    "build_hypotheses",
    "execute_research_loop",
    "research_input_fingerprint",
]
