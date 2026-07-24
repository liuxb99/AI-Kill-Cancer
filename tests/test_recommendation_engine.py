"""
Tests for Recommendation Engine components (P3A-10).

Covers:
- WeightRegistry (register, unregister, query, evidence level)
- EvidenceAggregator (aggregate, grouping, weighting)
- DrugRanker (ranking with sort keys)
- RecommendationRule (evaluate with conditions/actions)
- DrugRanking scoring functions (EvidenceScore, Sensitivity, Resistance,
  ConflictScore, OverallScore, DrugRankingEngine)
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from src.backend.clinical.drug_ranking import (
    DrugRankingEngine,
    DrugRankingResult,
    EvidenceScore,
    OverallScore,
    Resistance,
    Sensitivity,
    compute_conflict_score,
    compute_evidence_score,
    compute_overall_score,
    compute_resistance,
    compute_sensitivity,
)
from src.backend.clinical.evidence_models import (
    EvidenceBundle,
    EvidenceItem,
)
from src.backend.clinical.evidence_weight import (
    ConfidenceLevel,
    EvidenceLevel,
    EvidenceTier,
    EvidenceWeightConfig,
    WeightRegistry,
)
from src.backend.clinical.recommendation_engine import (
    DrugRanker,
    EvidenceAggregator,
    RecommendationEngine,
    RecommendationRule,
)


# ═══════════════════════════════════════════════════════════════════════════════
# WeightRegistry Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestWeightRegistry:
    """Test WeightRegistry registration, query, and evidence-level resolution."""

    def setup_method(self):
        """Save registry state before each test."""
        self._saved_sources = dict(WeightRegistry._sources)

    def teardown_method(self):
        """Restore registry state after each test."""
        WeightRegistry._sources.clear()
        WeightRegistry._sources.update(self._saved_sources)

    def test_default_sources_present(self):
        """The six default sources should be registered."""
        sources = WeightRegistry.registered_sources()
        for expected in ("fda", "nccn", "oncokb", "civic", "dgidb", "opencravat"):
            assert expected in sources, f"Default source {expected!r} missing"

    def test_get_weight_known_source(self):
        """get_weight returns correct numeric weight for a known source+tier."""
        weight = WeightRegistry.get_weight("nccn", "Category 1")
        assert weight == 1.0

        weight = WeightRegistry.get_weight("nccn", "Category 2A")
        assert weight == 0.85

        weight = WeightRegistry.get_weight("dgidb", "FDA-approved")
        # DGIdb has base_weight=0.85, tier=0.90 → 0.85*0.90=0.765
        assert weight == pytest.approx(0.765)

    def test_get_weight_unknown_tier_returns_zero(self):
        """An unrecognised native tier should return 0.0."""
        weight = WeightRegistry.get_weight("fda", "NonExistentTier")
        assert weight == 0.0

    def test_get_weight_unknown_source_raises(self):
        """get_weight should raise KeyError for an unregistered source."""
        with pytest.raises(KeyError):
            WeightRegistry.get_weight("nonexistent_source", "Category 1")

    def test_get_evidence_level(self):
        """get_evidence_level returns a fully populated EvidenceLevel."""
        level = WeightRegistry.get_evidence_level("nccn", "Category 1")
        assert isinstance(level, EvidenceLevel)
        assert level.source == "nccn"
        assert level.weight == 1.0
        assert level.confidence == ConfidenceLevel.HIGH
        assert level.tier == EvidenceTier.TIER_0

    def test_get_evidence_level_unknown_tier(self):
        """An unknown tier should produce a low confidence EvidenceLevel."""
        level = WeightRegistry.get_evidence_level("fda", "not_assessed")
        assert level.weight == 0.10
        assert level.confidence == ConfidenceLevel.UNKNOWN
        assert level.tier == EvidenceTier.TIER_4

    def test_register_custom_source(self):
        """Registering a new source should make it available."""
        config = EvidenceWeightConfig(
            source_name="custom_source",
            base_weight=1.0,
            tier_mapping={"High": 0.9, "Low": 0.3},
            weight_version="1.0.0",
        )
        WeightRegistry.register_source(config)
        assert "custom_source" in WeightRegistry.registered_sources()
        assert WeightRegistry.get_weight("custom_source", "High") == 0.9

    def test_register_duplicate_raises(self):
        """Registering an existing source without overwrite should raise."""
        config = EvidenceWeightConfig(
            source_name="fda",
            base_weight=1.0,
            tier_mapping={"Approved": 1.0},
            weight_version="1.0.0",
        )
        with pytest.raises(KeyError, match="already registered"):
            WeightRegistry.register_source(config)

    def test_register_duplicate_overwrite_ok(self):
        """Register with overwrite=True should silently replace."""
        config = EvidenceWeightConfig(
            source_name="fda",
            base_weight=0.5,
            tier_mapping={"Approved": 0.5},
            weight_version="2.0.0",
        )
        WeightRegistry.register_source(config, overwrite=True)
        assert WeightRegistry.get_weight("fda", "Approved") == 0.25  # 0.5*0.5

    def test_unregister_source(self):
        """Unregister a source removes it from the registry."""
        WeightRegistry.unregister_source("fda")
        assert "fda" not in WeightRegistry.registered_sources()

    def test_unregister_nonexistent_raises(self):
        """Unregistering a source that does not exist should raise KeyError."""
        with pytest.raises(KeyError):
            WeightRegistry.unregister_source("i_dont_exist")

    def test_get_config(self):
        """get_config returns the EvidenceWeightConfig for a source."""
        config = WeightRegistry.get_config("nccn")
        assert config.source_name == "nccn"
        assert "Category 1" in config.tier_mapping

    def test_get_config_unknown_raises(self):
        """get_config should raise KeyError for unknown source."""
        with pytest.raises(KeyError):
            WeightRegistry.get_config("ghost_source")

    def test_evidence_tier_inference(self):
        """_infer_tier returns correct tier based on weight thresholds."""
        assert WeightRegistry._infer_tier("test", "x", 0.95) == EvidenceTier.TIER_0
        assert WeightRegistry._infer_tier("test", "x", 0.80) == EvidenceTier.TIER_1
        assert WeightRegistry._infer_tier("test", "x", 0.60) == EvidenceTier.TIER_2
        assert WeightRegistry._infer_tier("test", "x", 0.35) == EvidenceTier.TIER_3
        assert WeightRegistry._infer_tier("test", "x", 0.10) == EvidenceTier.TIER_4

    def test_confidence_level_resolution(self):
        """resolve_confidence returns correct level per weight threshold."""
        config = WeightRegistry.get_config("nccn")
        assert config.resolve_confidence(0.90) == ConfidenceLevel.HIGH
        assert config.resolve_confidence(0.60) == ConfidenceLevel.MODERATE
        assert config.resolve_confidence(0.30) == ConfidenceLevel.LOW
        assert config.resolve_confidence(0.10) == ConfidenceLevel.UNKNOWN


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def sample_evidence_items() -> list[EvidenceItem]:
    """Create a standard set of evidence items for testing."""
    return [
        EvidenceItem(
            source="nccn",
            drug_name="Osimertinib",
            gene_symbol="EGFR",
            evidence_direction="supporting",
            evidence_level="Category 1",
            clinical_significance="sensitivity",
        ),
        EvidenceItem(
            source="fda",
            drug_name="Osimertinib",
            gene_symbol="EGFR",
            evidence_direction="supporting",
            evidence_level="Approved",
            clinical_significance="sensitivity",
        ),
        EvidenceItem(
            source="civic",
            drug_name="Osimertinib",
            gene_symbol="EGFR",
            evidence_direction="supporting",
            evidence_level="A",
            clinical_significance="sensitivity",
        ),
        EvidenceItem(
            source="dgidb",
            drug_name="Osimertinib",
            gene_symbol="EGFR",
            evidence_direction="neutral",
            evidence_level="FDA-approved",
            clinical_significance="",
        ),
        EvidenceItem(
            source="nccn",
            drug_name="Pembrolizumab",
            gene_symbol="PD-L1",
            evidence_direction="supporting",
            evidence_level="Category 2A",
            clinical_significance="sensitivity",
        ),
        EvidenceItem(
            source="civic",
            drug_name="Pembrolizumab",
            gene_symbol="PD-L1",
            evidence_direction="resistance",
            evidence_level="C",
            clinical_significance="resistance",
        ),
    ]


@pytest.fixture
def sample_bundle(sample_evidence_items) -> EvidenceBundle:
    """Create an EvidenceBundle from sample_evidence_items."""
    return EvidenceBundle(items=sample_evidence_items)


@pytest.fixture
def single_drug_bundle() -> EvidenceBundle:
    """Bundle with a single drug having multiple evidence items."""
    return EvidenceBundle(items=[
        EvidenceItem(
            source="nccn",
            drug_name="Osimertinib",
            gene_symbol="EGFR",
            evidence_direction="supporting",
            evidence_level="Category 1",
            clinical_significance="sensitivity",
        ),
        EvidenceItem(
            source="fda",
            drug_name="Osimertinib",
            gene_symbol="EGFR",
            evidence_direction="supporting",
            evidence_level="Approved",
            clinical_significance="sensitivity",
        ),
    ])


@pytest.fixture
def empty_bundle() -> EvidenceBundle:
    """Bundle with zero evidence items."""
    return EvidenceBundle(items=[])


@pytest.fixture
def drug_aggregate_single() -> dict[str, Any]:
    """Simulated aggregated data for a single drug (as returned by EvidenceAggregator)."""
    return {
        "Osimertinib": {
            "evidence_scores": [
                {"weight": 1.0, "source": "nccn", "tier": "Category 1", "direction": "supporting", "clinical_significance": "sensitivity", "conflict_status": ""},
                {"weight": 1.0, "source": "fda", "tier": "Approved", "direction": "supporting", "clinical_significance": "sensitivity", "conflict_status": ""},
                {"weight": 0.85, "source": "civic", "tier": "A", "direction": "supporting", "clinical_significance": "sensitivity", "conflict_status": ""},
            ],
            "total_weight": 2.85,
            "source_count": 3,
            "item_count": 3,
            "highest_weight": 1.0,
            "sources": {"nccn", "fda", "civic"},
            "directions": {"supporting"},
        }
    }


@pytest.fixture
def drug_aggregate_multi() -> dict[str, Any]:
    """Simulated aggregated data for two drugs."""
    return {
        "Osimertinib": {
            "evidence_scores": [
                {"weight": 1.0, "source": "nccn", "tier": "Category 1", "direction": "supporting", "clinical_significance": "sensitivity", "conflict_status": ""},
                {"weight": 1.0, "source": "fda", "tier": "Approved", "direction": "supporting", "clinical_significance": "sensitivity", "conflict_status": ""},
                {"weight": 0.765, "source": "dgidb", "tier": "FDA-approved", "direction": "neutral", "clinical_significance": "", "conflict_status": ""},
            ],
            "total_weight": 2.765,
            "source_count": 3,
            "item_count": 3,
            "highest_weight": 1.0,
            "sources": {"nccn", "fda", "dgidb"},
            "directions": {"supporting", "neutral"},
        },
        "Pembrolizumab": {
            "evidence_scores": [
                {"weight": 0.85, "source": "nccn", "tier": "Category 2A", "direction": "supporting", "clinical_significance": "sensitivity", "conflict_status": ""},
                {"weight": 0.65, "source": "civic", "tier": "C", "direction": "resistance", "clinical_significance": "resistance", "conflict_status": ""},
            ],
            "total_weight": 1.50,
            "source_count": 2,
            "item_count": 2,
            "highest_weight": 0.85,
            "sources": {"nccn", "civic"},
            "directions": {"supporting", "resistance"},
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# EvidenceAggregator Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestEvidenceAggregator:
    """Test evidence aggregation with source-tier weighting."""

    def test_aggregate_empty(self, empty_bundle):
        """Empty evidence bundle yields empty aggregation."""
        agg = EvidenceAggregator()
        result = agg.aggregate(empty_bundle)
        assert result == {}

    def test_aggregate_single_drug(self, single_drug_bundle):
        """Single drug with two high-tier evidence items."""
        agg = EvidenceAggregator()
        result = agg.aggregate(single_drug_bundle)
        assert "Osimertinib" in result
        drug = result["Osimertinib"]
        assert drug["item_count"] == 2
        assert drug["source_count"] == 2
        assert drug["total_weight"] == pytest.approx(2.0)  # 1.0 (nccn Cat1) + 1.0 (fda Approved)
        assert drug["highest_weight"] == 1.0
        assert "nccn" in drug["sources"]
        assert "fda" in drug["sources"]

    def test_aggregate_multiple_drugs(self, sample_bundle):
        """Multiple drugs are grouped and aggregated separately."""
        agg = EvidenceAggregator()
        result = agg.aggregate(sample_bundle)
        assert "Osimertinib" in result
        assert "Pembrolizumab" in result

        osim = result["Osimertinib"]
        pembro = result["Pembrolizumab"]

        # Osimertinib has more evidence items and higher weight
        assert osim["item_count"] > pembro["item_count"]
        assert osim["total_weight"] > pembro["total_weight"]

    def test_aggregate_item_without_drug_ignored(self):
        """Items without a drug_name should be skipped."""
        bundle = EvidenceBundle(items=[
            EvidenceItem(
                source="nccn",
                drug_name=None,
                gene_symbol="EGFR",
                evidence_level="Category 1",
            ),
        ])
        agg = EvidenceAggregator()
        result = agg.aggregate(bundle)
        assert result == {}

    def test_aggregate_unregistered_source_falls_back(self):
        """An item from an unregistered source should get weight 0.0."""
        bundle = EvidenceBundle(items=[
            EvidenceItem(
                source="unknown_source",
                drug_name="TestDrug",
                evidence_level="SomeLevel",
            ),
        ])
        agg = EvidenceAggregator()
        result = agg.aggregate(bundle)
        assert "TestDrug" in result
        assert result["TestDrug"]["total_weight"] == 0.0
        assert result["TestDrug"]["evidence_scores"][0]["weight"] == 0.0

    def test_aggregate_tracks_directions(self, sample_bundle):
        """Aggregate should collect unique evidence directions."""
        agg = EvidenceAggregator()
        result = agg.aggregate(sample_bundle)
        assert "supporting" in result["Osimertinib"]["directions"]
        assert "resistance" in result["Pembrolizumab"]["directions"]

    def test_aggregate_with_context(self, sample_bundle):
        """Aggregate should accept optional context without error."""
        agg = EvidenceAggregator()
        result = agg.aggregate(sample_bundle, context={"phase": "test"})
        assert "Osimertinib" in result


# ═══════════════════════════════════════════════════════════════════════════════
# DrugRanker Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestDrugRanker:
    """Test drug ranking logic."""

    def test_rank_empty(self):
        """Empty aggregated data yields empty list."""
        ranker = DrugRanker()
        result = ranker.rank({})
        assert result == []

    def test_rank_single(self, drug_aggregate_single):
        """Single drug should rank #1."""
        ranker = DrugRanker()
        result = ranker.rank(drug_aggregate_single)
        assert len(result) == 1
        assert result[0]["drug_name"] == "Osimertinib"
        assert result[0]["rank"] == 1

    def test_rank_multiple(self, drug_aggregate_multi):
        """Multiple drugs sorted by total_weight descending."""
        ranker = DrugRanker()
        result = ranker.rank(drug_aggregate_multi)
        assert len(result) == 2
        # Osimertinib has higher total_weight → rank 1
        assert result[0]["drug_name"] == "Osimertinib"
        assert result[0]["rank"] == 1
        assert result[1]["drug_name"] == "Pembrolizumab"
        assert result[1]["rank"] == 2
        # Verify scores
        assert result[0]["total_weight"] > result[1]["total_weight"]

    def test_rank_structure(self, drug_aggregate_single):
        """Each entry should contain expected keys."""
        ranker = DrugRanker()
        result = ranker.rank(drug_aggregate_single)
        entry = result[0]
        assert "drug_name" in entry
        assert "total_weight" in entry
        assert "source_count" in entry
        assert "item_count" in entry
        assert "highest_weight" in entry
        assert "rank" in entry
        assert "sources" in entry

    def test_rank_custom_sort_keys(self, drug_aggregate_multi):
        """Custom sort keys should change ranking order."""
        ranker = DrugRanker(sort_keys=["-source_count", "-total_weight"])
        result = ranker.rank(drug_aggregate_multi)
        # Osimertinib has 3 sources, Pembrolizumab has 2
        assert result[0]["drug_name"] == "Osimertinib"

        # Reverse order
        ranker_asc = DrugRanker(sort_keys=["total_weight"])
        result_asc = ranker_asc.rank(drug_aggregate_multi)
        # Pembrolizumab has lower total_weight → first when ascending
        assert result_asc[0]["drug_name"] == "Pembrolizumab"


