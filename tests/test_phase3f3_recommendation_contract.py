"""Phase 3F-3 recommendation architecture and report contract tests."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from src.backend.clinical.report_generator import ReportGenerator
from src.backend.contracts.recommendation_report import (
    RecommendationReport,
    RecommendationReportView,
)


ROOT = Path(__file__).resolve().parents[1]


def _payload() -> dict:
    return {
        "recommendation_id": "rec-001",
        "patient_id": "patient-001",
        "recommendations": [
            {
                "drug_name": "Lenvatinib",
                "rank": 1,
                "overall_score": 0.87,
                "evidence_score": 0.9,
                "sensitivity_score": 0.8,
                "resistance_score": 0.1,
                "conflict_score": 0.05,
                "explanations": [
                    {
                        "category": "guideline",
                        "detail": "Preferred systemic option",
                        "source": "NCCN",
                        "score_impact": 0.25,
                    }
                ],
            }
        ],
        "trace_id": "trace-001",
        "engine_version": "1.0.0",
        "report_html": None,
        "created_at": "2026-08-02T05:00:00+00:00",
    }


def test_contract_builds_immutable_framework_independent_report():
    report = RecommendationReport.from_mapping(_payload())

    assert isinstance(report, RecommendationReportView)
    assert report.recommendations[0].drug_name == "Lenvatinib"
    assert report.recommendations[0].explanations[0]["source"] == "NCCN"

    with pytest.raises(AttributeError):
        report.patient_id = "other"  # type: ignore[misc]


def test_report_generator_accepts_contract_and_renders_html():
    report = RecommendationReport.from_mapping(_payload())

    html = ReportGenerator().generate(
        report,
        variants=["BRAF V600E"],
        evidence_count=3,
        rules_evaluated=4,
        rules_fired=2,
    )

    assert "<!DOCTYPE html>" in html
    assert "Lenvatinib" in html
    assert "patient-001" in html
    assert "BRAF V600E" in html
    assert "trace-001" in html


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("recommendation_id", "   ", ValueError),
        ("recommendations", "not-a-list", TypeError),
        ("report_html", 123, TypeError),
    ],
)
def test_contract_rejects_invalid_transport_payload(field, value, error):
    payload = _payload()
    payload[field] = value
    with pytest.raises(error):
        RecommendationReport.from_mapping(payload)


def test_service_layer_has_no_api_imports():
    services_dir = ROOT / "src/backend/services"
    violations: list[str] = []

    for path in services_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("src.backend.api"):
                    violations.append(f"{path.name}:{node.lineno}:{node.module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("src.backend.api"):
                        violations.append(f"{path.name}:{node.lineno}:{alias.name}")

    assert violations == [], "Service-to-API reverse dependencies: " + ", ".join(violations)


def test_clinical_report_generator_has_no_api_imports():
    path = ROOT / "src/backend/clinical/report_generator.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports = [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    ]
    assert not any(module.startswith("src.backend.api") for module in imports)
