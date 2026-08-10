from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from src.backend.domain.enums import EvidenceDirectionEnum, EvidenceLevelEnum


@dataclass(frozen=True)
class _OutcomeObservation:
    case_id: str
    outcome_type: str
    outcome_value: str | None


def _norm(value: str | None) -> str:
    return (value or "").strip().upper()


def _event_like(value: str | None) -> bool | None:
    """Map common research outcome strings to descriptive event/no-event/unknown.

    This intentionally does not infer prognosis or treatment response. Unknown
    vocabulary remains unknown instead of being forced into a binary label.
    """
    text = _norm(value)
    if not text:
        return None
    positives = {
        "DECEASED",
        "DEAD",
        "RECURRENCE",
        "RECURRENT",
        "PROGRESSION",
        "PROGRESSIVE DISEASE",
        "EVENT",
        "YES",
        "TRUE",
        "1",
    }
    negatives = {
        "ALIVE",
        "NO RECURRENCE",
        "DISEASE FREE",
        "NO EVENT",
        "NO",
        "FALSE",
        "0",
    }
    if text in positives:
        return True
    if text in negatives:
        return False
    return None


def outcome_feedback_summary(cases: Sequence[Any]) -> dict[str, Any]:
    """Aggregate post-selection outcomes for research feedback only.

    The caller must select the cohort without outcome fields. The output keeps
    denominator/missingness explicit and never emits patient-level prognosis.
    """
    observations: list[_OutcomeObservation] = []
    for case in cases:
        for outcome in getattr(case, "outcomes", []) or []:
            observations.append(
                _OutcomeObservation(
                    case_id=str(getattr(case, "case_id", "")),
                    outcome_type=str(getattr(outcome, "outcome_type", "unknown")),
                    outcome_value=getattr(outcome, "outcome_value", None),
                )
            )

    by_type: dict[str, list[_OutcomeObservation]] = defaultdict(list)
    for item in observations:
        by_type[item.outcome_type].append(item)

    summaries: list[dict[str, Any]] = []
    for outcome_type in sorted(by_type):
        rows = by_type[outcome_type]
        classified = [_event_like(item.outcome_value) for item in rows]
        known = [value for value in classified if value is not None]
        events = sum(1 for value in known if value)
        non_events = sum(1 for value in known if not value)
        missing = len(rows) - len(known)
        summaries.append(
            {
                "outcome_type": outcome_type,
                "observations": len(rows),
                "known_binary_observations": len(known),
                "events": events,
                "non_events": non_events,
                "unknown_or_nonbinary": missing,
                "event_proportion": round(events / len(known), 4) if known else None,
                "missingness": round(missing / len(rows), 4) if rows else 0.0,
                "value_distribution": dict(
                    Counter((item.outcome_value or "unknown") for item in rows)
                ),
            }
        )

    total_cases = len(cases)
    cases_with_outcomes = len({item.case_id for item in observations if item.case_id})
    coverage = round(cases_with_outcomes / total_cases, 4) if total_cases else 0.0
    confidence = "low" if total_cases < 20 or coverage < 0.5 else "moderate"
    if total_cases >= 100 and coverage >= 0.8:
        confidence = "descriptive_high_coverage"

    return {
        "cohort_size": total_cases,
        "cases_with_outcomes": cases_with_outcomes,
        "outcome_coverage": coverage,
        "outcomes": summaries,
        "research_confidence": confidence,
        "selection_boundary": "outcome_blind_selection_required",
        "interpretation": "descriptive_association_only",
        "disclaimer": (
            "Post-selection research outcome summary only. It is not prognosis, "
            "causal inference, treatment efficacy, diagnosis, or clinical advice."
        ),
    }


def _case_has_biomarker(case: Any, gene: str, protein_change: str | None = None) -> bool:
    target_gene = _norm(gene)
    target_protein = _norm(protein_change)
    for variant in getattr(case, "variants", []) or []:
        if _norm(getattr(variant, "gene", None)) != target_gene:
            continue
        if target_protein and _norm(getattr(variant, "protein_change", None)) != target_protein:
            continue
        return True
    return False


