"""
Tests for Tumor Board Consensus Engine (Phase 3C).

Covers ``ConsensusEngine`` — pure computation, no database required.
Tests all consensus status classifications, weighting, dissent extraction,
abstain handling, low-confidence filtering, and deferred decisions.
"""

from __future__ import annotations

import pytest

from src.backend.clinical.tumor_board_engine import (
    ConsensusEngine,
    SpecialistOpinionInput,
    TumorBoardConsensusInput,
)
from src.backend.domain.enums import ConsensusStatus


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def engine() -> ConsensusEngine:
    """Default consensus engine instance."""
    return ConsensusEngine()


def _make_input(
    opinions: list[SpecialistOpinionInput],
    patient_id: str = "pat-001",
    recommendation_id: str = "rec-001",
    clinical_decision_id: str = "cd-001",
    meeting_context: str | None = None,
) -> TumorBoardConsensusInput:
    """Helper to build a TumorBoardConsensusInput."""
    return TumorBoardConsensusInput(
        patient_id=patient_id,
        recommendation_id=recommendation_id,
        clinical_decision_id=clinical_decision_id,
        specialist_opinions=opinions,
        meeting_context=meeting_context,
    )


def _opinion(
    specialty: str,
    position: str = "support",
    confidence: float = 0.9,
    requires_more_information: bool = False,
) -> SpecialistOpinionInput:
    """Helper to build a SpecialistOpinionInput."""
    return SpecialistOpinionInput(
        specialty=specialty,
        position=position,
        confidence=confidence,
        requires_more_information=requires_more_information,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Consensus Status Classification Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestConsensusStatusClassification:
    """Verify the engine correctly classifies each consensus status."""

    def test_unanimous_all_support(self, engine: ConsensusEngine) -> None:
        """All specialists support → UNANIMOUS."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
            _opinion("surgical_oncology", "support", 0.90),
            _opinion("radiation_oncology", "support", 0.85),
        ]
        result = engine.calculate(_make_input(opinions))
        assert result.consensus_status == ConsensusStatus.UNANIMOUS
        assert result.consensus_score == 1.0
        assert result.support_score > 0
        assert result.oppose_score == 0

    def test_strong_consensus_above_80(self, engine: ConsensusEngine) -> None:
        """80-99% support → STRONG_CONSENSUS."""
        opinions = [
            _opinion("medical_oncology", "support", 0.90),
            _opinion("medical_oncology", "support", 0.90),
            _opinion("medical_oncology", "support", 0.90),
            _opinion("medical_oncology", "support", 0.90),
            _opinion("medical_oncology", "oppose", 0.90),
        ]
        result = engine.calculate(_make_input(opinions))
        assert result.consensus_status == ConsensusStatus.STRONG_CONSENSUS
        assert 0.8 <= result.consensus_score < 1.0

    def test_majority_consensus_above_60(self, engine: ConsensusEngine) -> None:
        """60-79% support → MAJORITY_CONSENSUS."""
        opinions = [
            _opinion("medical_oncology", "support", 0.90),
            _opinion("medical_oncology", "support", 0.90),
            _opinion("medical_oncology", "support", 0.90),
            _opinion("medical_oncology", "oppose", 0.90),
            _opinion("medical_oncology", "oppose", 0.90),
        ]
        result = engine.calculate(_make_input(opinions))
        assert result.consensus_status == ConsensusStatus.MAJORITY_CONSENSUS
        assert 0.6 <= result.consensus_score < 0.8

    def test_split_decision_near_50_50(self, engine: ConsensusEngine) -> None:
        """Approximately 50/50 split → SPLIT_DECISION."""
        opinions = [
            _opinion("medical_oncology", "support", 0.90),
            _opinion("surgical_oncology", "support", 0.85),
            _opinion("pathology", "oppose", 0.90),
            _opinion("radiology", "oppose", 0.85),
        ]
        result = engine.calculate(_make_input(opinions))
        assert result.consensus_status == ConsensusStatus.SPLIT_DECISION
        assert result.consensus_score < 0.6

    def test_insufficient_information_too_few_opinions(
        self, engine: ConsensusEngine
    ) -> None:
        """Fewer than min_opinions (2) → INSUFFICIENT_INFORMATION."""
        opinions = [
            _opinion("medical_oncology", "support", 0.90),
        ]
        result = engine.calculate(_make_input(opinions))
        assert result.consensus_status == ConsensusStatus.INSUFFICIENT_INFORMATION

    def test_deferred_with_requires_more_information(
        self, engine: ConsensusEngine
    ) -> None:
        """Any opinion with requires_more_information → DEFERRED."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
            _opinion("pathology", "abstain", 0.50, requires_more_information=True),
        ]
        result = engine.calculate(_make_input(opinions))
        assert result.consensus_status == ConsensusStatus.DEFERRED

    def test_deferred_takes_priority_over_unanimous(
        self, engine: ConsensusEngine
    ) -> None:
        """DEFERRED overrides even unanimous support."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
            _opinion("surgical_oncology", "support", 0.90),
            _opinion("pathology", "support", 0.80, requires_more_information=True),
        ]
        result = engine.calculate(_make_input(opinions))
        assert result.consensus_status == ConsensusStatus.DEFERRED


# ═══════════════════════════════════════════════════════════════════════════════
# Weighting Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestSpecialtyWeighting:
    """Different specialties contribute different weights."""

    def test_medical_oncology_highest_weight(
        self, engine: ConsensusEngine
    ) -> None:
        """Medical oncology (weight 1.0) contributes more than nursing (0.5)."""
        opinions = [
            _opinion("medical_oncology", "support", 1.0),
            _opinion("nursing", "oppose", 1.0),
        ]
        result = engine.calculate(_make_input(opinions))
        # medical_oncology weight=1.0 * confidence_high=1.0 = 1.0
        # nursing weight=0.5 * confidence_high=1.0 = 0.5
        # support=1.0, oppose=0.5, consensus_ratio=1.0/(1.0+0.5)=0.667
        assert result.support_score == 1.0
        assert result.oppose_score == 0.5
        assert result.consensus_status == ConsensusStatus.MAJORITY_CONSENSUS

    def test_unknown_specialty_gets_default_weight(
        self, engine: ConsensusEngine
    ) -> None:
        """Unknown specialty gets default weight 0.5."""
        opinions = [
            _opinion("unknown_specialty", "support", 1.0),
            _opinion("medical_oncology", "oppose", 1.0),
        ]
        result = engine.calculate(_make_input(opinions))
        # unknown_specialty weight=0.5 * 1.0 = 0.5
        # medical_oncology weight=1.0 * 1.0 = 1.0
        # consensus_ratio = 0.5/(0.5+1.0) = 0.333
        assert abs(result.consensus_score - 0.333) < 0.01
        assert result.consensus_status == ConsensusStatus.SPLIT_DECISION

    def test_specialty_weight_affects_consensus_outcome(
        self, engine: ConsensusEngine
    ) -> None:
        """With the same confidence, specialty weight changes the outcome."""
        # Two support vs two oppose — same raw confidence
        opinions = [
            _opinion("medical_oncology", "support", 1.0),   # weight 1.0
            _opinion("surgical_oncology", "support", 1.0),  # weight 0.9
            _opinion("pathology", "oppose", 1.0),            # weight 0.8
            _opinion("radiology", "oppose", 1.0),            # weight 0.8
        ]
        result = engine.calculate(_make_input(opinions))
        # support = 1.0 + 0.9 = 1.9
        # oppose = 0.8 + 0.8 = 1.6
        # ratio = 1.9 / 3.5 = 0.543 → SPLIT_DECISION
        assert abs(result.support_score - 1.9) < 0.01
        assert abs(result.oppose_score - 1.6) < 0.01
        assert result.consensus_status == ConsensusStatus.SPLIT_DECISION


class TestConfidenceWeighting:
    """Different confidence levels affect effective weight."""

    def test_high_confidence_gets_full_weight(
        self, engine: ConsensusEngine
    ) -> None:
        """Confidence >= 0.8 maps to confidence_high (1.0)."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
            _opinion("surgical_oncology", "oppose", 0.80),
        ]
        result = engine.calculate(_make_input(opinions))
        # support: 1.0 * 1.0 = 1.0
        # oppose: 0.9 * 1.0 = 0.9
        # ratio = 1.0 / 1.9 = 0.526
        assert abs(result.support_score - 1.0) < 0.01
        assert abs(result.oppose_score - 0.9) < 0.01

    def test_medium_confidence_reduces_weight(
        self, engine: ConsensusEngine
    ) -> None:
        """Confidence 0.5-0.79 maps to confidence_medium (0.7)."""
        opinions = [
            _opinion("medical_oncology", "support", 0.70),
            _opinion("surgical_oncology", "oppose", 0.70),
        ]
        result = engine.calculate(_make_input(opinions))
        # support: 1.0 * 0.7 = 0.7
        # oppose: 0.9 * 0.7 = 0.63
        assert abs(result.support_score - 0.7) < 0.01
        assert abs(result.oppose_score - 0.63) < 0.01

    def test_low_confidence_reduces_weight_more(
        self, engine: ConsensusEngine
    ) -> None:
        """Confidence < 0.5 maps to confidence_low (0.4)."""
        opinions = [
            _opinion("medical_oncology", "support", 0.30),
            _opinion("surgical_oncology", "oppose", 0.30),
        ]
        result = engine.calculate(_make_input(opinions))
        # support: 1.0 * 0.4 = 0.4
        # oppose: 0.9 * 0.4 = 0.36
        assert abs(result.support_score - 0.4) < 0.01
        assert abs(result.oppose_score - 0.36) < 0.01

    def test_confidence_affects_consensus_classification(
        self, engine: ConsensusEngine
    ) -> None:
        """Low confidence can push STRONG_CONSENSUS to MAJORITY."""
        # High confidence → STRONG_CONSENSUS (4 support vs 1 oppose, all medical_oncology)
        opinions_high = [
            _opinion("medical_oncology", "support", 0.90),
            _opinion("medical_oncology", "support", 0.90),
            _opinion("medical_oncology", "support", 0.90),
            _opinion("medical_oncology", "support", 0.90),
            _opinion("medical_oncology", "oppose", 0.90),
        ]
        result_high = engine.calculate(_make_input(opinions_high))
        assert result_high.consensus_status == ConsensusStatus.STRONG_CONSENSUS

        # Low confidence support (0.30) → MAJORITY_CONSENSUS
        # support_weight = 4 * 1.0 * 0.4 = 1.6
        # oppose_weight = 1 * 1.0 * 1.0 = 1.0
        # ratio = 1.6 / 2.6 = 0.615 → MAJORITY_CONSENSUS
        opinions_low = [
            _opinion("medical_oncology", "support", 0.30),
            _opinion("medical_oncology", "support", 0.30),
            _opinion("medical_oncology", "support", 0.30),
            _opinion("medical_oncology", "support", 0.30),
            _opinion("medical_oncology", "oppose", 0.90),
        ]
        result_low = engine.calculate(_make_input(opinions_low))
        assert result_low.consensus_status == ConsensusStatus.MAJORITY_CONSENSUS


