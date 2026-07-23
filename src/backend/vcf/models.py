"""
VCF-specific Pydantic models.
"""

from __future__ import annotations

from pydantic import BaseModel


class VCFUploadResponse(BaseModel):
    """Response after VCF file upload and initial validation."""
    upload_id: str
    database_record_id: str | None = None
    filename: str
    size_bytes: int
    sha256: str
    file_type: str | None = None
    compression: str | None = None
    genome_build: str | None = None
    genome_build_confidence: str | None = None
    validation_status: str  # "pending" | "valid" | "invalid"
    analysis_eligible: str | None = None
    record_count: int = 0
    warnings: list[str] = []
    errors: list[str] = []
    created_at: str = ""