# ═══════════════════════════════════════════════════════════════════════════════
# RecommendationRule Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestRecommendationRule:
    """Test rule evaluation with conditions and actions."""

    def test_rule_no_condition_no_action(self):
        """Rule with no condition and no action should return None."""
        rule = RecommendationRule(
            rule_id="test_01",
            name="No-op",
            description="Does nothing.",
        )
        result = rule.evaluate({})
        assert result is None

    def test_rule_condition_true_action_returns(self):
        """When condition is True, action should execute and return a value."""
        def condition(ctx: dict) -> bool:
            return ctx.get("flag", False)

        def action(ctx: dict) -> str:
            return f"fired for {ctx['drug']}"

        rule = RecommendationRule(
            rule_id="test_02",
            name="Flag rule",
            condition=condition,
            action=action,
        )
        result = rule.evaluate({"flag": True, "drug": "Osimertinib"})
        assert result == "fired for Osimertinib"

    def test_rule_condition_false_skips(self):
        """When condition is False, action should not execute."""
        def condition(ctx: dict) -> bool:
            return ctx.get("flag", False)

        call_count = [0]

        def action(ctx: dict) -> str:
            call_count[0] += 1
            return "fired"

        rule = RecommendationRule(
            rule_id="test_03",
            name="Skip rule",
            condition=condition,
            action=action,
        )
        result = rule.evaluate({"flag": False})
        assert result is None
        assert call_count[0] == 0

    def test_rule_always_fires_when_no_condition(self):
        """Rule with no condition should always fire its action."""
        def action(ctx: dict) -> str:
            return "always"

        rule = RecommendationRule(
            rule_id="test_04",
            name="Always fire",
            action=action,
        )
        result = rule.evaluate({"anything": 42})
        assert result == "always"

    def test_rule_condition_exception_handled(self):
        """An exception in condition should be caught and rule skipped."""
        def condition(ctx: dict) -> bool:
            raise RuntimeError("oops")

        rule = RecommendationRule(
            rule_id="test_05",
            name="Failing condition",
            condition=condition,
        )
        result = rule.evaluate({})
        assert result is None  # gracefully handled

    def test_rule_action_exception_handled(self):
        """An exception in action should be caught and None returned."""
        def action(ctx: dict) -> str:
            raise RuntimeError("action failed")

        rule = RecommendationRule(
            rule_id="test_06",
            name="Failing action",
            condition=lambda ctx: True,
            action=action,
        )
        result = rule.evaluate({})
        assert result is None

    def test_rule_priority_ordering(self):
        """Rules should be sorted by priority descending."""
        rule_low = RecommendationRule(rule_id="low", name="Low", priority=0)
        rule_high = RecommendationRule(rule_id="high", name="High", priority=10)
        rule_med = RecommendationRule(rule_id="med", name="Med", priority=5)

        engine = RecommendationEngine.__new__(RecommendationEngine)
        engine._rules = sorted(
            [rule_low, rule_high, rule_med],
            key=lambda r: r.priority,
            reverse=True,
        )
        assert engine._rules[0].rule_id == "high"
        assert engine._rules[1].rule_id == "med"
        assert engine._rules[2].rule_id == "low"


