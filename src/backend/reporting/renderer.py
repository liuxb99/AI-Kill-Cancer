"""
ReportRenderer — renders clinical reports to HTML, JSON, and FHIR.
"""

from __future__ import annotations

from src.backend.reporting.models import ClinicalReport
from src.backend.reporting.templates import ReportTemplateRegistry


class ReportRenderer:
    """Renders clinical reports to various formats."""

    def __init__(self):
        self.templates = ReportTemplateRegistry()

    def render_html(self, report: ClinicalReport) -> str:
        """Render report as HTML."""
        return self.templates.render_html(report)

    def render_json(self, report: ClinicalReport) -> dict:
        """Render report as JSON dict."""
        return report.model_dump()


class PDFRenderer:
    """Renders clinical reports as PDF using WeasyPrint or Playwright."""

    def __init__(self):
        self.templates = ReportTemplateRegistry()
        self._engine = None
        self._engine_name = ""

    @property
    def available(self) -> bool:
        """Check if a PDF rendering engine is available."""
        if self._engine:
            return True
        try:
            import weasyprint  # noqa: F401
            self._engine_name = "weasyprint"
            return True
        except ImportError:
            pass
        try:
            import playwright  # noqa: F401
            self._engine_name = "playwright"
            return True
        except ImportError:
            pass
        return False

    def render_pdf(self, report: ClinicalReport) -> bytes:
        """Render report as PDF bytes."""
        html = self.templates.render_html(report)

        try:
            from weasyprint import HTML
            pdf_bytes = HTML(string=html).write_pdf()
            self._engine_name = "weasyprint"
            return pdf_bytes
        except ImportError:
            pass

        raise RuntimeError(
            "No PDF rendering engine available. "
            "Install weasyprint (pip install weasyprint) "
            "or playwright (pip install playwright && playwright install chromium). "
            "On Windows: pip install weasyprint may need GTK3. "
            "See https://doc.courtbouillon.org/weasyprint/stable/first_steps.html"
        )


class FHIRExporter:
    """Exports clinical reports in FHIR R4 format."""

    def export(self, report: ClinicalReport) -> dict:
        """
        Export report as FHIR-compatible bundle.
        This is a simplified FHIR representation.
        """
        bundle = {
            "resourceType": "Bundle",
            "type": "document",
            "timestamp": report.metadata.generated_at,
            "identifier": {"value": report.metadata.report_id},
            "entry": [
                {
                    "resource": {
                        "resourceType": "Composition",
                        "status": report.metadata.status,
                        "type": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "11502-2",
                                "display": "Laboratory report",
                            }]
                        },
                        "subject": {"display": f"Case {report.metadata.case_id}" if report.metadata.case_id else "Unknown"},
                        "date": report.metadata.generated_at,
                        "title": f"Clinical Genomics Report {report.metadata.report_id[:8]}",
                        "section": [],
                    }
                }
            ]
        }

        # Add variant section
        if report.variants:
            variant_text = "; ".join(
                f"{v.get('gene', '')} {v.get('hgvs', '')}" for v in report.variants
            )
            bundle["entry"][0]["resource"]["section"].append({
                "title": "Variants",
                "text": {"status": "generated", "div": f"<div>{variant_text}</div>"},
            })

        # Add evidence section
        if report.evidence_summary:
            bundle["entry"][0]["resource"]["section"].append({
                "title": "Evidence Summary",
                "text": {"status": "generated", "div": f"<div>{len(report.evidence_summary)} evidence items</div>"},
            })

        # Add drug ranking section
        if report.drug_ranking:
            ranking_text = "; ".join(
                f"#{d.get('rank', '')} {d.get('drug_name', '')}" for d in report.drug_ranking[:5]
            )
            bundle["entry"][0]["resource"]["section"].append({
                "title": "Drug Rankings",
                "text": {"status": "generated", "div": f"<div>{ranking_text}</div>"},
            })

        return bundle
