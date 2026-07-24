"""
Golden tests for the recommendation pipeline (P3A-10).

Uses predefined test data (variants + synthetic evidence) to validate the
complete recommendation pipeline output structure, ranking logic, and schema
conformance.  Marked with ``@pytest.mark.golden``.

These tests verify that:
- The pipeline produces results with the expected structure
- Rankings are in the correct order (highest score first)
- The output conforms to the expected schema
- Edge cases (single drug, multiple drugs, empty evidence) behave correctly
"""

from __future__ import annotations

import json
from typing import Any
from pathlib import Path

import pytest

from src.backend.clinical.drug_ranking import DrugRankingEngine
from src.backend.clinical.evidence_models import EvidenceBundle, EvidenceItem
from src.backend.clinical.evidence_weight import WeightRegistry
from src.backend.clinical.recommendation_engine import (
    DrugRanker,
    EvidenceAggregator,
)

pytestmark = [pytest.mark.golden]


# ═══════════════════════════════════════════════════════════════════════════════
# Golden Test Data
# ═══════════════════════════════════════════════════════════════════════════════

# Predefined variants used across golden tests
GOLDEN_VARIANTS: list[dict[str, str]] = [
    {"gene_symbol": "EGFR", "protein_change": "L858R"},
    {"gene_symbol": "KRAS", "protein_change": "G12C"},
    {"gene_symbol": "BRAF", "protein_change": "V600E"},
]


def make_evidence_item(
    *,
    source: str,
    drug_name: str,
    gene_symbol: str,
    evidence_level: str,
    evidence_direction: str = "supporting",
    clinical_significance: str = "",
    conflict_status: str = "",
) -> EvidenceItem:
    """Helper to create an EvidenceItem with standard defaults."""
    return EvidenceItem(
        source=source,
        drug_name=drug_name,
        gene_symbol=gene_symbol,
        evidence_level=evidence_level,
        evidence_direction=evidence_direction,
        clinical_significance=clinical_significance or evidence_direction,
        conflict_status=conflict_status,
    )


@pytest.fixture
def golden_evidence_bundle_multidrug() -> EvidenceBundle:
    """Predefined evidence bundle with multiple drugs and sources."""
    return EvidenceBundle(items=[
        # Osimertinib — strong evidence, 3 sources, all supporting
        make_evidence_item(
            source="nccn", drug_name="Osimertinib", gene_symbol="EGFR",
            evidence_level="Category 1", evidence_direction="supporting",
        ),
        make_evidence_item(
            source="fda", drug_name="Osimertinib", gene_symbol="EGFR",
            evidence_level="Approved", evidence_direction="supporting",
        ),
        make_evidence_item(
            source="civic", drug_name="Osimertinib", gene_symbol="EGFR",
            evidence_level="A", evidence_direction="supporting",
        ),
        # Pembrolizumab — mixed evidence (supporting + resistance)
        make_evidence_item(
            source="nccn", drug_name="Pembrolizumab", gene_symbol="PD-L1",
            evidence_level="Category 2A", evidence_direction="supporting",
        ),
        make_evidence_item(
            source="civic", drug_name="Pembrolizumab", gene_symbol="PD-L1",
            evidence_level="B", evidence_direction="resistance",
            clinical_significance="resistance",
        ),
        # Dabrafenib — single source, moderate evidence
        make_evidence_item(
            source="oncokb", drug_name="Dabrafenib", gene_symbol="BRAF",
            evidence_level="Level 2", evidence_direction="supporting",
        ),
    ])


@pytest.fixture
def golden_evidence_bundle_single_drug() -> EvidenceBundle:
    """Predefined evidence bundle with a single drug."""
    return EvidenceBundle(items=[
        make_evidence_item(
            source="nccn", drug_name="Osimertinib", gene_symbol="EGFR",
            evidence_level="Category 1", evidence_direction="supporting",
        ),
        make_evidence_item(
            source="fda", drug_name="Osimertinib", gene_symbol="EGFR",
            evidence_level="Approved", evidence_direction="supporting",
        ),
        make_evidence_item(
            source="civic", drug_name="Osimertinib", gene_symbol="EGFR",
            evidence_level="A", evidence_direction="supporting",
        ),
        make_evidence_item(
            source="dgidb", drug_name="Osimertinib", gene_symbol="EGFR",
            evidence_level="FDA-approved", evidence_direction="neutral",
        ),
    ])


