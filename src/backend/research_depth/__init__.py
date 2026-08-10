"""Research-only depth-analysis primitives for AI-Kill-Cancer."""

from .engine import (
    build_hypotheses,
    cohort_biomarker_stratification,
    evidence_conflict_groups,
    evidence_conflict_summary,
    outcome_feedback_summary,
    primary_conflict_summary,
)
from .lifecycle import (
    ALLOWED_HYPOTHESIS_STATUSES,
    load_hypothesis_versions,
    prioritize_research_tasks,
    transition_hypothesis_status,
)
from .orchestrator import execute_research_loop, research_input_fingerprint

__all__ = [
    "outcome_feedback_summary",
    "cohort_biomarker_stratification",
    "evidence_conflict_summary",
    "evidence_conflict_groups",
    "primary_conflict_summary",
    "build_hypotheses",
    "execute_research_loop",
    "research_input_fingerprint",
    "ALLOWED_HYPOTHESIS_STATUSES",
    "transition_hypothesis_status",
    "prioritize_research_tasks",
    "load_hypothesis_versions",
]