# ═══════════════════════════════════════════════════════════════════════════════
# DrugRanking Scoring Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestEvidenceScore:
    """Test compute_evidence_score function."""

    def test_empty_evidence(self):
        """Empty evidence list returns score with zeros."""
        aggregate = {
            "evidence_scores": [],
            "total_weight": 0.0,
            "source_count": 0,
            "item_count": 0,
            "highest_weight": 0.0,
        }
        score = compute_evidence_score(aggregate)
        assert score.total_weighted_score == 0.0
        assert score.source_diversity == 0.0
        assert score.highest_tier == "Tier_4"
        assert score.confidence_score == 0.0

    def test_high_quality_evidence(self, drug_aggregate_single):
        """Strong evidence yields high confidence score."""
        score = compute_evidence_score(
            drug_aggregate_single["Osimertinib"],
        )
        assert score.total_weighted_score > 0
        assert score.source_diversity > 0
        # highest_tier is determined from the evidence_scores' "tier" field
        # which comes from evidence_level strings like "Category 1", not "Tier_0"
        # So it will be the best tier string found
        assert score.confidence_score > 0.4
        assert score.total_weighted_score == 2.85
        assert score.source_diversity == 1.0

    def test_source_diversity_calculation(self):
        """source_diversity = source_count / item_count, capped at 1.0."""
        aggregate = {
            "evidence_scores": [
                {"weight": 0.5, "tier": "Tier_2", "direction": "supporting"},
                {"weight": 0.8, "tier": "Tier_1", "direction": "supporting"},
            ],
            "total_weight": 1.3,
            "source_count": 2,
            "item_count": 2,
            "highest_weight": 0.8,
        }
        score = compute_evidence_score(aggregate)
        assert score.source_diversity == pytest.approx(1.0)

    def test_custom_diversity_weight(self, drug_aggregate_single):
        """Diversity weight parameter affects confidence score."""
        agg = drug_aggregate_single["Osimertinib"]
        score_low = compute_evidence_score(agg, diversity_weight=0.1)
        score_high = compute_evidence_score(agg, diversity_weight=0.9)
        assert score_low.confidence_score != score_high.confidence_score

    def test_weight_cap(self):
        """Total weight above cap should be normalised to 1.0."""
        aggregate = {
            "evidence_scores": [{"weight": 10.0, "tier": "Tier_1", "direction": "supporting"}],
            "total_weight": 20.0,
            "source_count": 1,
            "item_count": 1,
            "highest_weight": 10.0,
        }
        score = compute_evidence_score(aggregate, weight_cap=10.0)
        assert score.confidence_score <= 1.0