@pytest.fixture
def golden_evidence_bundle_empty() -> EvidenceBundle:
    """Empty evidence bundle for edge-case testing."""
    return EvidenceBundle(items=[])


# ═══════════════════════════════════════════════════════════════════════════════
# Golden Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestGoldenRecommendationPipeline:
    """Golden tests for the full recommendation pipeline."""

    def test_golden_multidrug_output_structure(self, golden_evidence_bundle_multidrug):
        """Verify the pipeline output structure for multiple drugs."""
        # Step 1: Aggregate
        aggregator = EvidenceAggregator()
        aggregated = aggregator.aggregate(golden_evidence_bundle_multidrug)

        assert len(aggregated) >= 2, "Should have at least 2 drugs"
        assert "Osimertinib" in aggregated
        assert "Pembrolizumab" in aggregated

        # Verify aggregation structure
        for drug_name, agg_data in aggregated.items():
            assert "evidence_scores" in agg_data
            assert "total_weight" in agg_data
            assert "source_count" in agg_data
            assert "item_count" in agg_data
            assert "highest_weight" in agg_data
            assert "sources" in agg_data
            assert "directions" in agg_data
            assert isinstance(agg_data["evidence_scores"], list)
            assert agg_data["item_count"] >= 1
            assert agg_data["source_count"] >= 1

        # Step 2: Rank (simple)
        ranker = DrugRanker()
        ranked = ranker.rank(aggregated)
        assert len(ranked) == len(aggregated)

        # Highest total_weight drug should be ranked #1
        assert ranked[0]["rank"] == 1
        assert ranked[0]["total_weight"] >= ranked[1]["total_weight"]

        # Step 3: Detailed scoring
        engine = DrugRankingEngine()
        results = engine.rank(aggregated)
        assert len(results) == len(aggregated)

        # Verify result structure
        for r in results:
            assert r.drug_name in aggregated
            assert r.rank >= 1
            assert r.overall_score.raw_score is not None
            assert 0 <= r.evidence_score.confidence_score <= 1.0
            assert 0 <= r.sensitivity.score <= 1.0
            assert 0 <= r.resistance.score <= 1.0
            assert 0 <= r.conflict_score.score <= 1.0
            assert "item_count" in r.details
            assert "source_count" in r.details
            assert "sources" in r.details

    def test_golden_ranking_order(self, golden_evidence_bundle_multidrug):
        """Verify that drugs are ranked correctly by evidence strength.

        Expected order (by evidence strength):
        1. Osimertinib — 3 sources, all supporting, high tiers
        2. Dabrafenib — 1 source, supporting, moderate tier
        3. Pembrolizumab — 2 sources, mixed supporting + resistance
        """
        aggregator = EvidenceAggregator()
        aggregated = aggregator.aggregate(golden_evidence_bundle_multidrug)

        engine = DrugRankingEngine()
        results = engine.rank(aggregated)

        # Get drug names in rank order
        ranked_names = [r.drug_name for r in results]

        # Osimertinib should be first (strongest evidence)
        assert ranked_names[0] == "Osimertinib", (
            f"Expected Osimertinib first, got {ranked_names}"
        )

        # Osimertinib should have higher overall score than others
        assert results[0].overall_score.raw_score > results[1].overall_score.raw_score

        # Verify scores are descending
        for i in range(len(results) - 1):
            assert results[i].overall_score.raw_score >= results[i + 1].overall_score.raw_score, (
                f"Rank {i+1} ({results[i].drug_name}) should have >= score than "
                f"rank {i+2} ({results[i+1].drug_name})"
            )

    def test_golden_osimertinib_top_rank(self, golden_evidence_bundle_multidrug):
        """Osimertinib should rank #1 with highest evidence score."""
        aggregator = EvidenceAggregator()
        aggregated = aggregator.aggregate(golden_evidence_bundle_multidrug)

        engine = DrugRankingEngine()
        results = engine.rank(aggregated)

        top = results[0]
        assert top.drug_name == "Osimertinib"
        assert top.rank == 1
        # Osimertinib has Category 1 + Approved + A → moderate confidence
        assert top.evidence_score.confidence_score >= 0.5
        # All supporting → high sensitivity
        assert top.sensitivity.score >= 0.8
        # No resistance evidence
        assert top.resistance.score == 0.0

    def test_golden_pembrolizumab_resistance(self, golden_evidence_bundle_multidrug):
        """Pembrolizumab should have resistance penalty."""
        aggregator = EvidenceAggregator()
        aggregated = aggregator.aggregate(golden_evidence_bundle_multidrug)

        engine = DrugRankingEngine()
        results = engine.rank(aggregated)

        pembro = [r for r in results if r.drug_name == "Pembrolizumab"]
        assert len(pembro) == 1
        p = pembro[0]
        # Has resistance evidence
        assert p.resistance.score > 0
        # Has conflict (supporting + resistance)
        assert p.conflict_score.score > 0

    def test_golden_single_drug(self, golden_evidence_bundle_single_drug):
        """Pipeline handles single-drug input correctly."""
        aggregator = EvidenceAggregator()
        aggregated = aggregator.aggregate(golden_evidence_bundle_single_drug)
        assert len(aggregated) == 1

        ranker = DrugRanker()
        ranked = ranker.rank(aggregated)
        assert len(ranked) == 1
        assert ranked[0]["drug_name"] == "Osimertinib"
        assert ranked[0]["rank"] == 1

        engine = DrugRankingEngine()
        results = engine.rank(aggregated)
        assert len(results) == 1
        r = results[0]
        assert r.drug_name == "Osimertinib"
        assert r.rank == 1
        assert r.overall_score.raw_score > 0

    def test_golden_empty_evidence(self, golden_evidence_bundle_empty):
        """Pipeline handles empty evidence gracefully."""
        aggregator = EvidenceAggregator()
        aggregated = aggregator.aggregate(golden_evidence_bundle_empty)
        assert aggregated == {}

        ranker = DrugRanker()
        ranked = ranker.rank(aggregated)
        assert ranked == []

        engine = DrugRankingEngine()
        results = engine.rank(aggregated)
        assert results == []

    def test_golden_top_n(self, golden_evidence_bundle_multidrug):
        """top_n parameter limits the number of results."""
        aggregator = EvidenceAggregator()
        aggregated = aggregator.aggregate(golden_evidence_bundle_multidrug)

        engine = DrugRankingEngine()
        results_all = engine.rank(aggregated)
        results_top1 = engine.rank(aggregated, top_n=1)
        results_top2 = engine.rank(aggregated, top_n=2)

        assert len(results_top1) == 1
        assert len(results_top2) == 2
        assert len(results_top1) <= len(results_all)
        assert len(results_top2) <= len(results_all)

        if results_all:
            assert results_top1[0].drug_name == results_all[0].drug_name

    def test_golden_aggregation_scores(self, golden_evidence_bundle_multidrug):
        """Verify that aggregation scores are computed correctly."""
        aggregator = EvidenceAggregator()
        aggregated = aggregator.aggregate(golden_evidence_bundle_multidrug)

        # Osimertinib: NCCN Cat1 (1.0) + FDA Approved (1.0) + CIViC A (1.0) = 3.0
        osim = aggregated["Osimertinib"]
        assert osim["total_weight"] == pytest.approx(3.0)
        assert osim["source_count"] == 3
        assert osim["item_count"] == 3

        # Pembrolizumab: NCCN Cat2A (0.85) + CIViC B (0.85) = 1.70
        pembro = aggregated["Pembrolizumab"]
        assert pembro["total_weight"] == pytest.approx(1.70)
        assert pembro["source_count"] == 2
        assert pembro["item_count"] == 2

        # Dabrafenib: OncoKB Level2 (0.85) = 0.85
        dab = aggregated["Dabrafenib"]
        assert dab["total_weight"] == pytest.approx(0.85)
        assert dab["source_count"] == 1
        assert dab["item_count"] == 1

    def test_golden_scores_in_range(self, golden_evidence_bundle_multidrug):
        """Verify that all scores are within valid ranges."""
        aggregator = EvidenceAggregator()
        aggregated = aggregator.aggregate(golden_evidence_bundle_multidrug)

        engine = DrugRankingEngine()
        results = engine.rank(aggregated)

        for r in results:
            assert 0.0 <= r.overall_score.raw_score <= 1.0, (
                f"{r.drug_name} overall_score {r.overall_score.raw_score} out of range"
            )
            assert 0.0 <= r.evidence_score.confidence_score <= 1.0
            assert 0.0 <= r.sensitivity.score <= 1.0
            assert 0.0 <= r.resistance.score <= 1.0
            assert 0.0 <= r.conflict_score.score <= 1.0

    def test_golden_rank_assignment(self, golden_evidence_bundle_multidrug):
        """Verify that ranks are 1-based and consecutive."""
        aggregator = EvidenceAggregator()
        aggregated = aggregator.aggregate(golden_evidence_bundle_multidrug)

        engine = DrugRankingEngine()
        results = engine.rank(aggregated)

        ranks = sorted([r.rank for r in results])
        assert ranks == list(range(1, len(results) + 1))


