"""
Analysis pipeline job manager — DB-backed persistence.

Orchestrates: validation → normalization → VEP annotation → result storage.

Each job persists to AnalysisRun in the database for durability.
In-memory registry serves as runtime cache only.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.domain.analysis_run import AnalysisRunModel
from src.backend.domain.enums import AnalysisStatusEnum, NormalizationStatusEnum, NormalizationMethodEnum, NormalizationSemanticsEnum
from src.backend.pipeline.normalization import BcftoolsAdapter, NormalizedVariant, normalize_minimal_representation
from src.backend.pipeline.vep_adapter import VEPAdapter
from src.backend.pipeline.opencravat_adapter import OpenCRAVATAdapter
from src.backend.repositories.analysis_run_repo import AnalysisRunRepository

logger = logging.getLogger(__name__)


class AnalysisJob:
    """A single analysis pipeline execution with DB persistence."""

    def __init__(
        self,
        job_id: str,
        case_id: str,
        sequencing_test_id: str,
        raw_variants: list[dict],
        db_session: AsyncSession,
        pipeline_version: str = "0.3.1",
        git_commit: Optional[str] = None,
        genome_build: Optional[str] = None,
        upload_id: Optional[str] = None,
        normalization_adapter: Optional[BcftoolsAdapter] = None,
        vep_adapter: Optional[VEPAdapter] = None,
    ):
        self.job_id = job_id
        self.case_id = case_id
        self.sequencing_test_id = sequencing_test_id
        self.raw_variants = raw_variants
        self.pipeline_version = pipeline_version
        self.git_commit = git_commit or "unknown"
        self.genome_build = genome_build
        self.upload_id = upload_id
        self.db_session = db_session

        # Adapters
        self._norm_adapter = normalization_adapter or BcftoolsAdapter()
        self._vep_adapter = vep_adapter or VEPAdapter()
        self._repo = AnalysisRunRepository(db_session)

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

        # Normalization provenance
        self.normalization_method: str = "not_applicable"
        self.normalization_semantics: str = "not_applicable"

    async def _save_status(self) -> None:
        """Persist current job status to database."""
        try:
            await self._repo.update(
                uuid.UUID(self.job_id),
                status=self.status.value,
                started_at=self.started_at,
                finished_at=self.finished_at,
                duration_ms=self.duration_ms,
                warnings=self.warnings,
                errors=self.errors,
                output_manifest=self._build_manifest(),
            )
        except Exception as e:
            logger.error(f"Failed to persist job status {self.job_id}: {e}")

    def _build_manifest(self) -> dict:
        """Build input/output manifest for this job."""
        return {
            "input": {
                "upload_id": self.upload_id,
                "sequencing_test_id": self.sequencing_test_id,
                "variant_count": len(self.raw_variants),
                "genome_build": self.genome_build,
            },
            "output": {
                "normalized_count": len(self.normalized_variants),
                "annotated_count": len(self.annotation_results),
                "normalization_method": self.normalization_method,
                "normalization_semantics": self.normalization_semantics,
                "annotation_source": self.annotation_source,
            },
            "provenance": {
                "pipeline_version": self.pipeline_version,
                "git_commit": self.git_commit,
                "bcftools_version": self._norm_adapter.version if hasattr(self._norm_adapter, 'version') else "unknown",
                "vep_version": self._vep_adapter.version,
            },
        }

    async def run(self) -> None:
        """Execute the full analysis pipeline."""
        self.status = AnalysisStatusEnum.RUNNING
        self.started_at = datetime.now(timezone.utc)
        start_ms = int(time.time() * 1000)

        try:
            # ── Step 1: Normalization ─────────────────────────────────────
            logger.info(f"[Job {self.job_id}] Starting normalization...")
            norm_result = await self._norm_adapter.annotate(
                [(v["chromosome"], v["position"], v["reference"], v["alternate"])
                 for v in self.raw_variants],
                request_id=self.job_id,
                genome_build=self.genome_build or "",
            )

            if norm_result.source in ("bcftools",):
                self.normalization_method = "bcftools_canonical"
                self.normalization_semantics = "canonical_with_reference"
            else:
                self.normalization_method = "minimal_representation"
                self.normalization_semantics = "minimal_representation_only"

            if not norm_result.success and not norm_result.records:
                self.errors.extend(norm_result.errors)
                self.status = AnalysisStatusEnum.FAILED
                self.finished_at = datetime.now(timezone.utc)
                self.duration_ms = int(time.time() * 1000) - start_ms
                await self._save_status()
                return

            # Store normalized variants
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
                    normalization_method=r.get("normalization_method", "unknown"),
                ))

            if norm_result.warnings:
                self.warnings.extend(norm_result.warnings)

            # ── Step 2: VEP Annotation ────────────────────────────────────
            logger.info(f"[Job {self.job_id}] Starting VEP annotation...")
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
                self.status = AnalysisStatusEnum.COMPLETED
            else:
                self.warnings.append("VEP annotation returned no results")
                self.status = AnalysisStatusEnum.PARTIAL
                if vep_result.errors:
                    self.warnings.extend(vep_result.errors)

        except Exception as e:
            logger.exception(f"[Job {self.job_id}] Pipeline failed")
            self.errors.append(f"Pipeline error: {e}")
            self.status = AnalysisStatusEnum.FAILED

        finally:
            self.finished_at = datetime.now(timezone.utc)
            self.duration_ms = int(time.time() * 1000) - start_ms
            await self._save_status()
            logger.info(f"[Job {self.job_id}] Finished status={self.status.value} "
                        f"duration={self.duration_ms}ms")

    def get_provenance(self) -> dict:
        """Return full provenance for this analysis run."""
        return {
            "pipeline_version": self.pipeline_version,
            "git_commit": self.git_commit,
            "genome_build": self.genome_build,
            "upload_id": self.upload_id,
            "normalization": {
                "method": self.normalization_method,
                "semantics": self.normalization_semantics,
                "bcftools_version": self._norm_adapter.version if hasattr(self._norm_adapter, 'version') else "unknown",
            },
            "vep": {
                "method": "ensembl_rest_api",
                "version": self._vep_adapter.version,
                "source_url": "https://rest.ensembl.org/vep/human/region",
            },
            "opencravat": {"status": "not_configured"},
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "record_count": {
                "input": len(self.raw_variants),
                "normalized": len(self.normalized_variants),
                "annotated": len(self.annotation_results),
            },
        }


# ─── Job Manager ──────────────────────────────────────────────────────────────

# In-memory cache only — source of truth is database
_job_cache: dict[str, AnalysisJob] = {}


async def create_and_run_job(
    case_id: str,
    sequencing_test_id: str,
    raw_variants: list[dict],
    db_session: AsyncSession,
    pipeline_version: str = "0.3.1",
    git_commit: Optional[str] = None,
    genome_build: Optional[str] = None,
    upload_id: Optional[str] = None,
) -> AnalysisJob:
    """Create an analysis run in DB, execute pipeline, return job."""
    job_id = str(uuid.uuid4())

    # Create DB record
    repo = AnalysisRunRepository(db_session)
    await repo.create(
        id=job_id,
        case_id=case_id,
        sequencing_test_id=sequencing_test_id,
        status=AnalysisStatusEnum.PENDING.value,
        pipeline_version=pipeline_version,
        git_commit=git_commit,
        input_manifest={
            "upload_id": upload_id,
            "variant_count": len(raw_variants),
            "genome_build": genome_build,
        },
    )

    # Create and run job
    job = AnalysisJob(
        job_id=job_id,
        case_id=case_id,
        sequencing_test_id=sequencing_test_id,
        raw_variants=raw_variants,
        db_session=db_session,
        pipeline_version=pipeline_version,
        git_commit=git_commit,
        genome_build=genome_build,
        upload_id=upload_id,
    )
    _job_cache[job_id] = job

    # Run pipeline
    await job.run()
    return job


async def load_job_from_db(job_id: str, db_session: AsyncSession) -> Optional[AnalysisJob]:
    """Load a job's status from database (without re-executing)."""
    # Check cache first
    if job_id in _job_cache:
        return _job_cache[job_id]

    # Load from DB
    repo = AnalysisRunRepository(db_session)
    try:
        record = await repo.get(uuid.UUID(job_id))
    except Exception:
        return None

    if record is None:
        return None

    # Create minimal job representation
    job = AnalysisJob(
        job_id=job_id,
        case_id=str(record.case_id) if record.case_id else "",
        sequencing_test_id=str(record.sequencing_test_id) if record.sequencing_test_id else "",
        raw_variants=[],
        db_session=db_session,
        pipeline_version=record.pipeline_version or "unknown",
        git_commit=record.git_commit,
    )
    job.status = record.status
    job.started_at = record.started_at
    job.finished_at = record.finished_at
    job.duration_ms = record.duration_ms
    job.warnings = list(record.warnings or [])
    job.errors = list(record.errors or [])
    _job_cache[job_id] = job
    return job


def get_cached_job(job_id: str) -> Optional[AnalysisJob]:
    """Get a job from runtime cache only."""
    return _job_cache.get(job_id)