class TestSensitivity:
    """Test compute_sensitivity function."""

    def test_empty_evidence(self):
        """No evidence items yields zero sensitivity."""
        sens = compute_sensitivity("TestDrug", [])
        assert sens.score == 0.0
        assert sens.supporting_item_count == 0
        assert sens.total_item_count == 0
        assert "No evidence items" in sens.details

    def test_all_supporting(self):
        """All supporting items should give high sensitivity."""
        items = [
            {"direction": "supporting", "weight": 1.0},
            {"direction": "supporting", "weight": 0.8},
        ]
        sens = compute_sensitivity("DrugA", items)
        assert sens.score == pytest.approx(1.0)
        assert sens.supporting_item_count == 2
        assert sens.total_item_count == 2

    def test_mixed_directions(self):
        """Mixed directions reduce sensitivity."""
        items = [
            {"direction": "supporting", "weight": 1.0},
            {"direction": "resistance", "weight": 1.0},
            {"direction": "neutral", "weight": 1.0},
        ]
        sens = compute_sensitivity("DrugA", items)
        # supporting: (1.0 * 1.0) = 1.0, contributes to total_weight
        # resistance: contributes NOTHING to total_weight
        # neutral: (1.0 * 0.3) = 0.3, contributes to total_weight
        # supporting_weight = 1.0 + 0.3 = 1.3, total_weight = 2.0
        # score = 1.3 / 2.0 = 0.65
        assert sens.score == pytest.approx(0.65, rel=1e-3)
        assert sens.supporting_item_count == 1
        assert sens.total_item_count == 3

    def test_custom_neutral_factor(self):
        """Neutral_factor changes sensitivity contribution of neutral items."""
        items = [
            {"direction": "neutral", "weight": 1.0},
        ]
        sens_default = compute_sensitivity("DrugA", items, neutral_factor=0.3)
        sens_custom = compute_sensitivity("DrugA", items, neutral_factor=0.8)
        assert sens_custom.score > sens_default.score

    def test_supporting_bonus(self):
        """Supporting bonus amplifies supporting weight contribution."""
        items = [
            {"direction": "supporting", "weight": 1.0},
        ]
        sens = compute_sensitivity("DrugA", items, supporting_bonus=2.0)
        # (1.0 * 2.0) / 1.0 = 2.0, capped at 1.0
        assert sens.score == 1.0

    def test_fuzzy_direction_matching(self):
        """Direction strings like 'sensitive' and 'responder' should be normalised."""
        items = [
            {"direction": "sensitive", "weight": 1.0},
            {"direction": "Responder", "weight": 0.8},
        ]
        sens = compute_sensitivity("DrugA", items)
        assert sens.score == pytest.approx(1.0)
        assert sens.supporting_item_count == 2