# ═══════════════════════════════════════════════════════════════════════════════
# WeightRegistry Golden Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestGoldenWeightRegistry:
    """Golden tests for WeightRegistry with known source configs."""

    def test_golden_nccn_weights(self):
        """NCCN tier mapping should produce known weights."""
        assert WeightRegistry.get_weight("nccn", "Category 1") == 1.0
        assert WeightRegistry.get_weight("nccn", "Category 2A") == 0.85
        assert WeightRegistry.get_weight("nccn", "Category 2B") == 0.70
        assert WeightRegistry.get_weight("nccn", "Category 3") == 0.50
        assert WeightRegistry.get_weight("nccn", "not_assessed") == 0.20

    def test_golden_fda_weights(self):
        """FDA tier mapping should produce known weights."""
        assert WeightRegistry.get_weight("fda", "Approved") == 1.0
        assert WeightRegistry.get_weight("fda", "Breakthrough Therapy") == 0.90
        assert WeightRegistry.get_weight("fda", "Fast Track") == 0.75
        assert WeightRegistry.get_weight("fda", "Orphan Drug") == 0.60
        assert WeightRegistry.get_weight("fda", "Investigational") == 0.40

    def test_golden_dgidb_weights_with_base(self):
        """DGIdb applies base_weight=0.85 to its tier weights."""
        # FDA-approved: 0.90 * 0.85 = 0.765
        assert WeightRegistry.get_weight("dgidb", "FDA-approved") == pytest.approx(0.765)
        # Clinical trial: 0.70 * 0.85 = 0.595
        assert WeightRegistry.get_weight("dgidb", "Clinical trial") == pytest.approx(0.595)

    def test_golden_registered_sources(self):
        """All six default sources should be registered."""
        sources = WeightRegistry.registered_sources()
        expected = {"fda", "nccn", "oncokb", "civic", "dgidb", "opencravat"}
        assert sources == expected


