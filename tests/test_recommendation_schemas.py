"""
Schema validation tests for clinical recommendation JSON Schemas (P3A-10).

Covers:
- Loading all JSON Schema files
- Validating that each schema is valid JSON Schema
- Creating test data that conforms to each schema
- Creating test data that violates each schema (to verify rejection)
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
from jsonschema.validators import validator_for
import pytest
from referencing import Registry, Resource

from src.backend.clinical.schemas import (
    get_drug_score_schema,
    get_evidence_score_schema,
    get_recommendation_reason_schema,
    get_recommendation_result_schema,
)

# Path to the schemas directory
SCHEMA_DIR = Path(__file__).resolve().parent.parent / "src" / "backend" / "clinical" / "schemas"


def _build_schema_store() -> Registry:
    """Build a referencing.Registry containing all local schemas.

    This allows ``$ref`` references between schemas (e.g.
    drug_score.json → evidence_score.json) to resolve correctly
    without network access.
    """
    resources: dict[str, Resource] = {}
    for fname in SCHEMA_FILES:
        path = SCHEMA_DIR / fname
        with path.open(encoding="utf-8") as f:
            schema = json.load(f)
        uri = schema.get("$id", fname)
        resources[uri] = Resource.from_contents(schema)
    return Registry().with_resources(resources.items())


@pytest.fixture(scope="session")
def schema_store() -> Registry:
    """Provide a configured schema store for all tests."""
    return _build_schema_store()


@pytest.fixture
def validate_with_store(schema_store: Registry):
    """Return a function that validates data against a schema using the store."""
    def _validate(instance: dict, schema: dict) -> None:
        cls = validator_for(schema)
        validator = cls(schema, registry=schema_store)
        validator.validate(instance)
    return _validate

# List of all schema files to test
SCHEMA_FILES = [
    "recommendation_result.json",
    "drug_score.json",
    "evidence_score.json",
    "recommendation_reason.json",
]


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def schema_dicts() -> dict[str, dict]:
    """Load all JSON Schema files as dicts."""
    schemas = {}
    for fname in SCHEMA_FILES:
        path = SCHEMA_DIR / fname
        with path.open(encoding="utf-8") as f:
            schemas[fname] = json.load(f)
    return schemas


@pytest.fixture
def result_schema() -> dict:
    """Return the recommendation_result schema."""
    return get_recommendation_result_schema()


@pytest.fixture
def drug_score_schema() -> dict:
    """Return the drug_score schema."""
    return get_drug_score_schema()


@pytest.fixture
def evidence_score_schema() -> dict:
    """Return the evidence_score schema."""
    return get_evidence_score_schema()


@pytest.fixture
def reason_schema() -> dict:
    """Return the recommendation_reason schema."""
    return get_recommendation_reason_schema()


# ═══════════════════════════════════════════════════════════════════════════════
# Schema Loading Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestSchemaLoading:
    """Test that all schema files load correctly."""

    def test_all_schema_files_exist(self):
        """All schema files should exist in the schemas directory."""
        for fname in SCHEMA_FILES:
            path = SCHEMA_DIR / fname
            assert path.exists(), f"Schema file {fname} not found at {path}"
            assert path.is_file(), f"Schema file {fname} is not a file"

    def test_all_schemas_are_valid_json(self):
        """All schema files should be parseable as JSON."""
        for fname in SCHEMA_FILES:
            path = SCHEMA_DIR / fname
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data, dict), f"{fname} is not a dict"

    def test_schema_has_required_meta_fields(self, schema_dicts):
        """Each schema should have $schema, $id, title, type fields."""
        for fname, schema in schema_dicts.items():
            assert "$schema" in schema, f"{fname} missing $schema"
            assert "title" in schema, f"{fname} missing title"
            assert "type" in schema, f"{fname} missing type"
            assert schema["type"] == "object", f"{fname} type should be object"

    def test_schema_via_getter(self):
        """Each get_*_schema() function should return a valid dict."""
        assert isinstance(get_recommendation_result_schema(), dict)
        assert isinstance(get_drug_score_schema(), dict)
        assert isinstance(get_evidence_score_schema(), dict)
        assert isinstance(get_recommendation_reason_schema(), dict)


# ═══════════════════════════════════════════════════════════════════════════════
# Schema Self-Validation Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestSchemaSelfValidation:
    """Test that each schema is itself valid JSON Schema (Draft 2020-12)."""

    def test_recommendation_result_schema_is_valid(self, result_schema):
        """The recommendation_result schema should self-validate."""
        jsonschema.Draft202012Validator.check_schema(result_schema)

    def test_drug_score_schema_is_valid(self, drug_score_schema):
        """The drug_score schema should self-validate."""
        jsonschema.Draft202012Validator.check_schema(drug_score_schema)

    def test_evidence_score_schema_is_valid(self, evidence_score_schema):
        """The evidence_score schema should self-validate."""
        jsonschema.Draft202012Validator.check_schema(evidence_score_schema)

    def test_recommendation_reason_schema_is_valid(self, reason_schema):
        """The recommendation_reason schema should self-validate."""
        jsonschema.Draft202012Validator.check_schema(reason_schema)


# ═══════════════════════════════════════════════════════════════════════════════
# Schema Conformance Tests (valid data)
# ═══════════════════════════════════════════════════════════════════════════════


class TestRecommendationResultSchema:
    """Test data conformance to recommendation_result schema."""

    def test_valid_minimal(self, result_schema, validate_with_store):
        """Minimal valid data should pass validation."""
        data = {
            "patient_id": "P-001",
            "recommendations": [],
            "engine_version": "1.0.0",
            "created_at": "2025-06-18T14:30:00Z",
        }
        validate_with_store(data, result_schema)

    def test_valid_with_drugs(self, result_schema, validate_with_store):
        """Data with drug recommendations should pass."""
        data = {
            "patient_id": "P-001",
            "recommendations": [
                {
                    "drug_name": "Osimertinib",
                    "overall_score": 0.7834,
                    "evidence_score": {
                        "total_weighted_score": 8.25,
                        "source_diversity": 0.75,
                        "highest_tier": "Tier_0",
                        "confidence_score": 0.82,
                    },
                    "sensitivity": 0.85,
                    "resistance": 0.12,
                    "conflict_score": 0.05,
                    "rank": 1,
                    "details": {
                        "item_count": 12,
                        "source_count": 4,
                        "highest_weight": 3.5,
                        "sources": ["COSMIC", "CIViC", "OncoKB", "ClinicalTrials.gov"],
                    },
                },
            ],
            "trace_id": "a1b2c3d4e5f67890abcdef1234567890",
            "engine_version": "1.0.0",
            "created_at": "2025-06-18T14:30:00Z",
        }
        validate_with_store(data, result_schema)

    def test_invalid_missing_patient_id(self, result_schema, validate_with_store):
        """Missing required patient_id should fail."""
        data = {
            "recommendations": [],
            "engine_version": "1.0.0",
            "created_at": "2025-06-18T14:30:00Z",
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_with_store(data, result_schema)

    def test_invalid_missing_engine_version(self, result_schema, validate_with_store):
        """Missing required engine_version should fail."""
        data = {
            "patient_id": "P-001",
            "recommendations": [],
            "created_at": "2025-06-18T14:30:00Z",
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_with_store(data, result_schema)

    def test_invalid_extra_property(self, result_schema, validate_with_store):
        """Additional properties should be rejected."""
        data = {
            "patient_id": "P-001",
            "recommendations": [],
            "engine_version": "1.0.0",
            "created_at": "2025-06-18T14:30:00Z",
            "extra_field": "should_not_exist",
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_with_store(data, result_schema)


class TestDrugScoreSchema:
    """Test data conformance to drug_score schema."""

    def test_valid_minimal(self, drug_score_schema, validate_with_store):
        """Minimal valid drug score data should pass."""
        data = {
            "drug_name": "Osimertinib",
            "overall_score": 0.75,
            "evidence_score": {
                "total_weighted_score": 5.0,
                "source_diversity": 0.5,
                "highest_tier": "Tier_0",
                "confidence_score": 0.6,
            },
            "sensitivity": 0.8,
            "resistance": 0.1,
            "conflict_score": 0.05,
            "rank": 1,
        }
        validate_with_store(data, drug_score_schema)

    def test_valid_with_details(self, drug_score_schema, validate_with_store):
        """Drug score with details should pass."""
        data = {
            "drug_name": "Pembrolizumab",
            "overall_score": 0.521,
            "evidence_score": {
                "total_weighted_score": 4.5,
                "source_diversity": 0.5,
                "highest_tier": "Tier_1",
                "confidence_score": 0.55,
            },
            "sensitivity": 0.6,
            "resistance": 0.3,
            "conflict_score": 0.15,
            "rank": 2,
            "details": {
                "item_count": 6,
                "source_count": 3,
                "highest_weight": 2.0,
                "sources": ["CIViC", "OncoKB", "PubMed"],
            },
        }
        validate_with_store(data, drug_score_schema)

    def test_invalid_missing_drug_name(self, drug_score_schema, validate_with_store):
        """Missing required drug_name should fail."""
        data = {
            "overall_score": 0.75,
            "evidence_score": {
                "total_weighted_score": 5.0,
                "source_diversity": 0.5,
                "highest_tier": "Tier_0",
                "confidence_score": 0.6,
            },
            "sensitivity": 0.8,
            "resistance": 0.1,
            "conflict_score": 0.05,
            "rank": 1,
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_with_store(data, drug_score_schema)

    def test_invalid_missing_evidence_score(self, drug_score_schema, validate_with_store):
        """Missing required evidence_score should fail."""
        data = {
            "drug_name": "TestDrug",
            "overall_score": 0.75,
            "sensitivity": 0.8,
            "resistance": 0.1,
            "conflict_score": 0.05,
            "rank": 1,
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_with_store(data, drug_score_schema)

    def test_invalid_overall_score_type(self, drug_score_schema, validate_with_store):
        """overall_score must be a number."""
        data = {
            "drug_name": "TestDrug",
            "overall_score": "high",
            "evidence_score": {
                "total_weighted_score": 5.0,
                "source_diversity": 0.5,
                "highest_tier": "Tier_0",
                "confidence_score": 0.6,
            },
            "sensitivity": 0.8,
            "resistance": 0.1,
            "conflict_score": 0.05,
            "rank": 1,
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_with_store(data, drug_score_schema)

    def test_invalid_sensitivity_out_of_range(self, drug_score_schema, validate_with_store):
        """sensitivity must be in [0, 1]."""
        data = {
            "drug_name": "TestDrug",
            "overall_score": 0.75,
            "evidence_score": {
                "total_weighted_score": 5.0,
                "source_diversity": 0.5,
                "highest_tier": "Tier_0",
                "confidence_score": 0.6,
            },
            "sensitivity": 1.5,
            "resistance": 0.1,
            "conflict_score": 0.05,
            "rank": 1,
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_with_store(data, drug_score_schema)

    def test_invalid_extra_property(self, drug_score_schema, validate_with_store):
        """Additional properties should be rejected."""
        data = {
            "drug_name": "TestDrug",
            "overall_score": 0.75,
            "evidence_score": {
                "total_weighted_score": 5.0,
                "source_diversity": 0.5,
                "highest_tier": "Tier_0",
                "confidence_score": 0.6,
            },
            "sensitivity": 0.8,
            "resistance": 0.1,
            "conflict_score": 0.05,
            "rank": 1,
            "extra": "bad",
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_with_store(data, drug_score_schema)


class TestEvidenceScoreSchema:
    """Test data conformance to evidence_score schema."""

    def test_valid_minimal(self, evidence_score_schema, validate_with_store):
        """Minimal valid evidence score should pass."""
        data = {
            "total_weighted_score": 8.25,
            "source_diversity": 0.75,
            "highest_tier": "Tier_0",
            "confidence_score": 0.82,
        }
        validate_with_store(data, evidence_score_schema)

    def test_valid_with_source_breakdown(self, evidence_score_schema, validate_with_store):
        """Evidence score with source_breakdown should pass."""
        data = {
            "total_weighted_score": 8.25,
            "source_diversity": 0.75,
            "highest_tier": "Tier_0",
            "confidence_score": 0.82,
            "source_breakdown": {
                "sources": {
                    "CIViC": {
                        "total_weight": 3.5,
                        "item_count": 4,
                        "highest_tier": "Tier_0",
                        "directions": ["supporting"],
                    },
                    "OncoKB": {
                        "total_weight": 2.5,
                        "item_count": 3,
                        "highest_tier": "Tier_1",
                        "directions": ["supporting", "neutral"],
                    },
                },
            },
        }
        validate_with_store(data, evidence_score_schema)

    def test_invalid_missing_total_weighted_score(self, evidence_score_schema, validate_with_store):
        """Missing required total_weighted_score should fail."""
        data = {
            "source_diversity": 0.75,
            "highest_tier": "Tier_0",
            "confidence_score": 0.82,
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_with_store(data, evidence_score_schema)

    def test_invalid_negative_total_weight(self, evidence_score_schema, validate_with_store):
        """Negative total_weighted_score should fail (minimum: 0)."""
        data = {
            "total_weighted_score": -1.0,
            "source_diversity": 0.75,
            "highest_tier": "Tier_0",
            "confidence_score": 0.82,
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_with_store(data, evidence_score_schema)

    def test_invalid_source_diversity_out_of_range(self, evidence_score_schema, validate_with_store):
        """source_diversity must be in [0, 1]."""
        data = {
            "total_weighted_score": 5.0,
            "source_diversity": 1.5,
            "highest_tier": "Tier_0",
            "confidence_score": 0.82,
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_with_store(data, evidence_score_schema)

    def test_invalid_extra_property(self, evidence_score_schema, validate_with_store):
        """Additional properties should be rejected."""
        data = {
            "total_weighted_score": 5.0,
            "source_diversity": 0.5,
            "highest_tier": "Tier_2",
            "confidence_score": 0.5,
            "bad_field": "xyz",
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_with_store(data, evidence_score_schema)


class TestRecommendationReasonSchema:
    """Test data conformance to recommendation_reason schema."""

    def test_valid_minimal(self, reason_schema, validate_with_store):
        """Minimal valid reason data should pass."""
        data = {
            "drug_name": "Osimertinib",
            "rank": 1,
            "overall_score": 0.7834,
            "reasons": [],
        }
        validate_with_store(data, reason_schema)

    def test_valid_with_reasons(self, reason_schema, validate_with_store):
        """Data with reason items should pass."""
        data = {
            "drug_name": "Osimertinib",
            "rank": 1,
            "overall_score": 0.7834,
            "reasons": [
                {
                    "category": "evidence_support",
                    "detail": "Evidence confidence score is 0.8200.",
                    "source": "EvidenceAggregator",
                    "score_impact": 0.328,
                },
                {
                    "category": "sensitivity",
                    "detail": "Sensitivity score 0.8500 — 8/12 items.",
                    "source": "DrugRankingEngine",
                    "score_impact": 0.2975,
                },
                {
                    "category": "rule",
                    "detail": "Ranked #1 — leads DrugX by 0.1234 points.",
                    "source": "DrugRanker",
                    "score_impact": 0.1234,
                },
            ],
        }
        validate_with_store(data, reason_schema)

    def test_valid_with_trace_id(self, reason_schema, validate_with_store):
        """Reason item with trace_id should pass."""
        data = {
            "drug_name": "Osimertinib",
            "rank": 1,
            "overall_score": 0.7834,
            "reasons": [
                {
                    "category": "evidence_support",
                    "detail": "Weight 1.0000 from nccn.",
                    "source": "nccn",
                    "score_impact": 0.4,
                    "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                },
            ],
        }
        validate_with_store(data, reason_schema)

    def test_invalid_missing_drug_name(self, reason_schema, validate_with_store):
        """Missing required drug_name should fail."""
        data = {
            "rank": 1,
            "overall_score": 0.7834,
            "reasons": [],
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_with_store(data, reason_schema)

    def test_invalid_missing_reasons(self, reason_schema, validate_with_store):
        """Missing required reasons should fail."""
        data = {
            "drug_name": "TestDrug",
            "rank": 1,
            "overall_score": 0.5,
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_with_store(data, reason_schema)

    def test_invalid_category_enum(self, reason_schema, validate_with_store):
        """category must be one of the allowed enum values."""
        data = {
            "drug_name": "TestDrug",
            "rank": 1,
            "overall_score": 0.5,
            "reasons": [
                {
                    "category": "invalid_category",
                    "detail": "Some detail.",
                    "source": "Src",
                    "score_impact": 0.1,
                },
            ],
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_with_store(data, reason_schema)

    def test_invalid_reason_missing_detail(self, reason_schema, validate_with_store):
        """Reason item missing required detail should fail."""
        data = {
            "drug_name": "TestDrug",
            "rank": 1,
            "overall_score": 0.5,
            "reasons": [
                {
                    "category": "evidence_support",
                    "source": "Src",
                    "score_impact": 0.1,
                },
            ],
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_with_store(data, reason_schema)

    def test_invalid_reason_missing_source(self, reason_schema, validate_with_store):
        """Reason item missing required source should fail."""
        data = {
            "drug_name": "TestDrug",
            "rank": 1,
            "overall_score": 0.5,
            "reasons": [
                {
                    "category": "evidence_support",
                    "detail": "Some detail.",
                    "score_impact": 0.1,
                },
            ],
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_with_store(data, reason_schema)

    def test_invalid_extra_property(self, reason_schema, validate_with_store):
        """Additional properties should be rejected."""
        data = {
            "drug_name": "TestDrug",
            "rank": 1,
            "overall_score": 0.5,
            "reasons": [],
            "extra": "bad",
        }
        with pytest.raises(jsonschema.ValidationError):
            validate_with_store(data, reason_schema)


# ═══════════════════════════════════════════════════════════════════════════════
# Cross-Schema Reference Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestCrossSchemaReferences:
    """Test that $ref references between schemas resolve correctly."""

    def test_drug_score_refs_evidence_score(self, drug_score_schema, evidence_score_schema):
        """drug_score schema references evidence_score via $ref."""
        # The evidence_score property in drug_score uses $ref
        assert "evidence_score" in drug_score_schema["properties"]
        ref = drug_score_schema["properties"]["evidence_score"]
        assert "$ref" in ref, "evidence_score should use $ref"

    def test_result_refs_drug_score(self, result_schema):
        """recommendation_result references drug_score via $ref."""
        assert "recommendations" in result_schema["properties"]
        items = result_schema["properties"]["recommendations"]
        assert "items" in items
        assert "$ref" in items["items"], "recommendations items should use $ref"

    def test_reason_schema_has_defs(self, reason_schema):
        """recommendation_reason should have $defs with ReasonItem."""
        assert "$defs" in reason_schema
        assert "ReasonItem" in reason_schema["$defs"]

    def test_reason_refs_reason_item(self, reason_schema):
        """reasons array should reference ReasonItem via $ref."""
        assert "reasons" in reason_schema["properties"]
        items = reason_schema["properties"]["reasons"]
        assert "items" in items
        assert "$ref" in items["items"], "reasons items should use $ref"