class TestResistance:
    """Test compute_resistance function."""

    def test_empty_evidence(self):
        """No evidence yields zero resistance."""
        res = compute_resistance("TestDrug", [])
        assert res.score == 0.0
        assert res.resistance_item_count == 0

    def test_no_resistance(self):
        """All supporting items yield zero resistance."""
        items = [
            {"direction": "supporting", "weight": 1.0},
        ]
        res = compute_resistance("DrugA", items)
        assert res.score == 0.0
        assert res.resistance_item_count == 0

    def test_all_resistance(self):
        """All resistance items yield high resistance score."""
        items = [
            {"direction": "resistance", "weight": 1.0},
            {"direction": "resistance", "weight": 0.8},
        ]
        res = compute_resistance("DrugA", items)
        assert res.score == pytest.approx(1.0)
        assert res.resistance_item_count == 2

    def test_mixed_resistance(self):
        """Mixed evidence produces intermediate resistance score."""
        items = [
            {"direction": "supporting", "weight": 1.0},
            {"direction": "resistance", "weight": 1.0},
        ]
        res = compute_resistance("DrugA", items)
        assert res.score == pytest.approx(0.5)

    def test_clinical_significance_detection(self):
        """Resistance detected from clinical_significance field."""
        items = [
            {"direction": "supporting", "weight": 0.8, "clinical_significance": "resistance"},
        ]
        res = compute_resistance("DrugA", items)
        assert res.score > 0
        assert res.resistance_item_count == 1

    def test_fuzzy_resistance_keywords(self):
        """Keywords like 'non-response' in clinical_significance should trigger detection."""
        items = [
            {"direction": "supporting", "weight": 0.8, "clinical_significance": "non-response"},
        ]
        res = compute_resistance("DrugA", items)
        assert res.resistance_item_count == 1

    def test_resistance_penalty_multiplier(self):
        """Resistance penalty is applied via resistance_penalty parameter at overall level,
        but compute_resistance itself should use resistance_penalty for weight scaling."""
        items = [
            {"direction": "resistance", "weight": 1.0},
        ]
        res = compute_resistance("DrugA", items, resistance_penalty=2.0)
        # resistance_weight = 1.0 * 2.0 = 2.0, total_weight = 1.0, score = 2.0/1.0 = 2.0 capped to 1.0
        assert res.score == 1.0


