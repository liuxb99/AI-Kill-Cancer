"""
Schema getters for clinical recommendation JSON Schemas (Draft 2020-12).

Each ``get_*_schema()`` function loads and returns the corresponding JSON
Schema file as a Python dictionary, ready for validation with
``pydantic.TypeAdapter`` or ``jsonschema``.
"""

from __future__ import annotations

import json
from pathlib import Path

_SCHEMA_DIR = Path(__file__).resolve().parent


def _load_schema(name: str) -> dict:
    """Load a JSON Schema file from the schemas directory.

    Args:
        name: Schema file name (e.g. ``"recommendation_result.json"``).

    Returns:
        The parsed JSON Schema dictionary.
    """
    path = _SCHEMA_DIR / name
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def get_recommendation_result_schema() -> dict:
    """Return the ``RecommendationResult`` JSON Schema (Draft 2020-12).

    The schema describes the top-level recommendation pipeline output:
    ``patient_id``, ``recommendations`` (list of ``DrugScore``),
    ``trace_id``, ``engine_version``, and ``created_at``.

    Returns:
        JSON Schema dictionary.
    """
    return _load_schema("recommendation_result.json")


def get_drug_score_schema() -> dict:
    """Return the ``DrugScore`` JSON Schema (Draft 2020-12).

    The schema describes a single drug's scoring result: ``drug_name``,
    ``overall_score``, ``evidence_score`` (refs ``EvidenceScore``),
    ``sensitivity``, ``resistance``, ``conflict_score``, ``rank``, and
    ``details``.

    Returns:
        JSON Schema dictionary.
    """
    return _load_schema("drug_score.json")


def get_evidence_score_schema() -> dict:
    """Return the ``EvidenceScore`` JSON Schema (Draft 2020-12).

    The schema describes the evidence-derived score: ``total_weighted_score``,
    ``source_diversity``, ``highest_tier``, ``confidence_score``, and
    optional ``source_breakdown``.

    Returns:
        JSON Schema dictionary.
    """
    return _load_schema("evidence_score.json")


def get_recommendation_reason_schema() -> dict:
    """Return the ``RecommendationReason`` JSON Schema (Draft 2020-12).

    The schema describes a human-readable explanation for a drug's ranking:
    ``drug_name``, ``rank``, ``overall_score``, and ``reasons`` (list of
    ``ReasonItem`` with category, detail, source, score_impact, trace_id).

    Returns:
        JSON Schema dictionary.
    """
    return _load_schema("recommendation_reason.json")


__all__ = [
    "get_drug_score_schema",
    "get_evidence_score_schema",
    "get_recommendation_reason_schema",
    "get_recommendation_result_schema",
]