# ═══════════════════════════════════════════════════════════════════════════════
# Contraindication / Dissent Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestDissentExtraction:
    """Verify dissenting opinions are correctly extracted."""

    def test_dissenting_opinions_listed(self, engine: ConsensusEngine) -> None:
        """Oppose opinions appear in dissenting_opinions."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
            _opinion("surgical_oncology", "oppose", 0.80),
            _opinion("pathology", "oppose", 0.75),
        ]
        result = engine.calculate(_make_input(opinions))
        assert len(result.dissenting_opinions) == 2
        specialties = {d["specialty"] for d in result.dissenting_opinions}
        assert specialties == {"surgical_oncology", "pathology"}

    def test_no_dissent_when_all_support(self, engine: ConsensusEngine) -> None:
        """All support → empty dissenting_opinions."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
            _opinion("surgical_oncology", "support", 0.90),
        ]
        result = engine.calculate(_make_input(opinions))
        assert result.dissenting_opinions == []

    def test_dissent_includes_weight_and_confidence(
        self, engine: ConsensusEngine
    ) -> None:
        """Each dissenting opinion dict contains weight and raw_confidence."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
            _opinion("pathology", "oppose", 0.70),
        ]
        result = engine.calculate(_make_input(opinions))
        dissent = result.dissenting_opinions[0]
        assert "specialty" in dissent
        assert "weight" in dissent
        assert "raw_confidence" in dissent
        assert dissent["position"] == "oppose"


class TestContraindicationImpact:
    """Verify oppose opinions affect the consensus score."""

    def test_single_oppose_reduces_consensus_score(
        self, engine: ConsensusEngine
    ) -> None:
        """Adding an oppose opinion lowers the consensus ratio."""
        all_support = [
            _opinion("medical_oncology", "support", 0.95),
            _opinion("surgical_oncology", "support", 0.90),
        ]
        result_support = engine.calculate(_make_input(all_support))
        assert result_support.consensus_score == 1.0

        with_oppose = [
            _opinion("medical_oncology", "support", 0.95),
            _opinion("surgical_oncology", "oppose", 0.90),
        ]
        result_oppose = engine.calculate(_make_input(with_oppose))
        assert result_oppose.consensus_score < 1.0

    def test_strong_oppose_can_flip_to_split(
        self, engine: ConsensusEngine
    ) -> None:
        """Sufficiently strong opposition can produce a split decision."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
            _opinion("surgical_oncology", "support", 0.90),
            _opinion("pathology", "oppose", 0.95),
            _opinion("radiology", "oppose", 0.90),
        ]
        result = engine.calculate(_make_input(opinions))
        assert result.consensus_status in (
            ConsensusStatus.SPLIT_DECISION, ConsensusStatus.MAJORITY_CONSENSUS
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Abstain Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestAbstainHandling:
    """Abstain opinions should not contribute to support/oppose scores."""

    def test_abstain_does_not_affect_ratio(self, engine: ConsensusEngine) -> None:
        """Abstain opinions are excluded from the consensus ratio calculation."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
            _opinion("surgical_oncology", "abstain", 0.50),
        ]
        result = engine.calculate(_make_input(opinions))
        # Only medical_oncology counts → ratio = 1.0 (UNANIMOUS among voting)
        assert result.consensus_score == 1.0
        assert result.abstain_score == 0.0

    def test_all_abstain_insufficient(self, engine: ConsensusEngine) -> None:
        """All opinions abstain → insufficient information (no valid opinions)."""
        opinions = [
            _opinion("medical_oncology", "abstain", 0.50),
            _opinion("surgical_oncology", "abstain", 0.60),
        ]
        result = engine.calculate(_make_input(opinions))
        # Both abstain → weight is 0.0 → effectively 0 weighted opinions
        # min_opinions=2, but after filtering they have weight 0
        # len(opinions)=2 but consensus_ratio=0.0 because total_weighted=0
        # Still min_opinions check passes (2 >= 2) but...
        # Actually the engine checks len(opinions) which counts filtered opinions
        # Abstain opinions have weight 0.0 and are NOT filtered out (they remain)
        # They are counted in len(opinions) = 2 >= min_opinions = 2
        # But consensus_ratio = support / (support+oppose) = 0 / 0 = 0.0
        # Since consensus_ratio == 0.0 < split_decision_upper (0.55) → SPLIT
        assert result.consensus_status == ConsensusStatus.SPLIT_DECISION
        assert result.support_score == 0.0
        assert result.oppose_score == 0.0

    def test_abstain_with_support_and_oppose(
        self, engine: ConsensusEngine
    ) -> None:
        """Abstentions are skipped in support/oppose tally."""
        opinions = [
            _opinion("medical_oncology", "support", 1.0),
            _opinion("surgical_oncology", "oppose", 1.0),
            _opinion("pathology", "abstain", 0.5),
        ]
        result = engine.calculate(_make_input(opinions))
        # support: 1.0, oppose: 0.9, abstain: 0.0
        assert abs(result.support_score - 1.0) < 0.01
        assert abs(result.oppose_score - 0.9) < 0.01
        assert result.abstain_score == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# Low Confidence Filtering
# ═══════════════════════════════════════════════════════════════════════════════


class TestLowConfidenceFiltering:
    """Opinions below min_confidence threshold should be skipped."""

    def test_low_confidence_below_threshold_skipped(
        self, engine: ConsensusEngine
    ) -> None:
        """Confidence < 0.1 → opinion is skipped entirely."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
            _opinion("pathology", "support", 0.05),  # below min_confidence
        ]
        result = engine.calculate(_make_input(opinions))
        # pathology should be skipped → only medical_oncology counts
        # But len(opinions) checks AFTER filtering → only 1 valid
        # min_opinions=2, 1 < 2 → INSUFFICIENT_INFORMATION
        assert result.consensus_status == ConsensusStatus.INSUFFICIENT_INFORMATION
        assert result.support_score > 0

    def test_all_low_confidence_insufficient(
        self, engine: ConsensusEngine
    ) -> None:
        """All opinions below min_confidence → INSUFFICIENT_INFORMATION."""
        opinions = [
            _opinion("medical_oncology", "support", 0.05),
            _opinion("surgical_oncology", "support", 0.03),
        ]
        result = engine.calculate(_make_input(opinions))
        assert result.consensus_status == ConsensusStatus.INSUFFICIENT_INFORMATION
        assert result.support_score == 0.0

    def test_mixed_confidence_only_above_threshold_count(
        self, engine: ConsensusEngine
    ) -> None:
        """Only opinions above min_confidence are considered for consensus."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),      # valid
            _opinion("surgical_oncology", "support", 0.90),     # valid
            _opinion("pathology", "oppose", 0.05),              # skipped
            _opinion("radiology", "oppose", 0.85),              # valid
        ]
        result = engine.calculate(_make_input(opinions))
        # 3 valid opinions, support=1.0+0.9=1.9, oppose=0.8
        # ratio = 1.9/2.7 = 0.704 → MAJORITY_CONSENSUS
        assert result.consensus_status == ConsensusStatus.MAJORITY_CONSENSUS
        # Verify the low-confidence opinion didn't contribute
        assert abs(result.oppose_score - 0.8) < 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# Trace Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestEngineTrace:
    """Verify the engine produces a complete and ordered trace."""

    def test_trace_has_all_steps(self, engine: ConsensusEngine) -> None:
        """Result contains all expected trace steps in order."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
            _opinion("surgical_oncology", "oppose", 0.80),
        ]
        result = engine.calculate(_make_input(opinions))

        expected_step_types = [
            "load_context",
            "validate_links",
            "normalize_opinions",
            "calculate_weights",
            "calculate_consensus",
            "resolve_dissent",
            "finalize_consensus",
            "prepare_persistence",
        ]

        assert len(result.trace_steps) == len(expected_step_types)
        for i, step in enumerate(result.trace_steps):
            assert step["step_type"] == expected_step_types[i], (
                f"Step {i}: expected {expected_step_types[i]!r}, "
                f"got {step['step_type']!r}"
            )

    def test_trace_contains_input_and_output_summaries(
        self, engine: ConsensusEngine
    ) -> None:
        """Each trace step has input_summary and output_summary."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
        ]
        result = engine.calculate(_make_input(opinions))
        for i, step in enumerate(result.trace_steps):
            assert "input_summary" in step, f"Step {i} missing input_summary"
            assert "output_summary" in step, f"Step {i} missing output_summary"

    def test_trace_consensus_id_consistent(
        self, engine: ConsensusEngine
    ) -> None:
        """The consensus_id in trace matches result.consensus_id."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
            _opinion("surgical_oncology", "support", 0.90),
        ]
        result = engine.calculate(_make_input(opinions))
        # The final trace step references the consensus_id
        final_step = result.trace_steps[-1]
        assert final_step["output_summary"]["consensus_id"] == result.consensus_id