class TestConflictScore:
    """Test compute_conflict_score function."""

    def test_empty_evidence(self):
        """No evidence yields zero conflict."""
        conflict = compute_conflict_score([])
        assert conflict.score == 0.0
        assert conflict.conflicting_pairs == 0

    def test_single_item(self):
        """Single item cannot have conflict."""
        items = [{"direction": "supporting", "weight": 1.0}]
        conflict = compute_conflict_score(items)
        assert conflict.score == 0.0
        assert conflict.conflicting_pairs == 0

    def test_all_supporting(self):
        """All supporting items yield no conflict."""
        items = [
            {"direction": "supporting", "weight": 1.0},
            {"direction": "supporting", "weight": 0.8},
        ]
        conflict = compute_conflict_score(items)
        assert conflict.score == 0.0

    def test_supporting_vs_resistance(self):
        """Supporting vs resistance should create conflict pairs."""
        items = [
            {"direction": "supporting", "weight": 1.0},
            {"direction": "resistance", "weight": 1.0},
        ]
        conflict = compute_conflict_score(items)
        assert conflict.score > 0
        assert conflict.conflicting_pairs == 1  # 1 supporting × 1 resistance

    def test_conflicting_direction(self):
        """Items with 'conflicting' direction should also contribute."""
        items = [
            {"direction": "supporting", "weight": 1.0},
            {"direction": "conflicting", "weight": 1.0},
        ]
        conflict = compute_conflict_score(items)
        assert conflict.score > 0

    def test_conflict_threshold(self):
        """Items below conflict_threshold weight should be ignored."""
        items = [
            {"direction": "supporting", "weight": 1.0},
            {"direction": "resistance", "weight": 0.1},  # below threshold 0.2
        ]
        conflict = compute_conflict_score(items, conflict_threshold=0.2)
        assert conflict.score == 0.0  # resistance item filtered out

    def test_multiple_conflict_pairs(self):
        """Multiple supporting and resistance items multiply conflict pairs."""
        items = [
            {"direction": "supporting", "weight": 0.9},
            {"direction": "supporting", "weight": 0.8},
            {"direction": "resistance", "weight": 0.7},
            {"direction": "resistance", "weight": 0.6},
        ]
        conflict = compute_conflict_score(items)
        assert conflict.conflicting_pairs == 4  # 2 supporting × 2 resistance


