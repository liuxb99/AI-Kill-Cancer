"""
Clinical Report System — traceable clinical study reports.

Generates HTML, JSON, and FHIR-formatted reports from evidence, ranking,
and reasoning snapshots. Reports are versioned and immutable.
"""

from src.backend.reporting.builder import ReportBuilder
from src.backend.reporting.renderer import FHIRExporter, PDFRenderer, ReportRenderer
from src.backend.reporting.repository import ClinicalReportModel, ReportRepository
from src.backend.reporting.templates import ReportTemplateRegistry
from src.backend.reporting.validator import ReportValidator

__all__ = [
    "ReportBuilder", "ReportTemplateRegistry", "ReportValidator",
    "ReportRepository", "ClinicalReportModel",
    "ReportRenderer", "FHIRExporter", "PDFRenderer",
]