# ═══════════════════════════════════════════════════════════════════════════════
# JSON Schema Conformance (Schema Golden Tests)
# ═══════════════════════════════════════════════════════════════════════════════


class TestGoldenSchemaConformance:
    """Verify that pipeline outputs conform to JSON schemas."""

    @pytest.fixture(scope="class")
    def schemas(self):
        """Load all JSON schemas once per class."""
        schema_dir = Path(__file__).resolve().parent.parent / "src" / "backend" / "clinical" / "schemas"
        return {
            "recommendation_result": json.loads(
                (schema_dir / "recommendation_result.json").read_text(encoding="utf-8")
            ),
            "drug_score": json.loads(
                (schema_dir / "drug_score.json").read_text(encoding="utf-8")
            ),
            "evidence_score": json.loads(
                (schema_dir / "evidence_score.json").read_text(encoding="utf-8")
            ),
            "recommendation_reason": json.loads(
                (schema_dir / "recommendation_reason.json").read_text(encoding="utf-8")
            ),
        }

    @pytest.fixture(scope="class")
    def schema_store(self):
        """Build a schema store for $ref resolution."""
        from referencing import Registry, Resource
        schema_dir = Path(__file__).resolve().parent.parent / "src" / "backend" / "clinical" / "schemas"
        files = ["recommendation_result.json", "drug_score.json", "evidence_score.json", "recommendation_reason.json"]
        resources: dict[str, Resource] = {}
        for fname in files:
            path = schema_dir / fname
            schema = json.loads(path.read_text(encoding="utf-8"))
            uri = schema.get("$id", fname)
            resources[uri] = Resource.from_contents(schema)
        return Registry().with_resources(resources.items())

    def test_golden_schema_loading(self, schemas):
        """All schemas should load as valid dicts."""
        for name, schema in schemas.items():
            assert isinstance(schema, dict), f"{name} schema is not a dict"
            assert "$schema" in schema, f"{name} missing $schema"
            assert "type" in schema, f"{name} missing type"
            assert schema["type"] == "object", f"{name} type should be object"

    def test_golden_output_conforms_to_result_schema(
        self, golden_evidence_bundle_multidrug, schemas, schema_store
    ):
        """Pipeline output should conform to recommendation_result schema."""
        from jsonschema.validators import validator_for

        aggregator = EvidenceAggregator()
        aggregated = aggregator.aggregate(golden_evidence_bundle_multidrug)

        engine = DrugRankingEngine()
        results = engine.rank(aggregated)

        # Build a minimal RecommendationResult-like dict
        output = {
            "patient_id": "GOLDEN-001",
            "recommendations": [
                {
                    "drug_name": r.drug_name,
                    "overall_score": r.overall_score.raw_score,
                    "evidence_score": {
                        "total_weighted_score": r.evidence_score.total_weighted_score,
                        "source_diversity": r.evidence_score.source_diversity,
                        "highest_tier": r.evidence_score.highest_tier,
                        "confidence_score": r.evidence_score.confidence_score,
                    },
                    "sensitivity": r.sensitivity.score,
                    "resistance": r.resistance.score,
                    "conflict_score": r.conflict_score.score,
                    "rank": r.rank,
                    "details": r.details,
                }
                for r in results
            ],
            "trace_id": "golden-trace-001",
            "engine_version": "1.0.0",
            "created_at": "2025-06-18T14:30:00Z",
        }

        # Validate against schema with store for $ref resolution
        cls = validator_for(schemas["recommendation_result"])
        validator = cls(schemas["recommendation_result"], registry=schema_store)
        validator.validate(output)

    def test_golden_drug_score_conforms(self, golden_evidence_bundle_multidrug, schemas, schema_store):
        """Individual DrugScore should conform to drug_score schema."""
        from jsonschema.validators import validator_for

        aggregator = EvidenceAggregator()
        aggregated = aggregator.aggregate(golden_evidence_bundle_multidrug)

        engine = DrugRankingEngine()
        results = engine.rank(aggregated)

        schema = schemas["drug_score"]
        cls = validator_for(schema)
        validator = cls(schema, registry=schema_store)

        for r in results:
            drug_score = {
                "drug_name": r.drug_name,
                "overall_score": r.overall_score.raw_score,
                "evidence_score": {
                    "total_weighted_score": r.evidence_score.total_weighted_score,
                    "source_diversity": r.evidence_score.source_diversity,
                    "highest_tier": r.evidence_score.highest_tier,
                    "confidence_score": r.evidence_score.confidence_score,
                },
                "sensitivity": r.sensitivity.score,
                "resistance": r.resistance.score,
                "conflict_score": r.conflict_score.score,
                "rank": r.rank,
                "details": r.details,
            }
            validator.validate(drug_score)