class TestOverallScore:
    """Test compute_overall_score function."""

    def test_all_perfect_scores(self):
        """Perfect sub-scores should yield high overall score."""
        ev_score = EvidenceScore(
            total_weighted_score=10.0,
            source_diversity=1.0,
            highest_tier="Tier_0",
            confidence_score=0.9,
        )
        sens = Sensitivity(score=0.9, supporting_item_count=5, total_item_count=5, details="")
        res = Resistance(score=0.0, resistance_item_count=0, total_item_count=5, details="")
        conflict = compute_conflict_score([
            {"direction": "supporting", "weight": 1.0},
            {"direction": "supporting", "weight": 1.0},
        ])
        overall = compute_overall_score(ev_score, sens, res, conflict)
        # 0.40*0.9 + 0.35*0.9 - 0.15*0.0 - 0.10*0.0 = 0.36 + 0.315 = 0.675
        assert overall.raw_score == pytest.approx(0.675)

    def test_with_resistance_penalty(self):
        """Resistance should reduce overall score."""
        ev_score = EvidenceScore(confidence_score=0.5)
        sens = Sensitivity(score=0.5, supporting_item_count=3, total_item_count=5, details="")
        res = Resistance(score=0.8, resistance_item_count=4, total_item_count=5, details="")
        conflict = compute_conflict_score([
            {"direction": "supporting", "weight": 1.0},
            {"direction": "resistance", "weight": 1.0},
        ])
        overall = compute_overall_score(ev_score, sens, res, conflict)
        assert overall.raw_score < 0.5  # penalised

    def test_with_conflict_penalty(self):
        """Conflict should reduce overall score."""
        ev_score = EvidenceScore(confidence_score=0.5)
        sens = Sensitivity(score=0.5, supporting_item_count=3, total_item_count=5, details="")
        res = Resistance(score=0.0, resistance_item_count=0, total_item_count=5, details="")
        conflict = compute_conflict_score([
            {"direction": "supporting", "weight": 1.0},
            {"direction": "resistance", "weight": 1.0},
        ])
        overall = compute_overall_score(ev_score, sens, res, conflict)
        assert overall.raw_score < 0.5  # penalised

    def test_custom_weights(self):
        """Custom weight parameters change overall score."""
        ev_score = EvidenceScore(confidence_score=0.5)
        sens = Sensitivity(score=0.5, supporting_item_count=3, total_item_count=5, details="")
        res = Resistance(score=0.2, resistance_item_count=1, total_item_count=5, details="")
        conflict = compute_conflict_score([
            {"direction": "supporting", "weight": 1.0},
            {"direction": "resistance", "weight": 1.0},
        ])
        overall = compute_overall_score(
            ev_score, sens, res, conflict,
            evidence_weight=0.5, sensitivity_weight=0.3,
            resistance_penalty=0.1, conflict_penalty=0.1,
        )
        # 0.5*0.5 + 0.3*0.5 - 0.1*0.2 - 0.1*conflict.score
        assert overall.raw_score == pytest.approx(
            0.5 * 0.5 + 0.3 * 0.5 - 0.1 * 0.2 - 0.1 * conflict.score,
        )

    def test_overall_score_structure(self):
        """OverallScore should contain all sub-score values."""
        ev_score = EvidenceScore(confidence_score=0.6)
        sens = Sensitivity(score=0.7, supporting_item_count=3, total_item_count=5, details="")
        res = Resistance(score=0.1, resistance_item_count=1, total_item_count=5, details="")
        conflict = compute_conflict_score([
            {"direction": "supporting", "weight": 1.0},
            {"direction": "supporting", "weight": 1.0},
        ])
        overall = compute_overall_score(ev_score, sens, res, conflict)
        assert overall.evidence_score_value == 0.6
        assert overall.sensitivity_value == 0.7
        assert overall.resistance_value == 0.1
        assert overall.conflict_value == conflict.score


