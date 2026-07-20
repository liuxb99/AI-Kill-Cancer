"""
Tests for Drug Ranking Engine (v0.5.0).

Covers:
- EvidenceScorer
- ResistanceScorer
- SensitivityScorer
- GuidelineScorer
- RegulatoryScorer
- ClinicalTrialScorer
- ConflictPenalty
- UncertaintyPenalty
- DrugRankingEngine integration
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.backend.ranking.scorers import (
    EvidenceScorer, ResistanceScorer, SensitivityScorer,
    GuidelineScorer, RegulatoryScorer, ClinicalTrialScorer,
    EVIDENCE_LEVEL_WEIGHT, MATCH_LEVEL_WEIGHT,
)
from src.backend.ranking.penalties import ConflictPenalty, UncertaintyPenalty
from src.backend.ranking.engine import DrugRankingEngine
from src.backend.ranking.models import (
    DrugRankingResult, DrugRankItem, ScoreBreakdown,
)


# ─── Test Helpers ─────────────────────────────────────────────────────────────


def make_evidence(**kwargs) -> dict:
    """Create an evidence item dict with defaults."""
    defaults = {
        "id": "ev-001",
        "source": "civic",
        "source_record_id": "123",
        "gene_symbol": "BRAF",
        "drug_name": "Vemurafenib",
        "disease": "melanoma",
        "evidence_type": "predictive",
        "evidence_direction": "Supports",
        "evidence_level": "A",
        "clinical_significance": "sensitivity",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "_match_level": "exact_variant",
        "_conflict_status": "supporting",
    }
    defaults.update(kwargs)
    return defaults


def make_interaction(**kwargs) -> dict:
    defaults = {
        "gene_symbol": "BRAF",
        "drug_name": "Vemurafenib",
        "interaction_type": "inhibitor",
        "source_db_name": "DrugBank",
    }
    defaults.update(kwargs)
    return defaults


# ─── Test: EvidenceScorer ────────────────────────────────────────────────────


class TestEvidenceScorer:
    """Test the EvidenceScorer."""

    def setup_method(self):
        self.scorer = EvidenceScorer()

    def test_no_evidence_returns_zero(self):
        score, count, indep, ids = self.scorer.score("Vemurafenib", [], "exact_variant")
        assert score == 0.0
        assert count == 0

    def test_high_quality_evidence(self):
        items = [make_evidence(evidence_level="A", _match_level="exact_variant")]
        score, count, indep, ids = self.scorer.score("Vemurafenib", items)
        assert score > 0.0
        assert count == 1
        assert len(ids) >= 1

    def test_low_quality_evidence(self):
        items = [make_evidence(evidence_level="E", _match_level="gene_level_only")]
        score, count, indep, ids = self.scorer.score("Vemurafenib", items)
        high_items = [make_evidence(evidence_level="A", _match_level="exact_variant")]
        high_score, _, _, _ = self.scorer.score("Vemurafenib", high_items)
        # With supporting direction, level+match quality should differentiate
        assert score < high_score

    def test_multiple_sources(self):
        items = [
            make_evidence(id="ev-1", source="civic", source_record_id="r1"),
            make_evidence(id="ev-2", source="civic", source_record_id="r2"),
            make_evidence(id="ev-3", source="dgidb", source_record_id="r3"),
        ]
        score, count, indep, ids = self.scorer.score("Vemurafenib", items)
        assert count >= 2
        assert indep >= 1

    def test_ignores_wrong_drug(self):
        items = [make_evidence(drug_name="OtherDrug")]
        score, count, indep, ids = self.scorer.score("Vemurafenib", items)
        assert score == 0.0

    def test_conflicting_evidence(self):
        items = [make_evidence(evidence_direction="Does Not Support", clinical_significance="resistance")]
        score, count, indep, ids = self.scorer.score("Vemurafenib", items)
        assert score < 0  # Negative for conflicting

    def test_fresh_evidence_bonus(self):
        fresh = [make_evidence(retrieved_at=datetime.now(timezone.utc).isoformat())]
        old = [make_evidence(retrieved_at="2020-01-01T00:00:00")]
        fresh_score, _, _, _ = self.scorer.score("Vemurafenib", fresh)
        old_score, _, _, _ = self.scorer.score("Vemurafenib", old)
        assert fresh_score >= old_score


# ─── Test: ResistanceScorer ──────────────────────────────────────────────────


class TestResistanceScorer:
    def test_no_resistance(self):
        scorer = ResistanceScorer()
        items = [make_evidence(evidence_direction="Supports")]
        penalty, ids = scorer.score("Vemurafenib", items)
        assert penalty == 0.0

    def test_resistance_evidence(self):
        scorer = ResistanceScorer()
        items = [make_evidence(evidence_direction="Does Not Support", clinical_significance="resistance")]
        penalty, ids = scorer.score("Vemurafenib", items)
        assert penalty < 0


# ─── Test: SensitivityScorer ─────────────────────────────────────────────────


class TestSensitivityScorer:
    def test_no_sensitivity(self):
        scorer = SensitivityScorer()
        # Empty significance and neutral direction should yield 0
        items = [make_evidence(clinical_significance="", evidence_direction="neutral")]
        bonus = scorer.score("Vemurafenib", items)
        assert bonus == 0.0

    def test_sensitivity_bonus(self):
        scorer = SensitivityScorer()
        items = [make_evidence(clinical_significance="sensitivity")]
        bonus = scorer.score("Vemurafenib", items)
        assert bonus > 0

    def test_response_bonus(self):
        scorer = SensitivityScorer()
        items = [make_evidence(clinical_significance="improved_response")]
        bonus = scorer.score("Vemurafenib", items)
        assert bonus > 0


# ─── Test: GuidelineScorer ───────────────────────────────────────────────────


class TestGuidelineScorer:
    def test_known_guideline(self):
        scorer = GuidelineScorer()
        bonus, supported = scorer.score("Vemurafenib", "melanoma")
        assert bonus > 0
        assert supported

    def test_no_guideline(self):
        scorer = GuidelineScorer()
        bonus, supported = scorer.score("UnknownDrug", "unknown_disease")
        assert bonus == 0.0
        assert not supported

    def test_multiple_diseases(self):
        scorer = GuidelineScorer()
        bonus1, _ = scorer.score("Imatinib", "cml")
        bonus2, _ = scorer.score("Imatinib", "gist")
        assert bonus1 > 0
        assert bonus2 > 0


# ─── Test: RegulatoryScorer ──────────────────────────────────────────────────


class TestRegulatoryScorer:
    def test_fda_approved(self):
        scorer = RegulatoryScorer()
        bonus, approved = scorer.score("Vemurafenib")
        assert bonus > 0
        assert approved

    def test_not_approved(self):
        scorer = RegulatoryScorer()
        bonus, approved = scorer.score("ExperimentalDrugX")
        assert bonus == 0.0
        assert not approved


# ─── Test: ClinicalTrialScorer ───────────────────────────────────────────────


class TestClinicalTrialScorer:
    def test_trial_evidence(self):
        scorer = ClinicalTrialScorer()
        items = [make_evidence(evidence_type="clinical_trial")]
        bonus = scorer.score("Vemurafenib", items)
        assert bonus > 0

    def test_no_trial_evidence(self):
        scorer = ClinicalTrialScorer()
        items = [make_evidence(evidence_type="predictive")]
        bonus = scorer.score("Vemurafenib", items)
        assert bonus == 0.0


# ─── Test: ConflictPenalty ───────────────────────────────────────────────────


class TestConflictPenalty:
    def test_no_conflict(self):
        penalty = ConflictPenalty()
        items = [make_evidence(evidence_direction="Supports")]
        p = penalty.apply(items, "Vemurafenib")
        assert p == 0.0

    def test_single_conflict(self):
        penalty = ConflictPenalty()
        items = [make_evidence(evidence_direction="Does Not Support")]
        p = penalty.apply(items, "Vemurafenib")
        assert p < 0


# ─── Test: UncertaintyPenalty ────────────────────────────────────────────────


class TestUncertaintyPenalty:
    def test_no_uncertainty(self):
        penalty = UncertaintyPenalty()
        p = penalty.apply([], "Vemurafenib")
        assert p == 0.0

    def test_uncertain_evidence(self):
        penalty = UncertaintyPenalty()
        items = [make_evidence(evidence_direction="neutral")]
        p = penalty.apply(items, "Vemurafenib")
        assert p < 0


# ─── Test: DrugRankingEngine Integration ─────────────────────────────────────


class TestDrugRankingEngine:
    """Integration tests for the full DrugRankingEngine."""

    async def test_rank_no_evidence(self):
        engine = DrugRankingEngine()
        result = await engine.rank(
            gene_symbol="BRAF",
            evidence_items=[],
            drug_interactions=[],
        )
        assert result.ranking_count == 0
        assert result.status == "completed"

    async def test_rank_single_drug(self):
        engine = DrugRankingEngine()
        items = [make_evidence()]
        result = await engine.rank(
            gene_symbol="BRAF",
            evidence_items=items,
            drug_interactions=[],
            disease="melanoma",
        )
        assert result.ranking_count >= 1
        top = result.rankings[0]
        assert top.drug_name == "Vemurafenib"
        assert top.total_score > 0
        assert top.rank == 1

    async def test_rank_multiple_drugs(self):
        engine = DrugRankingEngine()
        items = [
            make_evidence(id="ev-1", drug_name="Vemurafenib", evidence_level="A"),
            make_evidence(id="ev-2", drug_name="Dabrafenib", evidence_level="B"),
            make_evidence(id="ev-3", drug_name="OtherDrug", evidence_level="E", _match_level="gene_level_only"),
        ]
        result = await engine.rank(
            gene_symbol="BRAF",
            evidence_items=items,
            drug_interactions=[],
        )
        assert result.ranking_count == 3
        # Best evidence should rank first
        assert result.rankings[0].total_score >= result.rankings[1].total_score

    async def test_rank_with_resistance(self):
        engine = DrugRankingEngine()
        items = [
            make_evidence(id="ev-1", drug_name="Vemurafenib", evidence_level="A",
                          evidence_direction="Supports", clinical_significance="sensitivity"),
            make_evidence(id="ev-2", drug_name="Vemurafenib", evidence_level="A",
                          evidence_direction="Does Not Support", clinical_significance="resistance"),
        ]
        result = await engine.rank(
            gene_symbol="BRAF",
            evidence_items=items,
            drug_interactions=[],
        )
        # With both supporting and resistance evidence, score should be reduced
        top = result.rankings[0]
        assert top.resistance_evidence_ids  # Has resistance evidence
        assert top.total_score < 5.0  # Penalty applied

    async def test_rank_with_conflict(self):
        engine = DrugRankingEngine()
        items = [
            make_evidence(id="ev-1", drug_name="DrugX", evidence_level="A",
                          evidence_direction="Supports"),
            make_evidence(id="ev-2", drug_name="DrugX", evidence_level="A",
                          evidence_direction="Conflicting"),
        ]
        result = await engine.rank(
            gene_symbol="BRAF",
            evidence_items=items,
            drug_interactions=[],
        )
        top = result.rankings[0]
        assert len(top.conflicting_evidence_ids) >= 1
        assert top.score_breakdown.conflict_penalty < 0

    async def test_rank_with_guideline_regulatory(self):
        engine = DrugRankingEngine()
        items = [make_evidence(drug_name="Vemurafenib", id="ev-1")]
        result = await engine.rank(
            gene_symbol="BRAF",
            evidence_items=items,
            drug_interactions=[],
            disease="melanoma",
        )
        top = result.rankings[0]
        # Vemurafenib has both guideline and regulatory support
        assert top.guideline_support
        assert top.regulatory_approval
        assert top.score_breakdown.guideline_score > 0
        assert top.score_breakdown.regulatory_score > 0

    async def test_rank_score_breakdown_structure(self):
        engine = DrugRankingEngine()
        items = [make_evidence(id="ev-1")]
        interactions = [make_interaction()]
        result = await engine.rank(
            gene_symbol="BRAF",
            evidence_items=items,
            drug_interactions=interactions,
        )
        top = result.rankings[0]
        breakdown = top.score_breakdown
        # Verify all breakdown fields present
        assert breakdown.evidence_score > 0
        assert breakdown.conflict_penalty <= 0
        assert breakdown.uncertainty_penalty <= 0
        # Total should be sum of all components
        expected_total = (breakdown.evidence_score + breakdown.sensitivity_score
                         + breakdown.resistance_score + breakdown.guideline_score
                         + breakdown.regulatory_score + breakdown.clinical_trial_score
                         + breakdown.conflict_penalty + breakdown.uncertainty_penalty)
        assert abs(top.total_score - round(expected_total, 4)) < 0.01

    async def test_rank_stable_sorting(self):
        """Same scores should produce stable ranking (alphabetical tiebreak)."""
        engine = DrugRankingEngine()
        # Two drugs with identical evidence profiles
        items = [
            make_evidence(id="ev-1", drug_name="AA-Drug", evidence_direction="Supports", evidence_level="B"),
            make_evidence(id="ev-2", drug_name="ZZ-Drug", evidence_direction="Supports", evidence_level="B"),
        ]
        result1 = await engine.rank(gene_symbol="TEST", evidence_items=items, drug_interactions=[])
        result2 = await engine.rank(gene_symbol="TEST", evidence_items=items, drug_interactions=[])

        # Rankings should be identical
        for r1, r2 in zip(result1.rankings, result2.rankings):
            assert r1.drug_name == r2.drug_name
            assert r1.rank == r2.rank
            assert r1.total_score == r2.total_score

    async def test_rank_evidence_snapshot_tracking(self):
        engine = DrugRankingEngine()
        items = [make_evidence(id="ev-1")]
        result = await engine.rank(
            gene_symbol="BRAF",
            evidence_items=items,
            drug_interactions=[],
            evidence_snapshot_id="snap-001",
            git_commit="abc123def456",
        )
        assert result.evidence_snapshot_id == "snap-001"
        assert result.git_commit == "abc123def456"
        assert result.ranking_algorithm_version == "0.5.0"


# ─── Test: Pydantic Models ───────────────────────────────────────────────────


class TestRankingModels:
    def test_score_breakdown_total(self):
        b = ScoreBreakdown(
            evidence_score=2.0, sensitivity_score=1.0, resistance_score=-0.5,
            guideline_score=2.0, regulatory_score=2.0, clinical_trial_score=1.0,
            conflict_penalty=-1.0, uncertainty_penalty=-0.3,
        )
        assert abs(b.total() - (2.0 + 1.0 - 0.5 + 2.0 + 2.0 + 1.0 - 1.0 - 0.3)) < 0.01

    def test_drug_rank_item(self):
        item = DrugRankItem(
            drug_name="TestDrug",
            rank=1,
            total_score=7.5,
            score_breakdown=ScoreBreakdown(),
            supporting_evidence_ids=["ev-1"],
            source_count=2,
            confidence="high",
        )
        assert item.drug_name == "TestDrug"
        assert item.rank == 1
        assert item.total_score == 7.5
        assert item.confidence == "high"

    def test_drug_ranking_result(self):
        result = DrugRankingResult(
            id="run-001",
            gene_symbol="BRAF",
            rankings=[],
            ranking_count=0,
            ranking_algorithm_version="0.5.0",
            status="completed",
        )
        assert result.id == "run-001"
        assert result.status == "completed"