def cohort_biomarker_stratification(
    cases: Sequence[Any],
    gene: str,
    protein_change: str | None = None,
) -> dict[str, Any]:
    """Compare biomarker-positive and negative cohorts descriptively."""
    positive = [case for case in cases if _case_has_biomarker(case, gene, protein_change)]
    negative = [case for case in cases if case not in positive]
    positive_outcomes = outcome_feedback_summary(positive)
    negative_outcomes = outcome_feedback_summary(negative)

    return {
        "biomarker": {
            "gene": gene.strip().upper(),
            "protein_change": protein_change.strip() if protein_change else None,
        },
        "total_cases": len(cases),
        "positive": {
            "cases": len(positive),
            "fraction": round(len(positive) / len(cases), 4) if cases else 0.0,
            "outcome_feedback": positive_outcomes,
        },
        "negative": {
            "cases": len(negative),
            "fraction": round(len(negative) / len(cases), 4) if cases else 0.0,
            "outcome_feedback": negative_outcomes,
        },
        "small_sample_warning": len(positive) < 20 or len(negative) < 20,
        "analysis_type": "descriptive_cohort_stratification",
        "causal_inference": False,
        "disclaimer": (
            "Biomarker stratification is descriptive research analysis only. "
            "Differences between groups do not establish causality or clinical utility."
        ),
    }


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _level_weight(level: Any) -> float:
    raw = _enum_value(level)
    return {
        EvidenceLevelEnum.LEVEL_1.value: 5.0,
        EvidenceLevelEnum.LEVEL_2.value: 4.0,
        EvidenceLevelEnum.LEVEL_3.value: 3.0,
        EvidenceLevelEnum.LEVEL_4.value: 2.0,
        EvidenceLevelEnum.LEVEL_5.value: 1.0,
        EvidenceLevelEnum.NOT_ASSESSED.value: 0.5,
    }.get(raw, 0.5)


def evidence_conflict_summary(evidence_items: Iterable[Any]) -> dict[str, Any]:
    """Summarize agreement/dissent without hiding high-level counter-evidence."""
    rows = list(evidence_items)
    buckets: dict[str, list[Any]] = defaultdict(list)
    for item in rows:
        buckets[_enum_value(getattr(item, "evidence_direction", "insufficient"))].append(item)

    supporting = buckets.get(EvidenceDirectionEnum.SUPPORTING.value, [])
    conflicting = buckets.get(EvidenceDirectionEnum.CONFLICTING.value, [])
    neutral = buckets.get(EvidenceDirectionEnum.NEUTRAL.value, [])
    insufficient = buckets.get(EvidenceDirectionEnum.INSUFFICIENT.value, [])
    decisive = len(supporting) + len(conflicting)
    agreement_ratio = round(max(len(supporting), len(conflicting)) / decisive, 4) if decisive else None

    support_weight = sum(_level_weight(getattr(item, "evidence_level", None)) for item in supporting)
    conflict_weight = sum(_level_weight(getattr(item, "evidence_level", None)) for item in conflicting)
    strongest_support = max((_level_weight(getattr(item, "evidence_level", None)) for item in supporting), default=0.0)
    strongest_conflict = max((_level_weight(getattr(item, "evidence_level", None)) for item in conflicting), default=0.0)

    if supporting and conflicting:
        severity = "high" if strongest_support >= 4.0 and strongest_conflict >= 4.0 else "moderate"
    elif decisive == 0:
        severity = "insufficient"
    else:
        severity = "none_detected"

    source_names = sorted({str(getattr(item, "source_name", "unknown")) for item in rows})

    def references(items: Sequence[Any]) -> list[dict[str, Any]]:
        return [
            {
                "id": str(getattr(item, "id", "")),
                "source_name": getattr(item, "source_name", None),
                "source_record_id": getattr(item, "source_record_id", None),
                "evidence_level": _enum_value(getattr(item, "evidence_level", "not_assessed")),
                "summary": getattr(item, "summary", None),
                "limitations": getattr(item, "limitations", None),
            }
            for item in items
        ]

    unresolved: list[str] = []
    if supporting and conflicting:
        unresolved.append("both_supporting_and_conflicting_evidence_present")
    if len(source_names) < 2 and rows:
        unresolved.append("limited_source_diversity")
    if neutral or insufficient:
        unresolved.append("neutral_or_insufficient_evidence_present")
    if strongest_conflict >= strongest_support and conflicting:
        unresolved.append("counter_evidence_is_not_weaker_than_supporting_evidence")

    return {
        "total": len(rows),
        "counts": {
            "supporting": len(supporting),
            "conflicting": len(conflicting),
            "neutral": len(neutral),
            "insufficient": len(insufficient),
        },
        "weighted_support": round(support_weight, 3),
        "weighted_conflict": round(conflict_weight, 3),
        "agreement_ratio": agreement_ratio,
        "conflict_severity": severity,
        "source_diversity": len(source_names),
        "sources": source_names,
        "supports": references(supporting),
        "opposes": references(conflicting),
        "unresolved_reasons": unresolved,
        "consensus_method": "direction_counts_plus_evidence_level_weighting",
        "majority_vote_only": False,
    }


