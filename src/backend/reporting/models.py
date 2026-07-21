"""
Pydantic models for clinical reports.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ReportMetadata(BaseModel):
    """Metadata for a clinical report."""
    report_id: str = ""
    case_id: Optional[str] = None
    version: str = "1.0.0"
    supersedes_report_id: Optional[str] = None
    status: str = "draft"  # draft, validated, final, withdrawn
    generated_at: str = ""
    git_commit: str = ""


class ReportSection(BaseModel):
    """A section of a clinical report."""
    title: str = ""
    content: str = ""
    evidence_ids: list[str] = []
    publications: list[str] = []


class ClinicalReport(BaseModel):
    """Complete clinical report."""
    model_config = ConfigDict(from_attributes=True)

    metadata: ReportMetadata = ReportMetadata()
    case_metadata: dict = {}
    sample_metadata: dict = {}
    sequencing_info: dict = {}
    variants: list[dict] = []
    evidence_summary: list[dict] = []
    drug_ranking: list[dict] = []
    resistance: list[dict] = []
    conflicts: list[dict] = []
    clinical_reasoning: Optional[dict] = None
    limitations: list[str] = []
    source_versions: dict = {}
    citations: list[dict] = []


class ReportCreateResponse(BaseModel):
    """Response when creating a report."""
    report_id: str = ""
    version: str = ""
    status: str = ""
    message: str = ""


class ReportListResponse(BaseModel):
    """List of reports."""
    reports: list[dict] = []
    total: int = 0