# ═══════════════════════════════════════════════════════════════════════════════
# DrugRankingEngine Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestDrugRankingEngine:
    """Test the full DrugRankingEngine pipeline."""

    def test_rank_empty(self):
        """Empty aggregated data yields empty results."""
        engine = DrugRankingEngine()
        results = engine.rank({})
        assert results == []

    def test_rank_single_drug(self, drug_aggregate_single):
        """Single drug should produce one DrugRankingResult."""
        engine = DrugRankingEngine()
        results = engine.rank(drug_aggregate_single)
        assert len(results) == 1
        r = results[0]
        assert isinstance(r, DrugRankingResult)
        assert r.drug_name == "Osimertinib"
        assert r.rank == 1
        assert r.overall_score.raw_score > 0
        assert r.evidence_score.confidence_score > 0
        assert r.sensitivity.score > 0
        assert r.resistance.score == 0
        assert r.conflict_score.score == 0

    def test_rank_multiple_drugs(self, drug_aggregate_multi):
        """Multiple drugs should be ranked by overall_score descending."""
        engine = DrugRankingEngine()
        results = engine.rank(drug_aggregate_multi)
        assert len(results) == 2
        # Osimertinib should rank first (higher evidence weight)
        assert results[0].drug_name == "Osimertinib"
        assert results[0].rank == 1
        assert results[1].drug_name == "Pembrolizumab"
        assert results[1].rank == 2
        # Osimertinib should have higher overall score
        assert results[0].overall_score.raw_score >= results[1].overall_score.raw_score

    def test_rank_top_n(self, drug_aggregate_multi):
        """top_n parameter limits the number of results."""
        engine = DrugRankingEngine()
        results = engine.rank(drug_aggregate_multi, top_n=1)
        assert len(results) == 1
        assert results[0].drug_name == "Osimertinib"

    def test_rank_drug_with_resistance(self):
        """Drugs with resistance evidence should have lower overall score."""
        agg = {
            "DrugX": {
                "evidence_scores": [
                    {"weight": 1.0, "source": "nccn", "tier": "Category 1", "direction": "supporting", "clinical_significance": "sensitivity", "conflict_status": ""},
                    {"weight": 0.85, "source": "civic", "tier": "A", "direction": "resistance", "clinical_significance": "resistance", "conflict_status": ""},
                ],
                "total_weight": 1.85,
                "source_count": 2,
                "item_count": 2,
                "highest_weight": 1.0,
                "sources": {"nccn", "civic"},
                "directions": {"supporting", "resistance"},
            }
        }
        engine = DrugRankingEngine()
        results = engine.rank(agg)
        assert len(results) == 1
        r = results[0]
        assert r.resistance.score > 0
        assert r.conflict_score.score > 0  # supporting + resistance = conflict
        # Overall should be reduced due to resistance and conflict
        assert r.overall_score.raw_score < 0.5

    def test_rank_result_structure(self, drug_aggregate_single):
        """DrugRankingResult should contain all expected sub-scores."""
        engine = DrugRankingEngine()
        results = engine.rank(drug_aggregate_single)
        r = results[0]
        assert r.drug_name == "Osimertinib"
        assert r.overall_score.raw_score is not None
        assert r.evidence_score.confidence_score is not None
        assert r.sensitivity.score is not None
        assert r.resistance.score is not None
        assert r.conflict_score.score is not None
        assert r.rank >= 1
        assert "item_count" in r.details
        assert "source_count" in r.details
        assert "sources" in r.details

    def test_rank_custom_weights(self, drug_aggregate_single):
        """Custom engine weights should change the overall score."""
        engine_default = DrugRankingEngine()
        engine_custom = DrugRankingEngine(
            evidence_weight=0.6,
            sensitivity_weight=0.2,
            resistance_penalty=0.1,
            conflict_penalty=0.1,
        )
        r_default = engine_default.rank(drug_aggregate_single)[0]
        r_custom = engine_custom.rank(drug_aggregate_single)[0]
        # Different weights should produce different raw_score
        assert r_default.overall_score.raw_score != r_custom.overall_score.raw_score

    def test_rank_stable_sorting(self):
        """Drugs with identical scores should have deterministic ordering."""
        agg = {
            "DrugA": {
                "evidence_scores": [{"weight": 1.0, "source": "nccn", "tier": "Category 1", "direction": "supporting", "clinical_significance": "", "conflict_status": ""}],
                "total_weight": 1.0,
                "source_count": 1,
                "item_count": 1,
                "highest_weight": 1.0,
                "sources": {"nccn"},
                "directions": {"supporting"},
            },
            "DrugB": {
                "evidence_scores": [{"weight": 1.0, "source": "nccn", "tier": "Category 1", "direction": "supporting", "clinical_significance": "", "conflict_status": ""}],
                "total_weight": 1.0,
                "source_count": 1,
                "item_count": 1,
                "highest_weight": 1.0,
                "sources": {"nccn"},
                "directions": {"supporting"},
            },
        }
        engine = DrugRankingEngine()
        r1 = engine.rank(agg)
        r2 = engine.rank(agg)
        for a, b in zip(r1, r2):
            assert a.drug_name == b.drug_name
            assert a.rank == b.rank


# ═══════════════════════════════════════════════════════════════════════════════
# EvidenceWeightConfig Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestEvidenceWeightConfig:
    """Test EvidenceWeightConfig validation and methods."""

    def test_valid_config(self):
        """A correctly formed config should pass validation."""
        config = EvidenceWeightConfig(
            source_name="test_source",
            base_weight=0.8,
            tier_mapping={"High": 0.9, "Low": 0.2},
            weight_version="1.0.0",
        )
        assert config.source_name == "test_source"
        assert config.base_weight == 0.8

    def test_invalid_tier_weight_raises(self):
        """Tier weight outside [0, 1] should raise ValidationError."""
        with pytest.raises(ValidationError):
            EvidenceWeightConfig(
                source_name="bad",
                tier_mapping={"High": 1.5},  # > 1.0
            )

    def test_invalid_base_weight_raises(self):
        """Base weight outside [0, 1] should raise ValidationError."""
        with pytest.raises(ValidationError):
            EvidenceWeightConfig(
                source_name="bad",
                base_weight=-0.1,
                tier_mapping={"High": 0.5},
            )

    def test_invalid_version_format_raises(self):
        """Version string must match semver pattern."""
        with pytest.raises(ValidationError):
            EvidenceWeightConfig(
                source_name="bad",
                tier_mapping={"High": 0.5},
                weight_version="abc",
            )

    def test_resolve_weight_with_base(self):
        """resolve_weight multiplies tier weight by base_weight."""
        config = EvidenceWeightConfig(
            source_name="test",
            base_weight=0.8,
            tier_mapping={"High": 0.9},
        )
        assert config.resolve_weight("High") == 0.72  # 0.9 * 0.8

    def test_resolve_weight_unknown(self):
        """Unknown tier returns 0.0."""
        config = EvidenceWeightConfig(
            source_name="test",
            tier_mapping={"High": 0.9},
        )
        assert config.resolve_weight("UnknownTier") == 0.0
