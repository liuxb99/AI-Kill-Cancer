"""
Analysis pipeline job manager — orchestrates VCF upload, validation,
normalization, VEP annotation, and result storage.

Each job is tracked with status, timing, versioning, and provenance.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from src.backend.domain.enums import AnalysisStatusEnum, NormalizationStatusEnum
from src.backend.pipeline.normalization import BcftoolsAdapter, NormalizedVariant
from src.backend.pipeline.vep_adapter import VEPAdapter
from src.backend.pipeline.opencravat_adapter import OpenCRAVATAdapter

logger = logging.getLogger(__name__)


class AnalysisJob:
    """A single analysis pipeline execution.

    Orchestrates: validation → normalization → VEP annotation → storage.

    Each step updates the job status and provenance.
    """

    def __init__(
        self,
        job_id: str,
        case_id: str,
        sequencing_test_id: str,
        raw_variants: list[dict],
        pipeline_version: str = "0.3.0",
        git_commit: Optional[str] = None,
        normalization_adapter: Optional[BcftoolsAdapter] = None,
        vep_adapter: Optional[VEPAdapter] = None,
    ):
        self.job_id = job_id
        self.case_id = case_id
        self.sequencing_test_id = sequencing_test_id
        self.raw_variants = raw_variants
        self.pipeline_version = pipeline_version
        self.git_commit = git_commit or "unknown"

        # Adapters
        self._norm_adapter = normalization_adapter or BcftoolsAdapter()
        self._vep_adapter = vep_adapter or VEPAdapter()

        # Status tracking
        self.status = AnalysisStatusEnum.PENDING
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.duration_ms: Optional[int] = None
        self.warnings: list[str] = []
        self.errors: list[str] = []

        # Results
        self.normalized_variants: list[NormalizedVariant] = []
        self.annotation_results: list[dict] = []
        self.annotation_source: str = "not_annotated"

    async def run(self) -> None:
        """Execute the full analysis pipeline."""
        self.status = AnalysisStatusEnum.RUNNING
        self.started_at = datetime.now(timezone.utc)
        start_ms = int(time.time() * 1000)

        try:
            # Step 1: Normalization
            logger.info(f"[Job {self.job_id}] Starting normalization...")
            self.warnings.append("Normalization: " + ("bcftools" if self._norm_adapter.available else "Python fallback"))
            norm_result = await self._norm_adapter.annotate(
                [(v["chromosome"], v["position"], v["reference"], v["alternate"])
                 for v in self.raw_variants],
                request_id=self.job_id,
            )
            if not norm_result.success and not norm_result.records:
                self.errors.extend(norm_result.errors)
                self.status = AnalysisStatusEnum.FAILED
                return

            self.normalized_variants = []
            for r in norm_result.records:
                self.normalized_variants.append(NormalizedVariant(
                    chromosome=r.get("chromosome", ""),
                    position=r.get("position", 0),
                    reference=r.get("reference", ""),
                    alternate=r.get("alternate", ""),
                    original_position=r.get("original_position", 0),
                    original_reference=r.get("original_reference", ""),
                    original_alternate=r.get("original_alternate", ""),
                ))

            # Step 2: VEP Annotation
            logger.info(f"[Job {self.job_id}] Starting VEP annotation ({len(self.normalized_variants)} variants)...")
            vep_payload = {
                "variants": [
                    {"chromosome": nv.chromosome, "position": nv.position,
                     "reference": nv.reference, "alternate": nv.alternate}
                    for nv in self.normalized_variants
                ]
            }
            vep_result = await self._vep_adapter.annotate(vep_payload, request_id=self.job_id)
            if vep_result.success or vep_result.records:
                self.annotation_results = vep_result.records
                self.annotation_source = "ensembl_vep"
                if vep_result.warnings:
                    self.warnings.extend(vep_result.warnings)
            else:
                self.warnings.append("VEP annotation returned no results")
                if vep_result.errors:
                    self.warnings.extend(vep_result.errors)

            self.status = AnalysisStatusEnum.COMPLETED

        except Exception as e:
            logger.exception(f"[Job {self.job_id}] Pipeline failed")
            self.errors.append(f"Pipeline error: {e}")
            self.status = AnalysisStatusEnum.FAILED

        finally:
            self.finished_at = datetime.now(timezone.utc)
            self.duration_ms = int(time.time() * 1000) - start_ms
            logger.info(f"[Job {self.job_id}] Finished with status {self.status.value} "
                        f"in {self.duration_ms}ms")

    def get_provenance(self) -> dict:
        """Return full provenance for this analysis run."""
        return {
            "pipeline_version": self.pipeline_version,
            "normalization": {
                "method": "bcftools" if self._norm_adapter.available else "python_fallback",
                "bcftools_version": self._norm_adapter.version,
            },
            "vep": {
                "method": "ensembl_rest_api",
                "version": self._vep_adapter.version,
                "source_url": "https://rest.ensembl.org/vep/human/region",
            },
            "opencravat": {"status": "not_configured", "reason": "OpenCRAVAT not installed"},
            "git_commit": self.git_commit,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "record_count": len(self.raw_variants),
            "normalized_count": len(self.normalized_variants),
            "annotated_count": len(self.annotation_results),
        }


# In-memory job registry (for Phase 2A — will be replaced with DB-backed in Phase 2B)
_job_registry: dict[str, AnalysisJob] = {}


async def run_analysis_job(
    case_id: str,
    sequencing_test_id: str,
    raw_variants: list[dict],
    pipeline_version: str = "0.3.0",
    git_commit: Optional[str] = None,
) -> AnalysisJob:
    """Create and run an analysis job."""
    job_id = str(uuid.uuid4())
    job = AnalysisJob(
        job_id=job_id,
        case_id=case_id,
        sequencing_test_id=sequencing_test_id,
        raw_variants=raw_variants,
        pipeline_version=pipeline_version,
        git_commit=git_commit,
    )
    _job_registry[job_id] = job
    await job.run()
    return job


def get_analysis_job(job_id: str) -> Optional[AnalysisJob]:
    """Get a job by ID from the in-memory registry."""
    return _job_registry.get(job_id)