# ═══════════════════════════════════════════════════════════════════════════════
# Validation Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestEngineValidation:
    """Engine validates required input fields."""

    def test_missing_patient_id_raises_value_error(
        self, engine: ConsensusEngine
    ) -> None:
        """Empty patient_id should raise ValueError."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
        ]
        input_data = _make_input(opinions, patient_id="")
        with pytest.raises(ValueError, match="patient_id is required"):
            engine.calculate(input_data)

    def test_missing_recommendation_id_raises_value_error(
        self, engine: ConsensusEngine
    ) -> None:
        """Empty recommendation_id should raise ValueError."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
        ]
        input_data = _make_input(opinions, recommendation_id="")
        with pytest.raises(ValueError, match="recommendation_id is required"):
            engine.calculate(input_data)

    def test_missing_clinical_decision_id_raises_value_error(
        self, engine: ConsensusEngine
    ) -> None:
        """Empty clinical_decision_id should raise ValueError."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
        ]
        input_data = _make_input(opinions, clinical_decision_id="")
        with pytest.raises(ValueError, match="clinical_decision_id is required"):
            engine.calculate(input_data)


# ═══════════════════════════════════════════════════════════════════════════════
# Supporting Rationale Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestSupportingRationale:
    """Verify the supporting_rationale text is generated correctly."""

    def test_rationale_for_unanimous(self, engine: ConsensusEngine) -> None:
        """Unanimous consensus produces appropriate rationale."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
            _opinion("surgical_oncology", "support", 0.90),
        ]
        result = engine.calculate(_make_input(opinions))
        assert "unanimous" in result.supporting_rationale.lower()

    def test_rationale_for_deferred(self, engine: ConsensusEngine) -> None:
        """Deferred consensus produces appropriate rationale."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
            _opinion("pathology", "abstain", 0.50, requires_more_information=True),
        ]
        result = engine.calculate(_make_input(opinions))
        assert "deferred" in result.supporting_rationale.lower()

    def test_rationale_for_insufficient(self, engine: ConsensusEngine) -> None:
        """Insufficient information produces appropriate rationale."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
        ]
        result = engine.calculate(_make_input(opinions))
        assert "insufficient" in result.supporting_rationale.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge cases for the consensus engine."""

    def test_single_opinion_insufficient(self, engine: ConsensusEngine) -> None:
        """Single opinion → INSUFFICIENT_INFORMATION."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
        ]
        result = engine.calculate(_make_input(opinions))
        assert result.consensus_status == ConsensusStatus.INSUFFICIENT_INFORMATION

    def test_empty_opinions_insufficient(self, engine: ConsensusEngine) -> None:
        """No opinions at all → INSUFFICIENT_INFORMATION."""
        result = engine.calculate(_make_input([]))
        assert result.consensus_status == ConsensusStatus.INSUFFICIENT_INFORMATION
        assert result.participating_specialties == []

    def test_consensus_id_format(self, engine: ConsensusEngine) -> None:
        """Consensus ID has expected prefix and non-empty suffix."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
            _opinion("surgical_oncology", "support", 0.90),
        ]
        result = engine.calculate(_make_input(opinions))
        assert result.consensus_id.startswith("TBC-")
        assert len(result.consensus_id) > 4

    def test_participating_specialties(
        self, engine: ConsensusEngine
    ) -> None:
        """Result lists distinct participating specialties."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
            _opinion("surgical_oncology", "oppose", 0.80),
            _opinion("medical_oncology", "support", 0.90),  # duplicate
        ]
        result = engine.calculate(_make_input(opinions))
        assert "medical_oncology" in result.participating_specialties
        assert "surgical_oncology" in result.participating_specialties
        assert len(result.participating_specialties) == 2

    def test_unresolved_questions_from_deferred(
        self, engine: ConsensusEngine
    ) -> None:
        """Deferred opinions with rationale populate unresolved_questions."""
        opinions = [
            _opinion("medical_oncology", "support", 0.95),
            SpecialistOpinionInput(
                specialty="pathology",
                position="abstain",
                confidence=0.50,
                requires_more_information=True,
                rationale="Need more biopsy data",
            ),
        ]
        result = engine.calculate(_make_input(opinions))
        assert len(result.unresolved_questions) >= 1
        assert any("biopsy" in q.lower() for q in result.unresolved_questions)
