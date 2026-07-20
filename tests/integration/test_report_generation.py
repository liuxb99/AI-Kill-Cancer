
"""
Integration test for report generation flow.
Tests: builder → validator → HTML → JSON → FHIR.
"""
import pytest
from src.backend.reporting.builder import ReportBuilder
from src.backend.reporting.validator import ReportValidator
from src.backend.reporting.renderer import ReportRenderer, FHIRExporter

class TestReportGenerationFlow:
    def test_report_with_all_data(self):
        builder = ReportBuilder()
        report = builder.build(
            case_metadata={"case_id": "case-1"},
            variants=[{"gene": "BRAF", "hgvs": "c.1799T>A"}],
            evidence_summary=[{"id": "ev-1", "drug_name": "Vemurafenib", "pmid": "12345678"}],
            drug_ranking=[{"rank": 1, "drug_name": "Vemurafenib", "total_score": 7.5}],
            limitations=["Test limitation"],
        )
        assert report.metadata.report_id is not None
        assert len(report.variants) == 1
        assert len(report.citations) == 1

    def test_report_validator_with_citations(self):
        builder = ReportBuilder()
        validator = ReportValidator()
        report = builder.build(
            variants=[{"gene": "BRAF"}],
            evidence_summary=[{"drug_name": "V", "pmid": "12345678"}],
            drug_ranking=[{"rank": 1, "drug_name": "V"}],
        )
        # Report needs citations from evidence with PMIDs
        assert len(report.citations) > 0
        # Should be valid now
        assert validator.is_valid(report)

    def test_html_contains_data(self):
        builder = ReportBuilder()
        renderer = ReportRenderer()
        report = builder.build(variants=[{"gene": "BRAF"}])
        html = renderer.render_html(report)
        assert "BRAF" in html
        assert "<html>" in html

    def test_fhir_export(self):
        exporter = FHIRExporter()
        builder = ReportBuilder()
        report = builder.build(variants=[{"gene": "BRAF"}])
        bundle = exporter.export(report)
        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "document"

