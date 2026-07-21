"""
Tests for Clinical Report System (v0.8.0).
"""

from __future__ import annotations


from src.backend.reporting.models import (
    ClinicalReport, ReportMetadata, ReportSection,
    ReportCreateResponse,
)
from src.backend.reporting.builder import ReportBuilder
from src.backend.reporting.validator import ReportValidator
from src.backend.reporting.renderer import ReportRenderer, FHIRExporter
from src.backend.reporting.templates import ReportTemplateRegistry


class TestReportModels:
    def test_report_metadata(self):
        m = ReportMetadata(report_id="r1", status="draft")
        assert m.report_id == "r1"
        assert m.status == "draft"
        assert m.version == "1.0.0"

    def test_report_section(self):
        s = ReportSection(title="Variants", content="Test", evidence_ids=["ev-1"])
        assert s.title == "Variants"
        assert len(s.evidence_ids) == 1

    def test_clinical_report(self):
        report = ClinicalReport(
            metadata=ReportMetadata(report_id="r1"),
            variants=[{"gene": "BRAF", "hgvs": "c.1799T>A"}],
            evidence_summary=[{"drug_name": "Vemurafenib", "evidence_direction": "Supports"}],
        )
        assert report.metadata.report_id == "r1"
        assert len(report.variants) == 1

    def test_report_create_response(self):
        resp = ReportCreateResponse(report_id="r1", status="draft")
        assert resp.report_id == "r1"


class TestReportBuilder:
    def test_build_minimal(self):
        builder = ReportBuilder()
        report = builder.build()
        assert report.metadata.report_id is not None
        assert report.metadata.status == "draft"
        assert len(report.variants) == 0

    def test_build_with_data(self):
        builder = ReportBuilder()
        report = builder.build(
            case_metadata={"case_id": "case-1", "patient": "P001"},
            variants=[{"gene": "BRAF", "hgvs": "c.1799T>A"}],
            evidence_summary=[{"id": "ev-1", "drug_name": "Vemurafenib", "pmid": "12345678"}],
            drug_ranking=[{"rank": 1, "drug_name": "Vemurafenib", "total_score": 7.5}],
            git_commit="abc123",
        )
        assert report.metadata.case_id == "case-1"
        assert len(report.variants) == 1
        assert len(report.evidence_summary) == 1
        assert len(report.drug_ranking) == 1
        assert len(report.citations) == 1
        assert report.metadata.git_commit == "abc123"

    def test_build_citations_from_evidence(self):
        builder = ReportBuilder()
        report = builder.build(
            evidence_summary=[
                {"id": "ev-1", "drug_name": "D1", "pmid": "111", "citation": "Author et al 2024"},
                {"id": "ev-2", "drug_name": "D2"},  # No PMID
            ],
        )
        assert len(report.citations) == 1
        assert report.citations[0]["pmid"] == "111"

    def test_build_with_limitations(self):
        builder = ReportBuilder()
        report = builder.build(
            limitations=["Small sample size", "Retrospective study"],
        )
        assert len(report.limitations) == 2


class TestReportValidator:
    def test_valid_report(self):
        validator = ReportValidator()
        report = ClinicalReport(
            metadata=ReportMetadata(report_id="r1", generated_at="2024-01-01"),
            variants=[{"gene": "BRAF"}],
            evidence_summary=[{"drug_name": "V"}],
            drug_ranking=[{"rank": 1, "drug_name": "V"}],
            citations=[{"pmid": "12345678"}],
        )
        assert validator.is_valid(report)

    def test_invalid_report(self):
        validator = ReportValidator()
        report = ClinicalReport()
        issues = validator.validate(report)
        assert len(issues) > 0


class TestReportRenderer:
    def test_render_html(self):
        renderer = ReportRenderer()
        report = ClinicalReport(
            metadata=ReportMetadata(report_id="r1", generated_at="2024-01-01"),
            variants=[{"gene": "BRAF", "hgvs": "c.1799T>A"}],
        )
        html = renderer.render_html(report)
        assert "<html>" in html
        assert "BRAF" in html
        assert "Clinical Genomics Report" in html

    def test_render_json(self):
        renderer = ReportRenderer()
        report = ClinicalReport(
            metadata=ReportMetadata(report_id="r1"),
            variants=[{"gene": "BRAF"}],
        )
        data = renderer.render_json(report)
        assert data["metadata"]["report_id"] == "r1"
        assert len(data["variants"]) == 1


class TestFHIRExporter:
    def test_export_fhir_bundle(self):
        exporter = FHIRExporter()
        report = ClinicalReport(
            metadata=ReportMetadata(report_id="r1", generated_at="2024-01-01T00:00:00Z"),
            variants=[{"gene": "BRAF", "hgvs": "c.1799T>A"}],
            evidence_summary=[{"drug_name": "Vemurafenib"}],
            drug_ranking=[{"rank": 1, "drug_name": "Vemurafenib", "total_score": 7.5}],
        )
        bundle = exporter.export(report)
        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "document"
        assert len(bundle["entry"]) == 1
        assert bundle["entry"][0]["resource"]["resourceType"] == "Composition"
        sections = bundle["entry"][0]["resource"]["section"]
        assert len(sections) >= 2

    def test_export_empty_report(self):
        exporter = FHIRExporter()
        report = ClinicalReport(metadata=ReportMetadata(report_id="r1"))
        bundle = exporter.export(report)
        assert bundle["resourceType"] == "Bundle"
        assert len(bundle["entry"][0]["resource"]["section"]) == 0


class TestReportTemplateRegistry:
    def test_default_template(self):
        registry = ReportTemplateRegistry()
        template = registry.get_template()
        assert "Clinical Genomics Report" in template

    def test_render_with_template(self):
        registry = ReportTemplateRegistry()
        report = ClinicalReport(
            metadata=ReportMetadata(report_id="r1", generated_at="2024-01-01"),
            variants=[{"gene": "BRAF"}],
        )
        html = registry.render_html(report)
        assert "r1" in html
        assert "BRAF" in html
        assert "research" in html.lower()