def build_hypotheses(
    stratification: dict[str, Any],
    conflict: dict[str, Any],
    *,
    max_items: int = 3,
) -> list[dict[str, Any]]:
    """Generate falsifiable research hypotheses from structured observations."""
    biomarker = stratification["biomarker"]
    positive = stratification["positive"]
    negative = stratification["negative"]
    hypotheses: list[dict[str, Any]] = []

    positive_outcomes = {
        item["outcome_type"]: item
        for item in positive["outcome_feedback"].get("outcomes", [])
    }
    negative_outcomes = {
        item["outcome_type"]: item
        for item in negative["outcome_feedback"].get("outcomes", [])
    }

    for outcome_type in sorted(set(positive_outcomes) & set(negative_outcomes)):
        p = positive_outcomes[outcome_type].get("event_proportion")
        n = negative_outcomes[outcome_type].get("event_proportion")
        if p is None or n is None:
            continue
        delta = round(p - n, 4)
        if abs(delta) < 0.1:
            continue
        direction = "higher" if delta > 0 else "lower"
        hypotheses.append(
            {
                "type": "cohort_outcome_association",
                "claim": (
                    f"{biomarker['gene']}"
                    f"{(' ' + biomarker['protein_change']) if biomarker.get('protein_change') else ''} "
                    f"positive PTC research cases may show a {direction} descriptive "
                    f"{outcome_type} event proportion than biomarker-negative cases."
                ),
                "rationale": {
                    "positive_event_proportion": p,
                    "negative_event_proportion": n,
                    "absolute_difference": delta,
                },
                "supporting_observations": ["outcome_blind_biomarker_stratification", "post_selection_outcome_summary"],
                "counter_evidence": conflict.get("opposes", []),
                "uncertainties": [
                    "observational_association",
                    "possible_confounding",
                    "missing_outcome_data",
                    "small_sample" if stratification.get("small_sample_warning") else "sample_size_not_flagged_small",
                ],
                "falsification_criteria": (
                    "In an independent, pre-specified cohort using outcome-blind selection, "
                    "the event-proportion difference is absent, reverses direction, or is "
                    "explained by measured confounders."
                ),
                "next_data_needed": [
                    "independent cohort",
                    "higher outcome completeness",
                    "pre-specified confounder set",
                    "time-to-event data when appropriate",
                ],
                "clinical_use": False,
            }
        )

    if conflict.get("conflict_severity") in {"moderate", "high"}:
        hypotheses.append(
            {
                "type": "evidence_conflict_resolution",
                "claim": (
                    f"The research evidence associated with {biomarker['gene']} may be "
                    "context-dependent because both supporting and conflicting evidence are present."
                ),
                "rationale": {
                    "conflict_severity": conflict.get("conflict_severity"),
                    "weighted_support": conflict.get("weighted_support"),
                    "weighted_conflict": conflict.get("weighted_conflict"),
                    "source_diversity": conflict.get("source_diversity"),
                },
                "supporting_observations": conflict.get("supports", []),
                "counter_evidence": conflict.get("opposes", []),
                "uncertainties": conflict.get("unresolved_reasons", []),
                "falsification_criteria": (
                    "A harmonized context-stratified evidence review shows that the apparent "
                    "conflict disappears after matching cancer, molecular, intervention, and endpoint contexts."
                ),
                "next_data_needed": [
                    "context-normalized evidence records",
                    "independent source replication",
                    "explicit endpoint harmonization",
                ],
                "clinical_use": False,
            }
        )

    return hypotheses[:max_items]
