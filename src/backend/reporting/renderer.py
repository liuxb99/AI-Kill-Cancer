"""
ReportRenderer — renders clinical reports to HTML, JSON, and FHIR.
"""

from __future__ import annotations

import json
from typing import Optional

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
