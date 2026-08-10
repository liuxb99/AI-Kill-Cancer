from types import SimpleNamespace

from src.backend.domain.enums import (
    EvidenceDirectionEnum,
    EvidenceLevelEnum,
    EvidenceTypeEnum,
)
from src.backend.research_depth.engine import (
    build_hypotheses,
    cohort_biomarker_stratification,
    evidence_conflict_groups,
    evidence_conflict_summary,
    outcome_feedback_summary,
    primary_conflict_summary,
)


def _case(
    case_id: str,
    *,
    gene: str | None,
    outcome: str | None,
    stage: str = "Stage III",
    sex: str = "F",
    age: str = "40-49",
):
    variants = []
    if gene:
        variants.append(SimpleNamespace(gene=gene, protein_change="p.V600E"))
    outcomes = []
    if outcome is not None:
        outcomes.append(SimpleNamespace(outcome_type="recurrence", outcome_value=outcome))
    return SimpleNamespace(
        case_id=case_id,
        variants=variants,
        outcomes=outcomes,
        pathologic_stage=stage,
        sex=sex,
        age_range=age,
        days_to_last_follow_up=None,
        days_to_death=None,
    )


def _evidence(
    direction,
    level,
    source,
    record,
    *,
    cancer="PTC",
    drug=None,
    variant=None,
    evidence_type=EvidenceTypeEnum.PREDICTIVE,
):
    return SimpleNamespace(
        id=record,
        gene_symbol="BRAF",
        cancer_type=cancer,
        drug_id=drug,
        variant_id=variant,
        evidence_type=evidence_type,
        evidence_direction=direction,
        evidence_level=level,
        source_name=source,
        source_record_id=record,
        summary=f"summary-{record}",
        limitations=None,
    )


def test_outcome_feedback_keeps_denominator_missingness_and_research_boundary():
    cases = [
        _case("A", gene="BRAF", outcome="recurrence"),
        _case("B", gene="BRAF", outcome="no recurrence"),
        _case("C", gene=None, outcome="unknown vocabulary"),
        _case("D", gene=None, outcome=None),
    ]

    result = outcome_feedback_summary(cases)

    assert result["cohort_size"] == 4
    assert result["cases_with_outcomes"] == 3
    assert result["outcome_coverage"] == 0.75
    recurrence = result["outcomes"][0]
    assert recurrence["known_binary_observations"] == 2
    assert recurrence["events"] == 1
    assert recurrence["non_events"] == 1
    assert recurrence["unknown_or_nonbinary"] == 1
    assert recurrence["event_proportion"] == 0.5
    assert result["selection_boundary"] == "outcome_blind_selection_required"
    assert result["interpretation"] == "descriptive_association_only"


def test_biomarker_stratification_separates_groups_and_exposes_confounding():
    cases = [
        _case("A", gene="BRAF", outcome="recurrence", stage="Stage IV"),
        _case("B", gene="BRAF", outcome="recurrence", stage="Stage IV"),
        _case("C", gene=None, outcome="no recurrence", stage="Stage I"),
        _case("D", gene=None, outcome="no recurrence", stage="Stage I"),
    ]

    result = cohort_biomarker_stratification(cases, "braf", "p.V600E")

    assert result["biomarker"] == {"gene": "BRAF", "protein_change": "p.V600E"}
    assert result["positive"]["cases"] == 2
    assert result["negative"]["cases"] == 2
    assert result["positive"]["outcome_feedback"]["outcomes"][0]["event_proportion"] == 1.0
    assert result["negative"]["outcome_feedback"]["outcomes"][0]["event_proportion"] == 0.0
    assert result["causal_inference"] is False
    assert result["small_sample_warning"] is True
    assert "baseline_imbalance:pathologic_stage" in result["confounding_warnings"]


def test_evidence_conflict_preserves_high_level_dissent():
    items = [
        _evidence(EvidenceDirectionEnum.SUPPORTING, EvidenceLevelEnum.LEVEL_1, "SourceA", "S1"),
        _evidence(EvidenceDirectionEnum.SUPPORTING, EvidenceLevelEnum.LEVEL_4, "SourceB", "S2"),
        _evidence(EvidenceDirectionEnum.CONFLICTING, EvidenceLevelEnum.LEVEL_1, "SourceC", "C1"),
    ]

    result = evidence_conflict_summary(items)

    assert result["counts"]["supporting"] == 2
    assert result["counts"]["conflicting"] == 1
    assert result["conflict_severity"] == "high"
    assert result["source_diversity"] == 3
    assert result["majority_vote_only"] is False
    assert result["opposes"][0]["source_record_id"] == "C1"
    assert "counter_evidence_is_not_weaker_than_supporting_evidence" in result["unresolved_reasons"]


def test_conflicts_are_not_invented_across_different_scientific_contexts():
    items = [
        _evidence(
            EvidenceDirectionEnum.SUPPORTING,
            EvidenceLevelEnum.LEVEL_1,
            "PTCSource",
            "PTC-S",
            cancer="PTC",
        ),
        _evidence(
            EvidenceDirectionEnum.CONFLICTING,
            EvidenceLevelEnum.LEVEL_1,
            "ATCSource",
            "ATC-C",
            cancer="ATC",
        ),
    ]

    groups = evidence_conflict_groups(items)
    assert len(groups) == 2
    assert all(group["conflict_severity"] == "none_detected" for group in groups)
    primary = primary_conflict_summary(items)
    assert primary["conflict_severity"] == "none_detected"


def test_hypothesis_generation_is_falsifiable_and_nonclinical():
    cases = [
        _case("A", gene="BRAF", outcome="recurrence"),
        _case("B", gene="BRAF", outcome="recurrence"),
        _case("C", gene=None, outcome="no recurrence"),
        _case("D", gene=None, outcome="no recurrence"),
    ]
    stratification = cohort_biomarker_stratification(cases, "BRAF", "p.V600E")
    conflict = primary_conflict_summary(
        [
            _evidence(EvidenceDirectionEnum.SUPPORTING, EvidenceLevelEnum.LEVEL_2, "A", "1"),
            _evidence(EvidenceDirectionEnum.CONFLICTING, EvidenceLevelEnum.LEVEL_2, "B", "2"),
        ]
    )

    hypotheses = build_hypotheses(stratification, conflict)

    assert hypotheses
    association = hypotheses[0]
    assert association["type"] == "cohort_outcome_association"
    assert association["clinical_use"] is False
    assert association["falsification_criteria"]
    assert association["next_data_needed"]
    assert association["counter_evidence"]
    assert association["rationale"]["outcome_type"] == "recurrence"
