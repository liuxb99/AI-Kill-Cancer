"""
ReportValidator — validates clinical report completeness and integrity.
"""

from __future__ import annotations

from src.backend.reporting.models import ClinicalReport


class ReportValidator:
    """Validates clinical reports for completeness."""

    def validate(self, report: ClinicalReport) -> list[str]:
        """Validate a report, returning a list of issues found."""
        issues = []

        if not report.metadata.report_id:
            issues.append("Missing report ID")

        if not report.metadata.generated_at:
            issues.append("Missing generation timestamp")

        if not report.variants:
            issues.append("No variants in report")

        if not report.evidence_summary:
            issues.append("No evidence in report")

        if not report.drug_ranking:
            issues.append("No drug ranking in report")

        if not report.citations:
            issues.append("No citations in report")

        return issues

    def is_valid(self, report: ClinicalReport) -> bool:
        return len(self.validate(report)) == 0
