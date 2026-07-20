"""
ReportBuilder — assembles clinical reports from evidence, ranking, and reasoning snapshots.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from src.backend.reporting.models import ClinicalReport, ReportMetadata


class ReportBuilder:
    """
    Assembles a clinical report from evidence, ranking, and reasoning data.
    """

    def build(self, case_metadata: Optional[dict] = None,
              sample_metadata: Optional[dict] = None,
              sequencing_info: Optional[dict] = None,
              variants: Optional[list[dict]] = None,
              evidence_summary: Optional[list[dict]] = None,
              drug_ranking: Optional[list[dict]] = None,
              resistance: Optional[list[dict]] = None,
              conflicts: Optional[list[dict]] = None,
              clinical_reasoning: Optional[dict] = None,
              limitations: Optional[list[str]] = None,
              source_versions: Optional[dict] = None,
              git_commit: str = "") -> ClinicalReport:
        """Build a clinical report from provided data."""
        report_id = str(uuid.uuid4())

        metadata = ReportMetadata(
            report_id=report_id,
            case_id=case_metadata.get("case_id", "") if case_metadata else None,
            version="1.0.0",
            status="draft",
            generated_at=datetime.now(timezone.utc).isoformat(),
            git_commit=git_commit,
        )

        citations = []
        for ev in (evidence_summary or []):
            if ev.get("pmid") or ev.get("citation"):
                citations.append({
                    "evidence_id": str(ev.get("id", "")),
                    "pmid": str(ev.get("pmid", "")),
                    "citation": str(ev.get("citation", "")),
                })

        return ClinicalReport(
            metadata=metadata,
            case_metadata=case_metadata or {},
            sample_metadata=sample_metadata or {},
            sequencing_info=sequencing_info or {},
            variants=variants or [],
            evidence_summary=evidence_summary or [],
            drug_ranking=drug_ranking or [],
            resistance=resistance or [],
            conflicts=conflicts or [],
            clinical_reasoning=clinical_reasoning,
            limitations=limitations or [],
            source_versions=source_versions or {},
            citations=citations,
        )
