"""Framework-independent recommendation report contract.

This module intentionally has no FastAPI or Pydantic dependency.  Service and
clinical layers use these immutable records while the API layer remains free to
map them into transport-specific response models.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable


@runtime_checkable
class RecommendationDrugView(Protocol):
    drug_name: str
    rank: int
    overall_score: float
    evidence_score: float
    sensitivity_score: float
    resistance_score: float
    conflict_score: float
    explanations: Sequence[Mapping[str, Any]]


@runtime_checkable
class RecommendationReportView(Protocol):
    recommendation_id: str
    patient_id: str
    recommendations: Sequence[RecommendationDrugView]
    trace_id: str
    engine_version: str
    report_html: str | None
    created_at: str


@dataclass(frozen=True, slots=True)
class RecommendationDrugRecord:
    drug_name: str
    rank: int
    overall_score: float
    evidence_score: float
    sensitivity_score: float
    resistance_score: float
    conflict_score: float
    explanations: tuple[dict[str, Any], ...] = ()

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RecommendationDrugRecord":
        return cls(
            drug_name=_require_text(value, "drug_name"),
            rank=_require_positive_int(value, "rank"),
            overall_score=_require_number(value, "overall_score"),
            evidence_score=_require_unit_score(value, "evidence_score"),
            sensitivity_score=_require_unit_score(value, "sensitivity_score"),
            resistance_score=_require_unit_score(value, "resistance_score"),
            conflict_score=_require_unit_score(value, "conflict_score"),
            explanations=tuple(_normalise_explanations(value.get("explanations", ()))),
        )


@dataclass(frozen=True, slots=True)
class RecommendationReport:
    recommendation_id: str
    patient_id: str
    recommendations: tuple[RecommendationDrugRecord, ...]
    trace_id: str
    engine_version: str
    report_html: str | None
    created_at: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RecommendationReport":
        raw_recommendations = value.get("recommendations")
        if not isinstance(raw_recommendations, (list, tuple)):
            raise TypeError("recommendations must be a list or tuple")
        report_html = value.get("report_html")
        if report_html is not None and not isinstance(report_html, str):
            raise TypeError("report_html must be a string or None")
        return cls(
            recommendation_id=_require_text(value, "recommendation_id"),
            patient_id=_require_text(value, "patient_id"),
            recommendations=tuple(
                RecommendationDrugRecord.from_mapping(item)
                for item in raw_recommendations
                if isinstance(item, Mapping)
            ),
            trace_id=_require_text(value, "trace_id"),
            engine_version=_require_text(value, "engine_version"),
            report_html=report_html,
            created_at=_require_text(value, "created_at"),
        )


def _require_text(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return item.strip()


def _require_positive_int(value: Mapping[str, Any], key: str) -> int:
    item = value.get(key)
    if isinstance(item, bool) or not isinstance(item, int) or item < 1:
        raise ValueError(f"{key} must be a positive integer")
    return item


def _require_number(value: Mapping[str, Any], key: str) -> float:
    item = value.get(key)
    if isinstance(item, bool) or not isinstance(item, (int, float)):
        raise TypeError(f"{key} must be numeric")
    return float(item)


def _require_unit_score(value: Mapping[str, Any], key: str) -> float:
    score = _require_number(value, key)
    if not 0.0 <= score <= 1.0:
        raise ValueError(f"{key} must be between 0 and 1")
    return score


def _normalise_explanations(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise TypeError("explanations must be a list or tuple")
    result: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise TypeError("each explanation must be a mapping")
        result.append(dict(item))
    return result


__all__ = [
    "RecommendationDrugRecord",
    "RecommendationDrugView",
    "RecommendationReport",
    "RecommendationReportView",
]
